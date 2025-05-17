import os
import json
import sys
from neo4j import GraphDatabase

class SchemaBuilder:
    def __init__(self, uri, auth):
        self.driver = GraphDatabase.driver(uri, auth=auth)
    
    def extract_schema_from_json(self, json_dir):
        """
        Extract schema from drug data JSON files
        """
        schema = {
            "nodes": [],
            "relationships": []
        }
        
        # Node labels and properties we know exist in our data
        nodes = {
            "Drug": ["name", "aliases"],
            "Disease": ["name"],
            "Protein": ["name"],
            "SideEffect": ["name"],
            "Condition": ["name"]
        }
        
        # Relationship types we know exist in our data
        relationships = [
            {"type": "INDICATED_FOR", "source": "Drug", "target": "Disease", "properties": []},
            {"type": "TARGETS", "source": "Drug", "target": "Protein", "properties": ["interaction_type"]},
            {"type": "CAUSES_ADR", "source": "Drug", "target": "SideEffect", "properties": ["source"]},
            {"type": "INTERACTS_WITH", "source": "Drug", "target": "Drug", "properties": ["effect", "evidence"]},
            {"type": "ELEVATES_RISK_FOR", "source": "Condition", "target": "SideEffect", "properties": ["explanation"]}
        ]
        
        # Convert to schema format
        for label, props in nodes.items():
            schema["nodes"].append({
                "label": label,
                "properties": props
            })
        
        schema["relationships"] = relationships
        
        return schema
    
    def extract_schema_from_database(self):
        """
        Extract schema directly from the Neo4j database
        """
        schema = {
            "nodes": [],
            "relationships": []
        }
        
        with self.driver.session() as session:
            # Get node labels and properties
            result = session.run("""
                CALL apoc.meta.schema()
                YIELD value
                RETURN value
            """)
            
            if not result.peek():
                print("No schema information found. Make sure APOC is installed and the database has data.")
                return schema
            
            meta_schema = result.single()["value"]
            
            # Process node labels
            for label, details in meta_schema.items():
                if "properties" in details:
                    node = {
                        "label": label,
                        "properties": list(details["properties"].keys())
                    }
                    schema["nodes"].append(node)
            
            # Get relationship types
            result = session.run("""
                CALL db.relationshipTypes()
                YIELD relationshipType
                RETURN relationshipType
            """)
            
            rel_types = [record["relationshipType"] for record in result]
            
            # For each relationship type, get properties and connected node labels
            for rel_type in rel_types:
                result = session.run(f"""
                    MATCH ()-[r:{rel_type}]->()
                    WITH r LIMIT 1
                    RETURN keys(r) AS properties
                """)
                
                props = result.single()["properties"] if result.peek() else []
                
                result = session.run(f"""
                    MATCH (a)-[r:{rel_type}]->(b)
                    WITH labels(a) AS source_labels, labels(b) AS target_labels
                    LIMIT 1
                    RETURN source_labels, target_labels
                """)
                
                record = result.single() if result.peek() else None
                source = record["source_labels"][0] if record and record["source_labels"] else "Unknown"
                target = record["target_labels"][0] if record and record["target_labels"] else "Unknown"
                
                rel = {
                    "type": rel_type,
                    "source": source,
                    "target": target,
                    "properties": props
                }
                schema["relationships"].append(rel)
        
        return schema
    
    def create_schema_json(self, output_path):
        """
        Create schema JSON file combining both database and JSON file information
        """
        # First get schema from database if available
        try:
            db_schema = self.extract_schema_from_database()
            print(f"Extracted schema from database: {len(db_schema['nodes'])} node types, {len(db_schema['relationships'])} relationship types")
        except Exception as e:
            print(f"Error extracting schema from database: {e}")
            db_schema = {"nodes": [], "relationships": []}
        
        # Then get schema from JSON files as fallback
        try:
            json_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "drug_data")
            json_schema = self.extract_schema_from_json(json_dir)
            print(f"Extracted schema from JSON files: {len(json_schema['nodes'])} node types, {len(json_schema['relationships'])} relationship types")
        except Exception as e:
            print(f"Error extracting schema from JSON files: {e}")
            json_schema = {"nodes": [], "relationships": []}
        
        # Merge schemas, prioritizing DB schema
        combined_schema = {
            "nodes": db_schema["nodes"],
            "relationships": db_schema["relationships"]
        }
        
        # Add any node types from JSON schema that don't exist in DB schema
        db_node_labels = {node["label"] for node in db_schema["nodes"]}
        for node in json_schema["nodes"]:
            if node["label"] not in db_node_labels:
                combined_schema["nodes"].append(node)
        
        # Add any relationship types from JSON schema that don't exist in DB schema
        db_rel_types = {rel["type"] for rel in db_schema["relationships"]}
        for rel in json_schema["relationships"]:
            if rel["type"] not in db_rel_types:
                combined_schema["relationships"].append(rel)
        
        # Write to file
        with open(output_path, 'w') as f:
            json.dump(combined_schema, f, indent=2)
        
        print(f"Combined schema saved to {output_path}")
        return combined_schema

if __name__ == "__main__":
    # Neo4j connection details
    NEO4J_URI = "neo4j+s://7ab56458.databases.neo4j.io"
    NEO4J_AUTH = ("neo4j", "v3rSbGYUTwCHLJIUJ3TB9S_Ug4Q3VAJup_pY5like0o")
    
    schema_builder = SchemaBuilder(NEO4J_URI, NEO4J_AUTH)
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kg_schema.json")
    schema_builder.create_schema_json(output_path)
