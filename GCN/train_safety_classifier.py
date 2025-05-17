import torch
import torch.nn as nn
import torch.nn.functional as F
import json
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# --- Load Graph Embeddings ---
# Assume one-hot features used during GCN training
num_nodes = 39  # Number of nodes in the graph
x = torch.eye(39)

edge_index = torch.load("gnn_data/edge_index.pt")
edge_type = torch.load("gnn_data/edge_type.pt")

# --- Load Entity Map ---
with open("gnn_data/entity_map.json") as f:
    entity_map = json.load(f)

# --- Load Safety Labels ---
with open("gnn_data/safety_node_labels.json") as f:
    node_label_map = json.load(f)
node_label_map = {int(k): v for k, v in node_label_map.items()}

# --- Load Trained GCN Model ---
from torch_geometric.nn import RGCNConv

class RGCN(nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels, num_relations, num_adrs):
        super().__init__()
        self.conv1 = RGCNConv(in_channels, hidden_channels, num_relations, num_bases=30)
        self.conv2 = RGCNConv(hidden_channels, out_channels, num_relations, num_bases=30)
        self.classifier = nn.Linear(out_channels, num_adrs)

    def forward(self, x, edge_index, edge_type):
        x = self.conv1(x, edge_index, edge_type)
        x = F.relu(x)
        x = self.conv2(x, edge_index, edge_type)
        return self.classifier(x)

# Load triples to determine ADR count
import pandas as pd
triples = pd.read_csv("kg_triples.tsv", sep="\t", header=None, names=["head", "relation", "tail"])

adr_nodes = set()
for _, row in triples.iterrows():
    if row["relation"] == "CAUSES_ADR":
        if row["tail"] in entity_map:
            adr_nodes.add(row["tail"])

# Determine the correct number of ADRs from the trained model
model = RGCN(
    in_channels=x.shape[1],
    hidden_channels=64,
    out_channels=64,
    num_relations=int(edge_type.max().item()) + 1,
    num_adrs=len(adr_nodes)  # Use the actual number of ADRs instead of hardcoded 3
)

# Modified loading to handle partial state dict loading
state_dict = torch.load("gnn_data/gnn_rgcn_model.pt")
model_dict = model.state_dict()

# Filter out classifier parameters (which have different shapes)
filtered_state_dict = {k: v for k, v in state_dict.items() if 'classifier' not in k}
model_dict.update(filtered_state_dict)
model.load_state_dict(model_dict, strict=False)
model.eval()

with torch.no_grad():
    h1 = model.conv1(x, edge_index, edge_type)
    h2 = F.relu(h1)
    embeddings = model.conv2(h2, edge_index, edge_type)

# --- Prepare Data ---
all_ids = list(node_label_map.keys())
all_labels = [node_label_map[i] for i in all_ids]
X = embeddings[all_ids]
y = torch.tensor(all_labels)

train_X, test_X, train_y, test_y = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

# --- Classifier ---
clf = nn.Sequential(
    nn.Linear(X.shape[1], 64),
    nn.ReLU(),
    nn.Linear(64, 3)
)

optimizer = torch.optim.Adam(clf.parameters(), lr=1e-2)
loss_fn = nn.CrossEntropyLoss()

# --- Training Loop ---
for epoch in range(1, 101):
    clf.train()
    optimizer.zero_grad()
    out = clf(train_X)
    loss = loss_fn(out, train_y)
    loss.backward()
    optimizer.step()

    if epoch % 10 == 0:
        clf.eval()
        with torch.no_grad():
            preds = torch.argmax(clf(test_X), dim=1)
            acc = (preds == test_y).float().mean().item()
            print(f"Epoch {epoch:03d} | Loss: {loss.item():.4f} | Accuracy: {acc:.4f}")

# --- Evaluation ---
clf.eval()
with torch.no_grad():
    final_preds = torch.argmax(clf(test_X), dim=1)
    print("\n" + classification_report(test_y, final_preds, target_names=["Low", "Medium", "High"]))
# --- Save the classifier ---
torch.save(clf.state_dict(), "gnn_data/safety_classifier.pt")
print("✅ Classifier saved to gnn_data/safety_classifier.pt")

