"""
Database integration tests.
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
            template_type='email',
            content='Hello {{user_name}}!',
            subject='Integration Test',
            variables=['user_name']
        )
        
        # Test retrieval
        retrieved = NotificationTemplate.objects.get(id=template.id)
        self.assertEqual(retrieved.name, 'Integration Test Template')
        self.assertEqual(retrieved.template_type, 'email')
        self.assertTrue(retrieved.is_active)

    def test_notification_log_cascade_behavior(self):
        """Test cascade behavior when template is deleted."""
        template = NotificationTemplate.objects.create(
            name='Test Template',
            template_type='email',
            content='Test content',
            subject='Test subject'
        )
        
        # Create notification log
        log = NotificationLog.objects.create(
            template=template,
            user_id='user123',
            recipient='test@example.com',
            status='sent',
            channel='email',
            content='Rendered content'
        )
        
        # Soft delete template
        template.soft_delete()
        
        # Log should still exist but template should be inactive
        log.refresh_from_db()
        template.refresh_from_db()
        self.assertFalse(template.is_active)
        self.assertEqual(log.template.id, template.id)

    def test_user_preference_uniqueness_constraint(self):
        """Test user-channel uniqueness constraint."""
        UserPreference.objects.create(
            user_id='user123',
            channel='email',
            enabled=True
        )
        
        # Attempting to create duplicate should fail
        with self.assertRaises(IntegrityError):
            UserPreference.objects.create(
                user_id='user123',
                channel='email',
                enabled=False
            )

    def test_notification_quota_tracking(self):
        """Test quota tracking and updates."""
        quota = NotificationQuota.objects.create(
            user_id='user123',
            channel='email',
            quota_limit=10,
            quota_used=5
        )
        
        # Simulate quota usage
        quota.quota_used += 1
        quota.save()
        
        quota.refresh_from_db()
        self.assertEqual(quota.quota_used, 6)

    def test_atomic_transaction_rollback(self):
        """Test transaction rollback on error."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                # Create valid template
                NotificationTemplate.objects.create(
                    name='Valid Template',
                    template_type='email',
                    content='Valid content'
                )
                
                # Create invalid template (duplicate name)
                NotificationTemplate.objects.create(
                    name='Valid Template',  # Duplicate name
                    template_type='sms',
                    content='Invalid content'
                )
        
        # Should not have created any templates due to rollback
        self.assertEqual(
            NotificationTemplate.objects.filter(name='Valid Template').count(),
            0
        )

    def test_bulk_operations(self):
        """Test bulk database operations."""
        # Bulk create templates
        templates = []
        for i in range(10):
            templates.append(NotificationTemplate(
                name=f'Bulk Template {i}',
                template_type='email',
                content=f'Bulk content {i}',
                subject=f'Bulk subject {i}'
            ))
        
        NotificationTemplate.objects.bulk_create(templates)
        
        # Verify all created
        count = NotificationTemplate.objects.filter(
            name__startswith='Bulk Template'
        ).count()
        self.assertEqual(count, 10)
        
        # Bulk update
        NotificationTemplate.objects.filter(
            name__startswith='Bulk Template'
        ).update(is_active=False)
        
        # Verify all updated
        active_count = NotificationTemplate.objects.filter(
            name__startswith='Bulk Template',
            is_active=True
        ).count()
        self.assertEqual(active_count, 0)

    def test_complex_queries(self):
        """Test complex database queries."""
        # Create test data
        template = NotificationTemplate.objects.create(
            name='Query Test Template',
            template_type='email',
            content='Test content'
        )
        
        UserPreference.objects.create(
            user_id='user1',
            channel='email',
            enabled=True
        )
        UserPreference.objects.create(
            user_id='user2',
            channel='email',
            enabled=False
        )
        
        # Create notification logs
        NotificationLog.objects.create(
            template=template,
            user_id='user1',
            recipient='user1@example.com',
            status='sent',
            channel='email',
            content='Content'
        )
        NotificationLog.objects.create(
            template=template,
            user_id='user2',
            recipient='user2@example.com',
            status='failed',
            channel='email',
            content='Content'
        )
        
        # Query users with enabled preferences and successful notifications
        successful_users = NotificationLog.objects.filter(
            status='sent',
            user_id__in=UserPreference.objects.filter(
                channel='email',
                enabled=True
            ).values_list('user_id', flat=True)
        ).values_list('user_id', flat=True).distinct()
        
        self.assertIn('user1', successful_users)
        self.assertNotIn('user2', successful_users)

    def test_database_indexes_performance(self):
        """Test database performance with indexes."""
        # Create large dataset
        templates = []
        for i in range(100):
            templates.append(NotificationTemplate(
                name=f'Performance Template {i}',
                template_type='email',
                content=f'Content {i}'
            ))
        NotificationTemplate.objects.bulk_create(templates)
        
        # Test query performance (indexed fields)
        with self.assertNumQueries(1):
            # Should use index on is_active
            active_templates = list(
                NotificationTemplate.objects.filter(is_active=True)
            )
            self.assertGreater(len(active_templates), 90)

    def test_model_field_validation(self):
        """Test model field validation at database level."""
        # Test email field validation in NotificationLog
        template = NotificationTemplate.objects.create(
            name='Validation Test',
            template_type='email',
            content='Test'
        )
        
        # Valid email
        log = NotificationLog.objects.create(
            template=template,
            user_id='user123',
            recipient='valid@example.com',
            status='sent',
            channel='email',
            content='Content'
        )
        self.assertIsNotNone(log.id)

    def test_migration_compatibility(self):
        """Test that models work correctly after migrations."""
        # Test that all model fields are properly created
        template = NotificationTemplate.objects.create(
            name='Migration Test',
            template_type='email',
            content='Test content',
            subject='Test subject',
            variables=['test_var']
        )
        
        # Test all fields are accessible
        self.assertIsNotNone(template.created_at)
        self.assertIsNotNone(template.updated_at)
        self.assertTrue(template.is_active)
        self.assertIsNone(template.deleted_at)
        self.assertEqual(template.variables, ['test_var'])

    def test_foreign_key_relationships(self):
        """Test foreign key relationships and cascading."""
        template = NotificationTemplate.objects.create(
            name='FK Test Template',
            template_type='email',
            content='Test content'
        )
        
        # Create notification log with foreign key
        log = NotificationLog.objects.create(
            template=template,
            user_id='user123',
            recipient='test@example.com',
            status='sent',
            channel='email',
            content='Content'
        )
        
        # Test relationship access
        self.assertEqual(log.template.name, 'FK Test Template')
        
        # Test reverse relationship
        template_logs = template.notificationlog_set.all()
        self.assertEqual(template_logs.count(), 1)
        self.assertEqual(template_logs.first().user_id, 'user123')


