"""
Unit tests for adapters.
"""
from unittest.mock import Mock, patch
from django.test import TestCase

from adapters.email_adapter import EmailAdapter
from adapters.sms_adapter import SMSAdapter
from adapters.push_adapter import PushAdapter
from adapters.circuit_breaker import CircuitBreaker
from adapters.retry_decorator import retry


class EmailAdapterTest(TestCase):
    """Test cases for EmailAdapter."""

    def setUp(self):
        """Set up test data."""
        self.adapter = EmailAdapter()
        self.notification_data = {
            'recipient': 'test@example.com',
            'subject': 'Test Subject',
            'content': 'Test content',
            'template_id': 1
        }

    @patch('adapters.email_adapter.send_mail')
    def test_send_email_success(self, mock_send_mail):
        """Test successful email sending."""
        mock_send_mail.return_value = True
        
        result = self.adapter.send(self.notification_data)
        
        self.assertTrue(result)
        mock_send_mail.assert_called_once()

    @patch('adapters.email_adapter.send_mail')
    def test_send_email_failure(self, mock_send_mail):
        """Test email sending failure."""
        mock_send_mail.side_effect = Exception("SMTP Error")
        
        result = self.adapter.send(self.notification_data)
        
        self.assertFalse(result)

    def test_validate_recipient_email(self):
        """Test email recipient validation."""
        # Valid email
        valid_data = self.notification_data.copy()
        self.assertTrue(self.adapter._validate_recipient(valid_data['recipient']))
        
        # Invalid email
        invalid_data = self.notification_data.copy()
        invalid_data['recipient'] = 'invalid-email'
        self.assertFalse(self.adapter._validate_recipient(invalid_data['recipient']))

    @patch('adapters.email_adapter.EmailAdapter._log_delivery')
    def test_delivery_logging(self, mock_log):
        """Test delivery attempt logging."""
        with patch('adapters.email_adapter.send_mail') as mock_send:
            mock_send.return_value = True
            
            self.adapter.send(self.notification_data)
            
            mock_log.assert_called_once()


class SMSAdapterTest(TestCase):
    """Test cases for SMSAdapter."""

    def setUp(self):
        """Set up test data."""
        self.adapter = SMSAdapter()
        self.notification_data = {
            'recipient': '+1234567890',
            'content': 'Test SMS content',
            'template_id': 1
        }

    @patch('adapters.sms_adapter.SMSAdapter._send_via_provider')
    def test_send_sms_success(self, mock_send):
        """Test successful SMS sending."""
        mock_send.return_value = {'status': 'sent', 'message_id': 'sms123'}
        
        result = self.adapter.send(self.notification_data)
        
        self.assertTrue(result)

    @patch('adapters.sms_adapter.SMSAdapter._send_via_provider')
    def test_send_sms_failure(self, mock_send):
        """Test SMS sending failure."""
        mock_send.side_effect = Exception("Provider Error")
        
        result = self.adapter.send(self.notification_data)
        
        self.assertFalse(result)

    def test_validate_phone_number(self):
        """Test phone number validation."""
        # Valid phone numbers
        valid_numbers = ['+1234567890', '+44123456789', '+81123456789']
        for number in valid_numbers:
            self.assertTrue(self.adapter._validate_recipient(number))
        
        # Invalid phone numbers
        invalid_numbers = ['123', 'invalid', '+123', '123456789012345']
        for number in invalid_numbers:
            self.assertFalse(self.adapter._validate_recipient(number))

    def test_format_message_content(self):
        """Test SMS message content formatting."""
        long_content = "This is a very long SMS message that exceeds the typical SMS length limit of 160 characters. It should be truncated or handled appropriately by the adapter."
        
        formatted = self.adapter._format_content(long_content)
        
        # Assuming SMS adapter truncates to 160 characters
        self.assertLessEqual(len(formatted), 160)


class PushAdapterTest(TestCase):
    """Test cases for PushAdapter."""

    def setUp(self):
        """Set up test data."""
        self.adapter = PushAdapter()
        self.notification_data = {
            'recipient': 'device_token_123',
            'title': 'Test Push',
            'content': 'Test push notification content',
            'template_id': 1
        }

    @patch('adapters.push_adapter.PushAdapter._send_via_fcm')
    def test_send_push_success(self, mock_send):
        """Test successful push notification sending."""
        mock_send.return_value = {'success': True, 'message_id': 'push123'}
        
        result = self.adapter.send(self.notification_data)
        
        self.assertTrue(result)

    @patch('adapters.push_adapter.PushAdapter._send_via_fcm')
    def test_send_push_failure(self, mock_send):
        """Test push notification sending failure."""
        mock_send.side_effect = Exception("FCM Error")
        
        result = self.adapter.send(self.notification_data)
        
        self.assertFalse(result)

    def test_validate_device_token(self):
        """Test device token validation."""
        # Valid token (simplified)
        valid_token = 'valid_device_token_123'
        self.assertTrue(self.adapter._validate_recipient(valid_token))
        
        # Invalid token
        invalid_token = ''
        self.assertFalse(self.adapter._validate_recipient(invalid_token))

    def test_format_push_payload(self):
        """Test push notification payload formatting."""
        payload = self.adapter._format_payload(self.notification_data)
        
        self.assertIn('title', payload)
        self.assertIn('body', payload)
        self.assertIn('data', payload)


