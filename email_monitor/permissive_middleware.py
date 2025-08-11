"""
Completely permissive middleware to allow all requests through tunnel
"""

class AllowAllMiddleware:
    """
    Middleware that allows all requests to pass through without any restrictions
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process request - allow everything
        response = self.get_response(request)
        
        # Add permissive headers to response
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH'
        response['Access-Control-Allow-Headers'] = '*'
        response['Access-Control-Allow-Credentials'] = 'true'
        response['X-Frame-Options'] = 'ALLOWALL'
        
        return response
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Allow all views
        return None
    
    def process_exception(self, request, exception):
        # Don't process exceptions - let them through
        return None
