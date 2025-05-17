from neo4j import GraphDatabase

# Neo4j connection config (from your earlier setup)
URI = "neo4j+s://7ab56458.databases.neo4j.io"
AUTH = ("neo4j", "v3rSbGYUTwCHLJIUJ3TB9S_Ug4Q3VAJup_pY5like0o")

driver = GraphDatabase.driver(URI, auth=AUTH)

def explain_safety(drug_name):
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
        result = session.run(query, drug=drug_name).single()
        return {
            "drug": result["drug"],
            "direct_adrs": [x for x in result["direct_adrs"] if x],
            "interacting_drugs": [x for x in result["interacting_drugs"] if x],
            "adrs_from_interactions": [x for x in result["adrs_from_interactions"] if x]
        }

def format_explanation(data):
    lines = [f"🧬 Drug: **{data['drug']}**"]
    if data["direct_adrs"]:
        lines.append(f"• Directly causes: {', '.join(data['direct_adrs'])}")
    if data["interacting_drugs"]:
        lines.append(f"• Interacts with: {', '.join(data['interacting_drugs'])}")
    if data["adrs_from_interactions"]:
        lines.append(f"• Indirectly linked to: {', '.join(data['adrs_from_interactions'])}")
    if len(lines) == 1:
        return f"No ADR or interaction data found for {data['drug']}"
    return "\n".join(lines)

if __name__ == "__main__":
    drug_list = ["Carfilzomib", "Dexamethasone", "Cyclophosphamide"]  # Add others if needed

    for drug in drug_list:
        result = explain_safety(drug)
        print("\n" + format_explanation(result))
