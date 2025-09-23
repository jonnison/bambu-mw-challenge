"""
API Views for Notification Service
Implements all required REST endpoints with proper HTTP methods and status codes.
"""
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from core.models import NotificationTemplate, NotificationLog, UserPreference
from core.services import NotificationService, NotificationTemplateService, UserPreferenceService
from core.repositories import (
    DjangoNotificationTemplateRepository,
    DjangoNotificationLogRepository, 
    DjangoUserPreferenceRepository,
    DjangoNotificationQuotaRepository
)
from .serializers import (
    NotificationTemplateSerializer,
    NotificationLogSerializer,
    UserPreferenceSerializer,
    SendNotificationSerializer,
    NotificationStatusUpdateSerializer,
    NotificationResponseSerializer,
    TemplateCreateSerializer,
    TemplateUpdateSerializer,
    PreferenceUpdateSerializer,
)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination configuration for all list endpoints."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@extend_schema_view(
    list=extend_schema(
        summary="List all notification templates",
        description="Retrieve a paginated list of all notification templates",
        responses={200: NotificationTemplateSerializer(many=True)},
    ),
    create=extend_schema(
        summary="Create new notification template",
        description="Create a new notification template with specified parameters",
        request=TemplateCreateSerializer,
        responses={
            201: NotificationTemplateSerializer,
            400: "Bad Request - Validation errors",
        },
    ),
    retrieve=extend_schema(
        summary="Get notification template details",
        description="Retrieve detailed information about a specific notification template",
        responses={
            200: NotificationTemplateSerializer,
            404: "Template not found",
        },
    ),
    update=extend_schema(
        summary="Update notification template",
        description="Update an existing notification template",
        request=TemplateUpdateSerializer,
        responses={
            200: NotificationTemplateSerializer,
            400: "Bad Request - Validation errors",
            404: "Template not found",
        },
    ),
    destroy=extend_schema(
        summary="Delete notification template",
        description="Delete a notification template permanently",
        responses={
            204: "Template deleted successfully",
            404: "Template not found",
        },
    ),
)
class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notification templates.
    
    Provides CRUD operations for notification templates with proper
    validation and error handling.
    """
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    pagination_class = StandardResultsSetPagination
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        template_repository = DjangoNotificationTemplateRepository()
        self.template_service = NotificationTemplateService(template_repository)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return TemplateCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TemplateUpdateSerializer
        return NotificationTemplateSerializer
    
    def perform_create(self, serializer):
        """Create template using business service."""
        template_data = serializer.validated_data
        template = self.template_service.create_template(**template_data)
        serializer.instance = template
    
    def perform_update(self, serializer):
        """Update template using business service."""
        template_data = serializer.validated_data
        template = self.template_service.update_template(
            template_id=self.get_object().id,
            **template_data
        )
        serializer.instance = template
    
    def perform_destroy(self, instance):
        """Delete template using business service."""
        self.template_service.delete_template(instance.id)


@extend_schema_view(
    send=extend_schema(
        summary="Send notification",
        description="Send a notification using specified template and context",
        request=SendNotificationSerializer,
        responses={
            202: NotificationResponseSerializer,
            400: "Bad Request - Validation errors",
            404: "Template or user not found",
        },
    ),
    retrieve=extend_schema(
        summary="Get notification details",
        description="Retrieve detailed information about a specific notification",
        responses={
            200: NotificationLogSerializer,
            404: "Notification not found",
        },
    ),
    user_notifications=extend_schema(
        summary="List user notifications",
        description="Retrieve paginated list of notifications for a specific user",
        parameters=[
            OpenApiParameter(
                name='user_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='User ID to filter notifications'
            ),
        ],
        responses={200: NotificationLogSerializer(many=True)},
    ),
    update_status=extend_schema(
        summary="Update notification status",
        description="Update the status of a specific notification",
        request=NotificationStatusUpdateSerializer,
        responses={
            200: NotificationLogSerializer,
            400: "Bad Request - Invalid status",
            404: "Notification not found",
        },
    ),
)
class NotificationViewSet(viewsets.ViewSet):
    """
    ViewSet for notification operations.
    
    Handles sending notifications and retrieving notification history.
    """
    pagination_class = StandardResultsSetPagination
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize repositories
        template_repository = DjangoNotificationTemplateRepository()
        log_repository = DjangoNotificationLogRepository()
        preference_repository = DjangoUserPreferenceRepository()
        quota_repository = DjangoNotificationQuotaRepository()
        
        # Initialize services with dependencies
        template_service = NotificationTemplateService(template_repository)
        self.notification_service = NotificationService(
            template_service=template_service,
            log_repository=log_repository,
            preference_repository=preference_repository,
            quota_repository=quota_repository
        )
    
    @action(detail=False, methods=['post'], url_path='send')
    def send(self, request: Request) -> Response:
        """
        Send a notification.
        
        POST /api/v1/notifications/send
        """
        serializer = SendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            notification_log = self.notification_service.send_notification(
                user_id=serializer.validated_data['user_id'],
                template_name=serializer.validated_data['template_name'],
                context=serializer.validated_data.get('context', {}),
                notification_type=serializer.validated_data.get('notification_type'),
                priority=serializer.validated_data.get('priority', 'normal'),
            )
            
            response_serializer = NotificationResponseSerializer({
                'id': notification_log.id,
                'status': notification_log.status,
                'message': 'Notification queued for delivery',
                'user_id': notification_log.user_id,
                'template_name': serializer.validated_data['template_name'],
                'notification_type': notification_log.type,
            })
            
            return Response(
                response_serializer.data,
                status=status.HTTP_202_ACCEPTED
            )
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def retrieve(self, request: Request, pk: str = None) -> Response:
        """
        Get notification details.
        
        GET /api/v1/notifications/{id}
        """
        try:
            notification = get_object_or_404(NotificationLog, id=pk)
            serializer = NotificationLogSerializer(notification)
            return Response(serializer.data)
        except Http404:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'], url_path='user/(?P<user_id>[^/.]+)')
    def user_notifications(self, request: Request, user_id: str = None) -> Response:
        """
        List user notifications.
        
        GET /api/v1/notifications/user/{user_id}
        """
        try:
            notifications = NotificationLog.objects.filter(
                user_id=user_id
            ).order_by('-created_at')
            
            # Apply pagination
            paginator = StandardResultsSetPagination()
            page = paginator.paginate_queryset(notifications, request)
            
            if page is not None:
                serializer = NotificationLogSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)
            
            serializer = NotificationLogSerializer(notifications, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['put'], url_path='status')
    def update_status(self, request: Request, pk: str = None) -> Response:
        """
        Update notification status.
        
        PUT /api/v1/notifications/{id}/status
        """
        try:
            notification = get_object_or_404(NotificationLog, id=pk)
            serializer = NotificationStatusUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Update status using business service
            updated_notification = self.notification_service.update_notification_status(
                notification_id=notification.id,
                new_status=serializer.validated_data['status'],
                error_message=serializer.validated_data.get('error_message'),
            )
            
            response_serializer = NotificationLogSerializer(updated_notification)
            return Response(response_serializer.data)
            
        except Http404:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema_view(
    get_preferences=extend_schema(
        summary="Get user preferences",
        description="Retrieve notification preferences for a specific user",
        parameters=[
            OpenApiParameter(
                name='user_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='User ID to get preferences for'
            ),
        ],
        responses={
            200: UserPreferenceSerializer,
            404: "User preferences not found",
        },
    ),
    update_preferences=extend_schema(
        summary="Update user preferences",
        description="Update notification preferences for a specific user",
        request=PreferenceUpdateSerializer,
        responses={
            200: UserPreferenceSerializer,
            400: "Bad Request - Validation errors",
        },
    ),
)
class UserPreferenceViewSet(viewsets.ViewSet):
    """
    ViewSet for user notification preferences.
    
    Handles getting and updating user notification preferences.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        preference_repository = DjangoUserPreferenceRepository()
        self.preference_service = UserPreferenceService(preference_repository)
    
    @action(detail=False, methods=['get'], url_path='user/(?P<user_id>[^/.]+)')
    def get_preferences(self, request: Request, user_id: str = None) -> Response:
        """
        Get user preferences.
        
        GET /api/v1/preferences/user/{user_id}
        """
        try:
            preferences = self.preference_service.get_user_preferences(int(user_id))
            serializer = UserPreferenceSerializer(preferences)
            return Response(serializer.data)
            
        except UserPreference.DoesNotExist:
            # Create default preferences if they don't exist
            preferences = self.preference_service.get_or_create_preferences(int(user_id))
            serializer = UserPreferenceSerializer(preferences)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['put'], url_path='user/(?P<user_id>[^/.]+)')
    def update_preferences(self, request: Request, user_id: str = None) -> Response:
        """
        Update user preferences.
        
        PUT /api/v1/preferences/user/{user_id}
        """
        try:
            serializer = PreferenceUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            preferences = self.preference_service.update_user_preferences(
                user_id=int(user_id),
                **serializer.validated_data
            )
            
            response_serializer = UserPreferenceSerializer(preferences)
            return Response(response_serializer.data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema_view(
    health=extend_schema(
        summary="Health check endpoint",
        description="Check the health status of the notification service",
        responses={200: "Service is healthy"},
    ),
    metrics=extend_schema(
        summary="Service metrics endpoint",
        description="Get service metrics for monitoring",
        responses={200: "Metrics data"},
    ),
)
class HealthViewSet(viewsets.ViewSet):
    """
    ViewSet for health checks and monitoring.
    """
    
    @action(detail=False, methods=['get'])
    def health(self, request: Request) -> Response:
        """
        Health check endpoint.
        
        GET /api/v1/health
        """
        # TODO: Add actual health checks for database, cache, message queue
        health_status = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'service': 'notification-service',
            'version': '1.0.0',
            'checks': {
                'database': 'ok',
                'cache': 'ok',
                'message_queue': 'ok',
            }
        }
        return Response(health_status)
    
    @action(detail=False, methods=['get'])
    def metrics(self, request: Request) -> Response:
        """
        Service metrics endpoint.
        
        GET /api/v1/metrics
        """
        # TODO: Add actual metrics collection
        metrics = {
            'notifications_sent_total': 0,
            'notifications_failed_total': 0,
            'templates_count': NotificationTemplate.objects.count(),
            'active_users': UserPreference.objects.count(),
        }
        return Response(metrics)

