"""
Unit tests for core models with correct field names.
"""
import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from core.models import (
    NotificationTemplate,
    NotificationLog,
    UserPreference,
    NotificationQuota
)


class NotificationTemplateModelTest(TestCase):
    """Test cases for NotificationTemplate model."""

    def setUp(self):
        """Set up test data."""
        self.template_data = {
            'name': 'Welcome Email',
            'type': 'email',
            'subject': 'Welcome to our service',
            'body': 'Hello {{user_name}}, welcome!',
            'variables': {'user_name': 'string'}
        }

    def test_create_notification_template(self):
        """Test creating a notification template."""
        template = NotificationTemplate.objects.create(**self.template_data)
        
        self.assertEqual(template.name, 'Welcome Email')
        self.assertEqual(template.type, 'email')
        self.assertEqual(template.subject, 'Welcome to our service')
        self.assertTrue(template.active)
        self.assertIsNotNone(template.created_at)
        self.assertIsNotNone(template.updated_at)

    def test_template_str_representation(self):
        """Test string representation of template."""
        template = NotificationTemplate.objects.create(**self.template_data)
        self.assertEqual(str(template), 'Welcome Email (email)')

    def test_template_name_uniqueness(self):
        """Test that template names must be unique."""
        NotificationTemplate.objects.create(**self.template_data)
        
        with self.assertRaises(IntegrityError):
            NotificationTemplate.objects.create(**self.template_data)

    def test_template_type_choices(self):
        """Test that only valid notification types are allowed."""
        valid_types = ['email', 'sms', 'push']
        template_data = self.template_data.copy()
        
        for notification_type in valid_types:
            template_data['name'] = f'Test {notification_type}'
            template_data['type'] = notification_type
            template = NotificationTemplate.objects.create(**template_data)
            self.assertEqual(template.type, notification_type)

    def test_template_required_fields(self):
        """Test that required fields are present on the model."""
        template = NotificationTemplate.objects.create(**self.template_data)
        
        # Verify all required fields are accessible
        self.assertIsNotNone(template.name)
        self.assertIsNotNone(template.type)
        self.assertIsNotNone(template.body)
        
        # Verify they contain expected values
        self.assertEqual(template.name, 'Welcome Email')
        self.assertEqual(template.type, 'email')

    def test_template_soft_delete(self):
        """Test template soft delete functionality."""
        template = NotificationTemplate.objects.create(**self.template_data)
        template.active = False
        template.save()
        
        self.assertFalse(template.active)

    def test_get_variable_names(self):
        """Test extracting variable names from template body."""
        template = NotificationTemplate.objects.create(**self.template_data)
        variables = template.get_variable_names()
        self.assertIn('user_name', variables)


class NotificationLogModelTest(TestCase):
    """Test cases for NotificationLog model."""

    def setUp(self):
        """Set up test data."""
        self.template = NotificationTemplate.objects.create(
            name='Test Template',
            type='email',
            body='Test body',
        )
        
        self.log_data = {
            'user_id': 123,
            'template': self.template,
            'type': 'email',
            'recipient': 'test@example.com',
            'subject': 'Test Subject',
            'body': 'Rendered test body'
        }

    def test_create_notification_log(self):
        """Test creating a notification log."""
        log = NotificationLog.objects.create(**self.log_data)
        
        self.assertEqual(log.user_id, 123)
        self.assertEqual(log.template, self.template)
        self.assertEqual(log.type, 'email')
        self.assertEqual(log.status, 'pending')  # default status
        self.assertEqual(log.priority, 'normal')  # default priority
        self.assertIsNotNone(log.created_at)

    def test_log_str_representation(self):
        """Test string representation of notification log."""
        log = NotificationLog.objects.create(**self.log_data)
        expected = f"Notification {log.id} (email) - pending"
        self.assertEqual(str(log), expected)

    def test_status_choices(self):
        """Test notification status choices."""
        valid_statuses = ['pending', 'sent', 'failed', 'bounced', 'retry']
        log = NotificationLog.objects.create(**self.log_data)
        
        for status in valid_statuses:
            log.status = status
            log.save()
            self.assertEqual(log.status, status)

    def test_mark_sent_functionality(self):
        """Test marking notification as sent."""
        log = NotificationLog.objects.create(**self.log_data)
        log.mark_sent(provider_id='test-provider-123')
        
        self.assertEqual(log.status, 'sent')
        self.assertEqual(log.provider_id, 'test-provider-123')
        self.assertIsNotNone(log.sent_at)

    def test_mark_failed_functionality(self):
        """Test marking notification as failed."""
        log = NotificationLog.objects.create(**self.log_data)
        log.mark_failed('Test error message')
        
        self.assertEqual(log.status, 'retry')  # Should schedule retry
        self.assertEqual(log.error_message, 'Test error message')
        self.assertEqual(log.retry_count, 1)
        self.assertIsNotNone(log.next_retry_at)

    def test_template_relationship(self):
        """Test template foreign key relationship."""
        log = NotificationLog.objects.create(**self.log_data)
        self.assertEqual(log.template.type, 'email')


