import os
import json
import uuid
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

# Create a blueprint for the enrichment routes
enrich_bp = Blueprint('enrich', __name__)

# Store initialization function to be called by the main app
def _initialize_enricher(app):
    """Initialize the Text2Cypher enricher with schema"""
    # Look for schema file
    schema_file = os.path.join(os.path.dirname(__file__), "kg_schema.json")
    
    # If schema doesn't exist, create it
    if not os.path.exists(schema_file):
        from .schema_builder import SchemaBuilder
        NEO4J_URI = "neo4j+s://7ab56458.databases.neo4j.io"
        NEO4J_AUTH = ("neo4j", "v3rSbGYUTwCHLJIUJ3TB9S_Ug4Q3VAJup_pY5like0o")
        
        schema_builder = SchemaBuilder(NEO4J_URI, NEO4J_AUTH)
        schema_builder.create_schema_json(schema_file)
    
    # Create the enricher instance
    from .text2cypher_enricher import Text2CypherEnricher
    app.text2cypher_enricher = Text2CypherEnricher(schema_file)
    return app.text2cypher_enricher

@enrich_bp.route('/upload_and_enrich', methods=['POST'])
def upload_and_enrich():
    """
    Handle PDF upload and knowledge graph enrichment
    """
    # Ensure enricher is initialized
    if not hasattr(current_app, 'text2cypher_enricher'):
        _initialize_enricher(current_app)
        
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected"}), 400
    
    if file and file.filename.lower().endswith('.pdf'):
        # Create a unique filename to avoid collisions
        unique_filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        # Ensure upload folder exists
        os.makedirs(upload_folder, exist_ok=True)
        
        # Save the file
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)
        
        try:
            # Process the PDF with Text2Cypher
            enricher = current_app.text2cypher_enricher
            result = enricher.enrich_from_pdf(filepath)
            
            # Add the filename to the result
            result["filename"] = file.filename
            
            return jsonify(result)
        except Exception as e:
            return jsonify({
                "status": "error", 
                "message": f"Error processing PDF: {str(e)}"
            }), 500
        finally:
            # Clean up the file after processing
            try:
                os.remove(filepath)
            except:
                pass  # Ignore cleanup errors
    
    return jsonify({"status": "error", "message": "Invalid file format. Please upload a PDF."}), 400

@enrich_bp.route('/get_schema', methods=['GET'])
def get_schema():
    """
    Return the current schema used for Text2Cypher
    """
    schema_file = os.path.join(os.path.dirname(__file__), "kg_schema.json")
    
    if os.path.exists(schema_file):
        with open(schema_file, 'r') as f:
            schema = json.load(f)
        return jsonify(schema)
    else:
        return jsonify({"status": "error", "message": "Schema file not found"}), 404

@enrich_bp.route('/rebuild_schema', methods=['POST'])
def rebuild_schema():
    """
    Rebuild the schema from the database and JSON files
    """
    try:
        from .schema_builder import SchemaBuilder
        NEO4J_URI = "neo4j+s://7ab56458.databases.neo4j.io"
        NEO4J_AUTH = ("neo4j", "v3rSbGYUTwCHLJIUJ3TB9S_Ug4Q3VAJup_pY5like0o")
        
        schema_builder = SchemaBuilder(NEO4J_URI, NEO4J_AUTH)
        schema_file = os.path.join(os.path.dirname(__file__), "kg_schema.json")
        schema = schema_builder.create_schema_json(schema_file)
        
        # Reinitialize the enricher
        current_app.text2cypher_enricher = Text2CypherEnricher(schema_file)
        
        return jsonify({
            "status": "success", 
            "message": "Schema rebuilt successfully",
            "schema": schema
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error rebuilding schema: {str(e)}"
        }), 500
