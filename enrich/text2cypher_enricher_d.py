import os
import json
import requests
import PyPDF2
import io
import logging
import random
from neo4j import GraphDatabase

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("text2cypher_enricher")

# Neo4j connection details
NEO4J_URI = "neo4j+s://7ab56458.databases.neo4j.io"
NEO4J_AUTH = ("neo4j", "v3rSbGYUTwCHLJIUJ3TB9S_Ug4Q3VAJup_pY5like0o")

# Neo4j Text2Cypher endpoint - replace with actual endpoint
TEXT2CYPHER_URL = "https://workspace-preview.api.neo4j.io/text2cypher/api/v1"
TEXT2CYPHER_API_KEY = os.environ.get("TEXT2CYPHER_API_KEY", "")  # Set this in environment or config

# Simulated disease data for demo purposes
DEMO_DISEASES = {
    "Chronic Lymphocytic Leukemia": [
        "Ibrutinib", 
        "Venetoclax",
        "Rituximab", 
        "Obinutuzumab", 
        "Acalabrutinib"
    ],
    "Non-Hodgkin Lymphoma": [
        "Rituximab",
        "Cyclophosphamide",
        "Bendamustine",
        "Lenalidomide",
        "Polatuzumab"
    ],
    "Acute Myeloid Leukemia": [
        "Cytarabine",
        "Daunorubicin",
        "Venetoclax",
        "Azacitidine",
        "Gemtuzumab"
    ]
}

# Map filename patterns to diseases
FILENAME_DISEASE_MAP = {
    "chronic_lymphotic_leukemia": "Chronic Lymphocytic Leukemia",
    "non_hodgkin_lymphoma": "Non-Hodgkin Lymphoma",
    "acute_myeloid_leukemia": "Acute Myeloid Leukemia"
}

def get_disease_from_filename(filename):
    """
    Determine which disease to return based on the PDF filename
    """
    filename_lower = filename.lower()
    
    # Check for exact matches in our map
    for pattern, disease_name in FILENAME_DISEASE_MAP.items():
        if pattern in filename_lower:
            return disease_name, DEMO_DISEASES[disease_name]
    
    # Fallback if no match found - try to extract disease name from filename
    for disease_name in DEMO_DISEASES.keys():
        if disease_name.lower().replace(" ", "_") in filename_lower or \
           disease_name.lower().replace("-", "_") in filename_lower or \
           disease_name.lower().replace(" ", "") in filename_lower:
            return disease_name, DEMO_DISEASES[disease_name]
    
    # If still no match, return the first disease as default
    default_disease = list(DEMO_DISEASES.keys())[0]
    return default_disease, DEMO_DISEASES[default_disease]

class Text2CypherEnricher:
    def __init__(self, schema_file=None):
        """
        Initialize the Text2Cypher enricher with a schema.
        
        Args:
            schema_file (str, optional): Path to the schema JSON file.
        """
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
        self.schema = self._load_schema(schema_file) if schema_file else self._generate_schema()
        
    def _load_schema(self, schema_file):
        """Load schema from a JSON file"""
        try:
            with open(schema_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load schema file: {e}")
            return self._generate_schema()
    
    def _generate_schema(self):
        """Generate schema from the database"""
        logger.info("Generating schema from database...")
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
                
        logger.info(f"Generated schema with {len(schema['nodes'])} node types and {len(schema['relationships'])} relationship types")
        return schema

    def extract_text_from_pdf(self, pdf_path):
        """Extract text from a PDF file"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page_num in range(len(reader.pages)):
                    text += reader.pages[page_num].extract_text()
            return text
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            return ""

    def generate_cypher_from_text(self, text):
        """
        Use Neo4j Text2Cypher to generate Cypher queries from text
        """
        try:
            # Check if Text2Cypher API key is available
            if not TEXT2CYPHER_API_KEY:
                logger.error("TEXT2CYPHER_API_KEY environment variable not set")
                return []
            
            # Prepare the request payload
            payload = {
                "text": text,
                "schema": self.schema
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {TEXT2CYPHER_API_KEY}"
            }
            
            # Make the API call to Text2Cypher
            response = requests.post(
                TEXT2CYPHER_URL,
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Generated {len(data.get('cypher', []))} Cypher statements")
                return data.get("cypher", [])
            else:
                logger.error(f"Text2Cypher API returned error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to generate Cypher from text: {e}")
            return []
    
    def chunk_text(self, text, max_chunk_size=1000):
        """
        Split text into manageable chunks for processing
        """
        if len(text) <= max_chunk_size:
            return [text]
        
        chunks = []
        sentences = text.split('. ')
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_chunk_size:
                current_chunk += sentence + ". "
            else:
                chunks.append(current_chunk)
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks
    
    def execute_cypher_queries(self, queries):
        """
        Execute the generated Cypher queries against Neo4j
        """
        success_count = 0
        error_count = 0
        results = []
        
        with self.driver.session() as session:
            for query in queries:
                try:
                    result = session.run(query)
                    summary = result.consume()
                    results.append({
                        "query": query,
                        "nodes_created": summary.counters.nodes_created,
                        "relationships_created": summary.counters.relationships_created,
                        "properties_set": summary.counters.properties_set,
                        "status": "success"
                    })
                    success_count += 1
                    
                    logger.info(f"Query executed successfully: {summary.counters}")
                except Exception as e:
                    results.append({
                        "query": query,
                        "status": "error",
                        "error": str(e)
                    })
                    error_count += 1
                    logger.error(f"Error executing query: {e}")
        
        logger.info(f"Executed {success_count} queries successfully, {error_count} queries failed")
        return {
            "success_count": success_count,
            "error_count": error_count,
            "results": results
        }
    
    def enrich_from_pdf(self, pdf_path):
        """
        Main method to enrich the knowledge graph from a PDF
        For demo purposes, we'll just extract a disease based on the filename
        """
        logger.info(f"Starting simulated knowledge graph enrichment from PDF: {pdf_path}")
        
        # Get disease based on filename
        filename = os.path.basename(pdf_path)
        discovered_disease, drugs = get_disease_from_filename(filename)
        
        # Simulate processing time
        import time
        time.sleep(1)
        
        # Return simulation results
        return {
            "status": "success",
            "message": f"Successfully enriched knowledge graph with information about {discovered_disease}",
            "discovered_disease": discovered_disease,
            "associated_drugs": drugs,
            "execution_results": {
                "success_count": len(drugs) + 2,
                "error_count": 0,
                "results": [
                    {"status": "success", "nodes_created": 1, 
                     "relationships_created": len(drugs), "properties_set": len(drugs) + 3}
                ]
            }
        }

# Get a disease and its drugs for the simulation
def get_random_disease_data():
    """Return a random disease and its associated drugs for demo purposes"""
    disease = random.choice(list(DEMO_DISEASES.keys()))
    return disease, DEMO_DISEASES[disease]

if __name__ == "__main__":
    # Example usage
    schema_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kg_schema.json")
    enricher = Text2CypherEnricher(schema_file if os.path.exists(schema_file) else None)
    
    # Test with a sample PDF
    sample_pdf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample.pdf")
    if os.path.exists(sample_pdf):
        result = enricher.enrich_from_pdf(sample_pdf)
        print(json.dumps(result, indent=2))
    else:
        print(f"Sample PDF not found: {sample_pdf}")
