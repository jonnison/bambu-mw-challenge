"""
Test fixtures and factory classes for creating test data.
"""
import factory
from factory.django import DjangoModelFactory
from django.utils import timezone

from core.models import (
    NotificationTemplate,
    NotificationLog,
    UserPreference,
    NotificationQuota
)


class NotificationTemplateFactory(DjangoModelFactory):
    """Factory for creating NotificationTemplate instances."""
    
    class Meta:
        model = NotificationTemplate
    
    name = factory.Sequence(lambda n: f"Template {n}")
    template_type = factory.Iterator(['email', 'sms', 'push', 'in_app'])
    subject = factory.Faker('sentence', nb_words=4)
    content = factory.Faker('text', max_nb_chars=200)
    variables = factory.LazyFunction(lambda: ['user_name', 'date'])
    is_active = True
    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)


class EmailTemplateFactory(NotificationTemplateFactory):
    """Factory for creating email notification templates."""
    
    template_type = 'email'
    subject = factory.Faker('sentence', nb_words=6)
    content = "Hello {{user_name}}, " + factory.Faker('text', max_nb_chars=150)
    variables = ['user_name']


class SMSTemplateFactory(NotificationTemplateFactory):
    """Factory for creating SMS notification templates."""
    
    template_type = 'sms'
    subject = None
    content = factory.Faker('text', max_nb_chars=160)  # SMS character limit
    variables = ['user_name', 'code']


class PushTemplateFactory(NotificationTemplateFactory):
    """Factory for creating push notification templates."""
    
    template_type = 'push'
    subject = factory.Faker('sentence', nb_words=3)
    content = factory.Faker('text', max_nb_chars=100)
    variables = ['sender_name']


class UserPreferenceFactory(DjangoModelFactory):
    """Factory for creating UserPreference instances."""
    
    class Meta:
        model = UserPreference
    
    user_id = factory.Sequence(lambda n: f"user{n}")
    channel = factory.Iterator(['email', 'sms', 'push', 'in_app'])
    enabled = True
    frequency = factory.Iterator(['immediate', 'hourly', 'daily', 'weekly'])
    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)


class NotificationQuotaFactory(DjangoModelFactory):
    """Factory for creating NotificationQuota instances."""
    
    class Meta:
        model = NotificationQuota
    
    user_id = factory.Sequence(lambda n: f"user{n}")
    channel = factory.Iterator(['email', 'sms', 'push', 'in_app'])
    quota_limit = factory.Faker('random_int', min=10, max=1000)
    quota_used = factory.LazyAttribute(lambda obj: obj.quota_limit // 4)  # 25% used
    reset_period = factory.Iterator(['hourly', 'daily', 'weekly', 'monthly'])
    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)


class NotificationLogFactory(DjangoModelFactory):
    """Factory for creating NotificationLog instances."""
    
    class Meta:
        model = NotificationLog
    
    template = factory.SubFactory(NotificationTemplateFactory)
    user_id = factory.Sequence(lambda n: f"user{n}")
    recipient = factory.Faker('email')
    status = factory.Iterator(['pending', 'sent', 'delivered', 'failed', 'read'])
    channel = factory.Iterator(['email', 'sms', 'push', 'in_app'])
    content = factory.Faker('text', max_nb_chars=200)
    error_message = None
    sent_at = factory.Maybe(
        'status',
        yes_declaration=factory.LazyFunction(timezone.now),
        no_declaration=None,
        condition=lambda status: status in ['sent', 'delivered', 'read']
    )
    delivered_at = factory.Maybe(
        'status',
        yes_declaration=factory.LazyFunction(timezone.now),
        no_declaration=None,
        condition=lambda status: status in ['delivered', 'read']
    )
    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)


class FailedNotificationLogFactory(NotificationLogFactory):
    """Factory for creating failed notification logs."""
    
    status = 'failed'
    error_message = factory.Faker('sentence', nb_words=8)
    sent_at = None
    delivered_at = None


class SentNotificationLogFactory(NotificationLogFactory):
    """Factory for creating sent notification logs."""
    
    status = 'sent'
    sent_at = factory.LazyFunction(timezone.now)
    delivered_at = None


class DeliveredNotificationLogFactory(NotificationLogFactory):
    """Factory for creating delivered notification logs."""
    
    status = 'delivered'
    sent_at = factory.LazyFunction(timezone.now)
    delivered_at = factory.LazyFunction(timezone.now)


