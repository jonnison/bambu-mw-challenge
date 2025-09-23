"""
Infrastructure URL configuration for monitoring endpoints.
"""
from django.urls import path
from django.http import JsonResponse

def prometheus_metrics(request):
    """Simple metrics endpoint."""
    return JsonResponse({'metrics': 'placeholder'})

urlpatterns = [
    path('', prometheus_metrics, name='metrics'),
]