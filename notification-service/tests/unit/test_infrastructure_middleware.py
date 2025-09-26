"""
Comprehensive tests for infrastructure middleware to achieve 100% coverage.
"""
import uuid
import time
import logging
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, RequestFactory
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin

from infrastructure.middleware import (
    RequestIDMiddleware,
    OpenTelemetryMiddleware,
    HealthCheckMiddleware
)


class RequestIDMiddlewareTest(TestCase):
    """Test cases for RequestIDMiddleware."""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = Mock()
        self.middleware = RequestIDMiddleware(self.get_response)
    
    def test_process_request_generates_request_id(self):
        """Test that process_request generates a unique request ID."""
        request = self.factory.get('/')
        
        # Before processing, request should not have request_id
        self.assertFalse(hasattr(request, 'request_id'))
        self.assertNotIn('X-Request-ID', request.META)
        
        # Process request
        result = self.middleware.process_request(request)
        
        # Should return None (continue processing)
        self.assertIsNone(result)
        
        # Should have generated request_id
        self.assertTrue(hasattr(request, 'request_id'))
        self.assertIn('X-Request-ID', request.META)
        
        # Should be valid UUID
        uuid.UUID(request.request_id)  # Will raise ValueError if invalid
        self.assertEqual(request.request_id, request.META['X-Request-ID'])
    
    def test_process_request_generates_different_ids(self):
        """Test that different requests get different IDs."""
        request1 = self.factory.get('/')
        request2 = self.factory.get('/')
        
        self.middleware.process_request(request1)
        self.middleware.process_request(request2)
        
        self.assertNotEqual(request1.request_id, request2.request_id)
    
    def test_process_response_adds_request_id_to_headers(self):
        """Test that process_response adds request ID to response headers."""
        request = self.factory.get('/')
        response = HttpResponse()
        
        # Process request first to generate ID
        self.middleware.process_request(request)
        request_id = request.request_id
        
        # Process response
        result = self.middleware.process_response(request, response)
        
        # Should return the same response
        self.assertEqual(result, response)
        
        # Should have X-Request-ID header
        self.assertEqual(response['X-Request-ID'], request_id)
    
    def test_process_response_without_request_id(self):
        """Test process_response when request doesn't have request_id."""
        request = self.factory.get('/')
        response = HttpResponse()
        
        # Don't process request, so no request_id
        result = self.middleware.process_response(request, response)
        
        # Should return the same response
        self.assertEqual(result, response)
        
        # Should not have X-Request-ID header
        self.assertNotIn('X-Request-ID', response)


