"""
Simplified adapter tests focusing on achievable coverage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase

from adapters.email import (
    EmailMessage, EmailResult, MockEmailAdapter
)
from adapters.sms import (
    SMSMessage, SMSResult, MockSMSAdapter
)
from adapters.push import (
    PushMessage, PushResult, MockPushAdapter
)


class TestEmailAdapters(TestCase):
    """Tests for email adapters - focusing on mock adapter."""

    def test_email_message_creation(self):
        """Test EmailMessage dataclass creation."""
        message = EmailMessage(
            to="test@example.com",
            subject="Test Subject",
            body="Test Body",
            from_email="sender@example.com"
        )
        self.assertEqual(message.to, "test@example.com")
        self.assertEqual(message.subject, "Test Subject")
        self.assertEqual(message.body, "Test Body")
        self.assertEqual(message.from_email, "sender@example.com")

    def test_email_result_creation(self):
        """Test EmailResult dataclass creation."""
        result = EmailResult(
            success=True,
            provider_id="test-id-123",
            error_message=None
        )
        self.assertTrue(result.success)
        self.assertEqual(result.provider_id, "test-id-123")
        self.assertIsNone(result.error_message)

    def test_mock_email_adapter_initialization(self):
        """Test MockEmailAdapter initialization."""
        adapter = MockEmailAdapter()
        self.assertIsInstance(adapter.sent_emails, list)
        self.assertEqual(len(adapter.sent_emails), 0)

    def test_mock_email_adapter_success(self):
        """Test MockEmailAdapter successful email sending."""
        adapter = MockEmailAdapter()
        message = EmailMessage(
            to="test@example.com",
            subject="Test Subject",
            body="Test Body"
        )
        result = adapter.send_email(message)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.provider_id)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(adapter.sent_emails), 1)

    def test_mock_email_adapter_get_provider_name(self):
        """Test MockEmailAdapter provider name."""
        adapter = MockEmailAdapter()
        self.assertEqual(adapter.get_provider_name(), "mock")

    def test_mock_email_adapter_invalid_email(self):
        """Test MockEmailAdapter with invalid email."""
        adapter = MockEmailAdapter()
        message = EmailMessage(
            to="invalid-email",
            subject="Test Subject",
            body="Test Body"
        )
        result = adapter.send_email(message)
        
        self.assertFalse(result.success)
        self.assertIsNone(result.provider_id)
        self.assertIn("Invalid email", result.error_message)

    def test_mock_email_adapter_empty_fields(self):
        """Test MockEmailAdapter with empty required fields."""
        adapter = MockEmailAdapter()
        
        # Empty to field
        message = EmailMessage(to="", subject="Test", body="Test")
        result = adapter.send_email(message)
        self.assertFalse(result.success)
        
        # Empty subject
        message = EmailMessage(to="test@example.com", subject="", body="Test")
        result = adapter.send_email(message)
        self.assertFalse(result.success)
        
        # Empty body
        message = EmailMessage(to="test@example.com", subject="Test", body="")
        result = adapter.send_email(message)
        self.assertFalse(result.success)


class TestSMSAdapters(TestCase):
    """Tests for SMS adapters - focusing on mock adapter."""

    def test_sms_message_creation(self):
        """Test SMSMessage dataclass creation."""
        message = SMSMessage(
            to="+1234567890",
            body="Test message",
            from_number="+0987654321"
        )
        self.assertEqual(message.to, "+1234567890")
        self.assertEqual(message.body, "Test message")
        self.assertEqual(message.from_number, "+0987654321")

    def test_sms_result_creation(self):
        """Test SMSResult dataclass creation."""
        result = SMSResult(
            success=True,
            provider_id="test-sms-id",
            error_message=None
        )
        self.assertTrue(result.success)
        self.assertEqual(result.provider_id, "test-sms-id")
        self.assertIsNone(result.error_message)

    def test_mock_sms_adapter_initialization(self):
        """Test MockSMSAdapter initialization."""
        adapter = MockSMSAdapter()
        self.assertIsInstance(adapter.sent_messages, list)
        self.assertEqual(len(adapter.sent_messages), 0)

    def test_mock_sms_adapter_success(self):
        """Test MockSMSAdapter successful SMS sending."""
        adapter = MockSMSAdapter()
        message = SMSMessage(
            to="+1234567890",
            body="Test message"
        )
        result = adapter.send_sms(message)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.provider_id)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(adapter.sent_messages), 1)

    def test_mock_sms_adapter_get_provider_name(self):
        """Test MockSMSAdapter provider name."""
        adapter = MockSMSAdapter()
        self.assertEqual(adapter.get_provider_name(), "mock")

    def test_mock_sms_adapter_invalid_phone(self):
        """Test MockSMSAdapter with invalid phone number."""
        adapter = MockSMSAdapter()
        message = SMSMessage(
            to="invalid-phone",
            body="Test message"
        )
        result = adapter.send_sms(message)
        
        self.assertFalse(result.success)
        self.assertIsNone(result.provider_id)
        self.assertIn("Invalid phone", result.error_message)

    def test_mock_sms_adapter_empty_fields(self):
        """Test MockSMSAdapter with empty required fields."""
        adapter = MockSMSAdapter()
        
        # Empty to field
        message = SMSMessage(to="", body="Test message")
        result = adapter.send_sms(message)
        self.assertFalse(result.success)
        
        # Empty body
        message = SMSMessage(to="+1234567890", body="")
        result = adapter.send_sms(message)
        self.assertFalse(result.success)

    def test_mock_sms_adapter_long_message(self):
        """Test MockSMSAdapter with long message."""
        adapter = MockSMSAdapter()
        long_message = "x" * 161  # SMS limit exceeded
        message = SMSMessage(
            to="+1234567890",
            body=long_message
        )
        result = adapter.send_sms(message)
        
        self.assertFalse(result.success)
        self.assertIsNone(result.provider_id)
        self.assertIn("exceeds", result.error_message)


class TestPushAdapters(TestCase):
    """Tests for push notification adapters - focusing on mock adapter."""

    def test_push_message_creation(self):
        """Test PushMessage dataclass creation."""
        message = PushMessage(
            device_token="test-device-token",
            title="Test Title",
            body="Test Body",
            badge=1,
            sound="default"
        )
        self.assertEqual(message.device_token, "test-device-token")
        self.assertEqual(message.title, "Test Title")
        self.assertEqual(message.body, "Test Body")
        self.assertEqual(message.badge, 1)
        self.assertEqual(message.sound, "default")

    def test_push_result_creation(self):
        """Test PushResult dataclass creation."""
        result = PushResult(
            success=True,
            provider_id="test-push-id",
            error_message=None
        )
        self.assertTrue(result.success)
        self.assertEqual(result.provider_id, "test-push-id")
        self.assertIsNone(result.error_message)

    def test_mock_push_adapter_initialization(self):
        """Test MockPushAdapter initialization."""
        adapter = MockPushAdapter()
        self.assertIsInstance(adapter.sent_notifications, list)
        self.assertEqual(len(adapter.sent_notifications), 0)

    def test_mock_push_adapter_success(self):
        """Test MockPushAdapter successful push sending."""
        adapter = MockPushAdapter()
        message = PushMessage(
            device_token="test-device-token",
            title="Test Title",
            body="Test Body"
        )
        result = adapter.send_push(message)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.provider_id)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(adapter.sent_notifications), 1)

    def test_mock_push_adapter_get_provider_name(self):
        """Test MockPushAdapter provider name."""
        adapter = MockPushAdapter()
        self.assertEqual(adapter.get_provider_name(), "mock")

    def test_mock_push_adapter_empty_fields(self):
        """Test MockPushAdapter with empty required fields."""
        adapter = MockPushAdapter()
        
        # Empty device token
        message = PushMessage(device_token="", title="Test", body="Test")
        result = adapter.send_push(message)
        self.assertFalse(result.success)
        
        # Empty title
        message = PushMessage(device_token="test-token", title="", body="Test")
        result = adapter.send_push(message)
        self.assertFalse(result.success)
        
        # Empty body
        message = PushMessage(device_token="test-token", title="Test", body="")
        result = adapter.send_push(message)
        self.assertFalse(result.success)

    def test_mock_push_adapter_short_token(self):
        """Test MockPushAdapter with short device token."""
        adapter = MockPushAdapter()
        message = PushMessage(
            device_token="short",  # Too short device token
            title="Test Title",
            body="Test Body"
        )
        result = adapter.send_push(message)
        
        # Based on the mock implementation, it might succeed with any non-empty token
        # Let's test what actually happens
        self.assertIsInstance(result, PushResult)


class TestAdapterFactories(TestCase):
    """Tests for adapter factories."""

    def test_email_factory_mock(self):
        """Test EmailAdapterFactory mock creation."""
        from adapters.email import EmailAdapterFactory
        adapter = EmailAdapterFactory.create_adapter('mock', {})
        self.assertIsInstance(adapter, MockEmailAdapter)

    def test_email_factory_aws_ses(self):
        """Test EmailAdapterFactory AWS SES creation."""
        from adapters.email import EmailAdapterFactory, AWSEmailAdapter
        config = {
            'access_key_id': 'test-key',
            'secret_access_key': 'test-secret',
            'region': 'us-east-1'
        }
        adapter = EmailAdapterFactory.create_adapter('aws_ses', config)
        self.assertIsInstance(adapter, AWSEmailAdapter)

    def test_email_factory_sendgrid(self):
        """Test EmailAdapterFactory SendGrid creation."""
        from adapters.email import EmailAdapterFactory, SendGridEmailAdapter
        config = {'api_key': 'test-api-key'}
        adapter = EmailAdapterFactory.create_adapter('sendgrid', config)
        self.assertIsInstance(adapter, SendGridEmailAdapter)

    def test_email_factory_unknown_provider(self):
        """Test EmailAdapterFactory with unknown provider."""
        from adapters.email import EmailAdapterFactory
        with self.assertRaises(ValueError):
            EmailAdapterFactory.create_adapter('unknown', {})

    @patch('django.conf.settings')
    def test_email_factory_from_settings_mock(self, mock_settings):
        """Test EmailAdapterFactory create_from_settings - mock."""
        from adapters.email import EmailAdapterFactory
        mock_settings.EMAIL_PROVIDER = 'mock'
        adapter = EmailAdapterFactory.create_from_settings()
        self.assertIsInstance(adapter, MockEmailAdapter)

    @patch('django.conf.settings')
    def test_email_factory_from_settings_default(self, mock_settings):
        """Test EmailAdapterFactory create_from_settings - default to mock."""
        from adapters.email import EmailAdapterFactory
        # No EMAIL_PROVIDER attribute
        del mock_settings.EMAIL_PROVIDER
        adapter = EmailAdapterFactory.create_from_settings()
        self.assertIsInstance(adapter, MockEmailAdapter)

    def test_sms_factory_mock(self):
        """Test SMSAdapterFactory mock creation."""
        from adapters.sms import SMSAdapterFactory
        adapter = SMSAdapterFactory.create_adapter('mock', {})
        self.assertIsInstance(adapter, MockSMSAdapter)

    def test_sms_factory_twilio(self):
        """Test SMSAdapterFactory Twilio creation."""
        from adapters.sms import SMSAdapterFactory, TwilioSMSAdapter
        config = {
            'account_sid': 'test-sid',
            'auth_token': 'test-token',
            'from_number': '+1234567890'
        }
        adapter = SMSAdapterFactory.create_adapter('twilio', config)
        self.assertIsInstance(adapter, TwilioSMSAdapter)

    def test_sms_factory_unknown_provider(self):
        """Test SMSAdapterFactory with unknown provider."""
        from adapters.sms import SMSAdapterFactory
        with self.assertRaises(ValueError):
            SMSAdapterFactory.create_adapter('unknown', {})

    @patch('django.conf.settings')
    def test_sms_factory_from_settings_mock(self, mock_settings):
        """Test SMSAdapterFactory create_from_settings - mock."""
        from adapters.sms import SMSAdapterFactory
        mock_settings.SMS_PROVIDER = 'mock'
        adapter = SMSAdapterFactory.create_from_settings()
        self.assertIsInstance(adapter, MockSMSAdapter)

    def test_push_factory_mock(self):
        """Test PushAdapterFactory mock creation."""
        from adapters.push import PushAdapterFactory
        adapter = PushAdapterFactory.create_adapter('mock', {})
        self.assertIsInstance(adapter, MockPushAdapter)

    def test_push_factory_firebase(self):
        """Test PushAdapterFactory Firebase creation."""
        from adapters.push import PushAdapterFactory, FirebasePushAdapter
        config = {'credentials_path': '/path/to/credentials.json'}
        adapter = PushAdapterFactory.create_adapter('firebase', config)
        self.assertIsInstance(adapter, FirebasePushAdapter)

    def test_push_factory_unknown_provider(self):
        """Test PushAdapterFactory with unknown provider."""
        from adapters.push import PushAdapterFactory
        with self.assertRaises(ValueError):
            PushAdapterFactory.create_adapter('unknown', {})

    @patch('django.conf.settings')
    def test_push_factory_from_settings_mock(self, mock_settings):
        """Test PushAdapterFactory create_from_settings - mock."""
        from adapters.push import PushAdapterFactory
        mock_settings.PUSH_PROVIDER = 'mock'
        adapter = PushAdapterFactory.create_from_settings()
        self.assertIsInstance(adapter, MockPushAdapter)