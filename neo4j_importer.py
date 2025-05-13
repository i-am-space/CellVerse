import os
import json
from py2neo import Graph, Node, Relationship
from neo4j import GraphDatabase

instance_id = "7ab56458"
username = "neo4j"
password = "v3rSbGYUTwCHLJIUJ3TB9S_Ug4Q3VAJup_pY5like0o"
URI = f"neo4j+s://{instance_id}.databases.neo4j.io"
AUTH = (username, password)

driver = GraphDatabase.driver(URI, auth=AUTH)

def load_json_files(folder):
    return [
        json.load(open(os.path.join(folder, f)))
        for f in os.listdir(folder)
        if f.endswith('.json') and f != "patient_risk_factors.json"
    ]

def load_risk_factors(json_path):
    with open(json_path, "r") as f:
        return json.load(f)["patient_risk_factors"]

def add_drug_data(tx, drug):
    tx.run("MERGE (d:Drug {name: $name, aliases: $aliases})", name=drug["drug_name"], aliases=drug.get("aliases", []))

    for disease in drug["indications"]:
        tx.run("""
            MERGE (dis:Disease {name: $disease})
            MERGE (d:Drug {name: $drug}) 
            MERGE (d)-[:INDICATED_FOR]->(dis)
        """, drug=drug["drug_name"], disease=disease)

    for t in drug["targets"]:
        tx.run("""
            MERGE (p:Protein {name: $protein})
            MERGE (d:Drug {name: $drug})
            MERGE (d)-[:TARGETS {interaction_type: $itype}]->(p)
        """, drug=drug["drug_name"], protein=t["protein"], itype=t["interaction_type"])

    for adr in drug["adverse_effects"]:
        tx.run("""
            MERGE (s:SideEffect {name: $adr})
            MERGE (d:Drug {name: $drug})
            MERGE (d)-[:CAUSES_ADR {source: $source}]->(s)
        """, drug=drug["drug_name"], adr=adr["name"], source=adr["source"])

    for inter in drug["interacts_with"]:
        tx.run("""
            MERGE (d1:Drug {name: $d1})
            MERGE (d2:Drug {name: $d2})
            MERGE (d1)-[:INTERACTS_WITH {effect: $effect, evidence: $evidence}]->(d2)
        """, d1=drug["drug_name"], d2=inter["drug"], effect=inter["effect"], evidence=inter["evidence"])

def add_risk_factor_data(tx, risk_factor_entry):
    # Use existing SideEffect node (matches adverse_effects)
    side_effect = risk_factor_entry["risk_factor"]
    explanation = risk_factor_entry["explanation"]

    for condition in risk_factor_entry["related_conditions"]:
        tx.run("""
            MERGE (c:Condition {name: $condition})
            MERGE (s:SideEffect {name: $side_effect})
            MERGE (c)-[:ELEVATES_RISK_FOR {explanation: $explanation}]->(s)
        """, condition=condition, side_effect=side_effect, explanation=explanation)

def build_graph(drug_folder, risk_factor_json_path):
    drug_data = load_json_files(drug_folder)
    risk_factors = load_risk_factors(risk_factor_json_path)

    with driver.session() as session:
        # Wipe the entire graph before insertion
        session.run("MATCH (n) DETACH DELETE n")

        for drug in drug_data:
            session.write_transaction(add_drug_data, drug)
        for rf in risk_factors:
            session.write_transaction(add_risk_factor_data, rf)

    print("Graph wiped and rebuilt with drugs and patient risk factors.")
    
build_graph("drug_data", "drug_data/patient_risk_factors.json")