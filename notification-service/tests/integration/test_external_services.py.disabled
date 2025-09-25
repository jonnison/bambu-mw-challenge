"""
External service integration tests.
"""
from django.test import TestCase, TransactionTestCase
from unittest.mock import Mock, patch, MagicMock
import time
import threading
from django.conf import settings

from adapters.email_adapter import EmailAdapter
from adapters.sms_adapter import SMSAdapter
from adapters.push_adapter import PushAdapter
from adapters.circuit_breaker import CircuitBreaker
from adapters.retry_decorator import retry
from events.publisher import EventPublisher
from events.consumer import EventConsumer


class MessageBrokerIntegrationTest(TestCase):
    """Test message broker integration."""

    def setUp(self):
        """Set up test data."""
        self.publisher = EventPublisher()
        self.consumer = EventConsumer()

    @patch('pika.BlockingConnection')
    def test_rabbitmq_connection(self, mock_connection):
        """Test RabbitMQ connection establishment."""
        mock_channel = Mock()
        mock_connection.return_value.channel.return_value = mock_channel
        
        result = self.publisher._connect()
        
        self.assertTrue(result)
        mock_connection.assert_called_once()

    @patch('pika.BlockingConnection')
    def test_event_publishing(self, mock_connection):
        """Test publishing events to RabbitMQ."""
        mock_channel = Mock()
        mock_connection.return_value.channel.return_value = mock_channel
        
        event_data = {
            'event_type': 'notification.sent',
            'user_id': 'user123',
            'template_id': 1,
            'timestamp': time.time()
        }
        
        result = self.publisher.publish_event('notification.sent', event_data)
        
        self.assertTrue(result)
        mock_channel.basic_publish.assert_called_once()

    @patch('pika.BlockingConnection')
    def test_event_consumption(self, mock_connection):
        """Test consuming events from RabbitMQ."""
        mock_channel = Mock()
        mock_connection.return_value.channel.return_value = mock_channel
        
        # Mock message
        mock_method = Mock()
        mock_properties = Mock()
        mock_body = b'{"event_type": "notification.sent", "user_id": "user123"}'
        
        # Set up callback
        callback_called = threading.Event()
        
        def test_callback(ch, method, properties, body):
            callback_called.set()
        
        self.consumer.subscribe_to_events('notification.sent', test_callback)
        
        # Simulate message processing
        self.consumer._process_message(mock_channel, mock_method, mock_properties, mock_body)
        
        # Verify callback was triggered
        self.assertTrue(callback_called.wait(timeout=1))

    @patch('pika.BlockingConnection')
    def test_connection_failure_handling(self, mock_connection):
        """Test handling of connection failures."""
        mock_connection.side_effect = Exception("Connection failed")
        
        result = self.publisher._connect()
        
        self.assertFalse(result)

    @patch('pika.BlockingConnection')
    def test_message_serialization(self, mock_connection):
        """Test message serialization for complex data."""
        mock_channel = Mock()
        mock_connection.return_value.channel.return_value = mock_channel
        
        complex_data = {
            'nested': {
                'data': [1, 2, 3],
                'timestamp': time.time()
            },
            'unicode': 'héllo wörld',
            'none_value': None
        }
        
        result = self.publisher.publish_event('test.event', complex_data)
        
        self.assertTrue(result)
        # Verify serialization worked
        mock_channel.basic_publish.assert_called_once()


class CircuitBreakerIntegrationTest(TestCase):
    """Test circuit breaker pattern integration."""

    def setUp(self):
        """Set up circuit breaker."""
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            timeout=1,  # Short timeout for testing
            expected_exception=Exception
        )

    def test_circuit_breaker_with_external_service(self):
        """Test circuit breaker protecting external service calls."""
        call_count = 0
        
        @self.circuit_breaker
        def external_service_call():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception("Service unavailable")
            return "success"
        
        # First 3 calls should fail and open circuit
        for _ in range(3):
            try:
                external_service_call()
            except Exception:
                pass
        
        self.assertEqual(self.circuit_breaker.state, "open")
        
        # Next call should be blocked by circuit breaker
        with self.assertRaises(Exception):
            external_service_call()
        
        # Call count should still be 3 (no additional calls made)
        self.assertEqual(call_count, 3)

    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        failure_count = 0
        
        @self.circuit_breaker
        def recovering_service():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:
                raise Exception("Service failing")
            return "recovered"
        
        # Open the circuit
        for _ in range(3):
            try:
                recovering_service()
            except Exception:
                pass
        
        self.assertEqual(self.circuit_breaker.state, "open")
        
        # Wait for timeout
        time.sleep(1.1)
        
        # Next call should succeed and close circuit
        result = recovering_service()
        self.assertEqual(result, "recovered")
        self.assertEqual(self.circuit_breaker.state, "closed")

    def test_circuit_breaker_with_email_adapter(self):
        """Test circuit breaker protecting email adapter."""
        email_adapter = EmailAdapter()
        
        # Apply circuit breaker to send method
        original_send = email_adapter.send
        protected_send = self.circuit_breaker(original_send)
        
        notification_data = {
            'recipient': 'test@example.com',
            'subject': 'Test',
            'content': 'Test content'
        }
        
        # Mock email sending to fail
        with patch('adapters.email_adapter.send_mail') as mock_send:
            mock_send.side_effect = Exception("SMTP Error")
            
            # Trigger circuit breaker
            for _ in range(3):
                try:
                    protected_send(notification_data)
                except Exception:
                    pass
            
            self.assertEqual(self.circuit_breaker.state, "open")


