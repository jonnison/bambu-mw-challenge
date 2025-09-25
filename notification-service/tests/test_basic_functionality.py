"""
Basic functionality tests with correct model field names.
"""
import pytest
from django.test import TestCase
from core.models import NotificationTemplate, UserPreference, NotificationQuota
from django.db import IntegrityError


class BasicFunctionalityTest(TestCase):
    """Test basic model functionality with correct field names."""

    def test_notification_template_creation(self):
        """Test creating a notification template with correct fields."""
        template = NotificationTemplate.objects.create(
            name='welcome_email',
            type='email',
            body='Hello {{user_name}}, welcome to our service!',
            subject='Welcome!',
            variables={'user_name': 'string'}
        )
        
        self.assertEqual(template.name, 'welcome_email')
        self.assertEqual(template.type, 'email')
        self.assertIn('{{user_name}}', template.body)
        self.assertTrue(template.active)
        
    def test_notification_template_unique_name(self):
        """Test that template names must be unique."""
        NotificationTemplate.objects.create(
            name='unique_template',
            type='email',
            body='Test body'
        )
        
        with self.assertRaises(IntegrityError):
            NotificationTemplate.objects.create(
                name='unique_template',
                type='sms',
                body='Different body'
            )

    def test_user_preference_creation(self):
        """Test creating user preferences with correct fields."""
        preference = UserPreference.objects.create(
            user_id=123,
            email_enabled=True,
            sms_enabled=False,
            push_enabled=True,
            max_emails_per_day=25,
            max_sms_per_day=5
        )
        
        self.assertEqual(preference.user_id, 123)
        self.assertTrue(preference.email_enabled)
        self.assertFalse(preference.sms_enabled)
        self.assertTrue(preference.push_enabled)
        self.assertEqual(preference.max_emails_per_day, 25)

    def test_notification_quota_creation(self):
        """Test creating notification quota with correct fields."""
        quota = NotificationQuota.objects.create(
            user_id=456,
            notification_type='email',
            count=10
        )
        
        self.assertEqual(quota.user_id, 456)
        self.assertEqual(quota.notification_type, 'email')
        self.assertEqual(quota.count, 10)

    def test_quota_increment_functionality(self):
        """Test quota increment functionality."""
        user_id = 789
        count = NotificationQuota.increment_quota(user_id, 'email')
        self.assertEqual(count, 1)
        
        # Increment again
        count = NotificationQuota.increment_quota(user_id, 'email')
        self.assertEqual(count, 2)

    def test_quota_check_exceeded(self):
        """Test quota exceeded check."""
        user_id = 999
        
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

    def test_user_preference_notification_allowed(self):
        """Test notification allowed functionality."""
        preference = UserPreference.objects.create(
            user_id=555,
            email_enabled=True,
            sms_enabled=False,
            push_enabled=True
        )
        
        # Should allow email and push, deny SMS
        self.assertTrue(preference.is_notification_allowed('email'))
        self.assertFalse(preference.is_notification_allowed('sms'))
        self.assertTrue(preference.is_notification_allowed('push'))

    def test_template_variable_extraction(self):
        """Test template variable name extraction."""
        template = NotificationTemplate.objects.create(
            name='multi_var_template',
            type='email',
            body='Hello {{user_name}}, your order {{order_id}} is ready. Amount: {{amount}}'
        )
        
        variables = template.get_variable_names()
        expected_vars = ['user_name', 'order_id', 'amount']
        
        self.assertEqual(sorted(variables), sorted(expected_vars))