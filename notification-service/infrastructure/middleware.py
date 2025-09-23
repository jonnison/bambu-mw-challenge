"""
Infrastructure middleware for monitoring, observability, and request processing.
"""
import uuid
import time
import logging
from django.utils.deprecation import MiddlewareMixin


logger = logging.getLogger(__name__)


class RequestIDMiddleware(MiddlewareMixin):
    """
    Adds a unique request ID to each HTTP request for tracing and logging.
    """
    
    def process_request(self, request):
        """
        Generate a unique request ID and add it to the request.
        """
        request_id = str(uuid.uuid4())
        request.META['X-Request-ID'] = request_id
        request.request_id = request_id
        return None
    
    def process_response(self, request, response):
        """
        Add the request ID to the response headers.
        """
        if hasattr(request, 'request_id'):
            response['X-Request-ID'] = request.request_id
        return response


class OpenTelemetryMiddleware(MiddlewareMixin):
    """
    OpenTelemetry middleware for distributed tracing.
    Note: This is a basic implementation. In production, use proper OpenTelemetry instrumentation.
    """
    
    def process_request(self, request):
        """
        Start a new span for the request.
        """
        # Store start time for request duration
        request._start_time = time.time()
        
        # In a real implementation, you would:
        # 1. Extract trace context from headers
        # 2. Start a new span
        # 3. Set span attributes
        
        return None
    
    def process_response(self, request, response):
        """
        End the span and record metrics.
        """
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            
            # Log request metrics
            logger.info(
                "Request completed",
                extra={
                    'request_id': getattr(request, 'request_id', 'unknown'),
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'duration_ms': round(duration * 1000, 2),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'remote_addr': self._get_client_ip(request),
                }
            )
        
        return response
    
    def _get_client_ip(self, request):
        """
        Get the client IP address from the request.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class HealthCheckMiddleware(MiddlewareMixin):
    """
    Middleware to handle health check requests efficiently.
    """
    
    def process_request(self, request):
        """
        Handle health check requests early in the middleware stack.
        """
        if request.path in ['/health/', '/health', '/api/health/', '/api/health']:
            from django.http import JsonResponse
            
            # Simple health check response
            health_data = {
                'status': 'healthy',
                'timestamp': time.time(),
                'service': 'notification-service'
            }
            
            return JsonResponse(health_data, status=200)
        
        return None