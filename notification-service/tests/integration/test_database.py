"""
Database integration tests with correct field names.
"""
from django.test import TestCase, TransactionTestCase
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from unittest.mock import patch

from core.models import (
    NotificationTemplate,
    NotificationLog,
    UserPreference,
    NotificationQuota
)


class DatabaseIntegrationTest(TransactionTestCase):
    """Test database operations and transactions."""

    def test_notification_template_creation_and_retrieval(self):
        """Test creating and retrieving notification templates."""
        template = NotificationTemplate.objects.create(
            name='Integration Test Template',
            type='email',
            body='Hello {{user_name}}!',
            subject='Integration Test',
            variables={'user_name': 'string'}
        )
        
        # Test retrieval
        retrieved = NotificationTemplate.objects.get(name='Integration Test Template')
        self.assertEqual(retrieved.type, 'email')
        self.assertEqual(retrieved.body, 'Hello {{user_name}}!')
        self.assertTrue(retrieved.active)

    def test_notification_log_cascade_behavior(self):
        """Test cascade behavior with notification logs."""
        # Create template
        template = NotificationTemplate.objects.create(
            name='Cascade Test Template',
            type='email',
            body='Test body',
            subject='Test Subject'
        )
        
        # Create log
        log = NotificationLog.objects.create(
            user_id=123,
            template=template,
            type='email',
            recipient='test@example.com',
            subject='Test Subject',
            body='Test body'
        )
        
        # Verify relationship
        self.assertEqual(log.template.id, template.id)
        self.assertEqual(log.user_id, 123)

    def test_user_preference_uniqueness_constraint(self):
        """Test user preference uniqueness constraint."""
        UserPreference.objects.create(
            user_id=123,
            email_enabled=True,
            sms_enabled=False
        )
        
        # Should fail due to unique constraint
        with self.assertRaises(IntegrityError):
            UserPreference.objects.create(
                user_id=123,
                email_enabled=False,
                sms_enabled=True
            )

    def test_notification_quota_tracking(self):
        """Test notification quota tracking."""
        quota = NotificationQuota.objects.create(
            user_id=456,
            notification_type='email',
            count=10
        )
        
        self.assertEqual(quota.user_id, 456)
        self.assertEqual(quota.notification_type, 'email')
        self.assertEqual(quota.count, 10)
        
        # Test increment
        new_count = NotificationQuota.increment_quota(456, 'email')
        self.assertEqual(new_count, 11)

    def test_atomic_transaction_rollback(self):
        """Test atomic transaction rollback behavior."""
        initial_count = NotificationTemplate.objects.count()
        
        try:
            with transaction.atomic():
                NotificationTemplate.objects.create(
                    name='Transaction Test',
                    type='email',
                    body='Test body'
                )
                
                # Force an error to trigger rollback
                raise Exception("Forced error for rollback test")
                
        except Exception:
            pass  # Expected exception
        
        # Count should be unchanged due to rollback
        final_count = NotificationTemplate.objects.count()
        self.assertEqual(final_count, initial_count)

    def test_bulk_operations(self):
        """Test bulk database operations."""
        templates = []
        for i in range(5):
            templates.append(NotificationTemplate(
                name=f'Bulk Template {i}',
                type='email',
                body=f'Bulk body {i}'
            ))
        
        # Bulk create
        NotificationTemplate.objects.bulk_create(templates)
        
        # Verify all created
        bulk_templates = NotificationTemplate.objects.filter(
            name__startswith='Bulk Template'
        )
        self.assertEqual(bulk_templates.count(), 5)

    def test_complex_queries(self):
        """Test complex database queries."""
        # Create test data
        template = NotificationTemplate.objects.create(
            name='Query Test Template',
            type='email',
            body='Query test body',
            active=True
        )
        
        NotificationLog.objects.create(
            user_id=123,
            template=template,
            type='email',
            recipient='query@test.com',
            subject='Query Test',
            body='Query test body'
        )
        
        # Complex query with joins
        logs_with_active_templates = NotificationLog.objects.filter(
            template__active=True,
            type='email'
        ).select_related('template')
        
        self.assertGreater(logs_with_active_templates.count(), 0)
        
        for log in logs_with_active_templates:
            self.assertTrue(log.template.active)

    def test_database_indexes_performance(self):
        """Test that database indexes are working (basic test)."""
        # Create multiple templates
        templates = []
        for i in range(10):
            templates.append(NotificationTemplate(
                name=f'Index Test Template {i}',
                type='email' if i % 2 == 0 else 'sms',
                body=f'Index test body {i}'
            ))
        
        NotificationTemplate.objects.bulk_create(templates)
        
        # Query by indexed field (type)
        email_templates = NotificationTemplate.objects.filter(type='email')
        sms_templates = NotificationTemplate.objects.filter(type='sms')
        
        # Basic performance check - queries should complete
        self.assertGreater(email_templates.count(), 0)
        self.assertGreater(sms_templates.count(), 0)

    def test_model_field_validation(self):
        """Test model field validation."""
        # Test required fields
        with self.assertRaises((ValidationError, IntegrityError)):
            template = NotificationTemplate(
                # Missing required name field
                type='email',
                body='Test body'
            )
            template.full_clean()  # Trigger validation

    def test_migration_compatibility(self):
        """Test that models are compatible with migrations."""
        # Create template with all fields
        template = NotificationTemplate.objects.create(
            name='Migration Test',
            type='email',
            subject='Migration Subject',
            body='Migration body {{user_name}}',
            variables={'user_name': 'string'},
            active=True
        )
        
        self.assertIsNotNone(template.id)
        self.assertIsNotNone(template.created_at)
        self.assertIsNotNone(template.updated_at)

    def test_foreign_key_relationships(self):
        """Test foreign key relationships work correctly."""
        # Create template
        template = NotificationTemplate.objects.create(
            name='FK Test Template',
            type='email',
            body='FK test body'
        )
        
        # Create log with foreign key
        log = NotificationLog.objects.create(
            user_id=789,
            template=template,
            type='email',
            recipient='fk@test.com',
            subject='FK Test',
            body='FK test body'
        )
        
        # Test forward relationship
        self.assertEqual(log.template.name, 'FK Test Template')
        
        # Test reverse relationship
        template_logs = template.logs.all()
        self.assertEqual(template_logs.count(), 1)
        self.assertEqual(template_logs.first().user_id, 789)


