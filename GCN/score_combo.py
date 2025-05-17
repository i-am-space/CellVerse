from neo4j import GraphDatabase
import torch
import torch.nn as nn
import torch.nn.functional as F
import json
from torch_geometric.nn import RGCNConv

# === Load graph tensors ===
edge_index = torch.load("gnn_data/edge_index.pt")
edge_type = torch.load("gnn_data/edge_type.pt")

with open("gnn_data/entity_map.json") as f:
    entity_map = json.load(f)

num_nodes = len(entity_map)
x = torch.eye(num_nodes)

# === Define RGCN ===
class RGCN(nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels, num_relations):
        super().__init__()
        self.conv1 = RGCNConv(in_channels, hidden_channels, num_relations, num_bases=30)
        self.conv2 = RGCNConv(hidden_channels, out_channels, num_relations, num_bases=30)

    def forward(self, x, edge_index, edge_type):
        x = self.conv1(x, edge_index, edge_type)
        x = F.relu(x)
        return self.conv2(x, edge_index, edge_type)

# === Load trained GCN model ===
model = RGCN(
    in_channels=num_nodes,
    hidden_channels=64,
    out_channels=64,
    num_relations=int(edge_type.max().item()) + 1
)
model.load_state_dict(torch.load("gnn_data/gnn_rgcn_model.pt"), strict=False)
model.eval()

with torch.no_grad():
    node_embeddings = model(x, edge_index, edge_type)

# === Load safety classifier ===
safety_clf = nn.Sequential(
    nn.Linear(64, 64),
    nn.ReLU(),
    nn.Linear(64, 3)
)
safety_clf.load_state_dict(torch.load("gnn_data/safety_classifier.pt"))
safety_clf.eval()

# === Neo4j Setup ===
URI = "neo4j+s://7ab56458.databases.neo4j.io"
AUTH = ("neo4j", "v3rSbGYUTwCHLJIUJ3TB9S_Ug4Q3VAJup_pY5like0o")
driver = GraphDatabase.driver(URI, auth=AUTH)

def get_explanation(drug):
    query = """
    MATCH (d:Drug {name: $drug})
    OPTIONAL MATCH (d)-[:CAUSES_ADR]->(a:SideEffect)
    OPTIONAL MATCH (d)-[:INTERACTS_WITH]->(d2:Drug)-[:CAUSES_ADR]->(a2:SideEffect)
    RETURN d.name AS drug,
           collect(DISTINCT a.name) AS direct_adrs,
           collect(DISTINCT d2.name) AS interacting_drugs,
           collect(DISTINCT a2.name) AS adrs_from_interactions
    """
    with driver.session() as session:
        record = session.run(query, drug=drug).single()
        return {
            "drug": record["drug"],
            "direct_adrs": [x for x in record["direct_adrs"] if x],
            "interacting_drugs": [x for x in record["interacting_drugs"] if x],
            "adrs_from_interactions": [x for x in record["adrs_from_interactions"] if x]
        }

def format_explanation(info):
    parts = []
    if info["direct_adrs"]:
        parts.append(f"• Direct ADRs: {', '.join(info['direct_adrs'])}")
    if info["interacting_drugs"]:
        parts.append(f"• Interacts with: {', '.join(info['interacting_drugs'])}")
    if info["adrs_from_interactions"]:
        parts.append(f"• Indirect ADRs: {', '.join(info['adrs_from_interactions'])}")
    return "\n".join(parts) if parts else "No ADR or interaction data found."

def score_combo(drug_list):
    valid_ids = [entity_map[d] for d in drug_list if d in entity_map]
    if not valid_ids:
        return {"error": "None of the drugs are in the KG."}

    combo_embedding = torch.mean(node_embeddings[valid_ids], dim=0, keepdim=True)
    with torch.no_grad():
        logits = safety_clf(combo_embedding)
        probs = torch.softmax(logits, dim=1).squeeze().tolist()
        risk_class = ["Low", "Medium", "High"][torch.argmax(logits).item()]

    explanations = {d: format_explanation(get_explanation(d)) for d in drug_list if d in entity_map}

    return {
        "combination": drug_list,
        "risk_class": risk_class,
        "probabilities": {
            "low": round(probs[0], 3),
            "medium": round(probs[1], 3),
            "high": round(probs[2], 3)
        },
        "explanations": explanations
    }

# Example
if __name__ == "__main__":
    result = score_combo(["Carfilzomib", "Dexamethasone", "Lenalidomide"])
    print("\n=== Risk Prediction ===")
    print(f"Risk Class: {result['risk_class']}")
    print(f"Probabilities: {result['probabilities']}")
    print("\n=== Explanation ===")
    for drug, exp in result["explanations"].items():
        print(f"\n🔹 {drug}\n{exp}")
