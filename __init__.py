#!/usr/bin/env python3
"""
Azure Functions startup module to ensure proper function app discovery
"""
import logging
import sys
import os

# Configure logging for Azure Functions
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def configure_app():
    """Configure the Function App for Azure deployment"""
    try:
        # Ensure Python path includes current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Python path: {sys.path}")
        
        # Import and initialize the function app
        from function_app import app
        logger.info("Function app imported successfully")
        
        return app
        
    except Exception as e:
        logger.error(f"Error configuring function app: {str(e)}")
        raise

# Initialize the app
if __name__ == "__main__":
    configure_app()
