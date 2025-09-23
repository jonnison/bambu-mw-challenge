"""
Pytest configuration and fixtures.
"""
import os
import django
import pytest
from django.conf import settings
from django.test.utils import get_runner

# Configure Django settings for testing
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_service.settings')
    django.setup()


@pytest.fixture(scope='session')
def django_db_setup():
    """Set up database for testing session."""
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }


@pytest.fixture
def api_client():
    """Provide API client for testing."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def sample_template():
    """Provide a sample notification template."""
    from core.models import NotificationTemplate
    return NotificationTemplate.objects.create(
        name='Test Template',
        template_type='email',
        content='Hello {{user_name}}!',
        subject='Test Subject',
        variables=['user_name']
    )


@pytest.fixture
def sample_user_preference():
    """Provide a sample user preference."""
    from core.models import UserPreference
    return UserPreference.objects.create(
        user_id='test_user',
        channel='email',
        enabled=True,
        frequency='immediate'
    )


@pytest.fixture
def sample_quota():
    """Provide a sample notification quota."""
    from core.models import NotificationQuota
    return NotificationQuota.objects.create(
        user_id='test_user',
        channel='email',
        quota_limit=100,
        quota_used=25
    )


@pytest.fixture
def sample_notification_log(sample_template):
    """Provide a sample notification log."""
    from core.models import NotificationLog
    return NotificationLog.objects.create(
        template=sample_template,
        user_id='test_user',
        recipient='test@example.com',
        status='sent',
        channel='email',
        content='Rendered content'
    )


@pytest.fixture
def mock_email_backend():
    """Mock email backend for testing."""
    from unittest.mock import patch
    with patch('django.core.mail.send_mail') as mock_send:
        mock_send.return_value = True
        yield mock_send


@pytest.fixture
def mock_message_broker():
    """Mock message broker for testing."""
    from unittest.mock import patch, Mock
    with patch('pika.BlockingConnection') as mock_connection:
        mock_channel = Mock()
        mock_connection.return_value.channel.return_value = mock_channel
        yield mock_channel


@pytest.fixture
def test_user_data():
    """Provide test user data for notifications."""
    return {
        'user_id': 'test_user_123',
        'email': 'testuser@example.com',
        'phone': '+1234567890',
        'device_token': 'device_token_abc123',
        'preferences': {
            'email': True,
            'sms': True,
            'push': False
        }
    }


@pytest.fixture
def notification_context():
    """Provide notification context variables."""
    return {
        'user_name': 'John Doe',
        'email': 'john@example.com',
        'verification_code': '123456',
        'expiry_time': '5 minutes',
        'order_id': 'ORD-12345',
        'amount': '$99.99'
    }


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Automatically enable database access for all tests.
    This fixture is autouse=True, so it applies to all tests.
    """
    pass


@pytest.fixture
def transactional_db(transactional_db):
    """Enable transactional database access."""
    return transactional_db


# Custom markers for test organization
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow
pytest.mark.external = pytest.mark.external
pytest.mark.database = pytest.mark.database
pytest.mark.api = pytest.mark.api
pytest.mark.models = pytest.mark.models
pytest.mark.services = pytest.mark.services
pytest.mark.adapters = pytest.mark.adapters