class TestDataMixin:
    """Mixin class providing common test data creation methods."""
    
    @classmethod
    def create_test_user_with_preferences(cls, user_id="test_user"):
        """Create a test user with complete preference set."""
        preferences = []
        for channel in ['email', 'sms', 'push']:
            preference = UserPreferenceFactory(
                user_id=user_id,
                channel=channel,
                enabled=True,
                frequency='immediate'
            )
            preferences.append(preference)
        return preferences
    
    @classmethod
    def create_test_templates_suite(cls):
        """Create a comprehensive set of test templates."""
        templates = {
            'email': EmailTemplateFactory(
                name='Welcome Email',
                content='Welcome {{user_name}} to our service!'
            ),
            'sms': SMSTemplateFactory(
                name='SMS Alert',
                content='Alert: {{message}} for {{user_name}}'
            ),
            'push': PushTemplateFactory(
                name='Push Notification',
                content='You have a new message from {{sender_name}}'
            )
        }
        return templates
    
    @classmethod
    def create_quota_scenarios(cls, user_id="test_user"):
        """Create various quota scenarios for testing."""
        scenarios = {
            'under_limit': NotificationQuotaFactory(
                user_id=user_id,
                channel='email',
                quota_limit=100,
                quota_used=25
            ),
            'at_limit': NotificationQuotaFactory(
                user_id=user_id,
                channel='sms',
                quota_limit=50,
                quota_used=50
            ),
            'over_limit': NotificationQuotaFactory(
                user_id=user_id,
                channel='push',
                quota_limit=200,
                quota_used=250
            )
        }
        return scenarios
    
    @classmethod
    def create_notification_history(cls, user_id="test_user", template=None):
        """Create notification history for testing."""
        if not template:
            template = EmailTemplateFactory()
        
        history = [
            SentNotificationLogFactory(
                template=template,
                user_id=user_id,
                channel='email'
            ),
            DeliveredNotificationLogFactory(
                template=template,
                user_id=user_id,
                channel='email'
            ),
            FailedNotificationLogFactory(
                template=template,
                user_id=user_id,
                channel='sms'
            )
        ]
        return history


class BulkTestDataFactory:
    """Factory for creating bulk test data."""
    
    @staticmethod
    def create_bulk_templates(count=10):
        """Create multiple templates for testing pagination, etc."""
        return NotificationTemplateFactory.create_batch(count)
    
    @staticmethod
    def create_bulk_users_with_preferences(user_count=5):
        """Create multiple users with complete preference sets."""
        users_data = {}
        for i in range(user_count):
            user_id = f"bulk_user_{i}"
            preferences = []
            for channel in ['email', 'sms', 'push']:
                preference = UserPreferenceFactory(
                    user_id=user_id,
                    channel=channel
                )
                preferences.append(preference)
            users_data[user_id] = preferences
        return users_data
    
    @staticmethod
    def create_bulk_notification_logs(count=50, template=None, users=None):
        """Create bulk notification logs for performance testing."""
        if not template:
            template = EmailTemplateFactory()
        
        if not users:
            users = [f"bulk_user_{i}" for i in range(10)]
        
        logs = []
        for i in range(count):
            user_id = users[i % len(users)]
            log = NotificationLogFactory(
                template=template,
                user_id=user_id
            )
            logs.append(log)
        return logs


# Test data constants
TEST_USERS = {
    'active_user': 'user123',
    'inactive_user': 'user456',
    'quota_exceeded_user': 'user789',
    'new_user': 'user999'
}

TEST_CHANNELS = ['email', 'sms', 'push', 'in_app']

TEST_TEMPLATE_VARIABLES = {
    'email': ['user_name', 'email', 'verification_link'],
    'sms': ['user_name', 'code', 'expiry_time'],
    'push': ['sender_name', 'message_preview'],
    'in_app': ['title', 'content', 'action_url']
}

SAMPLE_NOTIFICATION_DATA = {
    'welcome_email': {
        'template_id': 1,
        'user_id': 'user123',
        'recipient': 'test@example.com',
        'context': {
            'user_name': 'John Doe',
            'email': 'test@example.com'
        }
    },
    'sms_verification': {
        'template_id': 3,
        'user_id': 'user123',
        'recipient': '+1234567890',
        'context': {
            'user_name': 'John Doe',
            'code': '123456',
            'expiry_time': '5 minutes'
        }
    },
    'push_message': {
        'template_id': 4,
        'user_id': 'user123',
        'recipient': 'device_token_abc123',
        'context': {
            'sender_name': 'Alice Johnson',
            'message_preview': 'Hey, how are you doing?'
        }
    }
}