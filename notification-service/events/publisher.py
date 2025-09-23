"""
Event publisher for publishing domain events to message brokers.
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class NotificationEvent:
    """Base class for notification events."""
    event_id: str
    event_type: str
    aggregate_id: str
    user_id: int
    correlation_id: Optional[str]
    timestamp: str
    version: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class NotificationRequestedEvent(NotificationEvent):
    """Event published when a notification is requested."""
    template_name: str
    notification_type: str
    priority: str
    recipient: str
    metadata: Dict[str, Any]
    
    def __init__(
        self, 
        aggregate_id: str, 
        user_id: int, 
        template_name: str,
        notification_type: str,
        priority: str,
        recipient: str,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type="notification.requested",
            aggregate_id=aggregate_id,
            user_id=user_id,
            correlation_id=correlation_id,
            timestamp=datetime.utcnow().isoformat()
        )
        self.template_name = template_name
        self.notification_type = notification_type
        self.priority = priority
        self.recipient = recipient
        self.metadata = metadata or {}


@dataclass
class NotificationSentEvent(NotificationEvent):
    """Event published when a notification is successfully sent."""
    notification_type: str
    provider: str
    provider_id: str
    sent_at: str
    metadata: Dict[str, Any]
    
    def __init__(
        self,
        aggregate_id: str,
        user_id: int,
        notification_type: str,
        provider: str,
        provider_id: str,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type="notification.sent",
            aggregate_id=aggregate_id,
            user_id=user_id,
            correlation_id=correlation_id,
            timestamp=datetime.utcnow().isoformat()
        )
        self.notification_type = notification_type
        self.provider = provider
        self.provider_id = provider_id
        self.sent_at = datetime.utcnow().isoformat()
        self.metadata = metadata or {}


@dataclass
class NotificationFailedEvent(NotificationEvent):
    """Event published when a notification fails to send."""
    notification_type: str
    error_message: str
    retry_count: int
    next_retry_at: Optional[str]
    metadata: Dict[str, Any]
    
    def __init__(
        self,
        aggregate_id: str,
        user_id: int,
        notification_type: str,
        error_message: str,
        retry_count: int,
        next_retry_at: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type="notification.failed",
            aggregate_id=aggregate_id,
            user_id=user_id,
            correlation_id=correlation_id,
            timestamp=datetime.utcnow().isoformat()
        )
        self.notification_type = notification_type
        self.error_message = error_message
        self.retry_count = retry_count
        self.next_retry_at = next_retry_at
        self.metadata = metadata or {}


class EventPublisher:
    """Abstract base class for event publishers."""
    
    def publish(self, event: NotificationEvent) -> bool:
        """Publish an event."""
        raise NotImplementedError()
    
    def publish_batch(self, events: list[NotificationEvent]) -> bool:
        """Publish a batch of events."""
        raise NotImplementedError()


class RedisEventPublisher(EventPublisher):
    """Redis-based event publisher."""
    
    def __init__(self, redis_client, channel_prefix: str = "notification_events"):
        self.redis_client = redis_client
        self.channel_prefix = channel_prefix
    
    def publish(self, event: NotificationEvent) -> bool:
        """Publish event to Redis channel."""
        try:
            channel = f"{self.channel_prefix}.{event.event_type}"
            message = event.to_json()
            
            result = self.redis_client.publish(channel, message)
            logger.info(f"Published event {event.event_id} to channel {channel}")
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_id}: {e}")
            return False
    
    def publish_batch(self, events: list[NotificationEvent]) -> bool:
        """Publish batch of events to Redis."""
        try:
            pipe = self.redis_client.pipeline()
            
            for event in events:
                channel = f"{self.channel_prefix}.{event.event_type}"
                message = event.to_json()
                pipe.publish(channel, message)
            
            results = pipe.execute()
            success_count = sum(1 for result in results if result > 0)
            
            logger.info(f"Published {success_count}/{len(events)} events successfully")
            return success_count == len(events)
            
        except Exception as e:
            logger.error(f"Failed to publish event batch: {e}")
            return False


class CeleryEventPublisher(EventPublisher):
    """Celery-based event publisher for RabbitMQ/Redis broker."""
    
    def __init__(self, task_name: str = "events.publish_event"):
        self.task_name = task_name
    
    def publish(self, event: NotificationEvent) -> bool:
        """Publish event via Celery task."""
        try:
            from celery import current_app
            
            current_app.send_task(
                self.task_name,
                args=[event.to_dict()],
                routing_key=f"events.{event.event_type}"
            )
            
            logger.info(f"Queued event {event.event_id} for publishing via Celery")
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue event {event.event_id}: {e}")
            return False
    
    def publish_batch(self, events: list[NotificationEvent]) -> bool:
        """Publish batch of events via Celery."""
        try:
            from celery import current_app
            
            event_dicts = [event.to_dict() for event in events]
            current_app.send_task(
                "events.publish_event_batch",
                args=[event_dicts]
            )
            
            logger.info(f"Queued {len(events)} events for batch publishing via Celery")
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue event batch: {e}")
            return False


class MockEventPublisher(EventPublisher):
    """Mock event publisher for testing."""
    
    def __init__(self):
        self.published_events = []
    
    def publish(self, event: NotificationEvent) -> bool:
        """Mock publish - store event in memory."""
        self.published_events.append(event)
        logger.info(f"Mock published event {event.event_id}")
        return True
    
    def publish_batch(self, events: list[NotificationEvent]) -> bool:
        """Mock batch publish."""
        self.published_events.extend(events)
        logger.info(f"Mock published {len(events)} events")
        return True
    
    def get_published_events(self) -> list[NotificationEvent]:
        """Get all published events."""
        return self.published_events.copy()
    
    def clear(self):
        """Clear all published events."""
        self.published_events.clear()


class EventPublisherFactory:
    """Factory for creating event publishers."""
    
    @staticmethod
    def create_publisher(publisher_type: str = "mock", **config) -> EventPublisher:
        """Create an event publisher based on type."""
        if publisher_type == "mock":
            return MockEventPublisher()
        elif publisher_type == "redis":
            import redis
            redis_client = redis.Redis.from_url(config.get('redis_url', 'redis://localhost:6379/0'))
            return RedisEventPublisher(redis_client, config.get('channel_prefix', 'notification_events'))
        elif publisher_type == "celery":
            return CeleryEventPublisher(config.get('task_name', 'events.publish_event'))
        else:
            raise ValueError(f"Unknown publisher type: {publisher_type}")
    
    @staticmethod
    def create_from_settings() -> EventPublisher:
        """Create event publisher from Django settings."""
        from django.conf import settings
        
        publisher_type = getattr(settings, 'EVENT_PUBLISHER_TYPE', 'mock')
        
        if publisher_type == "redis":
            redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
            return EventPublisherFactory.create_publisher('redis', redis_url=redis_url)
        elif publisher_type == "celery":
            return EventPublisherFactory.create_publisher('celery')
        else:
            return EventPublisherFactory.create_publisher('mock')