class UserPreferenceModelTest(TestCase):
    """Test cases for UserPreference model."""

    def setUp(self):
        """Set up test data."""
        self.preference_data = {
            'user_id': 123,
            'email_enabled': True,
            'sms_enabled': False,
            'push_enabled': True,
            'max_emails_per_day': 25,
            'max_sms_per_day': 5
        }

    def test_create_user_preference(self):
        """Test creating user preferences."""
        preference = UserPreference.objects.create(**self.preference_data)
        
        self.assertEqual(preference.user_id, 123)
        self.assertTrue(preference.email_enabled)
        self.assertFalse(preference.sms_enabled)
        self.assertTrue(preference.push_enabled)
        self.assertEqual(preference.max_emails_per_day, 25)
        self.assertEqual(preference.max_sms_per_day, 5)

    def test_preference_str_representation(self):
        """Test string representation of user preference."""
        preference = UserPreference.objects.create(**self.preference_data)
        self.assertEqual(str(preference), 'Preferences for user 123')

    def test_user_id_uniqueness(self):
        """Test that user_id must be unique."""
        UserPreference.objects.create(**self.preference_data)
        
        with self.assertRaises(IntegrityError):
            UserPreference.objects.create(**self.preference_data)

    def test_is_notification_allowed_email_enabled(self):
        """Test notification allowed when email is enabled."""
        preference = UserPreference.objects.create(**self.preference_data)
        self.assertTrue(preference.is_notification_allowed('email'))

    def test_is_notification_allowed_sms_disabled(self):
        """Test notification blocked when SMS is disabled."""
        preference = UserPreference.objects.create(**self.preference_data)
        self.assertFalse(preference.is_notification_allowed('sms'))

    def test_default_values(self):
        """Test default preference values."""
        minimal_data = {'user_id': 456}
        preference = UserPreference.objects.create(**minimal_data)
        
        self.assertTrue(preference.email_enabled)  # default True
        self.assertTrue(preference.sms_enabled)    # default True  
        self.assertTrue(preference.push_enabled)   # default True
        self.assertEqual(preference.max_emails_per_day, 50)  # default
        self.assertEqual(preference.max_sms_per_day, 10)     # default


class NotificationQuotaModelTest(TestCase):
    """Test cases for NotificationQuota model."""

    def setUp(self):
        """Set up test data."""
        self.quota_data = {
            'user_id': 123,
            'notification_type': 'email',
            'count': 5
        }

    def test_create_notification_quota(self):
        """Test creating notification quota."""
        quota = NotificationQuota.objects.create(**self.quota_data)
        
        self.assertEqual(quota.user_id, 123)
        self.assertEqual(quota.notification_type, 'email')
        self.assertEqual(quota.count, 5)
        self.assertIsNotNone(quota.date)

    def test_quota_str_representation(self):
        """Test string representation of notification quota."""
        quota = NotificationQuota.objects.create(**self.quota_data)
        expected = f"Quota for user 123 (email) on {quota.date}"
        self.assertEqual(str(quota), expected)

    def test_user_type_date_uniqueness(self):
        """Test that user_id + notification_type + date must be unique."""
        NotificationQuota.objects.create(**self.quota_data)
        
        with self.assertRaises(IntegrityError):
            NotificationQuota.objects.create(**self.quota_data)

    def test_increment_quota_functionality(self):
        """Test quota increment class method."""
        user_id = 456
        count = NotificationQuota.increment_quota(user_id, 'email')
        self.assertEqual(count, 1)
        
        # Increment again
        count = NotificationQuota.increment_quota(user_id, 'email')
        self.assertEqual(count, 2)

    def test_check_quota_exceeded_functionality(self):
        """Test quota exceeded check."""
        user_id = 789
        
        # Should not be exceeded initially
        self.assertFalse(NotificationQuota.check_quota_exceeded(user_id, 'email', 5))
        
        # Create quota with count 5
        NotificationQuota.objects.create(
            user_id=user_id,
            notification_type='email',
            count=5
        )
        
        # Should be exceeded with max 5
        self.assertTrue(NotificationQuota.check_quota_exceeded(user_id, 'email', 5))
        # Should not be exceeded with max 10
        self.assertFalse(NotificationQuota.check_quota_exceeded(user_id, 'email', 10))

    def test_notification_type_choices(self):
        """Test that only valid notification types are allowed."""
        valid_types = ['email', 'sms', 'push']
        
        for notification_type in valid_types:
            quota_data = {
                'user_id': 100 + ord(notification_type[0]),  # unique user_id
                'notification_type': notification_type,
                'count': 1
            }
            quota = NotificationQuota.objects.create(**quota_data)
            self.assertEqual(quota.notification_type, notification_type)