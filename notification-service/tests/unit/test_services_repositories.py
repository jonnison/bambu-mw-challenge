"""
Services and Repositories Testing

Comprehensive testing for core business logic services and data repositories.
"""
import uuid
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User

from core.services import NotificationTemplateService, UserPreferenceService
from core.repositories import (
    DjangoNotificationTemplateRepository, 
    DjangoUserPreferenceRepository,
    DjangoNotificationLogRepository,
    DjangoNotificationQuotaRepository
)
from tests.fixtures.factories import (
    NotificationTemplateFactory,
    UserPreferenceFactory,
    NotificationLogFactory,
    NotificationQuotaFactory
)


class TemplateServiceValidationTest(TestCase):
    """Test template service validation and error handling"""
    
    def setUp(self):
        self.template_repo = DjangoNotificationTemplateRepository()
        self.service = NotificationTemplateService(self.template_repo)
    
    def test_create_template_duplicate_name(self):
        """Test creating template with duplicate name"""
        template_data = {
            'name': 'duplicate_test',
            'type': 'email',
            'body': 'Test body'
        }
        
        # Create first template
        self.service.create_template(template_data)
        
        # Try to create second with same name
        with self.assertRaises(ValueError) as cm:
            self.service.create_template(template_data)
        
        self.assertIn('already exists', str(cm.exception))
    
    def test_create_template_validation_errors(self):
        """Test template validation errors"""
        # Test invalid type
        with self.assertRaises(ValueError) as cm:
            self.service.create_template({
                'name': 'test',
                'type': 'invalid_type',
                'body': 'body'
            })
        self.assertIn('Invalid notification type', str(cm.exception))
        
        # Test short name
        with self.assertRaises(ValueError) as cm:
            self.service.create_template({
                'name': 'ab',  # Too short
                'type': 'email',
                'body': 'body'
            })
        self.assertIn('at least 3 characters', str(cm.exception))
        
        # Test missing required fields
        with self.assertRaises(ValueError) as cm:
            self.service.create_template({
                'name': 'test'
                # Missing body and type
            })
        self.assertIn('Missing required field', str(cm.exception))
    
    def test_update_nonexistent_template(self):
        """Test updating template that doesn't exist"""
        non_existent_id = uuid.uuid4()
        
        with self.assertRaises(ValueError) as cm:
            self.service.update_template(non_existent_id, {'body': 'new body'})
        
        self.assertIn('not found', str(cm.exception))
    
    def test_render_template_complex(self):
        """Test template rendering with various contexts"""
        template = NotificationTemplateFactory(
            subject='Hello {{name}}!',
            body='Welcome {{name}}, your order {{order_id}} is ready!'
        )
        
        context = {
            'name': 'John Doe',
            'order_id': '12345'
        }
        
        result = self.service.render_template(template, context)
        
        self.assertEqual(result['subject'], 'Hello John Doe!')
        self.assertIn('Welcome John Doe', result['body'])
        self.assertIn('order 12345', result['body'])


class UserPreferenceServiceExtendedTest(TestCase):
    """Test user preference service extended scenarios"""
    
    def setUp(self):
        self.preference_repo = DjangoUserPreferenceRepository()
        self.service = UserPreferenceService(self.preference_repo)
        self.user = User.objects.create_user(username='testuser', password='test123')
    
    def test_validation_comprehensive(self):
        """Test all preference validation scenarios"""
        user_id = self.user.id
        
        # Test boolean field validation
        invalid_boolean_prefs = [
            {'email_enabled': 'yes'},
            {'sms_enabled': 1},
            {'push_enabled': 'true'},
        ]
        
        for pref in invalid_boolean_prefs:
            with self.assertRaises(ValueError) as cm:
                self.service.update_user_preferences(user_id, pref)
            self.assertIn('must be a boolean', str(cm.exception))
        
        # Test numeric field validation
        invalid_numeric_prefs = [
            {'max_emails_per_day': 'many'},
            {'max_sms_per_day': -5},
            {'max_emails_per_day': 1.5},
        ]
        
        for pref in invalid_numeric_prefs:
            with self.assertRaises(ValueError) as cm:
                self.service.update_user_preferences(user_id, pref)
            self.assertIn('non-negative integer', str(cm.exception))
    
    def test_get_multiple_user_preferences(self):
        """Test getting preferences for multiple users"""
        # Create some users with preferences
        user1 = User.objects.create_user(username='user1', password='test')
        user2 = User.objects.create_user(username='user2', password='test')
        user3 = User.objects.create_user(username='user3', password='test')  # No preferences
        
        UserPreferenceFactory(user_id=user1.id, email_enabled=True)
        UserPreferenceFactory(user_id=user2.id, sms_enabled=True)
        
        user_ids = [user1.id, user2.id, user3.id]
        preferences = self.service.get_multiple_user_preferences(user_ids)
        
        # Should return preferences for users 1 and 2, but not 3
        self.assertEqual(len(preferences), 2)
        returned_user_ids = [p.user_id for p in preferences]
        self.assertIn(user1.id, returned_user_ids)
        self.assertIn(user2.id, returned_user_ids)
        self.assertNotIn(user3.id, returned_user_ids)


