"""
SMS adapter implementations for different providers.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SMSMessage:
    """SMS message data structure."""
    to: str
    body: str
    from_number: Optional[str] = None


@dataclass
class SMSResult:
    """SMS sending result."""
    success: bool
    provider_id: Optional[str] = None
    error_message: Optional[str] = None


class SMSAdapter(ABC):
    """Abstract base class for SMS adapters."""
    
    @abstractmethod
    def send_sms(self, message: SMSMessage) -> SMSResult:
        """Send an SMS message."""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name."""
        pass


class MockSMSAdapter(SMSAdapter):
    """Mock SMS adapter for testing and development."""
    
    def __init__(self):
        self.sent_messages = []
    
    def send_sms(self, message: SMSMessage) -> SMSResult:
        """Simulate sending an SMS."""
        try:
            # Simulate some basic validation
            if not message.to or not message.to.startswith('+'):
                return SMSResult(
                    success=False,
                    error_message="Invalid phone number format (must start with +)"
                )
            
            if not message.body:
                return SMSResult(
                    success=False,
                    error_message="Message body is required"
                )
            
            if len(message.body) > 160:
                return SMSResult(
                    success=False,
                    error_message="Message body exceeds 160 characters"
                )
            
            # Simulate success
            provider_id = f"mock_sms_{len(self.sent_messages) + 1:06d}"
            
            self.sent_messages.append({
                'to': message.to,
                'body': message.body,
                'from_number': message.from_number,
                'provider_id': provider_id
            })
            
            logger.info(f"Mock SMS sent to {message.to}: {message.body[:50]}...")
            
            return SMSResult(
                success=True,
                provider_id=provider_id
            )
            
        except Exception as e:
            logger.error(f"Mock SMS adapter error: {e}")
            return SMSResult(
                success=False,
                error_message=str(e)
            )
    
    def get_provider_name(self) -> str:
        return "mock"


class TwilioSMSAdapter(SMSAdapter):
    """Twilio SMS adapter."""
    
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of Twilio client."""
        if self._client is None:
            try:
                from twilio.rest import Client
                self._client = Client(self.account_sid, self.auth_token)
            except ImportError:
                raise ImportError("twilio is required for Twilio SMS adapter")
        return self._client
    
    def send_sms(self, message: SMSMessage) -> SMSResult:
        """Send SMS via Twilio."""
        try:
            twilio_message = self.client.messages.create(
                body=message.body,
                from_=message.from_number or self.from_number,
                to=message.to
            )
            
            return SMSResult(
                success=True,
                provider_id=twilio_message.sid
            )
            
        except Exception as e:
            logger.error(f"Twilio SMS error: {e}")
            return SMSResult(
                success=False,
                error_message=str(e)
            )
    
    def get_provider_name(self) -> str:
        return "twilio"


class SMSAdapterFactory:
    """Factory for creating SMS adapters."""
    
    @staticmethod
    def create_adapter(provider: str, config: Dict[str, Any]) -> SMSAdapter:
        """Create an SMS adapter based on provider configuration."""
        if provider == 'mock':
            return MockSMSAdapter()
        elif provider == 'twilio':
            return TwilioSMSAdapter(
                account_sid=config['account_sid'],
                auth_token=config['auth_token'],
                from_number=config['from_number']
            )
        else:
            raise ValueError(f"Unknown SMS provider: {provider}")
    
    @staticmethod
    def create_from_settings() -> SMSAdapter:
        """Create SMS adapter from Django settings."""
        from django.conf import settings
        
        provider = getattr(settings, 'SMS_PROVIDER', 'mock')
        
        if provider == 'mock':
            return MockSMSAdapter()
        elif provider == 'twilio':
            config = {
                'account_sid': settings.TWILIO_ACCOUNT_SID,
                'auth_token': settings.TWILIO_AUTH_TOKEN,
                'from_number': settings.TWILIO_FROM_NUMBER
            }
            return TwilioSMSAdapter(**config)
        else:
            # Fallback to mock for unknown providers
            logger.warning(f"Unknown SMS provider '{provider}', using mock adapter")
            return MockSMSAdapter()