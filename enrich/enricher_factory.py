import os
import importlib.util
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("enricher_factory")

def get_enricher(use_real_implementation=False, api_key=None):
    """
    Factory function to get the appropriate Text2Cypher enricher implementation
    
    Args:
        use_real_implementation (bool): Whether to use the real implementation
        api_key (str, optional): The API key for Text2Cypher
        
    Returns:
        An instance of Text2CypherEnricher (demo) or RealText2CypherEnricher
    """
    # Set API key if provided
    if api_key:
        os.environ["TEXT2CYPHER_API_KEY"] = api_key
    
    schema_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kg_schema.json")
    
    if use_real_implementation:
        # Check if API key is available
        if not os.environ.get("TEXT2CYPHER_API_KEY"):
            logger.warning("No API key for Text2Cypher available. Using demo implementation instead.")
            from text2cypher_enricher import Text2CypherEnricher
            return Text2CypherEnricher(schema_file if os.path.exists(schema_file) else None)
        
        # Import the real implementation
        try:
            from text2cypher_enricher import RealText2CypherEnricher
            logger.info("Using real Text2Cypher implementation")
            return RealText2CypherEnricher(schema_file if os.path.exists(schema_file) else None)
        except ImportError as e:
            logger.error(f"Failed to import real implementation: {e}")
            from text2cypher_enricher import Text2CypherEnricher
            return Text2CypherEnricher(schema_file if os.path.exists(schema_file) else None)
    else:
        # Use demo implementation
        from text2cypher_enricher_d import Text2CypherEnricher
        logger.info("Using demo Text2Cypher implementation")
        return Text2CypherEnricher(schema_file if os.path.exists(schema_file) else None)

def get_disease_from_filename(filename):
    """Proxy function to the one in text2cypher_enricher"""
    from text2cypher_enricher_d import get_disease_from_filename as get_disease
    return get_disease(filename)