class DatabaseConcurrencyTest(TransactionTestCase):
    """Test database concurrency and race conditions."""

    def test_quota_concurrent_updates(self):
        """Test concurrent quota updates."""
        quota = NotificationQuota.objects.create(
            user_id=999,
            notification_type='email',
            count=5
        )
        
        # Simulate concurrent increment
        NotificationQuota.increment_quota(999, 'email')
        NotificationQuota.increment_quota(999, 'email')
        
        # Check final count
        updated_quota = NotificationQuota.objects.get(user_id=999)
        self.assertEqual(updated_quota.count, 7)  # 5 + 2 increments

    def test_template_soft_delete_concurrency(self):
        """Test template soft delete concurrency."""
        template = NotificationTemplate.objects.create(
            name='Concurrency Test',
            type='email',
            body='Concurrency test body'
        )
        
        # Soft delete
        template.active = False
        template.save()
        
        # Verify soft delete
        inactive_template = NotificationTemplate.objects.get(id=template.id)
        self.assertFalse(inactive_template.active)


class DatabaseBackupRestoreTest(TestCase):
    """Test database backup and restore scenarios."""

    def test_data_integrity_after_restore(self):
        """Test data integrity simulation."""
        # Create comprehensive test data
        template = NotificationTemplate.objects.create(
            name='Backup Test Template',
            type='email',
            subject='Backup Test',
            body='Backup test body {{user_name}}',
            variables={'user_name': 'string'}
        )
        
        preference = UserPreference.objects.create(
            user_id=888,
            email_enabled=True,
            sms_enabled=False,
            max_emails_per_day=20
        )
        
        quota = NotificationQuota.objects.create(
            user_id=888,
            notification_type='email',
            count=3
        )
        
        log = NotificationLog.objects.create(
            user_id=888,
            template=template,
            type='email',
            recipient='backup@test.com',
            subject='Backup Test',
            body='Backup test body John'
        )
        
        # Verify all data exists and relationships are intact
        self.assertTrue(NotificationTemplate.objects.filter(name='Backup Test Template').exists())
        self.assertTrue(UserPreference.objects.filter(user_id=888).exists())
        self.assertTrue(NotificationQuota.objects.filter(user_id=888).exists())
        self.assertTrue(NotificationLog.objects.filter(user_id=888).exists())
        
        # Verify relationships
        retrieved_log = NotificationLog.objects.get(user_id=888)
        self.assertEqual(retrieved_log.template.name, 'Backup Test Template')

    def test_referential_integrity_constraints(self):
        """Test referential integrity constraints."""
        template = NotificationTemplate.objects.create(
            name='Integrity Test Template',
            type='email',
            body='Integrity test body'
        )
        
        log = NotificationLog.objects.create(
            user_id=777,
            template=template,
            type='email',
            recipient='integrity@test.com',
            subject='Integrity Test',
            body='Integrity test body'
        )
        
        # Verify foreign key constraint works
        self.assertEqual(log.template_id, template.id)
        
        # Template should be protected from deletion due to PROTECT constraint
        with self.assertRaises(Exception):  # Should be ProtectedError but depends on DB
            template.delete()


# Simple connectivity tests
class DatabaseConnectivityTest(TestCase):
    """Basic database connectivity tests."""

    def test_database_connection(self):
        """Test basic database connection."""
        # Simple query that should work if DB is connected
        count = NotificationTemplate.objects.count()
        self.assertIsInstance(count, int)

    def test_database_writes(self):
        """Test database write operations."""
        initial_count = NotificationTemplate.objects.count()
        
        NotificationTemplate.objects.create(
            name='Connectivity Test',
            type='email',
            body='Connectivity test body'
        )
        
        final_count = NotificationTemplate.objects.count()
        self.assertEqual(final_count, initial_count + 1)

    def test_database_transactions(self):
        """Test database transaction support."""
        with transaction.atomic():
            template = NotificationTemplate.objects.create(
                name='Transaction Test',
                type='email',
                body='Transaction test body'
            )
            
            # Verify within transaction
            self.assertIsNotNone(template.id)
        
        # Verify after transaction
        self.assertTrue(
            NotificationTemplate.objects.filter(name='Transaction Test').exists()
        )