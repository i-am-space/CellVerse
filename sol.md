## Project Implementation Plan

**Title:** *Knowledge Graph–Based Predictive System for Adverse Drug Interactions in Multiple Myeloma*
**Updated Objective:**
To construct a biomedical knowledge graph from structured and unstructured sources to enable **predictive modeling for adverse drug interactions**, focusing on:

* **Link Prediction** to identify undocumented interactions
* **Node Classification** to assess safety likelihood of drugs in multiple myeloma combination therapies

---

## 🔧 Step-by-Step Breakdown of Tasks and Modules

### 🔹 **1. Data Acquisition and Structuring**

**Tasks:**

* Collect drug data for 5 core drugs used in multiple myeloma: *Carfilzomib, Lenalidomide, Dexamethasone, Bortezomib, Cyclophosphamide*
* Parse structured label data (e.g., from DailyMed) to extract:

  * Adverse reactions
  * Interactions
  * Indications
  * Target proteins

**Module:** `drug_data_parser.py`
**Output:** Standardized JSON files (1 per drug)

---

### 🔹 **2. Knowledge Graph Construction in Neo4j**

**Tasks:**

* Define a consistent schema (`Drug`, `Protein`, `SideEffect`, `Condition`, `Disease`)
* Define relationships (`INTERACTS_WITH`, `CAUSES_ADR`, `TARGETS`, `ELEVATES_RISK_FOR`, `INDICATED_FOR`, etc.)
* Implement a graph ingestion pipeline using the Neo4j driver
* Include a graph reset feature for rebuilds

**Module:** `neo4j_importer.py`
**Core Functionality:**

* Constructs the base graph from structured JSON data
* Creates a navigable biomedical ontology in Neo4j

---

### 🔹 **3. Patient-Specific Risk Factor Integration**

**Tasks:**

* Build a separate patient risk factor module to integrate:

  * `Condition` nodes (e.g., Hypertension, CKD)
  * Links from conditions to side effects (`ELEVATES_RISK_FOR`)
* Ensure risk factors match existing adverse effect nodes (no duplication)

**Enhancement to Module:** `neo4j_importer.py`
**Core Functionality:**

* Enables risk-aware interaction modeling for specific patient populations

---

### 🔹 **4. Literature Mining & Knowledge Graph Enrichment (NLP)**

**Tasks:**

* Automate search and download of PubMed abstracts using E-Utilities
* Use **PubTator** to annotate entities: drugs, diseases, ADRs, proteins
* Extract semantic triplets (subject–relation–object) and ingest into KG
* Normalize new entities using ontologies (RxNorm, MeSH)

**Module:** `literature_miner.py`
**Core Functionality:**

* Enriches KG with real-world biomedical knowledge
* Expands relational coverage beyond structured drug labels

---

### 🔹 **5. Graph Export for Modeling**

**Tasks:**

* Query Neo4j to export the full KG as `(head, relation, tail)` triples
* Format data for PyKEEN (link prediction) and PyTorch Geometric (node classification)

**Script:** `export_kg_to_tsv.py`
**Output:** `kg_triples.tsv`

---

### 🔹 **6. Predictive Modeling (Core ML Module)**

#### A. **Link Prediction via PyKEEN**

**Tasks:**

* Train a model (e.g., TransE, ComplEx) on triples
* Generate predictions for new `INTERACTS_WITH` edges
* Score candidate interactions and return high-confidence results

**Module:** `link_prediction_trainer.py`
**Output:** Predicted drug–drug interactions with confidence scores

---

#### B. **Node Classification (Safety Likelihood Scoring)**

**Tasks:**

* Represent each drug node with embeddings (Node2Vec, GCN, etc.)
* Label drugs as high-risk or low-risk based on known ADRs or clinical risk
* Train a classifier (e.g., logistic regression or GNN) to predict safety

**Module:** `node_classifier.py`
**Core Functionality:**

* Classifies drug nodes by interaction safety likelihood
* Enables proactive exclusion of unsafe drug combinations

---

### 🔹 **7. Prediction Injection + Visualization**

**Tasks:**

* Insert predicted edges and classification results back into Neo4j

  * e.g., `PREDICTED_INTERACTS_WITH`, `SAFETY_SCORE`
* Visualize using Neo4j Bloom or Cypher queries

**Module:** `results_injector.py`
**Core Functionality:**

* Makes predictive outputs explorable and queryable
* Enables clinicians or analysts to explore "what-if" combinations

---

## 🔁 Iterative Evaluation & Fine-Tuning

At each stage:

* Evaluate model quality (MRR, Hits\@K, F1)
* Tune hyperparameters (embedding dimension, margin loss, etc.)
* Add external ontologies (e.g., MedDRA) for better semantic structure

---

## 📌 Summary of Core Functionalities to Be Developed

| Module                       | Core Functionality                                      |
| ---------------------------- | ------------------------------------------------------- |
| `neo4j_importer.py`          | Build and manage biomedical knowledge graph             |
| `literature_miner.py`        | Automatically extract relations from PubMed             |
| `link_prediction_trainer.py` | Learn embeddings and predict new drug–drug interactions |
| `node_classifier.py`         | Classify drug nodes by safety likelihood                |
| `results_injector.py`        | Reintegrate and visualize ML results in Neo4j           |

---

