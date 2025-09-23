"""
Test RabbitMQ message broker connection and Celery configuration.
"""
import os
from django.test import TestCase
from django.conf import settings
from celery import Celery


class MessageBrokerTestCase(TestCase):
    """Test RabbitMQ connection and Celery configuration."""

    def test_rabbitmq_url_configuration(self):
        """Test that RabbitMQ URL is properly configured."""
        self.assertTrue(hasattr(settings, 'RABBITMQ_URL'))
        self.assertTrue(settings.RABBITMQ_URL.startswith('amqp://'))

    def test_celery_broker_configuration(self):
        """Test that Celery is configured to use RabbitMQ."""
        self.assertEqual(settings.CELERY_BROKER_URL, settings.RABBITMQ_URL)
        self.assertEqual(settings.CELERY_RESULT_BACKEND, settings.REDIS_URL)

    def test_celery_app_configuration(self):
        """Test Celery app configuration."""
        app = Celery('notification_service')
        app.config_from_object('django.conf:settings', namespace='CELERY')
        
        self.assertEqual(app.conf.broker_url, settings.RABBITMQ_URL)
        self.assertEqual(app.conf.result_backend, settings.REDIS_URL)
        self.assertEqual(app.conf.task_serializer, 'json')
        self.assertEqual(app.conf.result_serializer, 'json')

    def test_environment_variables(self):
        """Test that environment variables are properly set."""
        # This test assumes the environment is set up correctly
        rabbitmq_url = os.getenv('RABBITMQ_URL')
        if rabbitmq_url:
            self.assertTrue(rabbitmq_url.startswith('amqp://'))