class OpenTelemetryMiddlewareTest(TestCase):
    """Test cases for OpenTelemetryMiddleware."""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = Mock()
        self.middleware = OpenTelemetryMiddleware(self.get_response)
    
    def test_process_request_sets_start_time(self):
        """Test that process_request sets start time."""
        request = self.factory.get('/')
        
        with patch('time.time', return_value=123456.789):
            result = self.middleware.process_request(request)
        
        # Should return None (continue processing)
        self.assertIsNone(result)
        
        # Should have start time set
        self.assertTrue(hasattr(request, '_start_time'))
        self.assertEqual(request._start_time, 123456.789)
    
    @patch('infrastructure.middleware.logger')
    def test_process_response_logs_metrics(self, mock_logger):
        """Test that process_response logs request metrics."""
        request = self.factory.get('/test-path')
        request.method = 'POST'
        request.request_id = 'test-request-id'
        request.META['HTTP_USER_AGENT'] = 'Test Agent'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        response = HttpResponse(status=201)
        
        # Set start time
        start_time = 123456.789
        end_time = 123456.889  # 100ms later
        request._start_time = start_time
        
        with patch('time.time', return_value=end_time):
            result = self.middleware.process_response(request, response)
        
        # Should return the same response
        self.assertEqual(result, response)
        
        # Should have logged the request
        mock_logger.info.assert_called_once_with(
            "Request completed",
            extra={
                'request_id': 'test-request-id',
                'method': 'POST',
                'path': '/test-path',
                'status_code': 201,
                'duration_ms': 100.0,
                'user_agent': 'Test Agent',
                'remote_addr': '192.168.1.1',
            }
        )
    
    @patch('infrastructure.middleware.logger')
    def test_process_response_without_start_time(self, mock_logger):
        """Test process_response when request doesn't have start time."""
        request = self.factory.get('/')
        response = HttpResponse()
        
        # Don't set start time
        result = self.middleware.process_response(request, response)
        
        # Should return the same response
        self.assertEqual(result, response)
        
        # Should not have logged anything
        mock_logger.info.assert_not_called()
    
    @patch('infrastructure.middleware.logger')
    def test_process_response_without_request_id(self, mock_logger):
        """Test process_response when request doesn't have request_id."""
        request = self.factory.get('/test-path')
        request.method = 'GET'
        request.META['HTTP_USER_AGENT'] = 'Test Agent'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        response = HttpResponse(status=200)
        
        # Set start time but no request_id
        request._start_time = 123456.789
        
        with patch('time.time', return_value=123456.839):
            result = self.middleware.process_response(request, response)
        
        # Should return the same response
        self.assertEqual(result, response)
        
        # Should have logged with 'unknown' request_id
        mock_logger.info.assert_called_once_with(
            "Request completed",
            extra={
                'request_id': 'unknown',
                'method': 'GET',
                'path': '/test-path',
                'status_code': 200,
                'duration_ms': 50.0,
                'user_agent': 'Test Agent',
                'remote_addr': '192.168.1.1',
            }
        )
    
    def test_get_client_ip_with_x_forwarded_for(self):
        """Test _get_client_ip with X-Forwarded-For header."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1, 10.0.0.2, 10.0.0.3'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        ip = self.middleware._get_client_ip(request)
        
        # Should return the first IP from X-Forwarded-For
        self.assertEqual(ip, '10.0.0.1')
    
    def test_get_client_ip_without_x_forwarded_for(self):
        """Test _get_client_ip without X-Forwarded-For header."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        ip = self.middleware._get_client_ip(request)
        
        # Should return REMOTE_ADDR
        self.assertEqual(ip, '192.168.1.1')
    
    def test_get_client_ip_without_any_ip(self):
        """Test _get_client_ip without any IP headers."""
        request = self.factory.get('/')
        # Remove REMOTE_ADDR that RequestFactory adds by default
        if 'REMOTE_ADDR' in request.META:
            del request.META['REMOTE_ADDR']
        
        ip = self.middleware._get_client_ip(request)
        
        # Should return None
        self.assertIsNone(ip)
    
    @patch('infrastructure.middleware.logger')
    def test_process_response_empty_user_agent(self, mock_logger):
        """Test process_response with empty user agent."""
        request = self.factory.get('/test-path')
        request.method = 'GET'
        request.request_id = 'test-request-id'
        # No HTTP_USER_AGENT in META
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        response = HttpResponse(status=200)
        
        request._start_time = 123456.789
        
        with patch('time.time', return_value=123456.839):
            result = self.middleware.process_response(request, response)
        
        # Should have logged with empty user_agent
        mock_logger.info.assert_called_once_with(
            "Request completed",
            extra={
                'request_id': 'test-request-id',
                'method': 'GET',
                'path': '/test-path',
                'status_code': 200,
                'duration_ms': 50.0,
                'user_agent': '',
                'remote_addr': '192.168.1.1',
            }
        )


