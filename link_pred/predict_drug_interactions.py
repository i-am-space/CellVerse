import os
import torch
import json
import pandas as pd
import numpy as np
from pykeen.triples import TriplesFactory
from tqdm import tqdm
from neo4j import GraphDatabase
from pykeen.pipeline import PipelineResult
from pykeen.models import TransE

# Neo4j connection parameters
URI = "neo4j+s://7ab56458.databases.neo4j.io"
AUTH = ("neo4j", "v3rSbGYUTwCHLJIUJ3TB9S_Ug4Q3VAJup_pY5like0o")
driver = GraphDatabase.driver(URI, auth=AUTH)

# Load the trained model and triples factory
model_directory = "trained_model"

# Manual model loading approach since metadata.json is empty
try:
    print("Loading model components manually...")
    
    # Load triples factory with weights_only=False
    triples_factory = torch.load(os.path.join(model_directory, "triples_factory.pt"), weights_only=False)
    
    # Check for trained_model.pt
    if os.path.exists(os.path.join(model_directory, "trained_model.pt")):
        state_dict_path = os.path.join(model_directory, "trained_model.pt")
        print(f"Found state dict at {state_dict_path}")
        model_state_dict = torch.load(state_dict_path, weights_only=False)
        
        # Create model with the same configuration as used in training
        model = TransE(
            triples_factory=triples_factory,
            embedding_dim=128  # Same value used in your training
        )
        
        # Load the trained weights
        model.load_state_dict(model_state_dict)
        print("Successfully loaded TransE model from state dictionary")
    else:
        # Try to load the pickle file directly with weights_only=False
        model = torch.load(os.path.join(model_directory, "trained_model.pkl"), weights_only=False)
        print("Successfully loaded model from pickle file")
        
except Exception as e:
    print(f"Error loading model manually: {e}")
    print("Trying to construct a new TransE model...")
    
    # Load just the triples factory
    triples_factory = torch.load(os.path.join(model_directory, "triples_factory.pt"), weights_only=False)
    
    # Create a new TransE model with the same dimensions as your training
    model = TransE(
        triples_factory=triples_factory,
        embedding_dim=128  # Same value used in your training
    )
    print("Created new TransE model - NOTE: This model is NOT trained")

# Load entity and relation mappings
with open(os.path.join(model_directory, "entity_to_id.json"), "r") as f:
    entity_to_id = json.load(f)

with open(os.path.join(model_directory, "relation_to_id.json"), "r") as f:
    relation_to_id = json.load(f)

id_to_entity = {v: k for k, v in entity_to_id.items()}

# Get all drugs from Neo4j
def get_drugs():
    with driver.session() as session:
        result = session.run("MATCH (d:Drug) RETURN d.name AS drug_name")
        return [record["drug_name"] for record in result]

# Get existing interactions
def get_existing_interactions():
    with driver.session() as session:
        result = session.run(
            "MATCH (d1:Drug)-[:INTERACTS_WITH]->(d2:Drug) RETURN d1.name AS drug1, d2.name AS drug2"
        )
        return {(record["drug1"], record["drug2"]) for record in result}

# Get all drugs
all_drugs = get_drugs()
print(f"Found {len(all_drugs)} drugs in the knowledge graph")

# Filter to only include drugs that are in our entity_to_id mapping
valid_drugs = [drug for drug in all_drugs if drug in entity_to_id]
print(f"{len(valid_drugs)} drugs found in the trained model")

# Get existing interactions to exclude
existing_interactions = get_existing_interactions()
print(f"Found {len(existing_interactions)} existing drug-drug interactions to exclude")

# Get relation ID for INTERACTS_WITH
interaction_rel_id = relation_to_id.get("INTERACTS_WITH")
if interaction_rel_id is None:
    raise ValueError("INTERACTS_WITH relation not found in the trained model")

# Generate all possible drug-drug pairs to evaluate
pairs_to_check = []
for i, drug1 in enumerate(valid_drugs):
    for drug2 in valid_drugs[i+1:]:  # Avoid self-interactions and duplicates
        # Skip if interaction already exists
        if (drug1, drug2) in existing_interactions or (drug2, drug1) in existing_interactions:
            continue
        
        # Ensure we're not checking self-interactions
        if drug1 == drug2:
            continue
            
        if drug1 in entity_to_id and drug2 in entity_to_id:
            pairs_to_check.append((drug1, drug2))

print(f"Generated {len(pairs_to_check)} potential drug-drug interaction pairs to evaluate")

# Predict and rank potential interactions
results = []
batch_size = 1000  # Process in batches to avoid memory issues

for i in range(0, len(pairs_to_check), batch_size):
    batch = pairs_to_check[i:i+batch_size]
    batch_triples = []
    
    for drug1, drug2 in batch:
        # Convert names to IDs
        head_id = entity_to_id[drug1]
        tail_id = entity_to_id[drug2]
        
        # Add the triple to evaluate
        batch_triples.append((head_id, interaction_rel_id, tail_id))
    
    # Convert to tensor
    batch_tensor = torch.tensor(batch_triples, dtype=torch.long)
    
    # Get scores from the model
    with torch.no_grad():
        scores = model.score_hrt(batch_tensor)
    
    # Add results to our list
    for j, (drug1, drug2) in enumerate(batch):
        results.append({
            "drug1": drug1,
            "drug2": drug2,
            "score": scores[j].item()
        })

# Remove any duplicates from results before creating DataFrame
unique_pairs = set()
unique_results = []

for result in results:
    pair = tuple(sorted([result["drug1"], result["drug2"]]))
    if pair not in unique_pairs:
        unique_pairs.add(pair)
        unique_results.append(result)

# Sort by score (higher score = more likely interaction)
results_df = pd.DataFrame(unique_results)
results_df = results_df.sort_values(by="score", ascending=False)

# Save top predictions
top_n = min(1000, len(results_df))
results_df.head(top_n).to_csv("predicted_drug_interactions.csv", index=False)

print(f"✅ Top {top_n} predicted drug-drug interactions saved to 'predicted_drug_interactions.csv'")
print("Top 10 predicted interactions:")
print(results_df.head(10))
