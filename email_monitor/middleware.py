import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class CSRFDebugMiddleware(MiddlewareMixin):
    """
    Middleware to debug CSRF verification process
    """
    
    def process_request(self, request):
        # Log request details for CSRF debugging
        if request.path == '/monitor/contacts/upload/':
            logger.info(f"=== CSRF DEBUG MIDDLEWARE - REQUEST ===")
            logger.info(f"Path: {request.path}")
            logger.info(f"Method: {request.method}")
            logger.info(f"Host: {request.get_host()}")
            logger.info(f"Secure: {request.is_secure()}")
            logger.info(f"CSRF Token in META: {request.META.get('CSRF_COOKIE', 'None')}")
            logger.info(f"CSRF Token in Headers: {request.META.get('HTTP_X_CSRFTOKEN', 'None')}")
            logger.info(f"Referrer: {request.META.get('HTTP_REFERER', 'None')}")
            logger.info(f"Origin: {request.META.get('HTTP_ORIGIN', 'None')}")
            logger.info(f"X-Forwarded-Host: {request.META.get('HTTP_X_FORWARDED_HOST', 'None')}")
            logger.info(f"X-Forwarded-Proto: {request.META.get('HTTP_X_FORWARDED_PROTO', 'None')}")
        
        return None
    
    def process_response(self, request, response):
        # Log response for CSRF debugging
        if request.path == '/monitor/contacts/upload/' and response.status_code == 403:
            logger.error(f"=== CSRF DEBUG MIDDLEWARE - 403 RESPONSE ===")
            logger.error(f"Response status: {response.status_code}")
            logger.error(f"Response content: {response.content[:500]}")  # First 500 chars
        
        return response