class CircuitBreakerTest(TestCase):
    """Test cases for CircuitBreaker."""

    def setUp(self):
        """Set up test data."""
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            timeout=60,
            expected_exception=Exception
        )

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        @self.circuit_breaker
        def successful_function():
            return "success"
        
        result = successful_function()
        self.assertEqual(result, "success")
        self.assertEqual(self.circuit_breaker.state, "closed")

    def test_circuit_breaker_open_state(self):
        """Test circuit breaker opens after failures."""
        @self.circuit_breaker
        def failing_function():
            raise Exception("Test failure")
        
        # Trigger failures to open circuit
        for _ in range(3):
            try:
                failing_function()
            except Exception:
                pass
        
        self.assertEqual(self.circuit_breaker.state, "open")
        
        # Next call should raise CircuitBreakerOpen exception
        with self.assertRaises(Exception):
            failing_function()

    def test_circuit_breaker_half_open_state(self):
        """Test circuit breaker half-open state."""
        # Mock time to control timeout
        with patch('time.time') as mock_time:
            # Set initial time
            mock_time.return_value = 0
            
            @self.circuit_breaker
            def failing_function():
                raise Exception("Test failure")
            
            # Open the circuit
            for _ in range(3):
                try:
                    failing_function()
                except Exception:
                    pass
            
            # Advance time beyond timeout
            mock_time.return_value = 70
            
            # Circuit should be half-open now
            try:
                failing_function()
            except Exception:
                pass
            
            self.assertEqual(self.circuit_breaker.state, "half-open")

    def test_circuit_breaker_reset(self):
        """Test circuit breaker reset functionality."""
        @self.circuit_breaker
        def function_that_recovers():
            if self.circuit_breaker.failure_count < 3:
                raise Exception("Still failing")
            return "success"
        
        # Open the circuit
        for _ in range(3):
            try:
                function_that_recovers()
            except Exception:
                pass
        
        self.assertEqual(self.circuit_breaker.state, "open")
        
        # Reset the circuit breaker
        self.circuit_breaker.reset()
        
        self.assertEqual(self.circuit_breaker.state, "closed")
        self.assertEqual(self.circuit_breaker.failure_count, 0)


class RetryDecoratorTest(TestCase):
    """Test cases for retry decorator."""

    def test_retry_success_first_attempt(self):
        """Test retry decorator with successful first attempt."""
        call_count = 0
        
        @retry(max_attempts=3, delay=0.1)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_function()
        
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 1)

    def test_retry_success_after_failures(self):
        """Test retry decorator with success after failures."""
        call_count = 0
        
        @retry(max_attempts=3, delay=0.1)
        def function_that_recovers():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = function_that_recovers()
        
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)

    def test_retry_max_attempts_exceeded(self):
        """Test retry decorator when max attempts exceeded."""
        call_count = 0
        
        @retry(max_attempts=3, delay=0.1)
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise Exception("Persistent failure")
        
        with self.assertRaises(Exception):
            always_failing_function()
        
        self.assertEqual(call_count, 3)

    def test_retry_exponential_backoff(self):
        """Test retry decorator with exponential backoff."""
        call_times = []
        
        @retry(max_attempts=3, delay=0.1, backoff_factor=2)
        def function_with_timing():
            import time
            call_times.append(time.time())
            raise Exception("Test failure")
        
        with self.assertRaises(Exception):
            function_with_timing()
        
        # Should have 3 attempts with increasing delays
        self.assertEqual(len(call_times), 3)

    def test_retry_specific_exceptions(self):
        """Test retry decorator with specific exception types."""
        call_count = 0
        
        @retry(max_attempts=3, delay=0.1, exceptions=(ValueError,))
        def function_with_specific_exception():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Retryable error")
            elif call_count == 2:
                raise RuntimeError("Non-retryable error")
            return "success"
        
        with self.assertRaises(RuntimeError):
            function_with_specific_exception()
        
        # Should only retry once (ValueError), then fail on RuntimeError
        self.assertEqual(call_count, 2)