class RetryPatternIntegrationTest(TestCase):
    """Test retry pattern integration."""

    def test_retry_with_exponential_backoff(self):
        """Test retry pattern with exponential backoff."""
        attempt_times = []
        
        @retry(max_attempts=3, delay=0.1, backoff_factor=2)
        def unreliable_service():
            attempt_times.append(time.time())
            if len(attempt_times) < 3:
                raise Exception("Service temporarily unavailable")
            return "success"
        
        start_time = time.time()
        result = unreliable_service()
        total_time = time.time() - start_time
        
        self.assertEqual(result, "success")
        self.assertEqual(len(attempt_times), 3)
        
        # Verify exponential backoff timing
        self.assertGreater(total_time, 0.1 + 0.2)  # First delay + second delay

    def test_retry_with_sms_adapter(self):
        """Test retry pattern with SMS adapter."""
        sms_adapter = SMSAdapter()
        
        # Apply retry decorator
        @retry(max_attempts=3, delay=0.1)
        def send_with_retry(notification_data):
            return sms_adapter.send(notification_data)
        
        notification_data = {
            'recipient': '+1234567890',
            'content': 'Test SMS'
        }
        
        with patch.object(sms_adapter, '_send_via_provider') as mock_send:
            # First two calls fail, third succeeds
            mock_send.side_effect = [
                Exception("Network error"),
                Exception("Timeout"),
                {'status': 'sent', 'message_id': 'sms123'}
            ]
            
            result = send_with_retry(notification_data)
            
            self.assertTrue(result)
            self.assertEqual(mock_send.call_count, 3)

    def test_retry_exhaustion(self):
        """Test retry pattern when all attempts are exhausted."""
        attempt_count = 0
        
        @retry(max_attempts=3, delay=0.1)
        def persistent_failure():
            nonlocal attempt_count
            attempt_count += 1
            raise Exception(f"Failure {attempt_count}")
        
        with self.assertRaises(Exception) as context:
            persistent_failure()
        
        self.assertEqual(attempt_count, 3)
        self.assertIn("Failure 3", str(context.exception))


class EmailServiceIntegrationTest(TestCase):
    """Test email service integration."""

    def setUp(self):
        """Set up email adapter."""
        self.email_adapter = EmailAdapter()

    @patch('django.core.mail.send_mail')
    def test_email_sending_success(self, mock_send_mail):
        """Test successful email sending."""
        mock_send_mail.return_value = True
        
        notification_data = {
            'recipient': 'test@example.com',
            'subject': 'Test Email',
            'content': 'This is a test email',
            'template_id': 1
        }
        
        result = self.email_adapter.send(notification_data)
        
        self.assertTrue(result)
        mock_send_mail.assert_called_once_with(
            subject='Test Email',
            message='This is a test email',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['test@example.com'],
            fail_silently=False
        )

    @patch('django.core.mail.send_mail')
    def test_email_sending_failure(self, mock_send_mail):
        """Test email sending failure handling."""
        mock_send_mail.side_effect = Exception("SMTP connection failed")
        
        notification_data = {
            'recipient': 'test@example.com',
            'subject': 'Test Email',
            'content': 'This is a test email'
        }
        
        result = self.email_adapter.send(notification_data)
        
        self.assertFalse(result)

    def test_email_validation(self):
        """Test email address validation."""
        valid_emails = [
            'test@example.com',
            'user.name@domain.co.uk',
            'user+tag@example.org'
        ]
        
        invalid_emails = [
            'invalid-email',
            '@example.com',
            'user@',
            'user..double.dot@example.com'
        ]
        
        for email in valid_emails:
            self.assertTrue(self.email_adapter._validate_recipient(email))
        
        for email in invalid_emails:
            self.assertFalse(self.email_adapter._validate_recipient(email))


