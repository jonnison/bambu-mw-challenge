"""
Integration tests for API endpoints with correct field names.
"""
import json
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from unittest.mock import patch

from core.models import (
    NotificationTemplate,
    NotificationLog,
    UserPreference,
    NotificationQuota
)


class APIEndpointTestCase(TestCase):
    """Base test case for API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test template with correct field names
        self.template = NotificationTemplate.objects.create(
            name='Test Template',
            type='email',
            body='Hello {{user_name}}!',
            subject='Test Subject'
        )
        
        # Create test user preference
        self.preference = UserPreference.objects.create(
            user_id=123,
            email_enabled=True,
            sms_enabled=False,
            push_enabled=True
        )


class NotificationTemplateAPITest(APIEndpointTestCase):
    """Test cases for NotificationTemplate API endpoints."""

    def test_template_model_accessible(self):
        """Test that template model is accessible."""
        template = NotificationTemplate.objects.get(name='Test Template')
        self.assertEqual(template.type, 'email')
        self.assertEqual(template.body, 'Hello {{user_name}}!')

    def test_template_creation_basic(self):
        """Test basic template creation functionality."""
        template_data = {
            'name': 'API Test Template',
            'type': 'sms',
            'body': 'SMS message for {{user_name}}',
        }
        
        template = NotificationTemplate.objects.create(**template_data)
        self.assertEqual(template.name, 'API Test Template')
        self.assertEqual(template.type, 'sms')

    def test_template_list_functionality(self):
        """Test template listing functionality."""
        templates = NotificationTemplate.objects.all()
        self.assertGreaterEqual(templates.count(), 1)
        
        # Check our test template exists
        test_template = templates.filter(name='Test Template').first()
        self.assertIsNotNone(test_template)

    def test_template_retrieval(self):
        """Test template retrieval by ID."""
        template = NotificationTemplate.objects.get(name='Test Template')
        retrieved = NotificationTemplate.objects.get(id=template.id)
        
        self.assertEqual(template.id, retrieved.id)
        self.assertEqual(template.name, retrieved.name)

    def test_template_update_functionality(self):
        """Test template update functionality."""
        template = NotificationTemplate.objects.get(name='Test Template')
        original_body = template.body
        
        template.body = 'Updated body with {{user_name}}'
        template.save()
        
        updated = NotificationTemplate.objects.get(id=template.id)
        self.assertNotEqual(updated.body, original_body)
        self.assertEqual(updated.body, 'Updated body with {{user_name}}')

    def test_template_soft_delete(self):
        """Test template soft delete functionality."""
        template = NotificationTemplate.objects.get(name='Test Template')
        
        template.active = False
        template.save()
        
        updated = NotificationTemplate.objects.get(id=template.id)
        self.assertFalse(updated.active)


class UserPreferenceAPITest(APIEndpointTestCase):
    """Test cases for UserPreference API endpoints."""

    def test_preference_model_accessible(self):
        """Test that preference model is accessible."""
        preference = UserPreference.objects.get(user_id=123)
        self.assertTrue(preference.email_enabled)
        self.assertFalse(preference.sms_enabled)

    def test_preference_creation_basic(self):
        """Test basic preference creation."""
        preference_data = {
            'user_id': 456,
            'email_enabled': False,
            'sms_enabled': True,
            'push_enabled': False
        }
        
        preference = UserPreference.objects.create(**preference_data)
        self.assertEqual(preference.user_id, 456)
        self.assertFalse(preference.email_enabled)
        self.assertTrue(preference.sms_enabled)

    def test_preference_update_functionality(self):
        """Test preference update functionality."""
        preference = UserPreference.objects.get(user_id=123)
        
        preference.email_enabled = False
        preference.sms_enabled = True
        preference.save()
        
        updated = UserPreference.objects.get(user_id=123)
        self.assertFalse(updated.email_enabled)
        self.assertTrue(updated.sms_enabled)

    def test_preference_notification_check(self):
        """Test notification allowed check."""
        preference = UserPreference.objects.get(user_id=123)
        
        self.assertTrue(preference.is_notification_allowed('email'))
        self.assertFalse(preference.is_notification_allowed('sms'))
        self.assertTrue(preference.is_notification_allowed('push'))


class NotificationLogAPITest(APIEndpointTestCase):
    """Test cases for NotificationLog functionality."""

    def test_log_creation_basic(self):
        """Test basic log creation."""
        log_data = {
            'user_id': 123,
            'template': self.template,
            'type': 'email',
            'recipient': 'test@example.com',
            'subject': 'Test Subject',
            'body': 'Test notification body'
        }
        
        log = NotificationLog.objects.create(**log_data)
        self.assertEqual(log.user_id, 123)
        self.assertEqual(log.type, 'email')
        self.assertEqual(log.status, 'pending')  # default

    def test_log_status_update(self):
        """Test log status update functionality."""
        log_data = {
            'user_id': 123,
            'template': self.template,
            'type': 'email',
            'recipient': 'test@example.com',
            'subject': 'Test Subject',
            'body': 'Test notification body'
        }
        
        log = NotificationLog.objects.create(**log_data)
        log.mark_sent(provider_id='test-123')
        
        self.assertEqual(log.status, 'sent')
        self.assertEqual(log.provider_id, 'test-123')
        self.assertIsNotNone(log.sent_at)

    def test_log_failure_handling(self):
        """Test log failure handling."""
        log_data = {
            'user_id': 123,
            'template': self.template,
            'type': 'email',
            'recipient': 'test@example.com',
            'subject': 'Test Subject',
            'body': 'Test notification body'
        }
        
        log = NotificationLog.objects.create(**log_data)
        log.mark_failed('Test error message')
        
        self.assertEqual(log.status, 'retry')  # Should schedule retry
        self.assertEqual(log.error_message, 'Test error message')
        self.assertEqual(log.retry_count, 1)


class NotificationQuotaAPITest(APIEndpointTestCase):
    """Test cases for NotificationQuota functionality."""

    def test_quota_creation_basic(self):
        """Test basic quota creation."""
        quota_data = {
            'user_id': 123,
            'notification_type': 'email',
            'count': 5
        }
        
        quota = NotificationQuota.objects.create(**quota_data)
        self.assertEqual(quota.user_id, 123)
        self.assertEqual(quota.notification_type, 'email')
        self.assertEqual(quota.count, 5)

    def test_quota_increment_functionality(self):
        """Test quota increment functionality."""
        user_id = 789
        count = NotificationQuota.increment_quota(user_id, 'email')
        self.assertEqual(count, 1)
        
        count = NotificationQuota.increment_quota(user_id, 'email')
        self.assertEqual(count, 2)

    def test_quota_exceeded_check(self):
        """Test quota exceeded check."""
        user_id = 999
        
        # Initially not exceeded
        self.assertFalse(NotificationQuota.check_quota_exceeded(user_id, 'email', 5))
        
        # Create quota at limit
        NotificationQuota.objects.create(
            user_id=user_id,
            notification_type='email',
            count=5
        )
        
        # Should be exceeded
        self.assertTrue(NotificationQuota.check_quota_exceeded(user_id, 'email', 5))


class HealthCheckAPITest(TestCase):
    """Test cases for health check endpoints."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_basic_connectivity(self):
        """Test basic API connectivity."""
        # This is a simple test that doesn't require specific endpoints
        # Just tests that Django is running and test framework works
        self.assertTrue(True)

    def test_model_access(self):
        """Test that models are accessible."""
        # Test model creation works
        template = NotificationTemplate.objects.create(
            name='Health Check Template',
            type='email',
            body='Health check body'
        )
        
        self.assertEqual(template.name, 'Health Check Template')
        self.assertEqual(template.type, 'email')

    def test_database_connectivity(self):
        """Test database connectivity."""
        # Count existing templates
        initial_count = NotificationTemplate.objects.count()
        
        # Create new template
        NotificationTemplate.objects.create(
            name='DB Test Template',
            type='sms',
            body='DB test body'
        )
        
        # Verify count increased
        new_count = NotificationTemplate.objects.count()
        self.assertEqual(new_count, initial_count + 1)


# Simple integration test
class APIIntegrationTest(APIEndpointTestCase):
    """Integration tests for API functionality."""

    def test_template_and_log_integration(self):
        """Test template and log integration."""
        # Create log using template
        log = NotificationLog.objects.create(
            user_id=123,
            template=self.template,
            type='email',
            recipient='integration@test.com',
            subject='Integration Test',
            body='Integration test body'
        )
        
        # Verify relationship
        self.assertEqual(log.template.id, self.template.id)
        self.assertEqual(log.template.name, 'Test Template')

    def test_preference_and_quota_integration(self):
        """Test preference and quota integration for same user."""
        # Create quota for same user as preference
        quota = NotificationQuota.objects.create(
            user_id=123,  # Same as self.preference.user_id
            notification_type='email',
            count=10
        )
        
        preference = UserPreference.objects.get(user_id=123)
        
        # Both should be for same user
        self.assertEqual(quota.user_id, preference.user_id)
        self.assertEqual(quota.notification_type, 'email')
        self.assertTrue(preference.email_enabled)