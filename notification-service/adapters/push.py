"""
Push notification adapter implementations for different providers.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PushMessage:
    """Push notification message data structure."""
    device_token: str
    title: str
    body: str
    data: Optional[Dict[str, Any]] = None
    badge: Optional[int] = None
    sound: Optional[str] = None


@dataclass
class PushResult:
    """Push notification sending result."""
    success: bool
    provider_id: Optional[str] = None
    error_message: Optional[str] = None


class PushAdapter(ABC):
    """Abstract base class for push notification adapters."""
    
    @abstractmethod
    def send_push(self, message: PushMessage) -> PushResult:
        """Send a push notification."""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name."""
        pass


class MockPushAdapter(PushAdapter):
    """Mock push adapter for testing and development."""
    
    def __init__(self):
        self.sent_notifications = []
    
    def send_push(self, message: PushMessage) -> PushResult:
        """Simulate sending a push notification."""
        try:
            # Simulate some basic validation
            if not message.device_token:
                return PushResult(
                    success=False,
                    error_message="Device token is required"
                )
            
            if not message.title or not message.body:
                return PushResult(
                    success=False,
                    error_message="Title and body are required"
                )
            
            # Simulate success
            provider_id = f"mock_push_{len(self.sent_notifications) + 1:06d}"
            
            self.sent_notifications.append({
                'device_token': message.device_token,
                'title': message.title,
                'body': message.body,
                'data': message.data,
                'provider_id': provider_id
            })
            
            logger.info(f"Mock push sent to {message.device_token[:20]}...: {message.title}")
            
            return PushResult(
                success=True,
                provider_id=provider_id
            )
            
        except Exception as e:
            logger.error(f"Mock push adapter error: {e}")
            return PushResult(
                success=False,
                error_message=str(e)
            )
    
    def get_provider_name(self) -> str:
        return "mock"


class FirebasePushAdapter(PushAdapter):
    """Firebase Cloud Messaging (FCM) push adapter."""
    
    def __init__(self, credentials_path: str):
        self.credentials_path = credentials_path
        self._app = None
    
    @property
    def app(self):
        """Lazy initialization of Firebase app."""
        if self._app is None:
            try:
                import firebase_admin
                from firebase_admin import credentials
                
                if not firebase_admin._apps:
                    cred = credentials.Certificate(self.credentials_path)
                    self._app = firebase_admin.initialize_app(cred)
                else:
                    self._app = firebase_admin.get_app()
            except ImportError:
                raise ImportError("firebase-admin is required for Firebase push adapter")
        return self._app
    
    def send_push(self, message: PushMessage) -> PushResult:
        """Send push notification via Firebase FCM."""
        try:
            from firebase_admin import messaging
            
            # Ensure app is initialized
            _ = self.app
            
            # Create FCM message
            fcm_message = messaging.Message(
                notification=messaging.Notification(
                    title=message.title,
                    body=message.body
                ),
                data=message.data or {},
                token=message.device_token,
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            badge=message.badge,
                            sound=message.sound or 'default'
                        )
                    )
                ) if message.badge or message.sound else None
            )
            
            response = messaging.send(fcm_message)
            
            return PushResult(
                success=True,
                provider_id=response
            )
            
        except Exception as e:
            logger.error(f"Firebase FCM error: {e}")
            return PushResult(
                success=False,
                error_message=str(e)
            )
    
    def get_provider_name(self) -> str:
        return "firebase"


class PushAdapterFactory:
    """Factory for creating push notification adapters."""
    
    @staticmethod
    def create_adapter(provider: str, config: Dict[str, Any]) -> PushAdapter:
        """Create a push adapter based on provider configuration."""
        if provider == 'mock':
            return MockPushAdapter()
        elif provider == 'firebase':
            return FirebasePushAdapter(credentials_path=config['credentials_path'])
        else:
            raise ValueError(f"Unknown push provider: {provider}")
    
    @staticmethod
    def create_from_settings() -> PushAdapter:
        """Create push adapter from Django settings."""
        from django.conf import settings
        
        provider = getattr(settings, 'PUSH_PROVIDER', 'mock')
        
        if provider == 'mock':
            return MockPushAdapter()
        elif provider == 'firebase':
            config = {'credentials_path': settings.FIREBASE_CREDENTIALS_PATH}
            return FirebasePushAdapter(**config)
        else:
            # Fallback to mock for unknown providers
            logger.warning(f"Unknown push provider '{provider}', using mock adapter")
            return MockPushAdapter()