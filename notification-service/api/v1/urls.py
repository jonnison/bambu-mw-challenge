"""
URL configuration for API v1 endpoints.
Provides RESTful routing for all notification service endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationTemplateViewSet,
    NotificationViewSet,
    UserPreferenceViewSet,
    HealthViewSet,
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'templates', NotificationTemplateViewSet, basename='template')
router.register(r'preferences', UserPreferenceViewSet, basename='preference')
router.register(r'health', HealthViewSet, basename='health')

# Custom URL patterns for notification endpoints
notification_patterns = [
    path('send/', NotificationViewSet.as_view({'post': 'send'}), name='send-notification'),
    path('<int:pk>/', NotificationViewSet.as_view({'get': 'retrieve'}), name='notification-detail'),
    path('<int:pk>/status/', NotificationViewSet.as_view({'put': 'update_status'}), name='notification-status'),
    path('user/<int:user_id>/', NotificationViewSet.as_view({'get': 'user_notifications'}), name='user-notifications'),
]

# Main URL patterns
urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Custom notification endpoints
    path('notifications/', include(notification_patterns)),
]