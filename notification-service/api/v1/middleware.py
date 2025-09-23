"""
Rate limiting middleware for API endpoints.
"""
import time
from typing import Dict
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status


class RateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting middleware using sliding window approach.
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.rate_limits = {
            'default': {'requests': 1000, 'window': 3600},  # 1000 requests per hour
            'notifications': {'requests': 100, 'window': 3600},  # 100 notifications per hour
            'templates': {'requests': 200, 'window': 3600},  # 200 template ops per hour
        }
    
    def process_request(self, request):
        """Process incoming request for rate limiting."""
        if not request.path.startswith('/api/'):
            return None
        
        # Get client identifier (IP address or user ID)
        client_id = self.get_client_identifier(request)
        
        # Determine rate limit category
        limit_key = self.get_rate_limit_key(request.path)
        rate_config = self.rate_limits.get(limit_key, self.rate_limits['default'])
        
        # Check rate limit
        if self.is_rate_limited(client_id, limit_key, rate_config):
            return JsonResponse(
                {
                    'error': 'Rate limit exceeded',
                    'message': f"Maximum {rate_config['requests']} requests per {rate_config['window']} seconds",
                    'retry_after': rate_config['window']
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        return None
    
    def get_client_identifier(self, request) -> str:
        """Get unique identifier for the client."""
        # Try to get user ID from request
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"user_{request.user.id}"
        
        # Fall back to IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        return f"ip_{ip}"
    
    def get_rate_limit_key(self, path: str) -> str:
        """Determine rate limit category based on path."""
        if '/notifications/' in path:
            return 'notifications'
        elif '/templates/' in path:
            return 'templates'
        else:
            return 'default'
    
    def is_rate_limited(self, client_id: str, limit_key: str, rate_config: Dict) -> bool:
        """Check if client has exceeded rate limit."""
        cache_key = f"rate_limit_{limit_key}_{client_id}"
        current_time = int(time.time())
        window_start = current_time - rate_config['window']
        
        # Get current request timestamps
        requests = cache.get(cache_key, [])
        
        # Remove requests outside the window
        requests = [req_time for req_time in requests if req_time > window_start]
        
        # Check if limit exceeded
        if len(requests) >= rate_config['requests']:
            return True
        
        # Add current request
        requests.append(current_time)
        
        # Update cache
        cache.set(cache_key, requests, rate_config['window'])
        
        return False


class APIVersionMiddleware(MiddlewareMixin):
    """
    Middleware to handle API versioning.
    """
    
    def process_request(self, request):
        """Add API version to request."""
        if request.path.startswith('/api/'):
            # Extract version from path
            path_parts = request.path.split('/')
            if len(path_parts) >= 3 and path_parts[2].startswith('v'):
                request.api_version = path_parts[2]
            else:
                request.api_version = 'v1'  # Default version
        
        return None


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log API requests for monitoring.
    """
    
    def process_request(self, request):
        """Log API request details."""
        if request.path.startswith('/api/'):
            import logging
            logger = logging.getLogger('api.requests')
            
            logger.info(
                f"API Request: {request.method} {request.path}",
                extra={
                    'method': request.method,
                    'path': request.path,
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'ip_address': request.META.get('REMOTE_ADDR', ''),
                }
            )
        
        return None
    
    def process_response(self, request, response):
        """Log API response details."""
        if request.path.startswith('/api/'):
            import logging
            logger = logging.getLogger('api.responses')
            
            logger.info(
                f"API Response: {request.method} {request.path} - {response.status_code}",
                extra={
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                }
            )
        
        return response