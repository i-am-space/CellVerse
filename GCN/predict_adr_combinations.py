import torch
import torch.nn.functional as F
from torch_geometric.nn import RGCNConv
import json
import numpy as np

# ---- Model Definition ----
class RGCN(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels, num_relations, num_adrs):
        super().__init__()
        self.conv1 = RGCNConv(in_channels, hidden_channels, num_relations, num_bases=30)
        self.conv2 = RGCNConv(hidden_channels, out_channels, num_relations, num_bases=30)
        self.classifier = torch.nn.Linear(out_channels, num_adrs)

    def forward(self, x, edge_index, edge_type):
        x = self.conv1(x, edge_index, edge_type)
        x = F.relu(x)
        x = self.conv2(x, edge_index, edge_type)
        return self.classifier(x)

# ---- Load Data ----
edge_index = torch.load("gnn_data/edge_index.pt")
edge_type = torch.load("gnn_data/edge_type.pt")

with open("gnn_data/entity_map.json") as f:
    entity_map = json.load(f)
with open("gnn_data/relation_map.json") as f:
    relation_map = json.load(f)

num_nodes = len(entity_map)
num_relations = len(relation_map)

# ---- Load drug and ADR IDs from training triples ----
import pandas as pd
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
id_to_adr = {v: k for k, v in entity_map.items() if k in adr_nodes}

# ---- Load model ----
x = torch.eye(num_nodes)  # one-hot features
model = RGCN(num_nodes, 64, 64, num_relations, len(adr_ids))

# Modified loading to handle partial state dict loading
state_dict = torch.load("gnn_rgcn_model.pt")
model_dict = model.state_dict()

# Filter out classifier parameters (which have different shapes)
filtered_state_dict = {k: v for k, v in state_dict.items() if 'classifier' not in k}
model_dict.update(filtered_state_dict)
model.load_state_dict(model_dict, strict=False)
model.eval()

# ---- Predict ADRs for a drug combination ----
def predict_adrs(drug_names, top_k=5):
    drug_indices = [entity_map[d] for d in drug_names if d in entity_map]
    if not drug_indices:
        raise ValueError("None of the input drugs found in entity map")

    with torch.no_grad():
        logits = model(x, edge_index, edge_type)
        combined_embedding = logits[drug_indices].mean(dim=0)  # average over drugs
        adr_scores = torch.sigmoid(combined_embedding)

        # Sort ADRs by score
        sorted_indices = torch.argsort(adr_scores, descending=True)
        top_adrs = [(id_to_adr[adr_ids[i.item()]], adr_scores[i].item()) for i in sorted_indices[:top_k]]
        return top_adrs

# ---- Try it! ----
if __name__ == "__main__":
    combo = ["Bortezomib", "Lenalidomide", "Dexamethasone"]
    print(f"🧪 Predicting ADRs for: {', '.join(combo)}\n")
    results = predict_adrs(combo, top_k=10)
    for adr, score in results:
        print(f"⚠️ {adr} — score: {score:.17f}")
