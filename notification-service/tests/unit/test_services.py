"""
Unit tests for core services.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.core.exceptions import ValidationError

from core.models import (
    NotificationTemplate,
    NotificationLog,
    UserPreference,
    NotificationQuota
)
from core.services import (
    NotificationService,
    TemplateService,
    PreferenceService
)


class NotificationServiceTest(TestCase):
    """Test cases for NotificationService."""

    def setUp(self):
        """Set up test data."""
        self.template = NotificationTemplate.objects.create(
            name='Test Template',
            template_type='email',
            content='Hello {{user_name}}!',
            subject='Test Subject'
        )
        
        self.preference = UserPreference.objects.create(
            user_id='user123',
            channel='email',
            enabled=True,
            frequency='immediate'
        )
        
        self.quota = NotificationQuota.objects.create(
            user_id='user123',
            channel='email',
            quota_limit=100,
            quota_used=5
        )

    def test_send_notification_success(self):
        """Test successful notification sending."""
        service = NotificationService()
        
        with patch.object(service, '_send_via_adapter') as mock_send:
            mock_send.return_value = True
            
            result = service.send_notification(
                template_id=self.template.id,
                user_id='user123',
                recipient='test@example.com',
                context={'user_name': 'John'}
            )
            
            self.assertTrue(result)
            mock_send.assert_called_once()

    def test_send_notification_template_not_found(self):
        """Test notification sending with non-existent template."""
        service = NotificationService()
        
        with self.assertRaises(NotificationTemplate.DoesNotExist):
            service.send_notification(
                template_id=999,
                user_id='user123',
                recipient='test@example.com'
            )

    def test_send_notification_user_preference_disabled(self):
        """Test notification sending when user has disabled the channel."""
        self.preference.enabled = False
        self.preference.save()
        
        service = NotificationService()
        
        result = service.send_notification(
            template_id=self.template.id,
            user_id='user123',
            recipient='test@example.com'
        )
        
        self.assertFalse(result)

    def test_send_notification_quota_exceeded(self):
        """Test notification sending when quota is exceeded."""
        self.quota.quota_used = 150
        self.quota.save()
        
        service = NotificationService()
        
        result = service.send_notification(
            template_id=self.template.id,
            user_id='user123',
            recipient='test@example.com'
        )
        
        self.assertFalse(result)

    @patch('core.services.NotificationService._render_template')
    def test_render_template_with_context(self, mock_render):
        """Test template rendering with context variables."""
        mock_render.return_value = 'Hello John!'
        
        service = NotificationService()
        result = service._render_template(
            self.template,
            {'user_name': 'John'}
        )
        
        self.assertEqual(result, 'Hello John!')
        mock_render.assert_called_once_with(self.template, {'user_name': 'John'})

    def test_create_notification_log(self):
        """Test notification log creation."""
        service = NotificationService()
        
        log = service._create_notification_log(
            template=self.template,
            user_id='user123',
            recipient='test@example.com',
            status='sent',
            content='Rendered content'
        )
        
        self.assertEqual(log.template, self.template)
        self.assertEqual(log.user_id, 'user123')
        self.assertEqual(log.status, 'sent')
        self.assertIsInstance(log, NotificationLog)

    def test_update_quota_usage(self):
        """Test quota usage tracking."""
        service = NotificationService()
        initial_usage = self.quota.quota_used
        
        service._update_quota_usage('user123', 'email')
        
        self.quota.refresh_from_db()
        self.assertEqual(self.quota.quota_used, initial_usage + 1)

    def test_get_user_notifications(self):
        """Test retrieving user notification history."""
        # Create some notification logs
        NotificationLog.objects.create(
            template=self.template,
            user_id='user123',
            recipient='test@example.com',
            status='sent',
            channel='email',
            content='Test content 1'
        )
        NotificationLog.objects.create(
            template=self.template,
            user_id='user123',
            recipient='test@example.com',
            status='delivered',
            channel='email',
            content='Test content 2'
        )
        
        service = NotificationService()
        notifications = service.get_user_notifications('user123')
        
        self.assertEqual(notifications.count(), 2)
        self.assertTrue(all(n.user_id == 'user123' for n in notifications))


class TemplateServiceTest(TestCase):
    """Test cases for TemplateService."""

    def setUp(self):
        """Set up test data."""
        self.template_data = {
            'name': 'Test Template',
            'template_type': 'email',
            'content': 'Hello {{user_name}}!',
            'subject': 'Test Subject',
            'variables': ['user_name']
        }

    def test_create_template(self):
        """Test template creation."""
        service = TemplateService()
        template = service.create_template(**self.template_data)
        
        self.assertEqual(template.name, 'Test Template')
        self.assertEqual(template.template_type, 'email')
        self.assertTrue(template.is_active)

    def test_get_template_by_id(self):
        """Test retrieving template by ID."""
        template = NotificationTemplate.objects.create(**self.template_data)
        service = TemplateService()
        
        retrieved = service.get_template(template.id)
        self.assertEqual(retrieved.id, template.id)
        self.assertEqual(retrieved.name, template.name)

    def test_get_template_not_found(self):
        """Test retrieving non-existent template."""
        service = TemplateService()
        
        with self.assertRaises(NotificationTemplate.DoesNotExist):
            service.get_template(999)

    def test_update_template(self):
        """Test template update."""
        template = NotificationTemplate.objects.create(**self.template_data)
        service = TemplateService()
        
        updated = service.update_template(
            template.id,
            name='Updated Template',
            content='Updated content'
        )
        
        self.assertEqual(updated.name, 'Updated Template')
        self.assertEqual(updated.content, 'Updated content')

    def test_delete_template(self):
        """Test template soft deletion."""
        template = NotificationTemplate.objects.create(**self.template_data)
        service = TemplateService()
        
        service.delete_template(template.id)
        
        template.refresh_from_db()
        self.assertFalse(template.is_active)
        self.assertIsNotNone(template.deleted_at)

    def test_list_templates(self):
        """Test listing active templates."""
        # Create active templates
        NotificationTemplate.objects.create(**self.template_data)
        
        template_data_2 = self.template_data.copy()
        template_data_2['name'] = 'Template 2'
        NotificationTemplate.objects.create(**template_data_2)
        
        # Create inactive template
        template_data_3 = self.template_data.copy()
        template_data_3['name'] = 'Template 3'
        inactive_template = NotificationTemplate.objects.create(**template_data_3)
        inactive_template.soft_delete()
        
        service = TemplateService()
        templates = service.list_templates()
        
        self.assertEqual(templates.count(), 2)
        self.assertTrue(all(t.is_active for t in templates))

    def test_validate_template_variables(self):
        """Test template variable validation."""
        service = TemplateService()
        
        # Test valid template
        valid_template = "Hello {{user_name}}, your order {{order_id}} is ready!"
        variables = service._extract_variables(valid_template)
        expected_vars = ['user_name', 'order_id']
        self.assertEqual(set(variables), set(expected_vars))

    def test_render_template_content(self):
        """Test template content rendering."""
        template = NotificationTemplate.objects.create(**self.template_data)
        service = TemplateService()
        
        context = {'user_name': 'John Doe'}
        rendered = service.render_template(template, context)
        
        self.assertEqual(rendered, 'Hello John Doe!')

    def test_render_template_missing_variable(self):
        """Test template rendering with missing variables."""
        template = NotificationTemplate.objects.create(**self.template_data)
        service = TemplateService()
        
        context = {}  # Missing user_name
        
        with self.assertRaises(ValidationError):
            service.render_template(template, context)


class PreferenceServiceTest(TestCase):
    """Test cases for PreferenceService."""

    def setUp(self):
        """Set up test data."""
        self.preference_data = {
            'user_id': 'user123',
            'channel': 'email',
            'enabled': True,
            'frequency': 'immediate'
        }

    def test_get_user_preferences(self):
        """Test retrieving user preferences."""
        UserPreference.objects.create(**self.preference_data)
        
        # Create another preference for different channel
        preference_data_2 = self.preference_data.copy()
        preference_data_2['channel'] = 'sms'
        UserPreference.objects.create(**preference_data_2)
        
        service = PreferenceService()
        preferences = service.get_user_preferences('user123')
        
        self.assertEqual(preferences.count(), 2)
        self.assertTrue(all(p.user_id == 'user123' for p in preferences))

    def test_update_user_preference(self):
        """Test updating user preference."""
        preference = UserPreference.objects.create(**self.preference_data)
        service = PreferenceService()
        
        updated = service.update_user_preference(
            'user123',
            'email',
            enabled=False,
            frequency='daily'
        )
        
        self.assertFalse(updated.enabled)
        self.assertEqual(updated.frequency, 'daily')

    def test_create_user_preference(self):
        """Test creating new user preference."""
        service = PreferenceService()
        
        preference = service.create_user_preference(
            user_id='user456',
            channel='push',
            enabled=True,
            frequency='hourly'
        )
        
        self.assertEqual(preference.user_id, 'user456')
        self.assertEqual(preference.channel, 'push')
        self.assertTrue(preference.enabled)
        self.assertEqual(preference.frequency, 'hourly')

    def test_check_notification_allowed(self):
        """Test checking if notification is allowed for user."""
        UserPreference.objects.create(**self.preference_data)
        service = PreferenceService()
        
        # Test enabled preference
        allowed = service.is_notification_allowed('user123', 'email')
        self.assertTrue(allowed)
        
        # Test disabled preference
        self.preference_data['enabled'] = False
        UserPreference.objects.filter(
            user_id='user123',
            channel='email'
        ).update(enabled=False)
        
        allowed = service.is_notification_allowed('user123', 'email')
        self.assertFalse(allowed)

    def test_check_notification_allowed_no_preference(self):
        """Test checking notification allowed when no preference exists."""
        service = PreferenceService()
        
        # Should return True by default when no preference exists
        allowed = service.is_notification_allowed('user999', 'email')
        self.assertTrue(allowed)

    def test_get_user_preference_by_channel(self):
        """Test retrieving specific channel preference."""
        UserPreference.objects.create(**self.preference_data)
        service = PreferenceService()
        
        preference = service.get_user_preference('user123', 'email')
        self.assertEqual(preference.channel, 'email')
        self.assertTrue(preference.enabled)

    def test_get_user_preference_not_found(self):
        """Test retrieving non-existent preference."""
        service = PreferenceService()
        
        preference = service.get_user_preference('user999', 'email')
        self.assertIsNone(preference)

    def test_bulk_update_preferences(self):
        """Test bulk updating user preferences."""
        # Create multiple preferences
        channels = ['email', 'sms', 'push']
        for channel in channels:
            data = self.preference_data.copy()
            data['channel'] = channel
            UserPreference.objects.create(**data)
        
        service = PreferenceService()
        
        # Bulk disable all preferences
        service.bulk_update_user_preferences(
            'user123',
            {'enabled': False}
        )
        
        preferences = UserPreference.objects.filter(user_id='user123')
        self.assertTrue(all(not p.enabled for p in preferences))

    def test_delete_user_preferences(self):
        """Test deleting all user preferences."""
        # Create multiple preferences
        channels = ['email', 'sms', 'push']
        for channel in channels:
            data = self.preference_data.copy()
            data['channel'] = channel
            UserPreference.objects.create(**data)
        
        service = PreferenceService()
        service.delete_user_preferences('user123')
        
        preferences = UserPreference.objects.filter(user_id='user123')
        self.assertEqual(preferences.count(), 0)