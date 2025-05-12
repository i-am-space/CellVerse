import os
import json
from py2neo import Graph, Node, Relationship
from neo4j import GraphDatabase

instance_id = "7ab56458"
username = "neo4j"
password = "v3rSbGYUTwCHLJIUJ3TB9S_Ug4Q3VAJup_pY5like0o"
URI = f"neo4j+s://{instance_id}.databases.neo4j.io"
AUTH = (username, password)

with GraphDatabase.driver(URI, auth=AUTH) as driver:
    driver.verify_connectivity()

driver = GraphDatabase.driver(URI, auth=AUTH)

def load_json_files(folder):
    return [json.load(open(os.path.join(folder, f))) for f in os.listdir(folder) if f.endswith('.json')]

def add_drug_data(tx, drug):
    # Create drug node
    tx.run("MERGE (d:Drug {name: $name, aliases: $aliases})", name=drug["drug_name"], aliases=drug.get("aliases", []))

    # Create indication edges
    for disease in drug["indications"]:
        tx.run("""
            MERGE (dis:Disease {name: $disease})
            MERGE (d:Drug {name: $drug}) 
            MERGE (d)-[:INDICATED_FOR]->(dis)
        """, drug=drug["drug_name"], disease=disease)

    # Create target edges
    for t in drug["targets"]:
        tx.run("""
            MERGE (p:Protein {name: $protein})
            MERGE (d:Drug {name: $drug})
            MERGE (d)-[:TARGETS {interaction_type: $itype}]->(p)
        """, drug=drug["drug_name"], protein=t["protein"], itype=t["interaction_type"])

    # Create ADR edges
    for adr in drug["adverse_effects"]:
        tx.run("""
            MERGE (s:SideEffect {name: $adr})
            MERGE (d:Drug {name: $drug})
            MERGE (d)-[:CAUSES_ADR {source: $source}]->(s)
        """, drug=drug["drug_name"], adr=adr["name"], source=adr["source"])

    # Create drug-drug interaction edges
    for inter in drug["interacts_with"]:
        tx.run("""
            MERGE (d1:Drug {name: $d1})
            MERGE (d2:Drug {name: $d2})
            MERGE (d1)-[:INTERACTS_WITH {effect: $effect, evidence: $evidence}]->(d2)
        """, d1=drug["drug_name"], d2=inter["drug"], effect=inter["effect"], evidence=inter["evidence"])

def build_graph(folder):
    data = load_json_files(folder)
    with driver.session() as session:
        for drug in data:
            session.write_transaction(add_drug_data, drug)
    print("Finished building knowledge graph.")

# Run the import
build_graph("drug_data")