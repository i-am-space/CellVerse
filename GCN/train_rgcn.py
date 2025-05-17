import torch
import torch.nn.functional as F
from torch.nn import Linear
from torch_geometric.nn import RGCNConv
from torch_geometric.data import Data
import json
import numpy as np
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split
import pandas as pd

# --- Load Graph Data ---
edge_index = torch.load("gnn_data/edge_index.pt")
edge_type = torch.load("gnn_data/edge_type.pt")

with open("gnn_data/entity_map.json") as f:
    entity_map = json.load(f)
with open("gnn_data/relation_map.json") as f:
    relation_map = json.load(f)

num_nodes = len(entity_map)
num_relations = len(relation_map)

# --- Build ADR Labels ---
# Build multi-label Y: each row is a drug, columns are ADRs
# Use CAUSES_ADR edges to determine drug and ADR nodes
triples = pd.read_csv("kg_triples.tsv", sep="\t", header=None, names=["head", "relation", "tail"])

drug_nodes = set()
adr_nodes = set()

for _, row in triples.iterrows():
    if row["relation"] == "CAUSES_ADR":
        if row["head"] in entity_map and row["tail"] in entity_map:
            drug_nodes.add(row["head"])
            adr_nodes.add(row["tail"])

drug_ids = [entity_map[d] for d in drug_nodes]
adr_ids = [entity_map[a] for a in adr_nodes]

# Initialize binary label matrix
Y = torch.zeros((num_nodes, len(adr_ids)))

# Load triples to find CAUSES_ADR edges
import pandas as pd
triples = pd.read_csv("kg_triples.tsv", sep="\t", header=None, names=["head", "relation", "tail"])

for _, row in triples.iterrows():
    if row['relation'] == "CAUSES_ADR":
        drug_id = entity_map.get(row['head'])
        adr_id = entity_map.get(row['tail'])
        if drug_id is not None and adr_id in adr_ids:
            col_index = adr_ids.index(adr_id)
            Y[drug_id, col_index] = 1

# --- R-GCN Model ---
class RGCN(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels, num_relations):
        super().__init__()
        self.conv1 = RGCNConv(in_channels, hidden_channels, num_relations, num_bases=30)
        self.conv2 = RGCNConv(hidden_channels, out_channels, num_relations, num_bases=30)
        self.classifier = Linear(out_channels, len(adr_ids))

    def forward(self, x, edge_index, edge_type):
        x = self.conv1(x, edge_index, edge_type)
        x = F.relu(x)
        x = self.conv2(x, edge_index, edge_type)
        return self.classifier(x)

# Dummy node features (could replace with embeddings)
x = torch.eye(num_nodes)

# Train/test split (on drug nodes)
train_ids, test_ids = train_test_split(drug_ids, test_size=0.2, random_state=42)

# Model, optimizer
model = RGCN(num_nodes, 64, 64, num_relations)
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
loss_fn = torch.nn.BCEWithLogitsLoss()

# Training loop
for epoch in range(1, 101):
    model.train()
    optimizer.zero_grad()
    out = model(x, edge_index, edge_type)
    loss = loss_fn(out[train_ids], Y[train_ids])
    loss.backward()
    optimizer.step()
    
    if epoch % 10 == 0:
        model.eval()
        with torch.no_grad():
            logits = model(x, edge_index, edge_type)
            preds = torch.sigmoid(logits[test_ids]) > 0.5
            correct = (preds == Y[test_ids]).float()
            acc = correct.mean().item()
            print(f"Epoch {epoch:03d} | Loss: {loss.item():.4f} | Test Acc: {acc:.4f}")

# Save model
torch.save(model.state_dict(), "gnn_data/gnn_rgcn_model.pt")

# Also save metadata about the model structure
model_metadata = {
    "num_adrs": len(adr_ids),
    "adr_ids": adr_ids,
    "num_nodes": num_nodes,
    "num_relations": num_relations
}
import json
with open("gnn_data/model_metadata.json", "w") as f:
    json.dump(model_metadata, f)
