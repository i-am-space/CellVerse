# Text2Cypher Enrichment Module

This module provides functionality to enrich a Neo4j knowledge graph using PDF documents.

## Demo vs. Real Implementation

There are two implementations available:

1. **Demo Implementation** (`text2cypher_enricher.py`):
   - No API key required
   - Maps PDF filenames to predefined diseases
   - No actual text processing or API calls
   - Perfect for demos and testing the web interface

2. **Real Implementation** (`real_text2cypher_enricher.py`):
   - Requires a valid Neo4j Text2Cypher API key
   - Extracts text from PDFs
   - Processes text with Neo4j Text2Cypher API
   - Executes generated Cypher queries to enrich the graph

## Switching Between Implementations

Use the `enricher_factory.py` to easily switch between implementations:

```python
from enricher_factory import get_enricher

# Demo implementation (default)
demo_enricher = get_enricher(use_real_implementation=False)

# Real implementation with API key
real_enricher = get_enricher(use_real_implementation=True, api_key="your-api-key")

# Or set the API key as an environment variable
import os
os.environ["TEXT2CYPHER_API_KEY"] = "your-api-key"
real_enricher = get_enricher(use_real_implementation=True)

# Both implementations have the same interface
result = enricher.enrich_from_pdf("path/to/your.pdf")
```

## How to Get an API Key

1. Contact Neo4j to request access to their Text2Cypher API
2. Once approved, you'll receive an API key
3. Set the key as an environment variable: `export TEXT2CYPHER_API_KEY="your-api-key"`
4. Or pass it directly to `get_enricher()`

## PDF Naming Convention for Demo Mode

In demo mode, the following PDF filenames will map to specific diseases:
- `chronic_lymphotic_leukemia.pdf` → Chronic Lymphocytic Leukemia
- `non_hodgkin_lymphoma.pdf` → Non-Hodgkin Lymphoma
- `acute_myeloid_leukemia.pdf` → Acute Myeloid Leukemia