class HealthCheckMiddlewareTest(TestCase):
    """Test cases for HealthCheckMiddleware."""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = Mock()
        self.middleware = HealthCheckMiddleware(self.get_response)
    
    @patch('time.time', return_value=1234567890.123)
    def test_process_request_health_endpoint_slash(self, mock_time):
        """Test process_request with /health/ endpoint."""
        request = self.factory.get('/health/')
        
        result = self.middleware.process_request(request)
        
        # Should return JsonResponse
        self.assertIsInstance(result, JsonResponse)
        self.assertEqual(result.status_code, 200)
        
        # Check response content
        import json
        content = json.loads(result.content)
        expected = {
            'status': 'healthy',
            'timestamp': 1234567890.123,
            'service': 'notification-service'
        }
        self.assertEqual(content, expected)
    
    @patch('time.time', return_value=1234567890.456)
    def test_process_request_health_endpoint_no_slash(self, mock_time):
        """Test process_request with /health endpoint (no trailing slash)."""
        request = self.factory.get('/health')
        
        result = self.middleware.process_request(request)
        
        # Should return JsonResponse
        self.assertIsInstance(result, JsonResponse)
        self.assertEqual(result.status_code, 200)
        
        # Check response content
        import json
        content = json.loads(result.content)
        expected = {
            'status': 'healthy',
            'timestamp': 1234567890.456,
            'service': 'notification-service'
        }
        self.assertEqual(content, expected)
    
    @patch('time.time', return_value=1234567890.789)
    def test_process_request_api_health_endpoint_slash(self, mock_time):
        """Test process_request with /api/health/ endpoint."""
        request = self.factory.get('/api/health/')
        
        result = self.middleware.process_request(request)
        
        # Should return JsonResponse
        self.assertIsInstance(result, JsonResponse)
        self.assertEqual(result.status_code, 200)
        
        # Check response content
        import json
        content = json.loads(result.content)
        expected = {
            'status': 'healthy',
            'timestamp': 1234567890.789,
            'service': 'notification-service'
        }
        self.assertEqual(content, expected)
    
    @patch('time.time', return_value=1234567890.999)
    def test_process_request_api_health_endpoint_no_slash(self, mock_time):
        """Test process_request with /api/health endpoint (no trailing slash)."""
        request = self.factory.get('/api/health')
        
        result = self.middleware.process_request(request)
        
        # Should return JsonResponse
        self.assertIsInstance(result, JsonResponse)
        self.assertEqual(result.status_code, 200)
        
        # Check response content
        import json
        content = json.loads(result.content)
        expected = {
            'status': 'healthy',
            'timestamp': 1234567890.999,
            'service': 'notification-service'
        }
        self.assertEqual(content, expected)
    
    def test_process_request_non_health_endpoint(self):
        """Test process_request with non-health endpoint."""
        request = self.factory.get('/api/v1/notifications/')
        
        result = self.middleware.process_request(request)
        
        # Should return None (continue processing)
        self.assertIsNone(result)
    
    def test_process_request_similar_but_not_health_endpoint(self):
        """Test process_request with similar but not exact health endpoint."""
        # Test endpoints that contain 'health' but aren't exact matches
        test_paths = [
            '/healthcheck/',
            '/api/healthz/',
            '/health-check/',
            '/api/v1/health/',
            '/health/status/',
        ]
        
        for path in test_paths:
            with self.subTest(path=path):
                request = self.factory.get(path)
                result = self.middleware.process_request(request)
                # Should return None (continue processing)
                self.assertIsNone(result)


class MiddlewareIntegrationTest(TestCase):
    """Integration tests for all middleware working together."""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = Mock()
        self.request_id_middleware = RequestIDMiddleware(self.get_response)
        self.telemetry_middleware = OpenTelemetryMiddleware(self.get_response)
        self.health_middleware = HealthCheckMiddleware(self.get_response)
    
    def test_middleware_chain_normal_request(self):
        """Test middleware chain for a normal request."""
        request = self.factory.get('/api/v1/notifications/')
        response = HttpResponse()
        
        # Process through middleware chain
        # 1. Health check (should pass through)
        health_result = self.health_middleware.process_request(request)
        self.assertIsNone(health_result)
        
        # 2. Request ID
        request_id_result = self.request_id_middleware.process_request(request)
        self.assertIsNone(request_id_result)
        
        # 3. Telemetry
        telemetry_result = self.telemetry_middleware.process_request(request)
        self.assertIsNone(telemetry_result)
        
        # Verify request state
        self.assertTrue(hasattr(request, 'request_id'))
        self.assertTrue(hasattr(request, '_start_time'))
        self.assertIn('X-Request-ID', request.META)
        
        # Process response through middleware chain (reverse order)
        with patch('infrastructure.middleware.logger') as mock_logger:
            # 1. Telemetry response
            telemetry_response = self.telemetry_middleware.process_response(request, response)
            self.assertEqual(telemetry_response, response)
            
            # 2. Request ID response
            final_response = self.request_id_middleware.process_response(request, telemetry_response)
            self.assertEqual(final_response, response)
            
            # Verify final response
            self.assertEqual(final_response['X-Request-ID'], request.request_id)
            
            # Verify logging occurred
            mock_logger.info.assert_called_once()
    
    def test_middleware_chain_health_request(self):
        """Test middleware chain for a health check request."""
        request = self.factory.get('/health/')
        
        # Health middleware should short-circuit
        with patch('time.time', return_value=1234567890.123):
            result = self.health_middleware.process_request(request)
        
        # Should return JsonResponse directly
        self.assertIsInstance(result, JsonResponse)
        self.assertEqual(result.status_code, 200)
        
        # Other middleware shouldn't be needed for health check
        # but let's verify they work if called
        request_id_result = self.request_id_middleware.process_request(request)
        self.assertIsNone(request_id_result)
        
        telemetry_result = self.telemetry_middleware.process_request(request)
        self.assertIsNone(telemetry_result)


