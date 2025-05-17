from neo4j import GraphDatabase
import csv

# Replace these with your AuraDB credentials
instance_id = "7ab56458"
username = "neo4j"
password = "v3rSbGYUTwCHLJIUJ3TB9S_Ug4Q3VAJup_pY5like0o"
URI = f"neo4j+s://{instance_id}.databases.neo4j.io"
AUTH = (username, password)

driver = GraphDatabase.driver(URI, auth=AUTH)

RELATIONSHIPS = [
    "INTERACTS_WITH",
    "CAUSES_ADR",
    "TARGETS",
    "INDICATED_FOR",
    "ELEVATES_RISK_FOR"
]

triples = []

with driver.session() as session:
    for rel in RELATIONSHIPS:
        query = f"""
        MATCH (h)-[r:{rel}]->(t)
        RETURN h.name AS head, '{rel}' AS relation, t.name AS tail
        """
        result = session.run(query)
        triples.extend([(record["head"], record["relation"], record["tail"]) for record in result])

# Output TSV for PyKEEN
with open("kg_triples.tsv", "w", newline='', encoding="utf-8") as f:
    writer = csv.writer(f, delimiter='\t')
    writer.writerows(triples)

print("✅ Exported to kg_triples.tsv")
from neo4j import GraphDatabase
import csv

# Replace these with your AuraDB credentials
URI = "neo4j+s://7ab56458.databases.neo4j.io"
AUTH = ("neo4j", "v3rSbGYUTwCHLJIUJ3TB9S_Ug4Q3VAJup_pY5like0o")

driver = GraphDatabase.driver(URI, auth=AUTH)

RELATIONSHIPS = [
    "INTERACTS_WITH",
    "CAUSES_ADR",
    "TARGETS",
    "INDICATED_FOR",
    "ELEVATES_RISK_FOR"
]

triples = []

with driver.session() as session:
    for rel in RELATIONSHIPS:
        query = f"""
        MATCH (h)-[r:{rel}]->(t)
        RETURN h.name AS head, '{rel}' AS relation, t.name AS tail
        """
        result = session.run(query)
        triples.extend([(record["head"], record["relation"], record["tail"]) for record in result])

# Output TSV for PyKEEN
with open("kg_triples.tsv", "w", newline='', encoding="utf-8") as f:
    writer = csv.writer(f, delimiter='\t')
    writer.writerows(triples)

print("✅ Exported to kg_triples.tsv")
