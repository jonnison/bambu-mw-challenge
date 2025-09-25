"""
Enhanced integration tests for the Notification Service API endpoints.
Tests end-to-end functionality including authentication, validation, and external service integration.
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import NotificationTemplate, NotificationLog, UserPreference, NotificationQuota
from tests.fixtures.factories import (
    NotificationTemplateFactory,
    NotificationLogFactory,
    UserPreferenceFactory,
    NotificationQuotaFactory
)


class NotificationAPIIntegrationTest(APITestCase):
    """Comprehensive integration tests for notification API endpoints."""

    def setUp(self):
        """Set up test data and authentication."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create JWT token for authentication
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Create test templates
        self.email_template = NotificationTemplateFactory(
            name='test_email',
            type='email',
            subject='Test Subject: {{name}}',
            content='Hello {{name}}, this is a test email with {{message}}.',
            variables=['name', 'message']
        )
        
        self.sms_template = NotificationTemplateFactory(
            name='test_sms',
            type='sms',
            content='Hi {{name}}: {{message}}',
            variables=['name', 'message']
        )
        
        # Create user preferences
        self.user_preference = UserPreferenceFactory(
            user_id=self.user.id,
            email_enabled=True,
            sms_enabled=True,
            push_enabled=False
        )
        
        # Create quota
        self.quota = NotificationQuotaFactory(
            user_id=self.user.id,
            email_daily_limit=100,
            email_daily_sent=5,
            sms_daily_limit=20,
            sms_daily_sent=2
        )

    def test_send_email_notification_success(self):
        """Test successful email notification sending."""
        with patch('adapters.email.EmailAdapter.send') as mock_send:
            mock_send.return_value = Mock(
                success=True,
                provider_response={'MessageId': 'test-message-id'},
                error=None
            )
            
            url = reverse('api:v1:send-notification')
            data = {
                'user_id': self.user.id,
                'template_name': 'test_email',
                'recipient': 'recipient@example.com',
                'type': 'email',
                'variables': {
                    'name': 'John Doe',
                    'message': 'Welcome to our platform!'
                },
                'priority': 'normal'
            }
            
            response = self.client.post(url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertIn('id', response.data)
            self.assertEqual(response.data['status'], 'queued')
            self.assertEqual(response.data['type'], 'email')
            self.assertEqual(response.data['recipient'], 'recipient@example.com')
            
            # Verify notification log was created
            log = NotificationLog.objects.get(id=response.data['id'])
            self.assertEqual(log.user_id, self.user.id)
            self.assertEqual(log.template, self.email_template)
            self.assertEqual(log.recipient, 'recipient@example.com')

    def test_send_notification_invalid_template(self):
        """Test sending notification with non-existent template."""
        url = reverse('api:v1:send-notification')
        data = {
            'user_id': self.user.id,
            'template_name': 'nonexistent_template',
            'recipient': 'recipient@example.com',
            'type': 'email',
            'variables': {'name': 'John'}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('Template', response.data['error']['message'])

    def test_send_notification_quota_exceeded(self):
        """Test notification sending when quota is exceeded."""
        # Set quota to exceeded state
        self.quota.email_daily_sent = self.quota.email_daily_limit
        self.quota.save()
        
        url = reverse('api:v1:send-notification')
        data = {
            'user_id': self.user.id,
            'template_name': 'test_email',
            'recipient': 'recipient@example.com',
            'type': 'email',
            'variables': {'name': 'John', 'message': 'Test'}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('quota', response.data['error']['message'].lower())

    def test_send_notification_user_preferences_disabled(self):
        """Test notification sending when user has disabled the channel."""
        # Disable email notifications for user
        self.user_preference.email_enabled = False
        self.user_preference.save()
        
        url = reverse('api:v1:send-notification')
        data = {
            'user_id': self.user.id,
            'template_name': 'test_email',
            'recipient': 'recipient@example.com',
            'type': 'email',
            'variables': {'name': 'John', 'message': 'Test'}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('disabled', response.data['error']['message'].lower())

    def test_get_notification_status(self):
        """Test retrieving notification status."""
        # Create a notification log
        log = NotificationLogFactory(
            user_id=self.user.id,
            template=self.email_template,
            recipient='test@example.com',
            status='sent',
            provider_response={'MessageId': 'test-id'}
        )
        
        url = reverse('api:v1:notification-detail', kwargs={'notification_id': log.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(log.id))
        self.assertEqual(response.data['status'], 'sent')
        self.assertEqual(response.data['recipient'], 'test@example.com')
        self.assertIn('delivery_details', response.data)

    def test_list_user_notifications(self):
        """Test listing notifications for a user."""
        # Create multiple notification logs
        logs = [
            NotificationLogFactory(
                user_id=self.user.id,
                template=self.email_template,
                status='sent'
            ),
            NotificationLogFactory(
                user_id=self.user.id,
                template=self.sms_template,
                status='pending'
            ),
            NotificationLogFactory(
                user_id=999,  # Different user
                template=self.email_template,
                status='sent'
            )
        ]
        
        url = reverse('api:v1:notification-list')
        response = self.client.get(f'{url}?user_id={self.user.id}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)  # Only user's notifications
        self.assertEqual(len(response.data['results']), 2)

    def test_list_notifications_with_filters(self):
        """Test listing notifications with status and type filters."""
        # Create notifications with different statuses and types
        NotificationLogFactory(
            user_id=self.user.id,
            template=self.email_template,
            status='sent',
            type='email'
        )
        NotificationLogFactory(
            user_id=self.user.id,
            template=self.sms_template,
            status='pending',
            type='sms'
        )
        NotificationLogFactory(
            user_id=self.user.id,
            template=self.email_template,
            status='failed',
            type='email'
        )
        
        url = reverse('api:v1:notification-list')
        
        # Test status filter
        response = self.client.get(f'{url}?user_id={self.user.id}&status=sent')
        self.assertEqual(response.data['count'], 1)
        
        # Test type filter
        response = self.client.get(f'{url}?user_id={self.user.id}&type=email')
        self.assertEqual(response.data['count'], 2)
        
        # Test combined filters
        response = self.client.get(f'{url}?user_id={self.user.id}&status=sent&type=email')
        self.assertEqual(response.data['count'], 1)

    def test_update_notification_status(self):
        """Test updating notification status via webhook."""
        log = NotificationLogFactory(
            user_id=self.user.id,
            template=self.email_template,
            status='pending'
        )
        
        url = reverse('api:v1:notification-status-update', kwargs={'notification_id': log.id})
        data = {
            'status': 'bounced',
            'provider_response': {
                'bounce_type': 'Permanent',
                'bounce_reason': 'Invalid recipient'
            }
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'bounced')
        
        # Verify database was updated
        log.refresh_from_db()
        self.assertEqual(log.status, 'bounced')
        self.assertEqual(log.provider_response['bounce_type'], 'Permanent')


class TemplateAPIIntegrationTest(APITestCase):
    """Integration tests for template management endpoints."""

    def setUp(self):
        """Set up test data and authentication."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        self.template = NotificationTemplateFactory(
            name='existing_template',
            type='email',
            subject='Test Subject',
            content='Test content with {{variable}}'
        )

    def test_list_templates(self):
        """Test listing all templates."""
        url = reverse('api:v1:template-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'existing_template')

    def test_get_template_detail(self):
        """Test retrieving specific template details."""
        url = reverse('api:v1:template-detail', kwargs={'template_id': self.template.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'existing_template')
        self.assertEqual(response.data['type'], 'email')
        self.assertIn('usage_stats', response.data)

    def test_create_template(self):
        """Test creating a new template."""
        url = reverse('api:v1:template-list')
        data = {
            'name': 'new_template',
            'type': 'sms',
            'content': 'SMS content with {{name}}',
            'variables': ['name'],
            'metadata': {
                'description': 'Test SMS template',
                'category': 'marketing'
            }
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'new_template')
        self.assertEqual(response.data['type'], 'sms')
        
        # Verify template was created in database
        template = NotificationTemplate.objects.get(name='new_template')
        self.assertEqual(template.type, 'sms')

    def test_update_template(self):
        """Test updating an existing template."""
        url = reverse('api:v1:template-detail', kwargs={'template_id': self.template.id})
        data = {
            'name': 'updated_template',
            'type': 'email',
            'subject': 'Updated Subject',
            'content': 'Updated content with {{new_variable}}',
            'variables': ['new_variable']
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'updated_template')
        self.assertEqual(response.data['subject'], 'Updated Subject')
        
        # Verify database was updated
        self.template.refresh_from_db()
        self.assertEqual(self.template.name, 'updated_template')

    def test_delete_template(self):
        """Test soft deleting a template."""
        url = reverse('api:v1:template-detail', kwargs={'template_id': self.template.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify template was soft deleted (marked as inactive)
        self.template.refresh_from_db()
        self.assertFalse(self.template.active)

    def test_template_name_uniqueness(self):
        """Test that template names must be unique."""
        url = reverse('api:v1:template-list')
        data = {
            'name': 'existing_template',  # Same name as existing template
            'type': 'email',
            'content': 'Different content'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)


class UserPreferenceAPIIntegrationTest(APITestCase):
    """Integration tests for user preference endpoints."""

    def setUp(self):
        """Set up test data and authentication."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        self.preference = UserPreferenceFactory(
            user_id=self.user.id,
            email_enabled=True,
            sms_enabled=False,
            preferences={
                'quiet_hours': {
                    'enabled': True,
                    'start': '22:00',
                    'end': '08:00'
                }
            }
        )

    def test_get_user_preferences(self):
        """Test retrieving user preferences."""
        url = reverse('api:v1:user-preference-detail', kwargs={'user_id': self.user.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user_id'], self.user.id)
        self.assertTrue(response.data['email_enabled'])
        self.assertFalse(response.data['sms_enabled'])
        self.assertIn('quiet_hours', response.data)

    def test_update_user_preferences(self):
        """Test updating user preferences."""
        url = reverse('api:v1:user-preference-detail', kwargs={'user_id': self.user.id})
        data = {
            'email_enabled': False,
            'sms_enabled': True,
            'preferences': {
                'quiet_hours': {
                    'enabled': False
                },
                'categories': {
                    'marketing': False,
                    'security': True
                }
            }
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['email_enabled'])
        self.assertTrue(response.data['sms_enabled'])
        
        # Verify database was updated
        self.preference.refresh_from_db()
        self.assertFalse(self.preference.email_enabled)
        self.assertTrue(self.preference.sms_enabled)

    def test_create_user_preferences_if_not_exist(self):
        """Test creating preferences for user who doesn't have them."""
        new_user = User.objects.create_user(
            username='newuser',
            email='new@example.com',
            password='testpass123'
        )
        
        url = reverse('api:v1:user-preference-detail', kwargs={'user_id': new_user.id})
        data = {
            'email_enabled': True,
            'sms_enabled': True,
            'push_enabled': false
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify preferences were created
        preference = UserPreference.objects.get(user_id=new_user.id)
        self.assertTrue(preference.email_enabled)


class HealthCheckIntegrationTest(APITestCase):
    """Integration tests for health check endpoints."""

    def test_basic_health_check(self):
        """Test basic health check endpoint (no auth required)."""
        url = reverse('health:health-check')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'healthy')
        self.assertIn('timestamp', response.data)
        self.assertIn('services', response.data)
        self.assertIn('metrics', response.data)

    @patch('infrastructure.health.check_database')
    @patch('infrastructure.health.check_redis')
    @patch('infrastructure.health.check_rabbitmq')
    def test_detailed_health_check(self, mock_rabbitmq, mock_redis, mock_db):
        """Test detailed health check with service monitoring."""
        # Mock healthy services
        mock_db.return_value = {'status': 'healthy', 'response_time_ms': 10}
        mock_redis.return_value = {'status': 'healthy', 'response_time_ms': 2}
        mock_rabbitmq.return_value = {'status': 'healthy', 'response_time_ms': 5}
        
        url = reverse('health:detailed-health-check')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'healthy')
        self.assertIn('services', response.data)
        self.assertEqual(response.data['services']['database']['status'], 'healthy')


class ExternalServiceIntegrationTest(TransactionTestCase):
    """Integration tests for external service adapters."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.template = NotificationTemplateFactory(
            name='test_template',
            type='email',
            subject='Test: {{subject}}',
            content='Hello {{name}}'
        )

    @patch('adapters.email.SESProvider.send_email')
    def test_email_adapter_integration(self, mock_ses):
        """Test email adapter with mocked SES."""
        mock_ses.return_value = Mock(
            success=True,
            provider_response={'MessageId': 'test-message-id'}
        )
        
        from adapters.email import EmailAdapter
        
        adapter = EmailAdapter(provider='ses')
        result = adapter.send(
            recipient='test@example.com',
            subject='Test Subject',
            content='Test Content'
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.provider_response['MessageId'], 'test-message-id')
        mock_ses.assert_called_once()

    @patch('adapters.sms.TwilioProvider.send_sms')
    def test_sms_adapter_integration(self, mock_twilio):
        """Test SMS adapter with mocked Twilio."""
        mock_twilio.return_value = Mock(
            success=True,
            provider_response={'sid': 'test-sms-id'}
        )
        
        from adapters.sms import SMSAdapter
        
        adapter = SMSAdapter(provider='twilio')
        result = adapter.send(
            recipient='+1234567890',
            subject='',  # SMS doesn't use subject
            content='Test SMS message'
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.provider_response['sid'], 'test-sms-id')
        mock_twilio.assert_called_once()


class CeleryTaskIntegrationTest(TransactionTestCase):
    """Integration tests for Celery task processing."""

    def setUp(self):
        """Set up test data."""
        self.template = NotificationTemplateFactory(
            name='test_template',
            type='email',
            subject='Test Subject',
            content='Test Content'
        )

    @patch('adapters.email.EmailAdapter.send')
    def test_notification_task_processing(self, mock_send):
        """Test that notification tasks process correctly."""
        mock_send.return_value = Mock(
            success=True,
            provider_response={'MessageId': 'test-id'}
        )
        
        from core.tasks import send_notification_task
        
        # Create notification log
        log = NotificationLogFactory(
            template=self.template,
            recipient='test@example.com',
            status='pending'
        )
        
        # Execute task
        result = send_notification_task.apply(args=[{
            'log_id': str(log.id),
            'recipient': 'test@example.com',
            'subject': 'Test Subject',
            'content': 'Test Content',
            'type': 'email'
        }])
        
        self.assertTrue(result.successful())
        
        # Verify log was updated
        log.refresh_from_db()
        self.assertEqual(log.status, 'sent')


class WebhookIntegrationTest(APITestCase):
    """Integration tests for webhook endpoints."""

    def setUp(self):
        """Set up test data."""
        self.log = NotificationLogFactory(
            status='sent',
            provider_response={'MessageId': 'test-message-id'},
            type='email'
        )

    def test_ses_webhook_processing(self):
        """Test processing SES delivery webhook."""
        url = reverse('api:v1:ses-webhook')
        
        # Simulate SES bounce notification
        webhook_data = {
            'Type': 'Notification',
            'Message': json.dumps({
                'notificationType': 'Bounce',
                'bounce': {
                    'bounceType': 'Permanent',
                    'bouncedRecipients': [
                        {'emailAddress': 'test@example.com'}
                    ]
                },
                'mail': {
                    'messageId': 'test-message-id'
                }
            })
        }
        
        response = self.client.post(url, webhook_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify notification status was updated
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, 'bounced')

    def test_twilio_webhook_processing(self):
        """Test processing Twilio delivery webhook."""
        url = reverse('api:v1:twilio-webhook')
        
        webhook_data = {
            'MessageSid': 'test-sms-id',
            'MessageStatus': 'delivered',
            'To': '+1234567890'
        }
        
        # Create SMS log with matching provider response
        sms_log = NotificationLogFactory(
            status='sent',
            provider_response={'sid': 'test-sms-id'},
            type='sms'
        )
        
        response = self.client.post(url, webhook_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify SMS status was updated
        sms_log.refresh_from_db()
        self.assertEqual(sms_log.status, 'delivered')


class PerformanceIntegrationTest(TransactionTestCase):
    """Performance and load testing scenarios."""

    def test_bulk_notification_handling(self):
        """Test handling multiple notifications efficiently."""
        template = NotificationTemplateFactory(type='email')
        
        # Create multiple notification logs
        logs = [
            NotificationLogFactory(
                template=template,
                recipient=f'user{i}@example.com',
                status='pending'
            )
            for i in range(100)
        ]
        
        # Measure query count for batch processing
        with self.assertNumQueries(expected_num=5):  # Should be efficient
            from django.db import connection
            
            # Batch update status
            NotificationLog.objects.filter(
                id__in=[log.id for log in logs[:10]]
            ).update(status='sent')
            
            # Verify updates
            updated_count = NotificationLog.objects.filter(
                id__in=[log.id for log in logs[:10]],
                status='sent'
            ).count()
            
            self.assertEqual(updated_count, 10)

    def test_concurrent_notification_sending(self):
        """Test handling concurrent notification requests."""
        import threading
        import time
        
        template = NotificationTemplateFactory(type='email')
        results = []
        
        def send_notification():
            with patch('adapters.email.EmailAdapter.send') as mock_send:
                mock_send.return_value = Mock(success=True)
                
                log = NotificationLogFactory(
                    template=template,
                    status='pending'
                )
                
                # Simulate processing delay
                time.sleep(0.1)
                log.status = 'sent'
                log.save()
                results.append(log.id)
        
        # Create multiple threads
        threads = [threading.Thread(target=send_notification) for _ in range(10)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all notifications were processed
        self.assertEqual(len(results), 10)
        sent_count = NotificationLog.objects.filter(status='sent').count()
        self.assertEqual(sent_count, 10)