class MiddlewareInheritanceTest(TestCase):
    """Test that middleware classes properly inherit from MiddlewareMixin."""
    
    def test_request_id_middleware_inheritance(self):
        """Test RequestIDMiddleware inherits from MiddlewareMixin."""
        self.assertTrue(issubclass(RequestIDMiddleware, MiddlewareMixin))
        
        get_response = Mock()
        middleware = RequestIDMiddleware(get_response)
        self.assertIsInstance(middleware, MiddlewareMixin)
    
    def test_opentelemetry_middleware_inheritance(self):
        """Test OpenTelemetryMiddleware inherits from MiddlewareMixin."""
        self.assertTrue(issubclass(OpenTelemetryMiddleware, MiddlewareMixin))
        
        get_response = Mock()
        middleware = OpenTelemetryMiddleware(get_response)
        self.assertIsInstance(middleware, MiddlewareMixin)
    
    def test_health_check_middleware_inheritance(self):
        """Test HealthCheckMiddleware inherits from MiddlewareMixin."""
        self.assertTrue(issubclass(HealthCheckMiddleware, MiddlewareMixin))
        
        get_response = Mock()
        middleware = HealthCheckMiddleware(get_response)
        self.assertIsInstance(middleware, MiddlewareMixin)


class MiddlewareLoggingTest(TestCase):
    """Test logging configuration and behavior in middleware."""
    
    def test_logger_configuration(self):
        """Test that logger is properly configured."""
        from infrastructure.middleware import logger
        
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, 'infrastructure.middleware')
    
    @patch('infrastructure.middleware.logger')
    def test_telemetry_middleware_logging_levels(self, mock_logger):
        """Test that telemetry middleware logs at correct level."""
        factory = RequestFactory()
        get_response = Mock()
        middleware = OpenTelemetryMiddleware(get_response)
        
        request = factory.get('/test')
        request.request_id = 'test-id'
        request._start_time = 123456.789
        response = HttpResponse()
        
        with patch('time.time', return_value=123456.839):
            middleware.process_response(request, response)
        
        # Should call info level
        mock_logger.info.assert_called_once()
        mock_logger.debug.assert_not_called()
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()


class MiddlewareErrorHandlingTest(TestCase):
    """Test error handling in middleware."""
    
    def test_request_id_middleware_uuid_generation(self):
        """Test that UUID generation doesn't fail."""
        factory = RequestFactory()
        get_response = Mock()
        middleware = RequestIDMiddleware(get_response)
        request = factory.get('/')
        
        # Should not raise any exceptions
        result = middleware.process_request(request)
        self.assertIsNone(result)
        
        # Should generate valid UUID
        self.assertTrue(hasattr(request, 'request_id'))
        # This will raise ValueError if not a valid UUID
        uuid.UUID(request.request_id)
    
    def test_telemetry_middleware_time_calculation(self):
        """Test time calculation in telemetry middleware."""
        factory = RequestFactory()
        get_response = Mock()
        middleware = OpenTelemetryMiddleware(get_response)
        
        request = factory.get('/')
        request.request_id = 'test-id'
        response = HttpResponse()
        
        # Test with very small time difference
        request._start_time = 123456.789123
        
        with patch('time.time', return_value=123456.789124):  # 0.001ms difference
            with patch('infrastructure.middleware.logger') as mock_logger:
                result = middleware.process_response(request, response)
                
                self.assertEqual(result, response)
                
                # Check that duration was calculated correctly
                call_args = mock_logger.info.call_args[1]['extra']
                self.assertEqual(call_args['duration_ms'], 0.0)  # Rounded to 0.0
    
    def test_health_middleware_json_response_creation(self):
        """Test that health middleware creates proper JsonResponse."""
        factory = RequestFactory()
        get_response = Mock()
        middleware = HealthCheckMiddleware(get_response)
        
        request = factory.get('/health/')
        
        with patch('time.time', return_value=1234567890.123456):
            result = middleware.process_request(request)
        
        self.assertIsInstance(result, JsonResponse)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result['Content-Type'], 'application/json')
        
        # Verify JSON content structure
        import json
        content = json.loads(result.content)
        self.assertIn('status', content)
        self.assertIn('timestamp', content)
        self.assertIn('service', content)
        self.assertEqual(content['status'], 'healthy')
        self.assertEqual(content['service'], 'notification-service')
        self.assertIsInstance(content['timestamp'], float)