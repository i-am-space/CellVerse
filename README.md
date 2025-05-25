# MediMatch: A Graph-Based Clinical Safety Intelligence System

> **Special Jury Engineering Award Winner @ CellVerse Docathon**<br>
> Built in 3 days by a sleep-deprived second-year CS undergrad, selected from among 50+ teams of professionals (doctors + engineers)

---

## Overview

MediMatch is an intelligent, explainable, graph-based system that predicts the **risk and adverse outcomes of multi-drug combinations** in complex diseases, starting with **Multiple Myeloma**. By combining **Neo4j-powered knowledge graphs**, **GNN-based embedding models**, and **ML classifiers**, this project transforms drug safety from static, rule-based checklists into a dynamic, predictive decision support engine.

---

## Motivation

Despite the wide availability of drug interaction checkers, most systems are:

* Rule-based and reactive
* Unable to handle complex combinations (3+ drugs)
* Not contextualized to patient conditions or evolving biomedical knowledge

MediMatch is built to address:

* Unseen or unreported adverse drug interactions
* Multi-relational reasoning across drugs, ADRs, proteins, and conditions
* Interpretability and clinical context

---

## Key Features

| Component                              | Description                                                                         |
| -------------------------------------- | ----------------------------------------------------------------------------------- |
| **Knowledge Graph (Neo4j)**            | Structured representation of drugs, targets, adverse effects, and interactions      |
| **R-GCN Embedding**                    | Learns node embeddings from KG structure and relation types                         |
| **Safety Classifier (MLP)**            | Classifies drug combinations as Low, Medium, or High risk                           |
| **Link Prediction (TransE)**           | Predicts potential drug-drug interactions not present in current KG                 |
| **ADR Path Reasoning**                 | Uses Cypher queries to explain which ADRs are implicated in a drug combo            |
| **Web App Interface**                  | Select disease, choose drugs, and get back risk + explanation in a user-friendly UI |
| **KG Enrichment via PubMed** | Upload articles, convert to Cypher via LLM, expand the KG                           |

---

## 🗂️ Repository Structure

```
.
├── drug_data/                # JSON definitions of core drugs and patient risk factors
├── enrich/                   # PubMed KG enrichment via LLM
│   ├── text2cypher_enricher.py
│   └── schema_builder.py
├── GCN/                      # Graph data processing and training
│   ├── gnn_preproc.py        # Converts KG triples into PyG-compatible tensors
│   ├── train_rgcn.py         # Trains the R-GCN model
│   ├── train_safety_classifier.py # MLP classifier on node embeddings
│   ├── predict_adr_combinations.py # Reasoning over ADRs
│   ├── safety_labels.py      # Generates node risk labels
│   └── gnn_data/             # Saved PyTorch tensors, models, and mappings
├── link_pred/                # Link prediction models
│   ├── link_prediction.py    # PyKEEN TransE training
│   ├── predict_drug_interactions.py
│   └── predicted_drug_interactions.csv
├── webapp/                   # Web interface
│   ├── app.py                # Flask server entry point (to be added)
│   ├── explain_drug_safety.py
│   ├── neo4j_importer.py     # KG construction from JSON
│   ├── kg_to_tsv.py          # Converts JSON to triple TSV
│   └── Neo4j_creds.txt       # AuraDB credentials
└── kg_triples.tsv            # Final exported triples used across all models
```

---

## ⚙️ How It Works

### Step 1: 🧱 KG Construction

* JSON files contain curated drug data: drug name, ADRs, interactions, targets
* `neo4j_importer.py` wipes and imports this into Neo4j as a clean graph
* Output: An explorable KG in Neo4j AuraDB

### Step 2: 🔁 Preprocessing

* `gnn_preproc.py` reads the KG as triples and creates:

  * `edge_index.pt`, `edge_type.pt` → GNN inputs
  * `entity_map.json` → node name → ID mapping

### Step 3: 🔬 R-GCN Embedding

* `train_rgcn.py` trains a 2-layer **Relational Graph Convolutional Network**

  * Learns embeddings for every node based on structure + relations
* Saved to: `gnn_rgcn_model.pt`

### Step 4: 🧪 Safety Classification

* `safety_labels.py` assigns nodes a safety label (0 = low, 1 = medium, 2 = high) using heuristic overlap with ADRs
* `train_safety_classifier.py` trains a small MLP on top of node embeddings
* Outputs classification: risk level for a single drug or combination

### Step 5: 🔗 Link Prediction

* `link_prediction.py` trains a TransE model (via PyKEEN) on triples
* `predict_drug_interactions.py` scores all drug pairs not already in KG
* Predicts future/hidden interactions → usable in KG or as suggestions

### Step 6: 🧠 ADR Reasoning

* `predict_adr_combinations.py` explores all paths between selected drugs and ADRs
* Uses Neo4j Cypher queries to construct:

  > "Drug A interacts with Drug B which causes ADR X"

### Step 7: 🌐 Web Interface

* `/` → Home page with buttons for diseases and upload PDF (planned)
* `/multiple_myeloma` → lets users select drugs from available KG
* `/results` → calls `score_combo.py` and `explain_drug_safety.py` to:

  * Predict safety classification
  * Return top ADRs implicated with explanations

---

## 🩺 Real-World Applications

### 👩‍⚕️ For Clinicians

* Get **personalized risk** estimates for drug combinations
* Understand **why** a combination may be risky (target → ADR tracing)
* Aid in oncology or polypharmacy treatment planning

### 🧪 For Pharma Researchers

* Identify **under-reported** or **emerging** ADR signals
* Explore interaction paths between experimental drugs and known side effects
* Integrate PubMed enrichment for **literature-aware KG**

---

## 🏆 Recognition

This project was submitted to the **CellVerse Docathon**, a prestigious 3-week hackathon bringing together over 50 teams of clinicians and engineers to tackle biomedical problems.

* 🥇 **Award**: Special Jury Prize for Engineering Excellence
* 🧑‍💻 **Built**: Entire KG pipeline, 3 models, and web integration in **under 3 days** by a second-year undergraduate

---

## 📌 Future Work

* PubMed PDF ingestion with Text2Cypher LLM
* Node-level uncertainty quantification
* Disease generalization: support for other cancers, chronic illnesses
* Integration with FAERS/EHR data for external benchmarking
* Frontend improvements for mobile and tablet support

---

## 🛠 Requirements

```
pytorch
pykeen
torch_geometric
sklearn
neo4j
py2neo
flask
openai (for text enrichment)
pandas, tqdm
```

---

## 🙌 Acknowledgments

* Neo4j AuraDB (Graph platform)
* PyKEEN (link prediction engine)
* PyTorch Geometric (GNN training)
* CellVerse Organizers and Jury
