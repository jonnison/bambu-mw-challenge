"""
API serializers for request/response validation and transformation.
"""
from rest_framework import serializers
from core.models import NotificationTemplate, NotificationLog, UserPreference


class NotificationRequestSerializer(serializers.Serializer):
    """Serializer for notification send requests."""
    user_id = serializers.IntegerField(min_value=1)
    template_name = serializers.CharField(max_length=100)
    context = serializers.JSONField()
    priority = serializers.ChoiceField(
        choices=['low', 'normal', 'high', 'urgent'], 
        default='normal'
    )
    correlation_id = serializers.UUIDField(required=False, allow_null=True)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)


class NotificationResponseSerializer(serializers.Serializer):
    """Serializer for notification response."""
    notification_id = serializers.UUIDField()
    status = serializers.CharField()
    message = serializers.CharField(required=False)
    queued_at = serializers.DateTimeField(required=False)


class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer for notification log entries."""
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_type = serializers.CharField(source='template.type', read_only=True)
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'user_id', 'template_name', 'template_type', 'type', 
            'status', 'priority', 'recipient', 'subject', 'sent_at', 
            'error_message', 'retry_count', 'provider_id', 'correlation_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields


class NotificationStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating notification status."""
    status = serializers.ChoiceField(choices=['read', 'unread', 'archived'])
    updated_by = serializers.CharField(max_length=100, required=False)


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for notification templates."""
    variable_names = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
        source='get_variable_names'
    )
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'subject', 'body', 'type', 'variables',
            'active', 'variable_names', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'variable_names']
    
    def validate_name(self, value):
        """Validate template name uniqueness."""
        if self.instance:
            # Update case - exclude current instance
            if NotificationTemplate.objects.exclude(id=self.instance.id).filter(name=value).exists():
                raise serializers.ValidationError("Template with this name already exists.")
        else:
            # Create case
            if NotificationTemplate.objects.filter(name=value).exists():
                raise serializers.ValidationError("Template with this name already exists.")
        return value


class NotificationTemplateCreateSerializer(NotificationTemplateSerializer):
    """Serializer for creating notification templates."""
    
    class Meta(NotificationTemplateSerializer.Meta):
        extra_kwargs = {
            'name': {'required': True},
            'body': {'required': True},
            'type': {'required': True}
        }


class UserPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for user preferences."""
    
    class Meta:
        model = UserPreference
        fields = [
            'id', 'user_id', 'email_enabled', 'sms_enabled', 'push_enabled',
            'quiet_hours_start', 'quiet_hours_end', 'timezone',
            'max_emails_per_day', 'max_sms_per_day', 'frequency_preference',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate preference data."""
        quiet_start = data.get('quiet_hours_start')
        quiet_end = data.get('quiet_hours_end')
        
        if quiet_start and not quiet_end:
            raise serializers.ValidationError(
                "quiet_hours_end is required when quiet_hours_start is provided"
            )
        
        if quiet_end and not quiet_start:
            raise serializers.ValidationError(
                "quiet_hours_start is required when quiet_hours_end is provided"
            )
        
        return data


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