from .web_handler import enrich_bp, _initialize_enricher

def integrate_with_flask(app):
    """
    Add the enrich blueprint to a Flask application
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(enrich_bp, url_prefix='/enrich')
    
    # Initialize the enricher at startup
    with app.app_context():
        _initialize_enricher(app)
    
    # Create a more direct route for upload from the main form
    @app.route('/upload_article_enrich', methods=['POST'])
    def upload_article_enrich():
        from flask import request, redirect, url_for, flash
        from werkzeug.utils import secure_filename
        import os
        import uuid
        
        if 'article' not in request.files:
            flash('No file selected')
            return redirect(url_for('home'))
        
        file = request.files['article']
        if file.filename == '':
            flash('No file selected')
            return redirect(url_for('home'))
        
        if file and file.filename.lower().endswith('.pdf'):
            # Create a unique filename to avoid collisions
            unique_filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
            
            # Ensure upload folder exists
            os.makedirs(upload_folder, exist_ok=True)
            
            # Save the file
            filepath = os.path.join(upload_folder, unique_filename)
            file.save(filepath)
            
            try:
                # Import and initialize enricher if needed
                from .text2cypher_enricher import Text2CypherEnricher
                schema_file = os.path.join(os.path.dirname(__file__), "kg_schema.json")
                
                # Check if schema exists, if not create it
                if not os.path.exists(schema_file):
                    from .schema_builder import SchemaBuilder
                    NEO4J_URI = "neo4j+s://7ab56458.databases.neo4j.io"
                    NEO4J_AUTH = ("neo4j", "v3rSbGYUTwCHLJIUJ3TB9S_Ug4Q3VAJup_pY5like0o")
                    
                    schema_builder = SchemaBuilder(NEO4J_URI, NEO4J_AUTH)
                    schema_builder.create_schema_json(schema_file)
                
                # Process the PDF
                enricher = Text2CypherEnricher(schema_file)
                result = enricher.enrich_from_pdf(filepath)
                
                if result["status"] == "success":
                    flash(f"Successfully processed {file.filename}. Added {result['execution_results']['success_count']} new pieces of information to the knowledge graph.")
                else:
                    flash(f"Error processing {file.filename}: {result.get('message', 'Unknown error')}")
            except Exception as e:
                flash(f"Error processing file: {str(e)}")
            finally:
                # Clean up the file
                try:
                    os.remove(filepath)
                except:
                    pass  # Ignore cleanup errors
        else:
            flash('Invalid file format. Please upload a PDF.')
        
        return redirect(url_for('home'))
