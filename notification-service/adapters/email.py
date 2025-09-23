"""
Email adapter implementations for different providers.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """Email message data structure."""
    to: str
    subject: str
    body: str
    from_email: Optional[str] = None
    reply_to: Optional[str] = None
    attachments: Optional[list] = None


@dataclass
class EmailResult:
    """Email sending result."""
    success: bool
    provider_id: Optional[str] = None
    error_message: Optional[str] = None


class EmailAdapter(ABC):
    """Abstract base class for email adapters."""
    
    @abstractmethod
    def send_email(self, message: EmailMessage) -> EmailResult:
        """Send an email message."""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name."""
        pass


class MockEmailAdapter(EmailAdapter):
    """Mock email adapter for testing and development."""
    
    def __init__(self):
        self.sent_emails = []
    
    def send_email(self, message: EmailMessage) -> EmailResult:
        """Simulate sending an email."""
        try:
            # Simulate some basic validation
            if not message.to or '@' not in message.to:
                return EmailResult(
                    success=False,
                    error_message="Invalid email address"
                )
            
            if not message.subject or not message.body:
                return EmailResult(
                    success=False,
                    error_message="Subject and body are required"
                )
            
            # Simulate success
            provider_id = f"mock_email_{len(self.sent_emails) + 1:06d}"
            
            self.sent_emails.append({
                'to': message.to,
                'subject': message.subject,
                'body': message.body,
                'provider_id': provider_id,
                'timestamp': logger.info(f"Mock email sent to {message.to}: {message.subject}")
            })
            
            logger.info(f"Mock email sent to {message.to}: {message.subject}")
            
            return EmailResult(
                success=True,
                provider_id=provider_id
            )
            
        except Exception as e:
            logger.error(f"Mock email adapter error: {e}")
            return EmailResult(
                success=False,
                error_message=str(e)
            )
    
    def get_provider_name(self) -> str:
        return "mock"


class AWSEmailAdapter(EmailAdapter):
    """AWS SES email adapter."""
    
    def __init__(self, access_key_id: str, secret_access_key: str, region: str):
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of boto3 client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    'ses',
                    aws_access_key_id=self.access_key_id,
                    aws_secret_access_key=self.secret_access_key,
                    region_name=self.region
                )
            except ImportError:
                raise ImportError("boto3 is required for AWS SES adapter")
        return self._client
    
    def send_email(self, message: EmailMessage) -> EmailResult:
        """Send email via AWS SES."""
        try:
            response = self.client.send_email(
                Source=message.from_email or 'noreply@example.com',
                Destination={'ToAddresses': [message.to]},
                Message={
                    'Subject': {'Data': message.subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Text': {'Data': message.body, 'Charset': 'UTF-8'}
                    }
                },
                ReplyToAddresses=[message.reply_to] if message.reply_to else []
            )
            
            return EmailResult(
                success=True,
                provider_id=response['MessageId']
            )
            
        except Exception as e:
            logger.error(f"AWS SES error: {e}")
            return EmailResult(
                success=False,
                error_message=str(e)
            )
    
    def get_provider_name(self) -> str:
        return "aws_ses"


class SendGridEmailAdapter(EmailAdapter):
    """SendGrid email adapter."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def send_email(self, message: EmailMessage) -> EmailResult:
        """Send email via SendGrid."""
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail
            
            sg = sendgrid.SendGridAPIClient(api_key=self.api_key)
            
            mail = Mail(
                from_email=message.from_email or 'noreply@example.com',
                to_emails=message.to,
                subject=message.subject,
                plain_text_content=message.body
            )
            
            response = sg.send(mail)
            
            if response.status_code == 202:
                return EmailResult(
                    success=True,
                    provider_id=response.headers.get('X-Message-Id')
                )
            else:
                return EmailResult(
                    success=False,
                    error_message=f"SendGrid error: {response.status_code}"
                )
                
        except ImportError:
            raise ImportError("sendgrid is required for SendGrid adapter")
        except Exception as e:
            logger.error(f"SendGrid error: {e}")
            return EmailResult(
                success=False,
                error_message=str(e)
            )
    
    def get_provider_name(self) -> str:
        return "sendgrid"


class EmailAdapterFactory:
    """Factory for creating email adapters."""
    
    @staticmethod
    def create_adapter(provider: str, config: Dict[str, Any]) -> EmailAdapter:
        """Create an email adapter based on provider configuration."""
        if provider == 'mock':
            return MockEmailAdapter()
        elif provider == 'aws_ses':
            return AWSEmailAdapter(
                access_key_id=config['access_key_id'],
                secret_access_key=config['secret_access_key'],
                region=config['region']
            )
        elif provider == 'sendgrid':
            return SendGridEmailAdapter(api_key=config['api_key'])
        else:
            raise ValueError(f"Unknown email provider: {provider}")
    
    @staticmethod
    def create_from_settings() -> EmailAdapter:
        """Create email adapter from Django settings."""
        from django.conf import settings
        
        provider = getattr(settings, 'EMAIL_PROVIDER', 'mock')
        
        if provider == 'mock':
            return MockEmailAdapter()
        elif provider == 'aws_ses':
            config = {
                'access_key_id': settings.AWS_ACCESS_KEY_ID,
                'secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
                'region': settings.AWS_SES_REGION
            }
            return AWSEmailAdapter(**config)
        elif provider == 'sendgrid':
            config = {'api_key': settings.SENDGRID_API_KEY}
            return SendGridEmailAdapter(**config)
        else:
            # Fallback to mock for unknown providers
            logger.warning(f"Unknown email provider '{provider}', using mock adapter")
            return MockEmailAdapter()