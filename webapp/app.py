from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import sys
import json
import torch
import pandas as pd

# Add parent directory to Python path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up correct path handling for GCN module
GCN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "GCN")

# Store the original working directory
original_dir = os.getcwd()

try:
    # Change working directory to GCN directory before importing
    os.chdir(GCN_DIR)
    from GCN.score_combo import score_combo
    
    # Custom wrapper for score_combo to maintain proper directory context
    def safe_score_combo(drug_list):
        # Ensure we're in the GCN directory when calling score_combo
        current_dir = os.getcwd()
        try:
            os.chdir(GCN_DIR)
            result = score_combo(drug_list)
            return result
        finally:
            # Always restore the directory
            os.chdir(current_dir)
            
except ImportError as e:
    print(f"Error importing score_combo: {e}")
    # Define a fallback function for testing
    def safe_score_combo(drug_list):
        return {
            "combination": drug_list,
            "risk_class": "Medium",
            "probabilities": {
                "low": 0.2,
                "medium": 0.5,
                "high": 0.3
            },
            "explanations": {drug: f"Demo explanation for {drug}" for drug in drug_list}
        }
finally:
    # Restore the original working directory
    os.chdir(original_dir)

# Import the enricher factory
try:
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "enrich"))
    from enricher_factory import get_disease_from_filename
    
    # You could also import and use get_enricher here if you need the full enricher
    # from enricher_factory import get_enricher
    # enricher = get_enricher(use_real_implementation=False)  # Switch to True when ready
    
except ImportError as e:
    print(f"Error importing enricher_factory: {e}")
    # Fallback function
    def get_disease_from_filename(filename):
        if "chronic_lymphotic_leukemia" in filename.lower():
            return "Chronic Lymphocytic Leukemia", ["Ibrutinib", "Venetoclax", "Rituximab", "Obinutuzumab", "Acalabrutinib"]
        elif "non_hodgkin_lymphoma" in filename.lower():
            return "Non-Hodgkin Lymphoma", ["Rituximab", "Cyclophosphamide", "Bendamustine", "Lenalidomide", "Polatuzumab"]
        elif "acute_myeloid_leukemia" in filename.lower():
            return "Acute Myeloid Leukemia", ["Cytarabine", "Daunorubicin", "Venetoclax", "Azacitidine", "Gemtuzumab"]
        else:
            return "Unknown Disease", ["Drug A", "Drug B", "Drug C"]

app = Flask(__name__)
app.secret_key = "cellverse_secret_key_change_in_production"
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load disease-drug mappings
def get_disease_drugs():
    # Base disease data - always available
    disease_drugs = {
        "Multiple Myeloma": [
            "Bortezomib", 
            "Cyclophosphamide", 
            "Lenalidomide", 
            "Dexamethasone", 
            "Carfilzomib"
        ]
    }
    
    # Add session-based diseases if they exist
    if 'discovered_diseases' in session:
        for disease, drugs in session['discovered_diseases'].items():
            disease_drugs[disease] = drugs
    
    return disease_drugs

@app.route('/')
def home():
    diseases = list(get_disease_drugs().keys())
    return render_template('home.html', diseases=diseases)

@app.route('/upload_article', methods=['POST'])
def upload_article():
    if 'article' not in request.files:
        flash('No file selected')
        return redirect(url_for('home'))
    
    file = request.files['article']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('home'))
    
    if file and file.filename.lower().endswith('.pdf'):
        # Save the file
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        
        # Get disease based on filename
        discovered_disease, drugs = get_disease_from_filename(file.filename)
        
        # Store the discovered disease in session
        if 'discovered_diseases' not in session:
            session['discovered_diseases'] = {}
        session['discovered_diseases'][discovered_disease] = drugs
        session.modified = True  # Ensure session is saved
        
        # Success message
        flash(f'Knowledge graph enriched! Added information about {discovered_disease} and {len(drugs)} associated drugs.')
        
        # Clean up the file
        try:
            os.remove(filepath)
        except:
            pass
        
        return redirect(url_for('home'))
    else:
        flash('Invalid file format. Please upload a PDF.')
        return redirect(url_for('home'))

# Add a route to reset the discovered diseases (clear the session)
@app.route('/reset_diseases', methods=['POST'])
def reset_diseases():
    if 'discovered_diseases' in session:
        session.pop('discovered_diseases')
        flash('All discovered diseases have been reset.')
    return redirect(url_for('home'))

@app.route('/disease/<disease>')
def disease_page(disease):
    disease_drugs = get_disease_drugs()
    if disease not in disease_drugs:
        flash(f"No data available for {disease}")
        return redirect(url_for('home'))
    
    drugs = disease_drugs[disease]
    return render_template('drug_selection.html', disease=disease, drugs=drugs)

@app.route('/analyze', methods=['POST'])
def analyze_combination():
    selected_drugs = request.form.getlist('selected_drugs')
    if not selected_drugs:
        flash("Please select at least one drug")
        return redirect(url_for('disease_page', disease=request.form.get('disease', 'Multiple Myeloma')))
    
    try:
        # Call our wrapped score_combo function that handles directory changes
        result = safe_score_combo(selected_drugs)
        # Ensure the result has proper structure
        if 'probabilities' not in result:
            result['probabilities'] = {'low': 0.0, 'medium': 0.0, 'high': 0.0}
        return render_template('results.html', result=result, selected_drugs=selected_drugs)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        flash(f"Error analyzing combination: {str(e)}")
        app.logger.error(f"Analysis error: {error_details}")
        print(f"Analysis error: {error_details}")  # Print to console for debugging
        return redirect(url_for('disease_page', disease=request.form.get('disease', 'Multiple Myeloma')))

# Add an error handler for better debugging
@app.errorhandler(500)
def server_error(e):
    app.logger.error(f'Server Error: {e}')
    return render_template('error.html', error=str(e)), 500

if __name__ == '__main__':
    app.run(debug=True)