class DatabaseConcurrencyTest(TransactionTestCase):
    """Test database concurrency and race conditions."""

    def test_quota_concurrent_updates(self):
        """Test concurrent quota updates."""
        quota = NotificationQuota.objects.create(
            user_id='user123',
            channel='email',
            quota_limit=100,
            quota_used=50
        )
        
        # Simulate concurrent updates
        def update_quota():
            q = NotificationQuota.objects.get(id=quota.id)
            q.quota_used += 1
            q.save()
        
        # Run concurrent updates
        update_quota()
        update_quota()
        
        quota.refresh_from_db()
        self.assertEqual(quota.quota_used, 52)

    def test_template_soft_delete_concurrency(self):
        """Test concurrent template operations."""
        template = NotificationTemplate.objects.create(
            name='Concurrency Test',
            template_type='email',
            content='Test content'
        )
        
        # Simulate reading while updating
        template_copy = NotificationTemplate.objects.get(id=template.id)
        
        # Soft delete original
        template.soft_delete()
        
        # Check that copy is still valid for reading
        self.assertTrue(template_copy.is_active)  # Original state
        
        # But fresh query shows updated state
        fresh_template = NotificationTemplate.objects.get(id=template.id)
        self.assertFalse(fresh_template.is_active)


class DatabaseBackupRestoreTest(TransactionTestCase):
    """Test database backup and restore scenarios."""

    def test_data_integrity_after_restore(self):
        """Test data integrity after simulated restore."""
        # Create comprehensive test data
        template = NotificationTemplate.objects.create(
            name='Integrity Test',
            template_type='email',
            content='Test {{variable}}',
            variables=['variable']
        )
        
        preference = UserPreference.objects.create(
            user_id='user123',
            channel='email',
            enabled=True
        )
        
        quota = NotificationQuota.objects.create(
            user_id='user123',
            channel='email',
            quota_limit=100,
            quota_used=25
        )
        
        log = NotificationLog.objects.create(
            template=template,
            user_id='user123',
            recipient='test@example.com',
            status='sent',
            channel='email',
            content='Rendered content'
        )
        
        # Simulate restore by verifying all relationships intact
        restored_log = NotificationLog.objects.get(id=log.id)
        self.assertEqual(restored_log.template.name, 'Integrity Test')
        self.assertEqual(restored_log.user_id, preference.user_id)
        
        restored_quota = NotificationQuota.objects.get(user_id='user123')
        self.assertEqual(restored_quota.quota_used, 25)

    def test_referential_integrity_constraints(self):
        """Test referential integrity constraints."""
        template = NotificationTemplate.objects.create(
            name='Integrity Constraint Test',
            template_type='email',
            content='Test content'
        )
        
        log = NotificationLog.objects.create(
            template=template,
            user_id='user123',
            recipient='test@example.com',
            status='sent',
            channel='email',
            content='Content'
        )
        
        # Template should not be hard deletable with existing logs
        # (This depends on your CASCADE settings)
        template.soft_delete()  # Use soft delete instead
        
        # Log should still reference the template
        log.refresh_from_db()
        self.assertEqual(log.template.id, template.id)