class PushNotificationIntegrationTest(TestCase):
    """Test push notification service integration."""

    def setUp(self):
        """Set up push adapter."""
        self.push_adapter = PushAdapter()

    @patch('adapters.push_adapter.PushAdapter._send_via_fcm')
    def test_push_notification_success(self, mock_fcm):
        """Test successful push notification sending."""
        mock_fcm.return_value = {
            'success': True,
            'message_id': 'msg_123',
            'canonical_id': None
        }
        
        notification_data = {
            'recipient': 'device_token_123',
            'title': 'Test Notification',
            'content': 'This is a test push notification',
            'data': {'action': 'view_profile'}
        }
        
        result = self.push_adapter.send(notification_data)
        
        self.assertTrue(result)
        mock_fcm.assert_called_once()

    @patch('adapters.push_adapter.PushAdapter._send_via_fcm')
    def test_push_notification_failure(self, mock_fcm):
        """Test push notification failure handling."""
        mock_fcm.side_effect = Exception("FCM service unavailable")
        
        notification_data = {
            'recipient': 'device_token_123',
            'title': 'Test Notification',
            'content': 'This is a test push notification'
        }
        
        result = self.push_adapter.send(notification_data)
        
        self.assertFalse(result)

    def test_push_payload_formatting(self):
        """Test push notification payload formatting."""
        notification_data = {
            'recipient': 'device_token_123',
            'title': 'Test Title',
            'content': 'Test content',
            'data': {'key': 'value'}
        }
        
        payload = self.push_adapter._format_payload(notification_data)
        
        self.assertIn('notification', payload)
        self.assertIn('data', payload)
        self.assertEqual(payload['notification']['title'], 'Test Title')
        self.assertEqual(payload['notification']['body'], 'Test content')
        self.assertEqual(payload['data']['key'], 'value')


class RedisIntegrationTest(TestCase):
    """Test Redis integration for caching and sessions."""

    @patch('redis.Redis')
    def test_redis_connection(self, mock_redis):
        """Test Redis connection."""
        mock_redis_instance = Mock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.ping.return_value = True
        
        # Test connection
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        result = r.ping()
        
        self.assertTrue(result)

    @patch('django.core.cache.cache')
    def test_notification_caching(self, mock_cache):
        """Test notification template caching."""
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        
        # Simulate caching a template
        template_data = {
            'id': 1,
            'name': 'Cached Template',
            'content': 'Cached content'
        }
        
        # Cache miss
        cached_template = mock_cache.get('template:1')
        self.assertIsNone(cached_template)
        
        # Cache set
        mock_cache.set('template:1', template_data, timeout=3600)
        mock_cache.set.assert_called_with('template:1', template_data, timeout=3600)


class DatabaseConnectionPoolTest(TransactionTestCase):
    """Test database connection pool under load."""

    def test_concurrent_database_access(self):
        """Test concurrent database operations."""
        from core.models import NotificationTemplate
        import threading
        
        results = []
        errors = []
        
        def create_template(index):
            try:
                template = NotificationTemplate.objects.create(
                    name=f'Concurrent Template {index}',
                    template_type='email',
                    content=f'Content {index}'
                )
                results.append(template.id)
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_template, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        self.assertEqual(len(results), 10)
        self.assertEqual(len(errors), 0)

    def test_connection_pool_exhaustion(self):
        """Test behavior when connection pool is exhausted."""
        # This test would require configuring a very small connection pool
        # and creating enough concurrent connections to exhaust it
        pass  # Implementation depends on specific database configuration


class HealthCheckIntegrationTest(TestCase):
    """Test health check integration with external services."""

    @patch('pika.BlockingConnection')
    @patch('django.db.connection')
    @patch('redis.Redis')
    def test_comprehensive_health_check(self, mock_redis, mock_db, mock_rabbitmq):
        """Test comprehensive health check of all services."""
        # Mock successful connections
        mock_db.ensure_connection.return_value = None
        mock_rabbitmq.return_value.is_open = True
        mock_redis.return_value.ping.return_value = True
        
        from health_check.views import HealthViewSet
        
        health_view = HealthViewSet()
        
        # Test database health
        db_health = health_view._check_database()
        self.assertEqual(db_health['status'], 'healthy')
        
        # Test message broker health
        broker_health = health_view._check_message_broker()
        self.assertEqual(broker_health['status'], 'healthy')
        
        # Test cache health
        cache_health = health_view._check_cache()
        self.assertEqual(cache_health['status'], 'healthy')

    @patch('pika.BlockingConnection')
    def test_health_check_service_failure(self, mock_rabbitmq):
        """Test health check when services are failing."""
        mock_rabbitmq.side_effect = Exception("RabbitMQ unavailable")
        
        from health_check.views import HealthViewSet
        
        health_view = HealthViewSet()
        broker_health = health_view._check_message_broker()
        
        self.assertEqual(broker_health['status'], 'unhealthy')
        self.assertIn('error', broker_health)