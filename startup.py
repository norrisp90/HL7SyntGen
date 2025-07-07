#!/usr/bin/env python3
"""
Startup script for Azure Functions deployment.
This ensures proper module loading and function discovery.
"""

import sys
import os
import logging

# Configure logging for Azure
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main startup function for Azure Functions."""
    try:
        logger.info("=== Azure Functions Startup ===")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Working directory: {os.getcwd()}")
        logger.info(f"Python path: {sys.path}")
        
        # List current directory contents
        logger.info("Current directory contents:")
        for item in os.listdir("."):
            logger.info(f"  - {item}")
        
        # Import and validate function app
        try:
            import function_app
            logger.info("✓ Successfully imported function_app module")
            
            # Check if app object exists
            if hasattr(function_app, 'app'):
                logger.info("✓ Function app object found")
            else:
                logger.error("✗ Function app object not found")
                
        except ImportError as e:
            logger.error(f"✗ Failed to import function_app: {e}")
            raise
            
        # Validate required dependencies
        dependencies = ['azure.functions', 'faker', 'xml.etree.ElementTree']
        for dep in dependencies:
            try:
                __import__(dep)
                logger.info(f"✓ {dep} imported successfully")
            except ImportError as e:
                logger.error(f"✗ Failed to import {dep}: {e}")
                
        logger.info("=== Startup Complete ===")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

if __name__ == "__main__":
    main()
