"""Simple HTTP Basic Auth for production."""
import os
from functools import wraps
from flask import request, Response

def init_basic_auth(app):
    """Add basic auth if SITE_USERNAME and SITE_PASSWORD are set."""
    username = os.environ.get('SITE_USERNAME')
    password = os.environ.get('SITE_PASSWORD')
    
    if not username or not password:
        app.logger.info("Basic auth: disabled (no SITE_USERNAME/SITE_PASSWORD)")
        return
    
    app.logger.info("Basic auth: enabled")
    
    @app.before_request
    def require_basic_auth():
        # Skip auth for health check
        if request.path == '/health':
            return None
        
        auth = request.authorization
        if not auth or auth.username != username or auth.password != password:
            return Response(
                'Login required.', 401,
                {'WWW-Authenticate': 'Basic realm="SAP Transformation Platform"'}
            )
