"""
Comprehensive tests for events publisher to achieve 100% coverage
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, override_settings

from events.publisher import (
    NotificationEvent, 
    NotificationRequestedEvent,
    NotificationSentEvent,
    NotificationFailedEvent,
    EventPublisher,
    RedisEventPublisher,
    CeleryEventPublisher,
    MockEventPublisher,
    EventPublisherFactory
)


class TestNotificationEventComprehensive(TestCase):
    """Comprehensive tests for notification events"""

    def test_notification_event_creation(self):
        """Test creating notification event"""
        event = NotificationEvent(
            event_id="test-id",
            event_type="test.event",
            aggregate_id="agg-123",
            user_id=1,
            correlation_id="corr-123",
            timestamp="2024-01-01T00:00:00Z"
        )
        
        self.assertEqual(event.event_id, "test-id")
        self.assertEqual(event.event_type, "test.event")
        self.assertEqual(event.aggregate_id, "agg-123")
        self.assertEqual(event.user_id, 1)
        self.assertEqual(event.correlation_id, "corr-123")
        self.assertEqual(event.timestamp, "2024-01-01T00:00:00Z")
        self.assertEqual(event.version, 1)

    def test_to_dict(self):
        """Test converting event to dict"""
        event = NotificationEvent(
            event_id="test-id",
            event_type="test.event",
            aggregate_id="agg-123",
            user_id=1,
            correlation_id="corr-123",
            timestamp="2024-01-01T00:00:00Z"
        )
        
        result = event.to_dict()
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['event_id'], "test-id")
        self.assertEqual(result['event_type'], "test.event")
        self.assertEqual(result['user_id'], 1)

    def test_to_json(self):
        """Test converting event to JSON"""
        event = NotificationEvent(
            event_id="test-id",
            event_type="test.event",
            aggregate_id="agg-123",
            user_id=1,
            correlation_id="corr-123",
            timestamp="2024-01-01T00:00:00Z"
        )
        
        result = event.to_json()
        
        self.assertIsInstance(result, str)
        self.assertIn("test-id", result)
        self.assertIn("test.event", result)
        
        # Verify it's valid JSON
        parsed = json.loads(result)
        self.assertEqual(parsed['event_id'], "test-id")


class TestNotificationRequestedEventComprehensive(TestCase):
    """Comprehensive tests for notification requested event"""

    def test_event_creation_basic(self):
        """Test creating notification requested event"""
        event = NotificationRequestedEvent(
            aggregate_id="agg-123",
            user_id=1,
            template_name="welcome",
            notification_type="email",
            priority="high",
            recipient="test@example.com"
        )
        
        self.assertEqual(event.aggregate_id, "agg-123")
        self.assertEqual(event.user_id, 1)
        self.assertEqual(event.template_name, "welcome")
        self.assertEqual(event.notification_type, "email")
        self.assertEqual(event.priority, "high")
        self.assertEqual(event.recipient, "test@example.com")
        self.assertEqual(event.event_type, "notification.requested")
        self.assertEqual(event.metadata, {})
        self.assertIsNotNone(event.event_id)
        self.assertIsNotNone(event.timestamp)

    def test_event_with_metadata(self):
        """Test creating event with metadata"""
        metadata = {"key": "value", "source": "api"}
        
        event = NotificationRequestedEvent(
            aggregate_id="agg-123",
            user_id=1,
            template_name="welcome",
            notification_type="email",
            priority="high",
            recipient="test@example.com",
            metadata=metadata
        )
        
        self.assertEqual(event.metadata, metadata)

    def test_event_with_correlation_id(self):
        """Test creating event with correlation ID"""
        event = NotificationRequestedEvent(
            aggregate_id="agg-123",
            user_id=1,
            template_name="welcome",
            notification_type="email",
            priority="high",
            recipient="test@example.com",
            correlation_id="corr-456"
        )
        
        self.assertEqual(event.correlation_id, "corr-456")


class TestNotificationSentEventComprehensive(TestCase):
    """Comprehensive tests for notification sent event"""

    def test_event_creation_basic(self):
        """Test creating notification sent event"""
        event = NotificationSentEvent(
            aggregate_id="agg-123",
            user_id=1,
            notification_type="email",
            provider="ses",
            provider_id="msg-123"
        )
        
        self.assertEqual(event.aggregate_id, "agg-123")
        self.assertEqual(event.user_id, 1)
        self.assertEqual(event.notification_type, "email")
        self.assertEqual(event.provider, "ses")
        self.assertEqual(event.provider_id, "msg-123")
        self.assertEqual(event.event_type, "notification.sent")
        self.assertIsNotNone(event.sent_at)
        self.assertEqual(event.metadata, {})

    def test_event_with_correlation_and_metadata(self):
        """Test creating event with correlation ID and metadata"""
        metadata = {"delivery_time": "2024-01-01T00:01:00Z"}
        
        event = NotificationSentEvent(
            aggregate_id="agg-123",
            user_id=1,
            notification_type="email",
            provider="ses",
            provider_id="msg-123",
            correlation_id="corr-789",
            metadata=metadata
        )
        
        self.assertEqual(event.correlation_id, "corr-789")
        self.assertEqual(event.metadata, metadata)


class TestNotificationFailedEventComprehensive(TestCase):
    """Comprehensive tests for notification failed event"""

    def test_event_creation_basic(self):
        """Test creating notification failed event"""
        event = NotificationFailedEvent(
            aggregate_id="agg-123",
            user_id=1,
            notification_type="email",
            error_message="SMTP error",
            retry_count=1
        )
        
        self.assertEqual(event.aggregate_id, "agg-123")
        self.assertEqual(event.user_id, 1)
        self.assertEqual(event.notification_type, "email")
        self.assertEqual(event.error_message, "SMTP error")
        self.assertEqual(event.retry_count, 1)
        self.assertEqual(event.event_type, "notification.failed")
        self.assertIsNone(event.next_retry_at)
        self.assertEqual(event.metadata, {})

    def test_event_with_retry_time(self):
        """Test creating event with retry time"""
        retry_time = "2024-01-01T01:00:00Z"
        
        event = NotificationFailedEvent(
            aggregate_id="agg-123",
            user_id=1,
            notification_type="email",
            error_message="SMTP error",
            retry_count=1,
            next_retry_at=retry_time
        )
        
        self.assertEqual(event.next_retry_at, retry_time)

    def test_event_with_all_optional_params(self):
        """Test creating event with all optional parameters"""
        retry_time = "2024-01-01T01:00:00Z"
        metadata = {"error_code": "E001", "provider": "sendgrid"}
        
        event = NotificationFailedEvent(
            aggregate_id="agg-123",
            user_id=1,
            notification_type="email",
            error_message="SMTP error",
            retry_count=1,
            next_retry_at=retry_time,
            correlation_id="corr-456",
            metadata=metadata
        )
        
        self.assertEqual(event.next_retry_at, retry_time)
        self.assertEqual(event.correlation_id, "corr-456")
        self.assertEqual(event.metadata, metadata)


class TestEventPublisherAbstract(TestCase):
    """Test abstract event publisher"""

    def test_abstract_methods_raise_not_implemented(self):
        """Test that abstract methods raise NotImplementedError"""
        publisher = EventPublisher()
        event = NotificationEvent(
            event_id="test-id",
            event_type="test.event",
            aggregate_id="agg-123",
            user_id=1,
            timestamp="2024-01-01T00:00:00Z"
        )
        
        with self.assertRaises(NotImplementedError):
            publisher.publish(event)
        
        with self.assertRaises(NotImplementedError):
            publisher.publish_batch([event])


class TestRedisEventPublisher(TestCase):
    """Test Redis event publisher"""

    def setUp(self):
        self.mock_redis = Mock()
        self.publisher = RedisEventPublisher(self.mock_redis, "test_events")

    def test_initialization(self):
        """Test Redis publisher initialization"""
        self.assertEqual(self.publisher.redis_client, self.mock_redis)
        self.assertEqual(self.publisher.channel_prefix, "test_events")

    def test_initialization_default_prefix(self):
        """Test Redis publisher initialization with default prefix"""
        publisher = RedisEventPublisher(self.mock_redis)
        self.assertEqual(publisher.channel_prefix, "notification_events")

    def test_publish_success(self):
        """Test successful event publishing"""
        self.mock_redis.publish.return_value = 1
        
        event = NotificationRequestedEvent(
            aggregate_id="agg-123",
            user_id=1,
            template_name="welcome",
            notification_type="email",
            priority="high",
            recipient="test@example.com"
        )
        
        result = self.publisher.publish(event)
        
        self.assertTrue(result)
        self.mock_redis.publish.assert_called_once()
        call_args = self.mock_redis.publish.call_args
        self.assertEqual(call_args[0][0], "test_events.notification.requested")
        # The JSON contains the event data but template_name is in the event structure
        json_message = call_args[0][1]
        self.assertIn("agg-123", json_message)

    def test_publish_no_subscribers(self):
        """Test publishing with no subscribers"""
        self.mock_redis.publish.return_value = 0
        
        event = NotificationRequestedEvent(
            aggregate_id="agg-123",
            user_id=1,
            template_name="welcome",
            notification_type="email",
            priority="high",
            recipient="test@example.com"
        )
        
        result = self.publisher.publish(event)
        
        self.assertFalse(result)

    def test_publish_exception(self):
        """Test publish with exception"""
        self.mock_redis.publish.side_effect = Exception("Redis connection error")
        
        event = NotificationRequestedEvent(
            aggregate_id="agg-123",
            user_id=1,
            template_name="welcome",
            notification_type="email",
            priority="high",
            recipient="test@example.com"
        )
        
        result = self.publisher.publish(event)
        
        self.assertFalse(result)

    def test_publish_batch_success(self):
        """Test successful batch publishing"""
        mock_pipeline = Mock()
        mock_pipeline.execute.return_value = [1, 1, 1]
        self.mock_redis.pipeline.return_value = mock_pipeline
        
        events = [
            NotificationRequestedEvent(
                aggregate_id="agg-123",
                user_id=1,
                template_name="welcome",
                notification_type="email",
                priority="high",
                recipient="test@example.com"
            ),
            NotificationSentEvent(
                aggregate_id="agg-456",
                user_id=2,
                notification_type="sms",
                provider="twilio",
                provider_id="msg-456"
            ),
            NotificationFailedEvent(
                aggregate_id="agg-789",
                user_id=3,
                notification_type="push",
                error_message="Invalid token",
                retry_count=1
            )
        ]
        
        result = self.publisher.publish_batch(events)
        
        self.assertTrue(result)
        self.mock_redis.pipeline.assert_called_once()
        self.assertEqual(mock_pipeline.publish.call_count, 3)
        mock_pipeline.execute.assert_called_once()

    def test_publish_batch_partial_failure(self):
        """Test batch publishing with partial failures"""
        mock_pipeline = Mock()
        mock_pipeline.execute.return_value = [1, 0]  # Second one failed
        self.mock_redis.pipeline.return_value = mock_pipeline
        
        events = [
            NotificationRequestedEvent(
                aggregate_id="agg-123",
                user_id=1,
                template_name="welcome",
                notification_type="email",
                priority="high",
                recipient="test@example.com"
            ),
            NotificationSentEvent(
                aggregate_id="agg-456",
                user_id=2,
                notification_type="sms",
                provider="twilio",
                provider_id="msg-456"
            )
        ]
        
        result = self.publisher.publish_batch(events)
        
        self.assertFalse(result)

    def test_publish_batch_exception(self):
        """Test batch publishing with exception"""
        self.mock_redis.pipeline.side_effect = Exception("Pipeline error")
        
        events = [
            NotificationRequestedEvent(
                aggregate_id="agg-123",
                user_id=1,
                template_name="welcome",
                notification_type="email",
                priority="high",
                recipient="test@example.com"
            )
        ]
        
        result = self.publisher.publish_batch(events)
        
        self.assertFalse(result)


class TestCeleryEventPublisher(TestCase):
    """Test Celery event publisher"""

    def setUp(self):
        self.publisher = CeleryEventPublisher()

    def test_initialization_default(self):
        """Test Celery publisher initialization with default task name"""
        self.assertEqual(self.publisher.task_name, "events.publish_event")

    def test_initialization_custom_task(self):
        """Test Celery publisher initialization with custom task name"""
        publisher = CeleryEventPublisher("custom.publish")
        self.assertEqual(publisher.task_name, "custom.publish")

    @patch('celery.current_app')
    def test_publish_success(self, mock_current_app):
        """Test successful event publishing via Celery"""
        event = NotificationRequestedEvent(
            aggregate_id="agg-123",
            user_id=1,
            template_name="welcome",
            notification_type="email",
            priority="high",
            recipient="test@example.com"
        )
        
        result = self.publisher.publish(event)
        
        self.assertTrue(result)
        mock_current_app.send_task.assert_called_once_with(
            "events.publish_event",
            args=[event.to_dict()],
            routing_key="events.notification.requested"
        )

    @patch('celery.current_app')
    def test_publish_exception(self, mock_current_app):
        """Test publish with exception"""
        mock_current_app.send_task.side_effect = Exception("Celery error")
        
        event = NotificationRequestedEvent(
            aggregate_id="agg-123",
            user_id=1,
            template_name="welcome",
            notification_type="email",
            priority="high",
            recipient="test@example.com"
        )
        
        result = self.publisher.publish(event)
        
        self.assertFalse(result)

    @patch('celery.current_app')
    def test_publish_batch_success(self, mock_current_app):
        """Test successful batch publishing via Celery"""
        events = [
            NotificationRequestedEvent(
                aggregate_id="agg-123",
                user_id=1,
                template_name="welcome",
                notification_type="email",
                priority="high",
                recipient="test@example.com"
            ),
            NotificationSentEvent(
                aggregate_id="agg-456",
                user_id=2,
                notification_type="sms",
                provider="twilio",
                provider_id="msg-456"
            )
        ]
        
        result = self.publisher.publish_batch(events)
        
        self.assertTrue(result)
        mock_current_app.send_task.assert_called_once_with(
            "events.publish_event_batch",
            args=[[event.to_dict() for event in events]]
        )

    @patch('celery.current_app')
    def test_publish_batch_exception(self, mock_current_app):
        """Test batch publishing with exception"""
        mock_current_app.send_task.side_effect = Exception("Celery batch error")
        
        events = [
            NotificationRequestedEvent(
                aggregate_id="agg-123",
                user_id=1,
                template_name="welcome",
                notification_type="email",
                priority="high",
                recipient="test@example.com"
            )
        ]
        
        result = self.publisher.publish_batch(events)
        
        self.assertFalse(result)


class TestMockEventPublisher(TestCase):
    """Test Mock event publisher"""

    def setUp(self):
        self.publisher = MockEventPublisher()

    def test_initialization(self):
        """Test Mock publisher initialization"""
        self.assertEqual(len(self.publisher.published_events), 0)

    def test_publish_success(self):
        """Test successful event publishing"""
        event = NotificationRequestedEvent(
            aggregate_id="agg-123",
            user_id=1,
            template_name="welcome",
            notification_type="email",
            priority="high",
            recipient="test@example.com"
        )
        
        result = self.publisher.publish(event)
        
        self.assertTrue(result)
        self.assertEqual(len(self.publisher.published_events), 1)
        self.assertEqual(self.publisher.published_events[0], event)

    def test_publish_batch_success(self):
        """Test successful batch publishing"""
        events = [
            NotificationRequestedEvent(
                aggregate_id="agg-123",
                user_id=1,
                template_name="welcome",
                notification_type="email",
                priority="high",
                recipient="test@example.com"
            ),
            NotificationSentEvent(
                aggregate_id="agg-456",
                user_id=2,
                notification_type="sms",
                provider="twilio",
                provider_id="msg-456"
            )
        ]
        
        result = self.publisher.publish_batch(events)
        
        self.assertTrue(result)
        self.assertEqual(len(self.publisher.published_events), 2)
        self.assertEqual(self.publisher.published_events[0], events[0])
        self.assertEqual(self.publisher.published_events[1], events[1])

    def test_get_published_events(self):
        """Test getting published events"""
        event = NotificationRequestedEvent(
            aggregate_id="agg-123",
            user_id=1,
            template_name="welcome",
            notification_type="email",
            priority="high",
            recipient="test@example.com"
        )
        
        self.publisher.publish(event)
        retrieved_events = self.publisher.get_published_events()
        
        self.assertEqual(len(retrieved_events), 1)
        self.assertEqual(retrieved_events[0], event)
        # Verify it's a copy, not the original list
        self.assertIsNot(retrieved_events, self.publisher.published_events)

    def test_clear_events(self):
        """Test clearing published events"""
        event = NotificationRequestedEvent(
            aggregate_id="agg-123",
            user_id=1,
            template_name="welcome",
            notification_type="email",
            priority="high",
            recipient="test@example.com"
        )
        
        self.publisher.publish(event)
        self.assertEqual(len(self.publisher.published_events), 1)
        
        self.publisher.clear()
        self.assertEqual(len(self.publisher.published_events), 0)


class TestEventPublisherFactory(TestCase):
    """Test Event Publisher Factory"""

    def test_create_mock_publisher(self):
        """Test creating mock publisher"""
        publisher = EventPublisherFactory.create_publisher("mock")
        self.assertIsInstance(publisher, MockEventPublisher)

    @patch('redis.Redis')
    def test_create_redis_publisher(self, mock_redis_class):
        """Test creating Redis publisher"""
        mock_redis_client = Mock()
        mock_redis_class.from_url.return_value = mock_redis_client
        
        publisher = EventPublisherFactory.create_publisher(
            "redis", 
            redis_url="redis://localhost:6379/1",
            channel_prefix="custom_events"
        )
        
        self.assertIsInstance(publisher, RedisEventPublisher)
        mock_redis_class.from_url.assert_called_once_with("redis://localhost:6379/1")

    @patch('redis.Redis')
    def test_create_redis_publisher_defaults(self, mock_redis_class):
        """Test creating Redis publisher with defaults"""
        mock_redis_client = Mock()
        mock_redis_class.from_url.return_value = mock_redis_client
        
        publisher = EventPublisherFactory.create_publisher("redis")
        
        self.assertIsInstance(publisher, RedisEventPublisher)
        mock_redis_class.from_url.assert_called_once_with("redis://localhost:6379/0")

    def test_create_celery_publisher(self):
        """Test creating Celery publisher"""
        publisher = EventPublisherFactory.create_publisher("celery")
        self.assertIsInstance(publisher, CeleryEventPublisher)

    def test_create_celery_publisher_custom_task(self):
        """Test creating Celery publisher with custom task name"""
        publisher = EventPublisherFactory.create_publisher(
            "celery", 
            task_name="custom.publish_event"
        )
        self.assertIsInstance(publisher, CeleryEventPublisher)
        self.assertEqual(publisher.task_name, "custom.publish_event")

    def test_create_unknown_publisher_type(self):
        """Test creating unknown publisher type raises ValueError"""
        with self.assertRaises(ValueError) as context:
            EventPublisherFactory.create_publisher("unknown")
        
        self.assertIn("Unknown publisher type: unknown", str(context.exception))

    @override_settings(EVENT_PUBLISHER_TYPE='mock')
    def test_create_from_settings_mock(self):
        """Test creating publisher from settings - mock"""
        publisher = EventPublisherFactory.create_from_settings()
        self.assertIsInstance(publisher, MockEventPublisher)

    @override_settings(EVENT_PUBLISHER_TYPE='redis', REDIS_URL='redis://test:6379/2')
    @patch('events.publisher.EventPublisherFactory.create_publisher')
    def test_create_from_settings_redis(self, mock_create_publisher):
        """Test creating publisher from settings - Redis"""
        mock_publisher = Mock()
        mock_create_publisher.return_value = mock_publisher
        
        result = EventPublisherFactory.create_from_settings()
        
        mock_create_publisher.assert_called_once_with('redis', redis_url='redis://test:6379/2')
        self.assertEqual(result, mock_publisher)

    @override_settings(EVENT_PUBLISHER_TYPE='celery')
    @patch('events.publisher.EventPublisherFactory.create_publisher')
    def test_create_from_settings_celery(self, mock_create_publisher):
        """Test creating publisher from settings - Celery"""
        mock_publisher = Mock()
        mock_create_publisher.return_value = mock_publisher
        
        result = EventPublisherFactory.create_from_settings()
        
        mock_create_publisher.assert_called_once_with('celery')
        self.assertEqual(result, mock_publisher)

    def test_create_from_settings_default(self):
        """Test creating publisher from settings - default to mock"""
        with override_settings():
            # Remove EVENT_PUBLISHER_TYPE if it exists
            from django.conf import settings
            if hasattr(settings, 'EVENT_PUBLISHER_TYPE'):
                delattr(settings, 'EVENT_PUBLISHER_TYPE')
            
            publisher = EventPublisherFactory.create_from_settings()
            self.assertIsInstance(publisher, MockEventPublisher)

    @override_settings(EVENT_PUBLISHER_TYPE='unknown_type')
    def test_create_from_settings_unknown_fallback(self):
        """Test creating publisher from settings - unknown type falls back to mock"""
        publisher = EventPublisherFactory.create_from_settings()
        self.assertIsInstance(publisher, MockEventPublisher)