class RepositoryOperationsTest(TestCase):
    """Test various repository CRUD operations"""
    
    def test_user_preference_repository_operations(self):
        """Test user preference repository operations"""
        repo = DjangoUserPreferenceRepository()
        user = User.objects.create_user(username='repouser', password='test123')
        
        # Test get non-existent
        preferences = repo.get_by_user_id(user.id)
        self.assertIsNone(preferences)
        
        # Test create
        pref_data = {
            'email_enabled': True,
            'sms_enabled': False,
            'max_emails_per_day': 30
        }
        
        created = repo.create_or_update(user.id, pref_data)
        self.assertIsNotNone(created)
        self.assertTrue(created.email_enabled)
        self.assertFalse(created.sms_enabled)
        self.assertEqual(created.max_emails_per_day, 30)
        
        # Test update
        update_data = {
            'sms_enabled': True,
            'max_sms_per_day': 20
        }
        
        updated = repo.create_or_update(user.id, update_data)
        self.assertEqual(updated.id, created.id)  # Same record
        self.assertTrue(updated.sms_enabled)  # Updated
        self.assertEqual(updated.max_sms_per_day, 20)  # Updated
        self.assertTrue(updated.email_enabled)  # Preserved
    
    def test_quota_repository_operations(self):
        """Test quota repository operations"""
        repo = DjangoNotificationQuotaRepository()
        user = User.objects.create_user(username='quotauser', password='test123')
        today = date.today()
        
        # Test initial count
        count = repo.get_daily_count(user.id, 'email', today)
        self.assertEqual(count, 0)
        
        # Test increment
        new_count = repo.increment_count(user.id, 'email', today)
        self.assertEqual(new_count, 1)
        
        # Test multiple increments
        for i in range(2, 6):
            count = repo.increment_count(user.id, 'email', today)
            self.assertEqual(count, i)
        
        # Test quota checking
        self.assertFalse(repo.check_quota_exceeded(user.id, 'email', 10, today))
        self.assertTrue(repo.check_quota_exceeded(user.id, 'email', 3, today))
        
        # Test different notification type (should be 0)
        sms_count = repo.get_daily_count(user.id, 'sms', today)
        self.assertEqual(sms_count, 0)
    
    def test_notification_log_repository_operations(self):
        """Test notification log repository operations"""
        repo = DjangoNotificationLogRepository()
        user = User.objects.create_user(username='loguser', password='test123')
        template = NotificationTemplateFactory()
        
        # Create some logs
        log_data = {
            'user_id': user.id,
            'template': template,
            'type': 'email',
            'recipient': 'test@example.com',
            'subject': 'Test',
            'body': 'Test body',
            'status': 'pending'
        }
        
        log1 = repo.create(log_data)
        self.assertIsNotNone(log1)
        
        # Create another log
        log_data['type'] = 'sms'
        log_data['recipient'] = '+1234567890'
        log2 = repo.create(log_data)
        
        # Test get by id
        retrieved = repo.get_by_id(log1.id)
        self.assertEqual(retrieved.id, log1.id)
        
        # Test get user notifications
        logs, count = repo.get_user_notifications(user.id)
        self.assertGreaterEqual(count, 2)
        self.assertGreaterEqual(len(logs), 2)
        
        # Test filtering by status
        logs_pending, count_pending = repo.get_user_notifications(
            user.id, 
            status='pending'
        )
        self.assertGreaterEqual(count_pending, 2)
        
        # Test filtering by type
        logs_email, count_email = repo.get_user_notifications(
            user.id,
            notification_type='email'
        )
        self.assertGreaterEqual(count_email, 1)
        
        # Test update status
        repo.update_status(log1.id, 'sent')
        updated_log = repo.get_by_id(log1.id)
        self.assertEqual(updated_log.status, 'sent')


class TemplateRepositoryAdvancedTest(TestCase):
    """Test template repository advanced operations"""
    
    def test_template_repository_crud(self):
        """Test template repository CRUD operations"""
        repo = DjangoNotificationTemplateRepository()
        
        # Test create
        template_data = {
            'name': 'repo_test_template',
            'type': 'email',
            'subject': 'Test Subject',
            'body': 'Test body content',
            'active': True
        }
        
        created = repo.create(template_data)
        self.assertIsNotNone(created)
        self.assertEqual(created.name, 'repo_test_template')
        
        # Test get by id
        retrieved = repo.get_by_id(created.id)
        self.assertEqual(retrieved.id, created.id)
        
        # Test get by name
        by_name = repo.get_by_name('repo_test_template')
        self.assertEqual(by_name.id, created.id)
        
        # Test update
        update_data = {
            'subject': 'Updated Subject',
            'body': 'Updated body content'
        }
        
        updated = repo.update(created.id, update_data)
        self.assertEqual(updated.subject, 'Updated Subject')
        self.assertEqual(updated.body, 'Updated body content')
        
        # Test delete (soft delete)
        result = repo.delete(created.id)
        self.assertTrue(result)
        
        # Verify it's soft deleted
        deleted_template = repo.get_by_id(created.id)
        self.assertFalse(deleted_template.active)