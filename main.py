# Application settings for Azure Functions
# This file helps ensure proper configuration in Azure

import os

# Ensure the function app module is importable
def get_wsgi_app():
    """Entry point for Azure Functions runtime"""
    from function_app import app
    return app

# Export the app for Azure Functions runtime
app = get_wsgi_app()
