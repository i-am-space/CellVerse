from pykeen.pipeline import pipeline
from pykeen.triples import TriplesFactory
import os
import torch
import json

# Load triples and split them into training/testing sets
triples_factory = TriplesFactory.from_path("kg_triples.tsv")
training, testing = triples_factory.split(random_state=42)

# Run the training pipeline
result = pipeline(
    training=training,
    testing=testing,
    model="TransE",
    model_kwargs={"embedding_dim": 128},
    training_kwargs={"num_epochs": 100, "batch_size": 128},
    optimizer="adam",
    optimizer_kwargs={"lr": 1e-3},
    evaluator_kwargs={"filtered": True}
)

# Save the trained model and triples factory
os.makedirs("trained_model", exist_ok=True)
result.save_to_directory("trained_model")

# Save the triples factory explicitly
torch.save(training, os.path.join("trained_model", "training_triples.pt"))
torch.save(testing, os.path.join("trained_model", "testing_triples.pt"))
torch.save(triples_factory, os.path.join("trained_model", "triples_factory.pt"))

# Save entity and relation mappings for later use in prediction
with open(os.path.join("trained_model", "entity_to_id.json"), "w") as f:
    json.dump(triples_factory.entity_to_id, f)

with open(os.path.join("trained_model", "relation_to_id.json"), "w") as f:
    json.dump(triples_factory.relation_to_id, f)

print("✅ Model and triples factory saved to 'trained_model' directory")
print(f"Number of entities: {triples_factory.num_entities}")
print(f"Number of relations: {triples_factory.num_relations}")
