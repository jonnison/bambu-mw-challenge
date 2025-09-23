"""
Core business services for the notification domain.
"""
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from dataclasses import dataclass

from .models import NotificationTemplate, NotificationLog, UserPreference
from .repositories import (
    NotificationTemplateRepository, 
    NotificationLogRepository,
    UserPreferenceRepository,
    NotificationQuotaRepository
)

logger = logging.getLogger(__name__)


@dataclass
class NotificationRequest:
    """Data class for notification requests."""
    user_id: int
    template_name: str
    context: Dict[str, Any]
    priority: str = 'normal'
    correlation_id: Optional[uuid.UUID] = None
    scheduled_at: Optional[datetime] = None


@dataclass
class NotificationResult:
    """Data class for notification results."""
    notification_id: uuid.UUID
    status: str
    error_message: Optional[str] = None


class NotificationTemplateService:
    """Service for managing notification templates."""
    
    def __init__(self, template_repository: NotificationTemplateRepository):
        self.template_repository = template_repository
    
    def get_template(self, template_id: uuid.UUID) -> Optional[NotificationTemplate]:
        """Get template by ID."""
        return self.template_repository.get_by_id(template_id)
    
    def get_template_by_name(self, name: str) -> Optional[NotificationTemplate]:
        """Get template by name."""
        return self.template_repository.get_by_name(name)
    
    def list_templates(self, notification_type: Optional[str] = None) -> List[NotificationTemplate]:
        """List active templates."""
        return self.template_repository.list_active(notification_type)
    
    def create_template(self, template_data: Dict[str, Any]) -> NotificationTemplate:
        """Create a new template."""
        # Validate template data
        self._validate_template_data(template_data)
        
        # Check if template name already exists
        existing = self.template_repository.get_by_name(template_data['name'])
        if existing:
            raise ValueError(f"Template with name '{template_data['name']}' already exists")
        
        return self.template_repository.create(template_data)
    
    def update_template(self, template_id: uuid.UUID, update_data: Dict[str, Any]) -> NotificationTemplate:
        """Update an existing template."""
        template = self.template_repository.get_by_id(template_id)
        if not template:
            raise ValueError(f"Template with ID {template_id} not found")
        
        # Validate update data
        self._validate_template_data(update_data, is_update=True)
        
        return self.template_repository.update(template_id, update_data)
    
    def delete_template(self, template_id: uuid.UUID) -> bool:
        """Soft delete a template."""
        return self.template_repository.delete(template_id)
    
    def render_template(self, template: NotificationTemplate, context: Dict[str, Any]) -> Dict[str, str]:
        """Render template with context variables."""
        try:
            # Simple template rendering (in production, use Jinja2 or similar)
            rendered_body = template.body
            rendered_subject = template.subject or ""
            
            for key, value in context.items():
                placeholder = f"{{{{{key}}}}}"
                rendered_body = rendered_body.replace(placeholder, str(value))
                rendered_subject = rendered_subject.replace(placeholder, str(value))
            
            return {
                'subject': rendered_subject,
                'body': rendered_body
            }
        except Exception as e:
            logger.error(f"Failed to render template {template.id}: {e}")
            raise ValueError(f"Template rendering failed: {e}")
    
    def _validate_template_data(self, data: Dict[str, Any], is_update: bool = False):
        """Validate template data."""
        if not is_update:
            required_fields = ['name', 'body', 'type']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
        
        if 'type' in data and data['type'] not in ['email', 'sms', 'push']:
            raise ValueError("Invalid notification type")
        
        if 'name' in data and len(data['name']) < 3:
            raise ValueError("Template name must be at least 3 characters")


