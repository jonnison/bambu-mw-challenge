"""
Tests for events publisher
"""
import pytest
from unittest.mock import Mock, patch
from django.test import TestCase
from events.publisher import (
    NotificationEvent, 
    NotificationRequestedEvent,
    NotificationSentEvent,
    NotificationFailedEvent,
    EventPublisher
)


class TestNotificationEvent(TestCase):
    """Test base notification event"""
    
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
        
        assert event.event_id == "test-id"
        assert event.event_type == "test.event"
        assert event.aggregate_id == "agg-123"
        assert event.user_id == 1
        assert event.correlation_id == "corr-123"
        assert event.timestamp == "2024-01-01T00:00:00Z"
        assert event.version == 1
    
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
        
        assert isinstance(result, dict)
        assert result['event_id'] == "test-id"
        assert result['event_type'] == "test.event"
        assert result['user_id'] == 1
    
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
        
        assert isinstance(result, str)
        assert "test-id" in result
        assert "test.event" in result


class TestNotificationRequestedEvent(TestCase):
    """Test notification requested event"""
    
    def test_event_creation(self):
        """Test creating notification requested event"""
        event = NotificationRequestedEvent(
            aggregate_id="agg-123",
            user_id=1,
            template_name="welcome",
            notification_type="email",
            priority="high",
            recipient="test@example.com"
        )
        
        assert event.aggregate_id == "agg-123"
        assert event.user_id == 1
        assert event.template_name == "welcome"
        assert event.notification_type == "email"
        assert event.priority == "high"
        assert event.recipient == "test@example.com"
        assert event.event_type == "notification.requested"
        assert event.metadata == {}
    
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
        
        assert event.metadata == metadata


class TestNotificationSentEvent(TestCase):
    """Test notification sent event"""
    
    def test_event_creation(self):
        """Test creating notification sent event"""
        event = NotificationSentEvent(
            aggregate_id="agg-123",
            user_id=1,
            notification_type="email",
            provider="ses",
            provider_id="msg-123"
        )
        
        assert event.aggregate_id == "agg-123"
        assert event.user_id == 1
        assert event.notification_type == "email"
        assert event.provider == "ses"
        assert event.provider_id == "msg-123"
        assert event.event_type == "notification.sent"
        assert event.sent_at is not None
        assert event.metadata == {}


class TestNotificationFailedEvent(TestCase):
    """Test notification failed event"""
    
    def test_event_creation(self):
        """Test creating notification failed event"""
        event = NotificationFailedEvent(
            aggregate_id="agg-123",
            user_id=1,  
            notification_type="email",
            error_message="SMTP error",
            retry_count=1
        )
        
        assert event.aggregate_id == "agg-123"
        assert event.user_id == 1
        assert event.notification_type == "email"
        assert event.error_message == "SMTP error"
        assert event.retry_count == 1
        assert event.event_type == "notification.failed"
        assert event.next_retry_at is None
        assert event.metadata == {}
    
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
        
        assert event.next_retry_at == retry_time


class TestEventPublisher(TestCase):
    """Test event publisher"""

    def setUp(self):
        self.publisher = EventPublisher()
    
    def test_publisher_initialization(self):
        """Test publisher initialization"""
        assert self.publisher is not None
        assert hasattr(self.publisher, 'publish')
    
    def test_publish_event_method_exists(self):
        """Test that publish method exists"""
        assert hasattr(self.publisher, 'publish')
        assert callable(getattr(self.publisher, 'publish'))
    
    def test_publisher_has_methods(self):
        """Test publisher has required methods"""
        # These are the methods that actually exist
        assert hasattr(self.publisher, 'publish')
        assert hasattr(self.publisher, 'publish_batch')
    
    def test_event_serialization(self):
        """Test that published events are properly serialized"""
        event = NotificationRequestedEvent(
            aggregate_id="agg-123",
            user_id=1,
            template_name="welcome",
            notification_type="email",
            priority="high",
            recipient="test@example.com"
        )
        
        # Test the event can be serialized
        json_str = event.to_json()
        assert isinstance(json_str, str)
        assert "agg-123" in json_str
        assert "notification.requested" in json_str