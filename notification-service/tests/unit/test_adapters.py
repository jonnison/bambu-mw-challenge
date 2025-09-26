"""
Additional tests to improve coverage for adapters
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from adapters.email import EmailAdapter, MockEmailAdapter, AWSEmailAdapter, EmailMessage, EmailResult
from adapters.sms import SMSAdapter, MockSMSAdapter
from adapters.push import PushAdapter, MockPushAdapter


class TestEmailMessage(TestCase):
    """Test EmailMessage dataclass"""
    
    def test_email_message_creation(self):
        """Test creating email message"""
        message = EmailMessage(
            to="test@example.com",
            subject="Test Subject",
            body="Test Body"
        )
        
        assert message.to == "test@example.com"
        assert message.subject == "Test Subject"
        assert message.body == "Test Body"
        assert message.from_email is None
        assert message.reply_to is None
        assert message.attachments is None
    
    def test_email_message_with_optional_fields(self):
        """Test creating email message with optional fields"""
        message = EmailMessage(
            to="test@example.com",
            subject="Test Subject",
            body="Test Body",
            from_email="sender@example.com",
            reply_to="reply@example.com",
            attachments=["file.pdf"]
        )
        
        assert message.from_email == "sender@example.com"
        assert message.reply_to == "reply@example.com"
        assert message.attachments == ["file.pdf"]


class TestEmailResult(TestCase):
    """Test EmailResult dataclass"""
    
    def test_email_result_success(self):
        """Test successful email result"""
        result = EmailResult(
            success=True,
            provider_id="msg_123",
        )
        
        assert result.success is True
        assert result.provider_id == "msg_123"
        assert result.error_message is None
    
    def test_email_result_failure(self):
        """Test failed email result"""
        result = EmailResult(
            success=False,
            error_message="Email failed"
        )
        
        assert result.success is False
        assert result.error_message == "Email failed"
        assert result.provider_id is None


class TestMockEmailAdapter(TestCase):
    """Test mock email adapter"""
    
    def setUp(self):
        self.adapter = MockEmailAdapter()
    
    def test_mock_adapter_initialization(self):
        """Test mock adapter initialization"""
        assert self.adapter.sent_emails == []
        assert self.adapter.get_provider_name() == "mock"
    
    def test_send_email_success(self):
        """Test successful email sending"""
        message = EmailMessage(
            to="test@example.com",
            subject="Test Subject",
            body="Test Body"
        )
        
        result = self.adapter.send_email(message)
        
        assert result.success is True
        assert result.provider_id is not None
        assert len(self.adapter.sent_emails) == 1
    
    def test_send_email_invalid_address(self):
        """Test sending email with invalid address"""
        message = EmailMessage(
            to="invalid-email",
            subject="Test Subject",
            body="Test Body"
        )
        
        result = self.adapter.send_email(message)
        
        assert result.success is False
        assert "Invalid email address" in result.error_message
        assert len(self.adapter.sent_emails) == 0
    
    def test_send_email_missing_subject(self):
        """Test sending email with missing subject"""
        message = EmailMessage(
            to="test@example.com",
            subject="",
            body="Test Body"
        )
        
        result = self.adapter.send_email(message)
        
        assert result.success is False
        assert "Subject and body are required" in result.error_message
    
    def test_send_email_missing_body(self):
        """Test sending email with missing body"""
        message = EmailMessage(
            to="test@example.com",
            subject="Test Subject",
            body=""
        )
        
        result = self.adapter.send_email(message)
        
        assert result.success is False
        assert "Subject and body are required" in result.error_message


class TestAWSEmailAdapter(TestCase):
    """Test AWS SES email adapter"""
    
    def test_aws_adapter_initialization(self):
        """Test AWS adapter initialization"""
        adapter = AWSEmailAdapter(
            access_key_id="test_key",
            secret_access_key="test_secret",
            region="us-east-1"
        )
        
        assert adapter.access_key_id == "test_key"
        assert adapter.secret_access_key == "test_secret"
        assert adapter.region == "us-east-1"
        assert adapter.get_provider_name() == "aws_ses"
    
    @patch('boto3.client')
    def test_send_email_success(self, mock_boto_client):
        """Test successful email sending via AWS SES"""
        mock_ses = Mock()
        mock_ses.send_email.return_value = {
            'MessageId': 'aws_message_123'
        }
        mock_boto_client.return_value = mock_ses
        
        adapter = AWSEmailAdapter(
            access_key_id="test_key",
            secret_access_key="test_secret",
            region="us-east-1"
        )
        
        message = EmailMessage(
            to="test@example.com",
            subject="Test Subject",
            body="Test Body",
            from_email="sender@example.com"
        )
        
        result = adapter.send_email(message)
        
        assert result.success is True
        assert result.provider_id == "aws_message_123"
        mock_ses.send_email.assert_called_once()
    
    @patch('boto3.client')
    def test_send_email_failure(self, mock_boto_client):
        """Test email sending failure via AWS SES"""
        mock_ses = Mock()
        mock_ses.send_email.side_effect = Exception("AWS SES error")
        mock_boto_client.return_value = mock_ses
        
        adapter = AWSEmailAdapter(
            access_key_id="test_key",
            secret_access_key="test_secret",
            region="us-east-1"
        )
        
        message = EmailMessage(
            to="test@example.com",
            subject="Test Subject", 
            body="Test Body"
        )
        
        result = adapter.send_email(message)
        
        assert result.success is False
        assert "AWS SES error" in result.error_message