class NotificationService:
    """Core service for handling notifications."""
    
    def __init__(
        self,
        template_service: NotificationTemplateService,
        log_repository: NotificationLogRepository,
        preference_repository: UserPreferenceRepository,
        quota_repository: NotificationQuotaRepository
    ):
        self.template_service = template_service
        self.log_repository = log_repository
        self.preference_repository = preference_repository
        self.quota_repository = quota_repository
    
    def send_notification(self, request: NotificationRequest) -> NotificationResult:
        """
        Process a notification request.
        This creates a log entry and queues the notification for async processing.
        """
        try:
            # Get template
            template = self.template_service.get_template_by_name(request.template_name)
            if not template:
                raise ValueError(f"Template '{request.template_name}' not found")
            
            # Get user preferences
            preferences = self.preference_repository.get_by_user_id(request.user_id)
            if preferences:
                # Check if notification type is allowed
                if not preferences.is_notification_allowed(template.type):
                    return NotificationResult(
                        notification_id=uuid.uuid4(),
                        status='blocked',
                        error_message='Notification blocked by user preferences'
                    )
                
                # Check daily quota
                today = date.today()
                max_count = getattr(preferences, f'max_{template.type}s_per_day', 50)
                if self.quota_repository.check_quota_exceeded(
                    request.user_id, template.type, max_count, today
                ):
                    return NotificationResult(
                        notification_id=uuid.uuid4(),
                        status='quota_exceeded',
                        error_message=f'Daily {template.type} quota exceeded'
                    )
            
            # Render template
            rendered = self.template_service.render_template(template, request.context)
            
            # Determine recipient based on type and context
            recipient = self._get_recipient(template.type, request.context, request.user_id)
            
            # Create notification log
            log_data = {
                'user_id': request.user_id,
                'template': template,
                'type': template.type,
                'priority': request.priority,
                'recipient': recipient,
                'subject': rendered['subject'],
                'body': rendered['body'],
                'status': 'pending',
                'correlation_id': request.correlation_id,
                'metadata': {
                    'template_name': request.template_name,
                    'context_keys': list(request.context.keys()),
                    'scheduled_at': request.scheduled_at.isoformat() if request.scheduled_at else None
                }
            }
            
            notification = self.log_repository.create(log_data)
            
            # Increment quota
            if preferences:
                self.quota_repository.increment_count(
                    request.user_id, template.type, date.today()
                )
            
            # Queue for async processing (would trigger Celery task in real implementation)
            logger.info(f"Notification {notification.id} queued for processing")
            
            return NotificationResult(
                notification_id=notification.id,
                status='queued'
            )
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return NotificationResult(
                notification_id=uuid.uuid4(),
                status='failed',
                error_message=str(e)
            )
    
    def get_notification(self, notification_id: uuid.UUID) -> Optional[NotificationLog]:
        """Get notification by ID."""
        return self.log_repository.get_by_id(notification_id)
    
    def get_user_notifications(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
        status: Optional[str] = None,
        notification_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> tuple[List[NotificationLog], int]:
        """Get paginated notifications for a user."""
        return self.log_repository.get_user_notifications(
            user_id, limit, offset, status, notification_type, date_from, date_to
        )
    
    def update_notification_status(self, notification_id: uuid.UUID, status: str) -> Optional[NotificationLog]:
        """Update notification status."""
        try:
            return self.log_repository.update_status(notification_id, status)
        except Exception as e:
            logger.error(f"Failed to update notification status: {e}")
            return None
    
    def get_notifications_by_correlation_id(self, correlation_id: uuid.UUID) -> List[NotificationLog]:
        """Get all notifications with the same correlation ID."""
        return self.log_repository.get_by_correlation_id(correlation_id)
    
    def get_failed_notifications_for_retry(self, limit: int = 100) -> List[NotificationLog]:
        """Get failed notifications ready for retry."""
        return self.log_repository.get_failed_notifications_for_retry(limit)
    
    def _get_recipient(self, notification_type: str, context: Dict[str, Any], user_id: int) -> str:
        """Determine recipient based on notification type and context."""
        if notification_type == 'email':
            return context.get('email', f'user{user_id}@example.com')
        elif notification_type == 'sms':
            return context.get('phone', f'+1555000{user_id:04d}')
        elif notification_type == 'push':
            return context.get('device_token', f'device_token_{user_id}')
        else:
            raise ValueError(f"Unknown notification type: {notification_type}")


class UserPreferenceService:
    """Service for managing user preferences."""
    
    def __init__(self, preference_repository: UserPreferenceRepository):
        self.preference_repository = preference_repository
    
    def get_user_preferences(self, user_id: int) -> Optional[UserPreference]:
        """Get user preferences."""
        return self.preference_repository.get_by_user_id(user_id)
    
    def update_user_preferences(self, user_id: int, preferences: Dict[str, Any]) -> UserPreference:
        """Update user preferences."""
        # Validate preferences
        self._validate_preferences(preferences)
        
        return self.preference_repository.create_or_update(user_id, preferences)
    
    def get_multiple_user_preferences(self, user_ids: List[int]) -> List[UserPreference]:
        """Get preferences for multiple users."""
        return self.preference_repository.get_users_with_preferences(user_ids)
    
    def _validate_preferences(self, preferences: Dict[str, Any]):
        """Validate preference data."""
        # Validate boolean fields
        boolean_fields = ['email_enabled', 'sms_enabled', 'push_enabled']
        for field in boolean_fields:
            if field in preferences and not isinstance(preferences[field], bool):
                raise ValueError(f"{field} must be a boolean")
        
        # Validate numeric fields
        numeric_fields = ['max_emails_per_day', 'max_sms_per_day']
        for field in numeric_fields:
            if field in preferences:
                value = preferences[field]
                if not isinstance(value, int) or value < 0:
                    raise ValueError(f"{field} must be a non-negative integer")
        
        # Validate timezone
        if 'timezone' in preferences:
            # In production, validate against pytz.all_timezones
            pass