"""
Core Services Tests

This module provides comprehensive testing for core notification services.
"""
import pytest
import uuid
from datetime import datetime, timedelta, date
from unittest.mock import Mock, patch

from core.services import (
    NotificationTemplateService,
    UserPreferenceService,
    NotificationRequest,
    NotificationResult
)
from core.models import NotificationTemplate, UserPreference
from tests.fixtures.factories import (
    NotificationTemplateFactory,
    UserPreferenceFactory
)


@pytest.mark.django_db
class NotificationTemplateServiceTest:
    """Comprehensive tests for NotificationTemplateService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_repository = Mock()
        self.service = NotificationTemplateService(self.mock_repository)
        self.template = NotificationTemplateFactory.build()
    
    def test_get_template_success(self):
        """Test successful template retrieval"""
        template_id = uuid.uuid4()
        self.mock_repository.get_by_id.return_value = self.template
        
        result = self.service.get_template(template_id)
        
        assert result == self.template
        self.mock_repository.get_by_id.assert_called_once_with(template_id)
    
    def test_get_template_by_name_success(self):
        """Test successful template retrieval by name"""
        self.mock_repository.get_by_name.return_value = self.template
        
        result = self.service.get_template_by_name("test_template")
        
        assert result == self.template
        self.mock_repository.get_by_name.assert_called_once_with("test_template")
    
    def test_create_template_success_with_unique_name(self):
        """Test successful template creation with unique name"""
        template_data = {
            'name': f'Unique Template {uuid.uuid4()}',  # Make name unique
            'subject': 'Test Subject',
            'body': 'Hello {{name}}!',
            'type': 'email'
        }
        self.mock_repository.get_by_name.return_value = None  # Name doesn't exist
        self.mock_repository.create.return_value = self.template
        
        result = self.service.create_template(template_data)
        
        assert result == self.template
        self.mock_repository.create.assert_called_once_with(template_data)
    
    def test_create_template_validation_name_too_short(self):
        """Test template creation with name too short"""
        template_data = {
            'name': 'X',  # Too short
            'body': 'Hello!',
            'type': 'email'
        }
        
        with pytest.raises(ValueError, match="Template name must be at least 3 characters"):
            self.service.create_template(template_data)
    
    def test_create_template_validation_invalid_type(self):
        """Test template creation with invalid notification type"""
        template_data = {
            'name': 'Valid Name',
            'body': 'Hello!',
            'type': 'invalid_type'  # Invalid type
        }
        
        with pytest.raises(ValueError, match="Invalid notification type"):
            self.service.create_template(template_data)
    
    def test_update_template_success(self):
        """Test successful template update"""
        template_id = uuid.uuid4()
        update_data = {'subject': 'Updated Subject'}
        self.mock_repository.update.return_value = self.template
        
        result = self.service.update_template(template_id, update_data)
        
        assert result == self.template
        self.mock_repository.update.assert_called_once_with(template_id, update_data)
    
    def test_delete_template_success(self):
        """Test successful template deletion"""
        template_id = uuid.uuid4()
        self.mock_repository.delete.return_value = True
        
        result = self.service.delete_template(template_id)
        
        assert result is True
        self.mock_repository.delete.assert_called_once_with(template_id)
    
    def test_render_template_success(self):
        """Test successful template rendering"""
        template = NotificationTemplateFactory.build(
            subject="Hello {{name}}!",
            body="Welcome {{name}}, your code is {{code}}"
        )
        context = {'name': 'John', 'code': '12345'}
        
        result = self.service.render_template(template, context)
        
        assert result['subject'] == "Hello John!"
        assert result['body'] == "Welcome John, your code is 12345"


@pytest.mark.django_db
class UserPreferenceServiceTest:
    """Comprehensive tests for UserPreferenceService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_repository = Mock()
        self.service = UserPreferenceService(self.mock_repository)
        self.user_preferences = UserPreferenceFactory.build()
    
    def test_get_user_preferences_found(self):
        """Test successful user preferences retrieval"""
        user_id = 123
        self.mock_repository.get_by_user_id.return_value = self.user_preferences
        
        result = self.service.get_user_preferences(user_id)
        
        assert result == self.user_preferences
        self.mock_repository.get_by_user_id.assert_called_once_with(user_id)
    
    def test_update_user_preferences_success(self):
        """Test successful user preferences update"""
        user_id = 123
        preferences_data = {
            'email_enabled': True,
            'sms_enabled': False,
            'max_emails_per_day': 25
        }
        self.mock_repository.create_or_update.return_value = self.user_preferences
        
        result = self.service.update_user_preferences(user_id, preferences_data)
        
        assert result == self.user_preferences
        self.mock_repository.create_or_update.assert_called_once_with(user_id, preferences_data)
    
    def test_update_user_preferences_validation_boolean_error(self):
        """Test user preferences update with invalid boolean values"""
        user_id = 123
        preferences_data = {
            'email_enabled': 'yes',  # Should be boolean
            'sms_enabled': True
        }
        
        with pytest.raises(ValueError, match="email_enabled must be a boolean"):
            self.service.update_user_preferences(user_id, preferences_data)
    
    def test_update_user_preferences_validation_numeric_error(self):
        """Test user preferences update with invalid numeric values"""
        user_id = 123
        preferences_data = {
            'email_enabled': True,
            'max_emails_per_day': -5  # Should be non-negative
        }
        
        with pytest.raises(ValueError, match="max_emails_per_day must be a non-negative integer"):
            self.service.update_user_preferences(user_id, preferences_data)
    
    def test_get_multiple_user_preferences(self):
        """Test getting preferences for multiple users"""
        user_ids = [123, 456, 789]
        expected_preferences = [
            UserPreferenceFactory.build(user_id=123),
            UserPreferenceFactory.build(user_id=456),
            UserPreferenceFactory.build(user_id=789)
        ]
        self.mock_repository.get_users_with_preferences.return_value = expected_preferences
        
        result = self.service.get_multiple_user_preferences(user_ids)
        
        assert result == expected_preferences
        self.mock_repository.get_users_with_preferences.assert_called_once_with(user_ids)