# Re-run with correct local fallback paths based on uploaded context

import pandas as pd
import json
import os

# Adjusted path (user runs this in local VSCode setup)
triples = pd.read_csv("kg_triples.tsv", sep="\t", header=None, names=["head", "relation", "tail"])

# Load entity map (fixed path name)
with open("gnn_data/entity_map.json") as f:
    entity_map = json.load(f)

# Count ADRs and interactions per drug
adr_counts = {drug: 0 for drug in entity_map}
interact_counts = {drug: 0 for drug in entity_map}

for _, row in triples.iterrows():
    if row["relation"] == "CAUSES_ADR" and row["head"] in adr_counts:
        adr_counts[row["head"]] += 1
    elif row["relation"] == "INTERACTS_WITH" and row["head"] in interact_counts:
        interact_counts[row["head"]] += 1

# Assign risk levels
safety_labels = {}
for drug in entity_map:
    total_risk = adr_counts.get(drug, 0) + interact_counts.get(drug, 0)
    if total_risk >= 4:
        safety_labels[drug] = 2  # High risk
    elif total_risk >= 2:
        safety_labels[drug] = 1  # Medium risk
    elif total_risk >= 0:
        safety_labels[drug] = 0  # Low risk

# Map back to node indices
node_label_map = {entity_map[drug]: label for drug, label in safety_labels.items() if drug in entity_map}

# Save
os.makedirs("gnn_data", exist_ok=True)
with open("gnn_data/safety_node_labels.json", "w") as f:
    json.dump(node_label_map, f, indent=2)

print(f"✅ Created {len(node_label_map)} safety-labeled nodes.")
node_label_map
