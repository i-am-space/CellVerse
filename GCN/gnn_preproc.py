# Re-run after reset
import pandas as pd
import torch
import json
from collections import defaultdict
from sklearn.preprocessing import LabelEncoder

# Load your triples
triples_path = "kg_triples.tsv"
df = pd.read_csv(triples_path, sep="\t", header=None, names=["head", "relation", "tail"])

# Step 1: Encode entities and relations
entity_encoder = LabelEncoder()
relation_encoder = LabelEncoder()

all_entities = pd.concat([df['head'], df['tail']])
entity_encoder.fit(all_entities)
relation_encoder.fit(df['relation'])

df['head_id'] = entity_encoder.transform(df['head'])
df['tail_id'] = entity_encoder.transform(df['tail'])
df['rel_id'] = relation_encoder.transform(df['relation'])

# Step 2: Construct edge index and edge type
edge_index = torch.tensor(df[['head_id', 'tail_id']].values.T, dtype=torch.long)  # shape [2, num_edges]
edge_type = torch.tensor(df['rel_id'].values, dtype=torch.long)  # shape [num_edges]

# Step 3: Save entity/relation maps and edge data for GNN use
data_path = "gnn_data"
entity_map = dict(zip(entity_encoder.classes_, entity_encoder.transform(entity_encoder.classes_)))
relation_map = dict(zip(relation_encoder.classes_, relation_encoder.transform(relation_encoder.classes_)))

entity_map = {k: int(v) for k, v in entity_map.items()}
relation_map = {k: int(v) for k, v in relation_map.items()}


torch.save(edge_index, f"{data_path}_edge_index.pt")
torch.save(edge_type, f"{data_path}_edge_type.pt")
with open(f"{data_path}_entity_map.json", "w") as f:
    json.dump(entity_map, f, indent=2)
with open(f"{data_path}_relation_map.json", "w") as f:
    json.dump(relation_map, f, indent=2)

data_path
