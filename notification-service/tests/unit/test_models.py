"""
Unit tests for core models.
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
            'template_type': 'email',
            'subject': 'Welcome to our service',
            'content': 'Hello {{user_name}}, welcome!',
            'variables': ['user_name']
        }

    def test_create_notification_template(self):
        """Test creating a notification template."""
        template = NotificationTemplate.objects.create(**self.template_data)
        
        self.assertEqual(template.name, 'Welcome Email')
        self.assertEqual(template.template_type, 'email')
        self.assertEqual(template.subject, 'Welcome to our service')
        self.assertTrue(template.is_active)
        self.assertIsNotNone(template.created_at)
        self.assertIsNotNone(template.updated_at)

    def test_template_str_representation(self):
        """Test string representation of template."""
        template = NotificationTemplate.objects.create(**self.template_data)
        self.assertEqual(str(template), 'Welcome Email')

    def test_template_name_uniqueness(self):
        """Test that template names must be unique."""
        NotificationTemplate.objects.create(**self.template_data)
        
        with self.assertRaises(IntegrityError):
            NotificationTemplate.objects.create(**self.template_data)

    def test_template_type_choices(self):
        """Test template type validation."""
        valid_types = ['email', 'sms', 'push', 'in_app']
        
        for template_type in valid_types:
            template_data = self.template_data.copy()
            template_data['name'] = f'Test {template_type}'
            template_data['template_type'] = template_type
            template = NotificationTemplate.objects.create(**template_data)
            self.assertEqual(template.template_type, template_type)

    def test_template_required_fields(self):
        """Test that required fields are enforced."""
        required_fields = ['name', 'template_type', 'content']
        
        for field in required_fields:
            template_data = self.template_data.copy()
            del template_data[field]
            
            with self.assertRaises(IntegrityError):
                NotificationTemplate.objects.create(**template_data)

    def test_template_soft_delete(self):
        """Test soft delete functionality."""
        template = NotificationTemplate.objects.create(**self.template_data)
        template.soft_delete()
        
        self.assertFalse(template.is_active)
        self.assertIsNotNone(template.deleted_at)


class NotificationLogModelTest(TestCase):
    """Test cases for NotificationLog model."""

    def setUp(self):
        """Set up test data."""
        self.template = NotificationTemplate.objects.create(
            name='Test Template',
            template_type='email',
            content='Test content',
            subject='Test subject'
        )
        
        self.log_data = {
            'template': self.template,
            'user_id': 'user123',
            'recipient': 'test@example.com',
            'status': 'pending',
            'channel': 'email',
            'content': 'Rendered test content'
        }

    def test_create_notification_log(self):
        """Test creating a notification log."""
        log = NotificationLog.objects.create(**self.log_data)
        
        self.assertEqual(log.template, self.template)
        self.assertEqual(log.user_id, 'user123')
        self.assertEqual(log.recipient, 'test@example.com')
        self.assertEqual(log.status, 'pending')
        self.assertEqual(log.channel, 'email')
        self.assertIsNotNone(log.created_at)

    def test_log_str_representation(self):
        """Test string representation of notification log."""
        log = NotificationLog.objects.create(**self.log_data)
        expected = f"Notification to user123 via email (pending)"
        self.assertEqual(str(log), expected)

    def test_status_choices(self):
        """Test status field validation."""
        valid_statuses = ['pending', 'sent', 'delivered', 'failed', 'read']
        
        for status in valid_statuses:
            log_data = self.log_data.copy()
            log_data['status'] = status
            log = NotificationLog.objects.create(**log_data)
            self.assertEqual(log.status, status)

    def test_channel_choices(self):
        """Test channel field validation."""
        valid_channels = ['email', 'sms', 'push', 'in_app']
        
        for channel in valid_channels:
            log_data = self.log_data.copy()
            log_data['channel'] = channel
            log = NotificationLog.objects.create(**log_data)
            self.assertEqual(log.channel, channel)

    def test_template_relationship(self):
        """Test template foreign key relationship."""
        log = NotificationLog.objects.create(**self.log_data)
        self.assertEqual(log.template.name, 'Test Template')
        self.assertEqual(log.template.template_type, 'email')


class UserPreferenceModelTest(TestCase):
    """Test cases for UserPreference model."""

    def setUp(self):
        """Set up test data."""
        self.preference_data = {
            'user_id': 'user123',
            'channel': 'email',
            'enabled': True,
            'frequency': 'immediate'
        }

    def test_create_user_preference(self):
        """Test creating a user preference."""
        preference = UserPreference.objects.create(**self.preference_data)
        
        self.assertEqual(preference.user_id, 'user123')
        self.assertEqual(preference.channel, 'email')
        self.assertTrue(preference.enabled)
        self.assertEqual(preference.frequency, 'immediate')
        self.assertIsNotNone(preference.created_at)

    def test_preference_str_representation(self):
        """Test string representation of user preference."""
        preference = UserPreference.objects.create(**self.preference_data)
        expected = f"user123 - email preferences"
        self.assertEqual(str(preference), expected)

    def test_user_channel_uniqueness(self):
        """Test that user-channel combination must be unique."""
        UserPreference.objects.create(**self.preference_data)
        
        with self.assertRaises(IntegrityError):
            UserPreference.objects.create(**self.preference_data)

    def test_frequency_choices(self):
        """Test frequency field validation."""
        valid_frequencies = ['immediate', 'hourly', 'daily', 'weekly', 'never']
        
        for frequency in valid_frequencies:
            preference_data = self.preference_data.copy()
            preference_data['user_id'] = f'user_{frequency}'
            preference_data['frequency'] = frequency
            preference = UserPreference.objects.create(**preference_data)
            self.assertEqual(preference.frequency, frequency)

    def test_default_values(self):
        """Test default field values."""
        minimal_data = {
            'user_id': 'user456',
            'channel': 'email'
        }
        preference = UserPreference.objects.create(**minimal_data)
        
        self.assertTrue(preference.enabled)
        self.assertEqual(preference.frequency, 'immediate')


class NotificationQuotaModelTest(TestCase):
    """Test cases for NotificationQuota model."""

    def setUp(self):
        """Set up test data."""
        self.quota_data = {
            'user_id': 'user123',
            'channel': 'email',
            'quota_limit': 100,
            'quota_used': 5,
            'reset_period': 'daily'
        }

    def test_create_notification_quota(self):
        """Test creating a notification quota."""
        quota = NotificationQuota.objects.create(**self.quota_data)
        
        self.assertEqual(quota.user_id, 'user123')
        self.assertEqual(quota.channel, 'email')
        self.assertEqual(quota.quota_limit, 100)
        self.assertEqual(quota.quota_used, 5)
        self.assertEqual(quota.reset_period, 'daily')
        self.assertIsNotNone(quota.created_at)

    def test_quota_str_representation(self):
        """Test string representation of notification quota."""
        quota = NotificationQuota.objects.create(**self.quota_data)
        expected = f"user123 - email quota: 5/100"
        self.assertEqual(str(quota), expected)

    def test_user_channel_quota_uniqueness(self):
        """Test that user-channel quota combination must be unique."""
        NotificationQuota.objects.create(**self.quota_data)
        
        with self.assertRaises(IntegrityError):
            NotificationQuota.objects.create(**self.quota_data)

    def test_reset_period_choices(self):
        """Test reset period field validation."""
        valid_periods = ['hourly', 'daily', 'weekly', 'monthly']
        
        for period in valid_periods:
            quota_data = self.quota_data.copy()
            quota_data['user_id'] = f'user_{period}'
            quota_data['reset_period'] = period
            quota = NotificationQuota.objects.create(**quota_data)
            self.assertEqual(quota.reset_period, period)

    def test_quota_validation(self):
        """Test quota validation logic."""
        quota = NotificationQuota.objects.create(**self.quota_data)
        
        # Test quota usage tracking
        self.assertTrue(quota.quota_used <= quota.quota_limit)
        
        # Test quota exceeded
        quota.quota_used = 150
        quota.save()
        self.assertTrue(quota.quota_used > quota.quota_limit)

    def test_default_values(self):
        """Test default field values."""
        minimal_data = {
            'user_id': 'user789',
            'channel': 'sms'
        }
        quota = NotificationQuota.objects.create(**minimal_data)
        
        self.assertEqual(quota.quota_limit, 100)
        self.assertEqual(quota.quota_used, 0)
        self.assertEqual(quota.reset_period, 'daily')