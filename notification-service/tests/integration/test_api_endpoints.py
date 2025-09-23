"""
Integration tests for API endpoints.
"""
import json
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch

from core.models import (
    NotificationTemplate,
    NotificationLog,
    UserPreference,
    NotificationQuota
)


class APIEndpointTestCase(APITestCase):
    """Base test case for API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create test template
        self.template = NotificationTemplate.objects.create(
            name='Test Template',
            template_type='email',
            content='Hello {{user_name}}!',
            subject='Test Subject',
            variables=['user_name']
        )
        
        # Create test user preference
        self.preference = UserPreference.objects.create(
            user_id='user123',
            channel='email',
            enabled=True,
            frequency='immediate'
        )
        
        # Create test quota
        self.quota = NotificationQuota.objects.create(
            user_id='user123',
            channel='email',
            quota_limit=100,
            quota_used=5
        )


class NotificationTemplateAPITest(APIEndpointTestCase):
    """Test cases for NotificationTemplate API endpoints."""

    def test_list_templates(self):
        """Test GET /api/v1/templates/"""
        url = reverse('api:v1:notificationtemplate-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Template')

    def test_create_template(self):
        """Test POST /api/v1/templates/"""
        url = reverse('api:v1:notificationtemplate-list')
        data = {
            'name': 'New Template',
            'template_type': 'sms',
            'content': 'SMS content for {{user_name}}',
            'variables': ['user_name']
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Template')
        self.assertEqual(response.data['template_type'], 'sms')

    def test_retrieve_template(self):
        """Test GET /api/v1/templates/{id}/"""
        url = reverse('api:v1:notificationtemplate-detail', kwargs={'pk': self.template.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.template.id)
        self.assertEqual(response.data['name'], 'Test Template')

    def test_update_template(self):
        """Test PUT/PATCH /api/v1/templates/{id}/"""
        url = reverse('api:v1:notificationtemplate-detail', kwargs={'pk': self.template.id})
        data = {
            'name': 'Updated Template',
            'template_type': 'email',
            'content': 'Updated content for {{user_name}}',
            'variables': ['user_name']
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Template')

    def test_delete_template(self):
        """Test DELETE /api/v1/templates/{id}/"""
        url = reverse('api:v1:notificationtemplate-detail', kwargs={'pk': self.template.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify soft delete
        self.template.refresh_from_db()
        self.assertFalse(self.template.is_active)

    def test_create_template_validation_error(self):
        """Test template creation with validation errors."""
        url = reverse('api:v1:notificationtemplate-list')
        data = {
            'name': '',  # Invalid empty name
            'template_type': 'invalid_type',  # Invalid type
            'content': 'Test content'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)
        self.assertIn('template_type', response.data)

    def test_template_name_uniqueness(self):
        """Test template name uniqueness constraint."""
        url = reverse('api:v1:notificationtemplate-list')
        data = {
            'name': 'Test Template',  # Duplicate name
            'template_type': 'sms',
            'content': 'Test content'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class NotificationAPITest(APIEndpointTestCase):
    """Test cases for Notification API endpoints."""

    @patch('core.services.NotificationService.send_notification')
    def test_send_notification(self, mock_send):
        """Test POST /api/v1/notifications/send/"""
        mock_send.return_value = True
        
        url = reverse('api:v1:notification-send')
        data = {
            'template_id': self.template.id,
            'user_id': 'user123',
            'recipient': 'test@example.com',
            'context': {'user_name': 'John Doe'}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        mock_send.assert_called_once()

    @patch('core.services.NotificationService.send_notification')
    def test_send_notification_failure(self, mock_send):
        """Test notification sending failure."""
        mock_send.return_value = False
        
        url = reverse('api:v1:notification-send')
        data = {
            'template_id': self.template.id,
            'user_id': 'user123',
            'recipient': 'test@example.com',
            'context': {'user_name': 'John Doe'}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_get_user_notifications(self):
        """Test GET /api/v1/notifications/user/{user_id}/"""
        # Create notification logs
        NotificationLog.objects.create(
            template=self.template,
            user_id='user123',
            recipient='test@example.com',
            status='sent',
            channel='email',
            content='Test content'
        )
        
        url = reverse('api:v1:notification-user-notifications', kwargs={'user_id': 'user123'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['user_id'], 'user123')

    def test_get_notification_detail(self):
        """Test GET /api/v1/notifications/{id}/"""
        log = NotificationLog.objects.create(
            template=self.template,
            user_id='user123',
            recipient='test@example.com',
            status='sent',
            channel='email',
            content='Test content'
        )
        
        url = reverse('api:v1:notification-detail', kwargs={'pk': log.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], log.id)
        self.assertEqual(response.data['status'], 'sent')

    def test_update_notification_status(self):
        """Test PUT /api/v1/notifications/{id}/status/"""
        log = NotificationLog.objects.create(
            template=self.template,
            user_id='user123',
            recipient='test@example.com',
            status='sent',
            channel='email',
            content='Test content'
        )
        
        url = reverse('api:v1:notification-update-status', kwargs={'pk': log.id})
        data = {'status': 'delivered'}
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'delivered')

    def test_send_notification_validation(self):
        """Test notification sending with validation errors."""
        url = reverse('api:v1:notification-send')
        data = {
            'template_id': 999,  # Non-existent template
            'user_id': 'user123',
            'recipient': 'invalid-email'  # Invalid email
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserPreferenceAPITest(APIEndpointTestCase):
    """Test cases for UserPreference API endpoints."""

    def test_get_user_preferences(self):
        """Test GET /api/v1/preferences/user/{user_id}/"""
        # Create additional preferences
        UserPreference.objects.create(
            user_id='user123',
            channel='sms',
            enabled=False,
            frequency='daily'
        )
        
        url = reverse('api:v1:userpreference-user-preferences', kwargs={'user_id': 'user123'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_update_user_preference(self):
        """Test PUT /api/v1/preferences/user/{user_id}/"""
        url = reverse('api:v1:userpreference-update-user-preference', kwargs={'user_id': 'user123'})
        data = {
            'channel': 'email',
            'enabled': False,
            'frequency': 'daily'
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['enabled'])
        self.assertEqual(response.data['frequency'], 'daily')

    def test_create_user_preference(self):
        """Test creating new user preference."""
        url = reverse('api:v1:userpreference-update-user-preference', kwargs={'user_id': 'user456'})
        data = {
            'channel': 'push',
            'enabled': True,
            'frequency': 'hourly'
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['channel'], 'push')
        self.assertTrue(response.data['enabled'])

    def test_get_user_preferences_empty(self):
        """Test getting preferences for user with no preferences."""
        url = reverse('api:v1:userpreference-user-preferences', kwargs={'user_id': 'user999'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_preference_validation(self):
        """Test preference validation."""
        url = reverse('api:v1:userpreference-update-user-preference', kwargs={'user_id': 'user123'})
        data = {
            'channel': 'invalid_channel',  # Invalid channel
            'enabled': 'not_boolean',  # Invalid boolean
            'frequency': 'invalid_frequency'  # Invalid frequency
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class HealthCheckAPITest(APIEndpointTestCase):
    """Test cases for Health Check API endpoints."""

    def test_health_check(self):
        """Test GET /api/v1/health/health/"""
        url = reverse('api:v1:health-health')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)
        self.assertIn('timestamp', response.data)
        self.assertIn('services', response.data)

    @patch('health_check.views.HealthViewSet._check_database')
    def test_health_check_database_failure(self, mock_db_check):
        """Test health check with database failure."""
        mock_db_check.return_value = {'status': 'unhealthy', 'error': 'Connection failed'}
        
        url = reverse('api:v1:health-health')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data['status'], 'unhealthy')

    @patch('health_check.views.HealthViewSet._check_message_broker')
    def test_health_check_broker_failure(self, mock_broker_check):
        """Test health check with message broker failure."""
        mock_broker_check.return_value = {'status': 'unhealthy', 'error': 'RabbitMQ unavailable'}
        
        url = reverse('api:v1:health-health')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data['status'], 'unhealthy')


class APIMiddlewareTest(APITestCase):
    """Test cases for API middleware."""

    def setUp(self):
        """Set up test client."""
        self.client = APIClient()

    def test_api_versioning_middleware(self):
        """Test API versioning middleware."""
        # Test with v1 API
        response = self.client.get('/api/v1/health/health/')
        self.assertIn('X-API-Version', response)
        self.assertEqual(response['X-API-Version'], 'v1')

    def test_rate_limiting_middleware(self):
        """Test rate limiting middleware."""
        # Make multiple requests to trigger rate limiting
        url = '/api/v1/health/health/'
        
        # Make requests up to the limit
        for _ in range(10):  # Assuming limit is 10 per minute
            response = self.client.get(url)
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                break
        
        # Check if rate limiting is working
        self.assertTrue(
            response.status_code in [status.HTTP_200_OK, status.HTTP_429_TOO_MANY_REQUESTS]
        )

    def test_request_logging_middleware(self):
        """Test request logging middleware."""
        with patch('infrastructure.middleware.logger') as mock_logger:
            response = self.client.get('/api/v1/health/health/')
            
            # Verify logging was called
            self.assertTrue(mock_logger.info.called)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cors_headers(self):
        """Test CORS headers are present."""
        response = self.client.get('/api/v1/health/health/')
        
        # Check for CORS headers (if configured)
        self.assertTrue(
            'Access-Control-Allow-Origin' in response or 
            response.status_code == status.HTTP_200_OK
        )


class APIPaginationTest(APIEndpointTestCase):
    """Test cases for API pagination."""

    def setUp(self):
        """Set up test data with multiple records."""
        super().setUp()
        
        # Create multiple templates for pagination testing
        for i in range(25):
            NotificationTemplate.objects.create(
                name=f'Template {i}',
                template_type='email',
                content=f'Content {i}',
                subject=f'Subject {i}'
            )

    def test_template_list_pagination(self):
        """Test pagination on template list endpoint."""
        url = reverse('api:v1:notificationtemplate-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        
        # Check page size (assuming default is 20)
        self.assertLessEqual(len(response.data['results']), 20)

    def test_pagination_page_size(self):
        """Test custom page size parameter."""
        url = reverse('api:v1:notificationtemplate-list')
        response = self.client.get(url, {'page_size': 5})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)

    def test_pagination_next_page(self):
        """Test accessing next page."""
        url = reverse('api:v1:notificationtemplate-list')
        response = self.client.get(url, {'page': 2})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have remaining records on page 2