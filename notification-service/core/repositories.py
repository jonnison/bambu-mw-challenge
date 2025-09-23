"""
Repository interfaces for the notification service domain.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date

from .models import NotificationTemplate, NotificationLog, UserPreference, NotificationQuota


class NotificationTemplateRepository(ABC):
    """Repository interface for notification templates."""
    
    @abstractmethod
    def get_by_id(self, template_id: UUID) -> Optional[NotificationTemplate]:
        """Get template by ID."""
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[NotificationTemplate]:
        """Get template by name."""
        pass
    
    @abstractmethod
    def list_active(self, notification_type: Optional[str] = None) -> List[NotificationTemplate]:
        """List all active templates, optionally filtered by type."""
        pass
    
    @abstractmethod
    def create(self, template_data: Dict[str, Any]) -> NotificationTemplate:
        """Create a new template."""
        pass
    
    @abstractmethod
    def update(self, template_id: UUID, update_data: Dict[str, Any]) -> NotificationTemplate:
        """Update an existing template."""
        pass
    
    @abstractmethod
    def delete(self, template_id: UUID) -> bool:
        """Soft delete a template."""
        pass


class NotificationLogRepository(ABC):
    """Repository interface for notification logs."""
    
    @abstractmethod
    def get_by_id(self, log_id: UUID) -> Optional[NotificationLog]:
        """Get notification log by ID."""
        pass
    
    @abstractmethod
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
        """Get paginated notifications for a user with total count."""
        pass
    
    @abstractmethod
    def create(self, log_data: Dict[str, Any]) -> NotificationLog:
        """Create a new notification log entry."""
        pass
    
    @abstractmethod
    def update_status(self, log_id: UUID, status: str, **kwargs) -> NotificationLog:
        """Update notification status."""
        pass
    
    @abstractmethod
    def get_failed_notifications_for_retry(self, limit: int = 100) -> List[NotificationLog]:
        """Get failed notifications ready for retry."""
        pass
    
    @abstractmethod
    def get_by_correlation_id(self, correlation_id: UUID) -> List[NotificationLog]:
        """Get all notifications with the same correlation ID."""
        pass


class UserPreferenceRepository(ABC):
    """Repository interface for user preferences."""
    
    @abstractmethod
    def get_by_user_id(self, user_id: int) -> Optional[UserPreference]:
        """Get user preferences by user ID."""
        pass
    
    @abstractmethod
    def create_or_update(self, user_id: int, preferences: Dict[str, Any]) -> UserPreference:
        """Create or update user preferences."""
        pass
    
    @abstractmethod
    def get_users_with_preferences(self, user_ids: List[int]) -> List[UserPreference]:
        """Get preferences for multiple users."""
        pass


class NotificationQuotaRepository(ABC):
    """Repository interface for notification quotas."""
    
    @abstractmethod
    def get_daily_count(self, user_id: int, notification_type: str, date: date) -> int:
        """Get daily notification count for user and type."""
        pass
    
    @abstractmethod
    def increment_count(self, user_id: int, notification_type: str, date: date) -> int:
        """Increment and return new count."""
        pass
    
    @abstractmethod
    def check_quota_exceeded(self, user_id: int, notification_type: str, max_count: int, date: date) -> bool:
        """Check if quota is exceeded."""
        pass


# Django ORM Implementations

class DjangoNotificationTemplateRepository(NotificationTemplateRepository):
    """Django ORM implementation of notification template repository."""
    
    def get_by_id(self, template_id: UUID) -> Optional[NotificationTemplate]:
        try:
            return NotificationTemplate.objects.get(id=template_id)
        except NotificationTemplate.DoesNotExist:
            return None
    
    def get_by_name(self, name: str) -> Optional[NotificationTemplate]:
        try:
            return NotificationTemplate.objects.get(name=name, active=True)
        except NotificationTemplate.DoesNotExist:
            return None
    
    def list_active(self, notification_type: Optional[str] = None) -> List[NotificationTemplate]:
        queryset = NotificationTemplate.objects.filter(active=True)
        if notification_type:
            queryset = queryset.filter(type=notification_type)
        return list(queryset.order_by('name'))
    
    def create(self, template_data: Dict[str, Any]) -> NotificationTemplate:
        return NotificationTemplate.objects.create(**template_data)
    
    def update(self, template_id: UUID, update_data: Dict[str, Any]) -> NotificationTemplate:
        template = NotificationTemplate.objects.get(id=template_id)
        for key, value in update_data.items():
            setattr(template, key, value)
        template.save()
        return template
    
    def delete(self, template_id: UUID) -> bool:
        try:
            template = NotificationTemplate.objects.get(id=template_id)
            template.active = False
            template.save(update_fields=['active'])
            return True
        except NotificationTemplate.DoesNotExist:
            return False


class DjangoNotificationLogRepository(NotificationLogRepository):
    """Django ORM implementation of notification log repository."""
    
    def get_by_id(self, log_id: UUID) -> Optional[NotificationLog]:
        try:
            return NotificationLog.objects.select_related('template').get(id=log_id)
        except NotificationLog.DoesNotExist:
            return None
    
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
        queryset = NotificationLog.objects.filter(user_id=user_id).select_related('template')
        
        if status:
            queryset = queryset.filter(status=status)
        if notification_type:
            queryset = queryset.filter(type=notification_type)
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        total_count = queryset.count()
        notifications = list(queryset.order_by('-created_at')[offset:offset + limit])
        
        return notifications, total_count
    
    def create(self, log_data: Dict[str, Any]) -> NotificationLog:
        return NotificationLog.objects.create(**log_data)
    
    def update_status(self, log_id: UUID, status: str, **kwargs) -> NotificationLog:
        log = NotificationLog.objects.get(id=log_id)
        log.status = status
        for key, value in kwargs.items():
            setattr(log, key, value)
        log.save()
        return log
    
    def get_failed_notifications_for_retry(self, limit: int = 100) -> List[NotificationLog]:
        from django.utils import timezone
        return list(
            NotificationLog.objects.filter(
                status='retry',
                next_retry_at__lte=timezone.now()
            ).select_related('template')[:limit]
        )
    
    def get_by_correlation_id(self, correlation_id: UUID) -> List[NotificationLog]:
        return list(
            NotificationLog.objects.filter(correlation_id=correlation_id)
            .select_related('template')
            .order_by('created_at')
        )


class DjangoUserPreferenceRepository(UserPreferenceRepository):
    """Django ORM implementation of user preference repository."""
    
    def get_by_user_id(self, user_id: int) -> Optional[UserPreference]:
        try:
            return UserPreference.objects.get(user_id=user_id)
        except UserPreference.DoesNotExist:
            return None
    
    def create_or_update(self, user_id: int, preferences: Dict[str, Any]) -> UserPreference:
        preference, created = UserPreference.objects.update_or_create(
            user_id=user_id,
            defaults=preferences
        )
        return preference
    
    def get_users_with_preferences(self, user_ids: List[int]) -> List[UserPreference]:
        return list(UserPreference.objects.filter(user_id__in=user_ids))


class DjangoNotificationQuotaRepository(NotificationQuotaRepository):
    """Django ORM implementation of notification quota repository."""
    
    def get_daily_count(self, user_id: int, notification_type: str, date: date) -> int:
        try:
            quota = NotificationQuota.objects.get(
                user_id=user_id,
                notification_type=notification_type,
                date=date
            )
            return quota.count
        except NotificationQuota.DoesNotExist:
            return 0
    
    def increment_count(self, user_id: int, notification_type: str, date: date) -> int:
        return NotificationQuota.increment_quota(user_id, notification_type, date)
    
    def check_quota_exceeded(self, user_id: int, notification_type: str, max_count: int, date: date) -> bool:
        return NotificationQuota.check_quota_exceeded(user_id, notification_type, max_count, date)