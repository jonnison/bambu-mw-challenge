"""
Core domain models for the notification service.
"""
import uuid
from django.db import models
from django.core.validators import MinLengthValidator
from django.utils import timezone


class NotificationTemplate(models.Model):
    """
    Template for notifications with support for variables.
    """
    NOTIFICATION_TYPES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100, 
        unique=True,
        validators=[MinLengthValidator(3)],
        help_text="Unique template identifier"
    )
    subject = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text="Email subject or notification title"
    )
    body = models.TextField(
        help_text="Template body with variable placeholders like {{user_name}}"
    )
    type = models.CharField(
        max_length=20, 
        choices=NOTIFICATION_TYPES,
        help_text="Type of notification this template is for"
    )
    variables = models.JSONField(
        default=dict,
        help_text="Schema definition for template variables"
    )
    active = models.BooleanField(
        default=True,
        help_text="Whether this template is available for use"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_templates'
        ordering = ['name']
        indexes = [
            models.Index(fields=['type', 'active']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.type})"
    
    def get_variable_names(self):
        """Extract variable names from the body text."""
        import re
        return re.findall(r'\{\{(\w+)\}\}', self.body)


class NotificationLog(models.Model):
    """
    Log of all notification attempts and their outcomes.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
        ('retry', 'Retry'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.PositiveIntegerField(
        help_text="ID of the user receiving the notification"
    )
    template = models.ForeignKey(
        'NotificationTemplate',
        on_delete=models.PROTECT,
        related_name='logs',
        help_text="Template used for this notification"
    )
    type = models.CharField(
        max_length=20, 
        choices=NotificationTemplate.NOTIFICATION_TYPES,
        help_text="Type of notification sent"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        help_text="Current status of the notification"
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        help_text="Priority level for processing"
    )
    recipient = models.CharField(
        max_length=255,
        help_text="Email address, phone number, or device token"
    )
    subject = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text="Rendered subject line"
    )
    body = models.TextField(
        help_text="Rendered notification body"
    )
    sent_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When the notification was successfully sent"
    )
    error_message = models.TextField(
        blank=True, 
        null=True,
        help_text="Error details if sending failed"
    )
    retry_count = models.IntegerField(
        default=0,
        help_text="Number of retry attempts"
    )
    next_retry_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When to retry sending this notification"
    )
    provider_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text="External provider's message ID"
    )
    metadata = models.JSONField(
        default=dict,
        help_text="Additional metadata about the notification"
    )
    correlation_id = models.UUIDField(
        null=True, 
        blank=True,
        help_text="ID to correlate related notifications"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', '-created_at']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['type', 'status']),
            models.Index(fields=['status', 'retry_count']),
            models.Index(fields=['next_retry_at'], condition=models.Q(status='failed')),
            models.Index(fields=['correlation_id']),
        ]
    
    def __str__(self):
        return f"Notification {self.id} ({self.type}) - {self.status}"
    
    def mark_sent(self, provider_id=None):
        """Mark notification as successfully sent."""
        self.status = 'sent'
        self.sent_at = timezone.now()
        if provider_id:
            self.provider_id = provider_id
        self.save(update_fields=['status', 'sent_at', 'provider_id', 'updated_at'])
    
    def mark_failed(self, error_message, schedule_retry=True):
        """Mark notification as failed and optionally schedule retry."""
        self.status = 'failed'
        self.error_message = error_message
        self.retry_count += 1
        
        if schedule_retry and self.retry_count < 3:  # Max 3 retries
            # Exponential backoff: 1min, 5min, 15min
            retry_delays = [60, 300, 900]
            delay = retry_delays[min(self.retry_count - 1, len(retry_delays) - 1)]
            self.next_retry_at = timezone.now() + timezone.timedelta(seconds=delay)
            self.status = 'retry'
        
        self.save(update_fields=[
            'status', 'error_message', 'retry_count', 'next_retry_at', 'updated_at'
        ])


class UserPreference(models.Model):
    """
    User notification preferences and settings.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.PositiveIntegerField(
        unique=True,
        help_text="ID of the user these preferences belong to"
    )
    email_enabled = models.BooleanField(
        default=True,
        help_text="Whether user wants to receive email notifications"
    )
    sms_enabled = models.BooleanField(
        default=True,
        help_text="Whether user wants to receive SMS notifications"
    )
    push_enabled = models.BooleanField(
        default=True,
        help_text="Whether user wants to receive push notifications"
    )
    quiet_hours_start = models.TimeField(
        null=True, 
        blank=True,
        help_text="Start of quiet hours (no notifications)"
    )
    quiet_hours_end = models.TimeField(
        null=True, 
        blank=True,
        help_text="End of quiet hours (no notifications)"
    )
    timezone = models.CharField(
        max_length=50,
        default='UTC',
        help_text="User's timezone for quiet hours"
    )
    max_emails_per_day = models.PositiveIntegerField(
        default=50,
        help_text="Maximum number of emails per day"
    )
    max_sms_per_day = models.PositiveIntegerField(
        default=10,
        help_text="Maximum number of SMS per day"
    )
    frequency_preference = models.JSONField(
        default=dict,
        help_text="Frequency preferences per notification type"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_preferences'
        indexes = [
            models.Index(fields=['user_id']),
        ]
    
    def __str__(self):
        return f"Preferences for user {self.user_id}"
    
    def is_notification_allowed(self, notification_type, current_time=None):
        """Check if notification is allowed based on preferences."""
        if current_time is None:
            current_time = timezone.now()
        
        # Check if notification type is enabled
        if notification_type == 'email' and not self.email_enabled:
            return False
        elif notification_type == 'sms' and not self.sms_enabled:
            return False
        elif notification_type == 'push' and not self.push_enabled:
            return False
        
        # Check quiet hours
        if self.quiet_hours_start and self.quiet_hours_end:
            current_time_local = current_time.astimezone(timezone.get_current_timezone())
            current_hour = current_time_local.time()
            
            if self.quiet_hours_start <= self.quiet_hours_end:
                # Same day quiet hours
                if self.quiet_hours_start <= current_hour <= self.quiet_hours_end:
                    return False
            else:
                # Overnight quiet hours
                if current_hour >= self.quiet_hours_start or current_hour <= self.quiet_hours_end:
                    return False
        
        return True


class NotificationQuota(models.Model):
    """
    Track daily notification quotas per user and type.
    """
    user_id = models.PositiveIntegerField()
    notification_type = models.CharField(
        max_length=20, 
        choices=NotificationTemplate.NOTIFICATION_TYPES
    )
    date = models.DateField(default=timezone.now)
    count = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'notification_quotas'
        unique_together = ['user_id', 'notification_type', 'date']
        indexes = [
            models.Index(fields=['user_id', 'date']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"Quota for user {self.user_id} ({self.notification_type}) on {self.date}"
    
    @classmethod
    def increment_quota(cls, user_id, notification_type, date=None):
        """Increment the quota count for a user and notification type."""
        if date is None:
            date = timezone.now().date()
        
        quota, created = cls.objects.get_or_create(
            user_id=user_id,
            notification_type=notification_type,
            date=date,
            defaults={'count': 0}
        )
        quota.count += 1
        quota.save(update_fields=['count'])
        return quota.count
    
    @classmethod
    def check_quota_exceeded(cls, user_id, notification_type, max_count, date=None):
        """Check if user has exceeded their daily quota."""
        if date is None:
            date = timezone.now().date()
        
        try:
            quota = cls.objects.get(
                user_id=user_id,
                notification_type=notification_type,
                date=date
            )
            return quota.count >= max_count
        except cls.DoesNotExist:
            return False