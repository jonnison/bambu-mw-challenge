"""
API Serializers for Notification Service
Provides request/response validation and serialization for all API endpoints.
"""
from rest_framework import serializers
from core.models import NotificationTemplate, NotificationLog, UserPreference


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for NotificationTemplate model."""
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'subject', 'body', 'type', 'variables', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_variables(self, value):
        """Validate that variables is a valid JSON object."""
        if value is not None and not isinstance(value, dict):
            raise serializers.ValidationError("Variables must be a valid JSON object")
        return value


class TemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating notification templates."""
    
    class Meta:
        model = NotificationTemplate
        fields = ['name', 'subject', 'body', 'type', 'variables']
    
    def validate_name(self, value):
        """Ensure template name is unique."""
        if NotificationTemplate.objects.filter(name=value).exists():
            raise serializers.ValidationError("Template with this name already exists")
        return value
    
    def validate_type(self, value):
        """Validate notification type."""
        valid_types = ['email', 'sms', 'push']
        if value not in valid_types:
            raise serializers.ValidationError(f"Type must be one of: {', '.join(valid_types)}")
        return value


class TemplateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating notification templates."""
    
    class Meta:
        model = NotificationTemplate
        fields = ['name', 'subject', 'body', 'type', 'variables']
        extra_kwargs = {
            'name': {'required': False},
            'subject': {'required': False},
            'body': {'required': False},
            'type': {'required': False},
            'variables': {'required': False},
        }
    
    def validate_type(self, value):
        """Validate notification type."""
        valid_types = ['email', 'sms', 'push']
        if value not in valid_types:
            raise serializers.ValidationError(f"Type must be one of: {', '.join(valid_types)}")
        return value


class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer for NotificationLog model."""
    
    template_name = serializers.CharField(source='template.name', read_only=True)
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'user_id', 'template_id', 'template_name', 'type', 'status',
            'sent_at', 'error_message', 'metadata', 'created_at', 'updated_at',
            'retry_count', 'priority'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for UserPreference model."""
    
    class Meta:
        model = UserPreference
        fields = [
            'id', 'user_id', 'email_enabled', 'sms_enabled', 'push_enabled',
            'quiet_hours_start', 'quiet_hours_end', 'updated_at'
        ]
        read_only_fields = ['id', 'updated_at']


class PreferenceUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user preferences."""
    
    class Meta:
        model = UserPreference
        fields = [
            'email_enabled', 'sms_enabled', 'push_enabled',
            'quiet_hours_start', 'quiet_hours_end'
        ]
        extra_kwargs = {
            'email_enabled': {'required': False},
            'sms_enabled': {'required': False},
            'push_enabled': {'required': False},
            'quiet_hours_start': {'required': False},
            'quiet_hours_end': {'required': False},
        }
    
    def validate_quiet_hours(self, attrs):
        """Validate quiet hours configuration."""
        start = attrs.get('quiet_hours_start')
        end = attrs.get('quiet_hours_end')
        
        if start and end and start == end:
            raise serializers.ValidationError("Quiet hours start and end cannot be the same")
        
        return attrs


class SendNotificationSerializer(serializers.Serializer):
    """Serializer for sending notifications."""
    
    user_id = serializers.IntegerField(min_value=1)
    template_name = serializers.CharField(max_length=100)
    context = serializers.JSONField(required=False, default=dict)
    notification_type = serializers.ChoiceField(
        choices=['email', 'sms', 'push'],
        required=False,
        help_text="Override the template's default type"
    )
    priority = serializers.ChoiceField(
        choices=['low', 'normal', 'high'],
        default='normal',
        required=False
    )
    
    def validate_template_name(self, value):
        """Validate that template exists."""
        if not NotificationTemplate.objects.filter(name=value).exists():
            raise serializers.ValidationError(f"Template '{value}' does not exist")
        return value
    
    def validate_context(self, value):
        """Validate context is a dictionary."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Context must be a JSON object")
        return value


class NotificationResponseSerializer(serializers.Serializer):
    """Serializer for notification send response."""
    
    id = serializers.IntegerField()
    status = serializers.CharField()
    message = serializers.CharField()
    user_id = serializers.IntegerField()
    template_name = serializers.CharField()
    notification_type = serializers.CharField()


class NotificationStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating notification status."""
    
    status = serializers.ChoiceField(
        choices=['pending', 'sent', 'failed', 'bounced'],
        help_text="New status for the notification"
    )
    error_message = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Error message if status is 'failed'"
    )
    
    def validate(self, attrs):
        """Validate that error_message is provided for failed status."""
        if attrs.get('status') == 'failed' and not attrs.get('error_message'):
            raise serializers.ValidationError(
                "Error message is required when status is 'failed'"
            )
        return attrs


class BulkNotificationSerializer(serializers.Serializer):
    """Serializer for bulk notification sending."""
    
    user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=1000,
        help_text="List of user IDs (max 1000)"
    )
    template_name = serializers.CharField(max_length=100)
    context = serializers.JSONField(required=False, default=dict)
    priority = serializers.ChoiceField(
        choices=['low', 'normal', 'high'],
        default='normal',
        required=False
    )
    
    def validate_template_name(self, value):
        """Validate that template exists."""
        if not NotificationTemplate.objects.filter(name=value).exists():
            raise serializers.ValidationError(f"Template '{value}' does not exist")
        return value


class BulkNotificationResponseSerializer(serializers.Serializer):
    """Serializer for bulk notification response."""
    
    queued_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()
    message = serializers.CharField()
    details = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )


# Legacy serializers for backward compatibility
class NotificationRequestSerializer(SendNotificationSerializer):
    """Legacy serializer for notification requests."""
    pass


class NotificationTemplateCreateSerializer(TemplateCreateSerializer):
    """Legacy serializer for template creation."""
    pass


class PaginatedResponseSerializer(serializers.Serializer):
    """Serializer for paginated responses."""
    data = serializers.ListField()
    pagination = serializers.DictField()
    links = serializers.DictField()


class HealthCheckSerializer(serializers.Serializer):
    """Serializer for health check responses."""
    status = serializers.CharField()
    timestamp = serializers.DateTimeField()
    services = serializers.DictField()
    version = serializers.CharField()


class MetricsSerializer(serializers.Serializer):
    """Serializer for metrics responses."""
    notifications_sent_total = serializers.IntegerField()
    notifications_failed_total = serializers.IntegerField()
    notifications_pending_total = serializers.IntegerField()
    avg_processing_time_seconds = serializers.FloatField()
    error_rate_percentage = serializers.FloatField()
    uptime_seconds = serializers.IntegerField()


class ErrorResponseSerializer(serializers.Serializer):
    """Serializer for error responses."""
    error = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField(required=False)
    timestamp = serializers.DateTimeField()
    request_id = serializers.CharField(required=False)