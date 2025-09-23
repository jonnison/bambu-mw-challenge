# Notification Service Migration Plan

## Executive Summary

This document outlines a comprehensive migration plan for extracting the notification service from the MyBambu Django monolith into an independent microservice. The migration addresses tight coupling, performance issues, and scalability concerns while ensuring zero downtime and maintaining backward compatibility.

## Current State Analysis

### Existing Architecture Issues

#### 1. Tight Coupling Problems
- **Direct Model References**: Notification service directly accesses `UserProfile` and `Transaction` models from other apps
- **Shared Database**: All services share the same PostgreSQL database with no clear boundaries
- **Synchronous Dependencies**: Direct method calls between services without proper abstraction

#### 2. Performance Bottlenecks
- **N+1 Query Problems**: `get_user_notifications` method suffers from N+1 queries when loading templates
- **No Pagination**: Methods like `get_user_notifications` load all data without pagination
- **No Caching**: User preferences and templates are fetched from database on every request
- **Blocking Operations**: Synchronous notification sending blocks request threads

#### 3. Scalability Limitations
- **No Horizontal Scaling**: Monolithic deployment prevents independent scaling of notification service
- **No Circuit Breaker**: External provider failures can cascade to entire system
- **No Retry Logic**: Failed notifications are not automatically retried
- **No Rate Limiting**: Bulk operations can overwhelm external providers

#### 4. Operational Concerns
- **No Health Checks**: Service health cannot be monitored independently
- **Limited Observability**: No dedicated metrics for notification operations
- **No Graceful Shutdown**: Service cannot be stopped without losing in-flight requests

### Current Data Model

```sql
-- Current monolith tables that need migration
notifications_notificationtemplate (
    id, name, subject, body, type, variables, created_at, updated_at
)

notifications_notificationlog (
    id, user_id, template_id, type, status, sent_at, error_message, metadata, created_at
)

notifications_userpreference (
    id, user_id, email_enabled, sms_enabled, push_enabled, 
    quiet_hours_start, quiet_hours_end, max_emails_per_day, max_sms_per_day, updated_at
)
```

### External Dependencies
- **Email Provider**: Currently using simulated EmailProvider (should be AWS SES/SendGrid)
- **SMS Provider**: Currently using simulated SMSProvider (should be Twilio)
- **Push Provider**: Currently using simulated PushProvider (should be Firebase)
- **Celery**: For async task processing
- **Redis**: For Celery message broker

## Target Architecture

### Microservice Design Principles

#### 1. Service Boundaries
- **Single Responsibility**: Handle only notification-related operations
- **Data Ownership**: Own notification templates, logs, and user preferences
- **API-First**: Communicate only through well-defined REST/GraphQL APIs
- **Event-Driven**: Use async messaging for cross-service communication

#### 2. Hexagonal Architecture (Ports & Adapters)
```
notification-service/
├── domain/                     # Core business logic
│   ├── models/                # Domain entities
│   ├── services/              # Business services
│   └── repositories/          # Data access interfaces
├── application/               # Application layer
│   ├── commands/              # Command handlers
│   ├── queries/               # Query handlers
│   └── events/                # Event handlers
├── infrastructure/            # External concerns
│   ├── api/                   # REST API controllers
│   ├── database/              # Database implementations
│   ├── providers/             # External service adapters
│   └── messaging/             # Event publishing/consuming
└── config/                    # Configuration and startup
```

#### 3. Technology Stack
- **Framework**: Django (with Django REST Framework for APIs)
- **Database**: PostgreSQL (dedicated instance)
- **Message Broker**: RabbitMQ (for events and async messaging)
- **Caching**: Redis (for templates and preferences)
- **Testing**: pytest-django + pytest-asyncio
- **Documentation**: Django REST Framework browsable API + drf-spectacular (OpenAPI)
- **Monitoring**: OpenTelemetry + Prometheus + Grafana
- **Logging**: Structured logging with correlation IDs and OpenTelemetry tracing

## Migration Strategy

### Phase 1: Preparation & Setup

#### Step 1.1: Infrastructure Setup

1. **Create New Repository**
   ```pseudocode
   CREATE new Git repository for notification-service
   INITIALIZE project structure according to requirements.md
   SET UP version control and branching strategy
   ```

2. **Setup Development Environment**
   ```pseudocode
   CONFIGURE Docker containers for:
     - PostgreSQL database for notification data
     - Redis for caching and session storage
     - RabbitMQ for message brokering
     - Application container for Django service
   
   DEFINE environment variables for:
     - Database connections
     - Message broker settings
     - Observability endpoints (OpenTelemetry)
   ```

3. **Setup Project Structure (Following Requirements.md)**
   ```pseudocode
   notification-service/
   ├── Django project configuration
   ├── api/                     # API layer with routes, schemas, middleware
   ├── core/                    # Domain models, business services, repositories
   ├── adapters/                # External provider integrations (email/SMS/push)
   ├── events/                  # Event publishing and consumption
   ├── database/                # Database configuration and migrations
   ├── tests/                   # Unit, integration, and performance tests
   └── infrastructure/          # Monitoring, logging, deployment configs
   ```
           ├── __init__.py
           ├── telemetry.py
           └── middleware.py
   ```

#### Step 1.2: Database Design

1. **Create Migration Schema**
   ```sql
   -- New notification service database schema
   CREATE TABLE notification_templates (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       name VARCHAR(100) UNIQUE NOT NULL,
       subject VARCHAR(255),
       body TEXT NOT NULL,
       type VARCHAR(20) CHECK (type IN ('email', 'sms', 'push')) NOT NULL,
       variables JSONB DEFAULT '{}',
       is_active BOOLEAN DEFAULT true,
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       version INTEGER DEFAULT 1
   );

   CREATE TABLE notification_logs (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       user_id INTEGER NOT NULL,
       template_id UUID REFERENCES notification_templates(id),
       type VARCHAR(20) CHECK (type IN ('email', 'sms', 'push')) NOT NULL,
       status VARCHAR(20) CHECK (status IN ('pending', 'sent', 'failed', 'bounced', 'retry')) DEFAULT 'pending',
       recipient VARCHAR(255) NOT NULL,
       subject VARCHAR(255),
       content TEXT,
       provider_response JSONB DEFAULT '{}',
       sent_at TIMESTAMP WITH TIME ZONE,
       error_message TEXT,
       retry_count INTEGER DEFAULT 0,
       max_retries INTEGER DEFAULT 3,
       metadata JSONB DEFAULT '{}',
       correlation_id UUID,
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
   );

   CREATE TABLE user_preferences (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       user_id INTEGER UNIQUE NOT NULL,
       email_enabled BOOLEAN DEFAULT true,
       sms_enabled BOOLEAN DEFAULT true,
       push_enabled BOOLEAN DEFAULT true,
       quiet_hours_start TIME,
       quiet_hours_end TIME,
       timezone VARCHAR(50) DEFAULT 'UTC',
       max_emails_per_day INTEGER DEFAULT 10,
       max_sms_per_day INTEGER DEFAULT 5,
       language_code VARCHAR(10) DEFAULT 'en',
       updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
   );

   -- Indexes for performance
   CREATE INDEX idx_notification_logs_user_id_created_at ON notification_logs(user_id, created_at DESC);
   CREATE INDEX idx_notification_logs_status_type ON notification_logs(status, type);
   CREATE INDEX idx_notification_logs_correlation_id ON notification_logs(correlation_id);
   CREATE INDEX idx_notification_logs_retry ON notification_logs(status, retry_count) WHERE status = 'failed';
   ```

#### Step 1.3: API Design

1. **Define API Endpoints Structure (Following Requirements)**

   **Core Notification Endpoints:**
   
   **POST /api/v1/notifications/send/**
   - Description: Queue a notification for asynchronous processing
   - Request: user_id, template_name, context, priority, correlation_id (optional)
   - Response: 202 Accepted - notification ID and queued status
   - Errors: 400 (invalid template/user), 403 (disabled notification type), 500 (server error)

   **GET /api/v1/notifications/{notification_id}/**
   - Description: Retrieve details of a specific notification
   - Response: 200 OK - notification details (id, status, recipient, timestamps, metadata)
   - Errors: 404 (not found), 500 (server error)

   **GET /api/v1/notifications/user/{user_id}/**
   - Description: Get notification history for a specific user
   - Query params: limit, offset, status, type, date_from, date_to
   - Response: 200 OK - paginated list of notifications
   - Errors: 400 (invalid parameters), 500 (server error)

   **PUT /api/v1/notifications/{id}/status**
   - Description: Update notification status (mark as read/unread, etc.)
   - Request: status, updated_by (optional)
   - Response: 200 OK - updated notification with new status
   - Errors: 404 (notification not found), 400 (invalid status), 403 (unauthorized), 500 (server error)

   **Template Management Endpoints:**

   **GET /api/v1/templates/**
   - Description: List all available notification templates
   - Query params: type, active_only, search, limit, offset
   - Response: 200 OK - paginated list of templates with metadata
   - Errors: 400 (invalid parameters), 500 (server error)

   **POST /api/v1/templates**
   - Description: Create a new notification template
   - Request: name, subject, body, type, variables, active (optional)
   - Response: 201 Created - created template with ID and metadata
   - Errors: 400 (validation failed), 409 (template name already exists), 403 (unauthorized), 500 (server error)

   **GET /api/v1/templates/{template_name}/**
   - Description: Get specific template details
   - Response: 200 OK - template structure and variables
   - Errors: 404 (template not found), 500 (server error)

   **PUT /api/v1/templates/{id}**
   - Description: Update an existing notification template
   - Request: subject, body, variables, active (optional fields)
   - Response: 200 OK - updated template with metadata
   - Errors: 404 (template not found), 400 (validation failed), 403 (unauthorized), 500 (server error)

   **DELETE /api/v1/templates/{id}**
   - Description: Delete a notification template (soft delete to preserve history)
   - Response: 204 No Content - template marked as deleted
   - Errors: 404 (template not found), 409 (template in use), 403 (unauthorized), 500 (server error)

   **User Preference Endpoints:**

   **GET /api/v1/preferences/{user_id}/**
   - Description: Get user notification preferences
   - Response: 200 OK - user preference settings

   **PUT /api/v1/preferences/{user_id}/**
   - Description: Update user notification preferences
   - Request: email_enabled, sms_enabled, push_enabled, quiet_hours, etc.
   - Response: 200 OK - updated preferences

   **Health & Monitoring Endpoints:**

   **GET /api/v1/health/**
   - Description: Service health check
   - Response: 200 OK - service status, database connectivity, dependencies

   **GET /api/v1/metrics/**
   - Description: Service metrics for monitoring
   - Response: 200 OK - notification counts, error rates, performance metrics

2. **API Design Specifications**

   **Pagination Implementation:**
   ```json
   // Standard pagination response format
   {
     "data": [...],
     "pagination": {
       "page": 1,
       "per_page": 20,
       "total_pages": 15,
       "total_count": 284,
       "has_next": true,
       "has_previous": false
     },
     "links": {
       "first": "/api/v1/notifications/user/123?page=1&per_page=20",
       "last": "/api/v1/notifications/user/123?page=15&per_page=20",
       "next": "/api/v1/notifications/user/123?page=2&per_page=20",
       "previous": null
     }
   }
   ```

   **Pagination Headers:**
   ```
   X-Total-Count: 284
   X-Page: 1
   X-Per-Page: 20
   X-Total-Pages: 15
   Link: </api/v1/notifications/user/123?page=1&per_page=20>; rel="first",
         </api/v1/notifications/user/123?page=15&per_page=20>; rel="last",
         </api/v1/notifications/user/123?page=2&per_page=20>; rel="next"
   ```

   **Request Validation:**
   - All datetime fields must be ISO 8601 format
   - Pagination: page >= 1, per_page between 1-100 (default: 20)
   - Search terms: minimum 3 characters, alphanumeric + spaces only
   - Template variables: JSON schema validation for complex objects
   - User IDs: positive integers only

   **Rate Limiting Implementation:**
   
   **Rate Limit Tiers:**
   ```
   # Per-endpoint rate limits (requests per minute)
   POST /api/v1/notifications/send: 100/min per user, 1000/min per API key
   GET /api/v1/notifications/*: 300/min per user, 3000/min per API key  
   POST/PUT/DELETE /api/v1/templates/*: 20/min per user, 200/min per API key
   GET /api/v1/templates/*: 100/min per user, 1000/min per API key
   ```

   **Rate Limiting Headers:**
   ```
   X-RateLimit-Limit: 100           # Total requests allowed per window
   X-RateLimit-Remaining: 87        # Requests remaining in current window
   X-RateLimit-Reset: 1640995200    # Unix timestamp when window resets
   X-RateLimit-Window: 60           # Window size in seconds
   Retry-After: 23                  # Seconds to wait if rate limited (429 only)
   ```

   **Rate Limit Responses:**
   ```json
   // 429 Too Many Requests
   {
     "error": "rate_limit_exceeded",
     "message": "Rate limit exceeded. Try again in 23 seconds.",
     "retry_after": 23,
     "limit": 100,
     "window": 60
   }
   ```

   **API Versioning Strategy:**

   **Versioning Approach:**
   - **URL Path Versioning**: `/api/v1/`, `/api/v2/` for major versions
   - **Header Versioning**: `API-Version: 2024-09-22` for minor versions and features
   - **Backward Compatibility**: Maintain previous version for minimum 12 months
   - **Semantic Versioning**: Major.Minor.Patch (e.g., v1.2.3)

   **Version Support Policy:**
   ```
   Version Lifecycle:
   - v1.x: Current stable (full support)
   - v0.x: Deprecated (security fixes only, 6 months EOL)
   - Future v2.x: Planning phase
   ```

   **Deprecation Process:**
   1. **Announcement**: 6 months advance notice via headers and documentation
   2. **Warning Headers**: `Deprecation: true`, `Sunset: 2025-03-22T00:00:00Z`
   3. **Migration Guide**: Detailed upgrade path documentation
   4. **Sunset**: Remove deprecated endpoints after support period

   **Version Headers:**
   ```
   API-Version: v1                          # Current version used
   API-Supported-Versions: v1,v2           # All supported versions
   API-Latest-Version: v2                  # Latest available version
   Deprecation: true                       # If endpoint is deprecated
   Sunset: 2025-03-22T00:00:00Z           # When deprecated endpoint will be removed
   ```

   **Breaking vs Non-Breaking Changes:**
   ```
   Non-Breaking (Minor version):
   - Adding new optional fields
   - Adding new endpoints
   - Adding new enum values
   - Performance improvements

   Breaking (Major version):
   - Removing fields or endpoints
   - Changing field types
   - Modifying response structure
   - Changing authentication requirements
   ```

### Phase 2: Data Migration Strategy

#### Step 2.1: Dual-Write Implementation

1. **Create Data Migration Service**
   ```python
   # src/infrastructure/migration/data_migrator.py
   import asyncio
   from typing import Dict, List
   from sqlalchemy import create_engine
   from sqlalchemy.orm import sessionmaker

   class DataMigrator:
       def __init__(self, monolith_db_url: str, microservice_db_url: str):
           self.monolith_engine = create_engine(monolith_db_url)
           self.microservice_engine = create_engine(microservice_db_url)
           
       async def migrate_templates(self) -> Dict[str, int]:
           """Migrate notification templates from monolith to microservice"""
           # Implementation for template migration
           pass
           
       async def migrate_user_preferences(self) -> Dict[str, int]:
           """Migrate user preferences with proper validation"""
           # Implementation for preferences migration
           pass
           
       async def migrate_notification_logs(self, batch_size: int = 1000) -> Dict[str, int]:
           """Migrate historical notification logs in batches"""
           # Implementation for log migration with batching
           pass
   ```

2. **Implement Dual-Write Pattern**
   ```python
   # In the monolith - temporary dual-write adapter
   class NotificationDualWriter:
       def __init__(self):
           self.monolith_service = NotificationService()
           self.microservice_client = NotificationServiceClient()
           
       async def send_notification(self, user_id: int, template_name: str, context: dict):
           """Write to both monolith and microservice during transition"""
           
           # Primary write to monolith (for rollback capability)
           monolith_result = self.monolith_service.send_notification(user_id, template_name, context)
           
           # Secondary write to microservice (for validation)
           try:
               microservice_result = await self.microservice_client.send_notification({
                   'user_id': user_id,
                   'template_name': template_name,
                   'context': context
               })
               
               # Log discrepancies for monitoring
               if monolith_result != microservice_result.success:
                   logger.warning(f"Dual-write mismatch: monolith={monolith_result}, microservice={microservice_result.success}")
                   
           except Exception as e:
               logger.error(f"Microservice write failed: {e}")
               # Continue with monolith result
               
           return monolith_result
   ```

#### Step 2.2: Data Validation & Consistency

1. **Create Data Validation Scripts**
   ```python
   # scripts/validate_migration.py
   import asyncio
   from dataclasses import dataclass
   from typing import List, Dict

   @dataclass
   class ValidationResult:
       table_name: str
       monolith_count: int
       microservice_count: int
       missing_records: List[str]
       inconsistent_records: List[str]
       
   class MigrationValidator:
       async def validate_templates(self) -> ValidationResult:
           """Compare templates between monolith and microservice"""
           # Implementation
           pass
           
       async def validate_user_preferences(self) -> ValidationResult:
           """Validate user preferences migration"""
           # Implementation
           pass
           
       async def validate_notification_logs(self, sample_size: int = 10000) -> ValidationResult:
           """Validate sample of notification logs"""
           # Implementation
           pass
           
       async def generate_migration_report(self) -> Dict[str, ValidationResult]:
           """Generate comprehensive migration validation report"""
           results = {}
           results['templates'] = await self.validate_templates()
           results['preferences'] = await self.validate_user_preferences()
           results['logs'] = await self.validate_notification_logs()
           return results
   ```

### Phase 3: Service Implementation

#### Step 3.1: Core Domain Implementation

1. **Core Domain Models (Following Requirements Structure)**
   ```python
   # core/models.py (Domain models as per requirements)
   import uuid
   from django.db import models
   from django.contrib.postgres.fields import JSONField

   class NotificationTemplate(models.Model):
       NOTIFICATION_TYPES = [
           ('email', 'Email'),
           ('sms', 'SMS'),
           ('push', 'Push Notification'),
       ]
       
       id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
       name = models.CharField(max_length=100, unique=True)
       subject = models.CharField(max_length=255, blank=True)
       body = models.TextField()
       type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
       variables = JSONField(default=dict, blank=True)
       is_active = models.BooleanField(default=True)
       created_at = models.DateTimeField(auto_now_add=True)
       updated_at = models.DateTimeField(auto_now=True)
       version = models.IntegerField(default=1)

       class Meta:
           db_table = 'notification_templates'
           indexes = [
               models.Index(fields=['name', 'is_active']),
               models.Index(fields=['type', 'is_active']),
           ]

       def __str__(self):
           return f"{self.name} ({self.type})"

   class NotificationLog(models.Model):
       STATUS_CHOICES = [
           ('pending', 'Pending'),
           ('sent', 'Sent'),
           ('failed', 'Failed'),
           ('bounced', 'Bounced'),
           ('retry', 'Retry'),
       ]
       
       id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
       user_id = models.IntegerField()
       template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True)
       type = models.CharField(max_length=20, choices=NotificationTemplate.NOTIFICATION_TYPES)
       status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
       recipient = models.CharField(max_length=255)
       subject = models.CharField(max_length=255, blank=True)
       content = models.TextField()
       provider_response = JSONField(default=dict)
       sent_at = models.DateTimeField(null=True, blank=True)
       error_message = models.TextField(blank=True)
       retry_count = models.IntegerField(default=0)
       max_retries = models.IntegerField(default=3)
       metadata = JSONField(default=dict)
       correlation_id = models.UUIDField(null=True, blank=True)
       created_at = models.DateTimeField(auto_now_add=True)

       class Meta:
           db_table = 'notification_logs'
           indexes = [
               models.Index(fields=['user_id', '-created_at']),
               models.Index(fields=['status', 'type']),
               models.Index(fields=['correlation_id']),
               models.Index(fields=['status', 'retry_count']),
           ]

   class UserPreference(models.Model):
       id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
       user_id = models.IntegerField(unique=True)
       email_enabled = models.BooleanField(default=True)
       sms_enabled = models.BooleanField(default=True)
       push_enabled = models.BooleanField(default=True)
       quiet_hours_start = models.TimeField(null=True, blank=True)
       quiet_hours_end = models.TimeField(null=True, blank=True)
       timezone = models.CharField(max_length=50, default='UTC')
       max_emails_per_day = models.IntegerField(default=10)
       max_sms_per_day = models.IntegerField(default=5)
       language_code = models.CharField(max_length=10, default='en')
       updated_at = models.DateTimeField(auto_now=True)

       class Meta:
           db_table = 'user_preferences'

       def __str__(self):
           return f"Preferences for user {self.user_id}"
   ```

2. **Core Business Logic (Following Requirements Structure)**
   ```python
   # core/services.py (Business logic as per requirements)
   from django.utils import timezone
   from django.core.cache import cache
   from opentelemetry import trace
   from typing import Dict, Any, Optional
   import logging

   from .models import NotificationTemplate, NotificationLog, UserPreference
   from .repositories import NotificationRepository, TemplateRepository, PreferenceRepository
   from events.publisher import EventPublisher
   from infrastructure.monitoring.telemetry import metrics

   logger = logging.getLogger(__name__)
   tracer = trace.get_tracer(__name__)

   class NotificationService:
       """Core business service for notification operations"""
       
       def __init__(self):
           self.notification_repo = NotificationRepository()
           self.template_repo = TemplateRepository()
           self.preference_repo = PreferenceRepository()
           self.event_publisher = EventPublisher()
           
       @tracer.start_as_current_span("send_notification")
       def send_notification(self, 
                           user_id: int, 
                           template_name: str, 
                           context: Dict[str, Any],
                           correlation_id: Optional[str] = None) -> NotificationLog:
           """Send a notification with proper business logic"""
           
           span = trace.get_current_span()
           span.set_attributes({
               "notification.user_id": user_id,
               "notification.template_name": template_name,
               "notification.correlation_id": correlation_id or "none"
           })
           
           start_time = timezone.now()
           
           try:
               # 1. Get template via repository
               template = self.template_repo.get_by_name(template_name)
               if not template or not template.is_active:
                   metrics.counter('notification_errors_total', {'error_type': 'invalid_template'}).inc()
                   raise InvalidTemplateError(f"Template {template_name} not found or inactive")
               
               # 2. Get user preferences via repository
               preferences = self.preference_repo.get_by_user_id(user_id)
               if not self._is_notification_allowed(template.type, preferences):
                   metrics.counter('notification_blocked_total', {'type': template.type}).inc()
                   raise NotificationBlockedError(f"User {user_id} has disabled {template.type} notifications")
               
               # 3. Render content
               subject = self._render_template(template.subject, context) if template.subject else None
               content = self._render_template(template.body, context)
               
               # 4. Determine recipient
               recipient = self._get_recipient(user_id, template.type)
               
               # 5. Create notification via repository
               notification = self.notification_repo.create(
                   user_id=user_id,
                   template=template,
                   type=template.type,
                   status='pending',
                   recipient=recipient,
                   subject=subject,
                   content=content,
                   metadata=context,
                   correlation_id=correlation_id
               )
               
               # 6. Record metrics
               processing_time = (timezone.now() - start_time).total_seconds()
               metrics.histogram('notification_processing_duration_seconds', 
                               {'type': template.type}).observe(processing_time)
               metrics.counter('notification_created_total', {'type': template.type}).inc()
               
               # 7. Publish event for async processing
               self.event_publisher.publish_notification_requested(notification)
               
               span.set_attribute("notification.id", str(notification.id))
               span.set_status(trace.Status(trace.StatusCode.OK))
               
               return notification
               
           except Exception as e:
               metrics.counter('notification_errors_total', {'error_type': type(e).__name__}).inc()
               span.record_exception(e)
               span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
               logger.exception(f"Failed to send notification: {e}")
               raise
               
       def _is_notification_allowed(self, notification_type: str, preferences: UserPreference) -> bool:
           """Check if notification type is allowed for user"""
           if notification_type == 'email':
               return preferences.email_enabled
           elif notification_type == 'sms':
               return preferences.sms_enabled
           elif notification_type == 'push':
               return preferences.push_enabled
           return False
           
       def _render_template(self, template_str: str, context: Dict[str, Any]) -> str:
           """Simple template rendering - replaces {key} with values"""
           if not template_str:
               return ""
           
           result = template_str
           for key, value in context.items():
               result = result.replace(f'{{{key}}}', str(value))
           return result
           
       def _get_recipient(self, user_id: int, notification_type: str) -> str:
           """Get recipient address based on notification type"""
           # This would typically fetch from user service
           # For now, return mock data
           if notification_type == 'email':
               return f"user{user_id}@example.com"
           elif notification_type == 'sms':
               return f"+1555000{user_id:04d}"
           elif notification_type == 'push':
               return f"device_token_{user_id}"
           return ""

   # core/repositories.py (Data access layer as per requirements)
   from typing import Optional, List
   from django.core.cache import cache
   from .models import NotificationTemplate, NotificationLog, UserPreference

   class TemplateRepository:
       """Repository for notification template operations"""
       
       def get_by_name(self, name: str) -> Optional[NotificationTemplate]:
           """Get template by name with caching"""
           cache_key = f"notification_template:{name}"
           template = cache.get(cache_key)
           
           if template is None:
               try:
                   template = NotificationTemplate.objects.get(name=name, is_active=True)
                   cache.set(cache_key, template, timeout=300)  # 5 minutes
               except NotificationTemplate.DoesNotExist:
                   return None
                   
           return template
           
       def get_all_active(self) -> List[NotificationTemplate]:
           """Get all active templates"""
           return NotificationTemplate.objects.filter(is_active=True)
           
       def create(self, **kwargs) -> NotificationTemplate:
           """Create new template"""
           return NotificationTemplate.objects.create(**kwargs)

   class PreferenceRepository:
       """Repository for user preference operations"""
       
       def get_by_user_id(self, user_id: int) -> UserPreference:
           """Get user preferences by user ID with caching"""
           cache_key = f"user_preferences:{user_id}"
           preferences = cache.get(cache_key)
           
           if preferences is None:
               preferences, created = UserPreference.objects.get_or_create(
                   user_id=user_id,
                   defaults={
                       'email_enabled': True,
                       'sms_enabled': True,
                       'push_enabled': True
                   }
               )
               cache.set(cache_key, preferences, timeout=600)  # 10 minutes
               
           return preferences
           
       def update_preferences(self, user_id: int, **kwargs) -> UserPreference:
           """Update user preferences"""
           preferences = self.get_by_user_id(user_id)
           for key, value in kwargs.items():
               setattr(preferences, key, value)
           preferences.save()
           
           # Invalidate cache
           cache_key = f"user_preferences:{user_id}"
           cache.delete(cache_key)
           
           return preferences

   class NotificationRepository:
       """Repository for notification log operations"""
       
       def create(self, **kwargs) -> NotificationLog:
           """Create new notification log"""
           return NotificationLog.objects.create(**kwargs)
           
       def get_by_id(self, notification_id: str) -> Optional[NotificationLog]:
           """Get notification by ID"""
           try:
               return NotificationLog.objects.get(id=notification_id)
           except NotificationLog.DoesNotExist:
               return None
               
       def get_by_user_id(self, user_id: int, limit: int = 50) -> List[NotificationLog]:
           """Get notifications for user with pagination"""
           return NotificationLog.objects.filter(
               user_id=user_id
           ).order_by('-created_at')[:limit]
           
       def update_status(self, notification_id: str, status: str, **kwargs) -> NotificationLog:
           """Update notification status"""
           notification = self.get_by_id(notification_id)
           if notification:
               notification.status = status
               for key, value in kwargs.items():
                   setattr(notification, key, value)
               notification.save()
           return notification

   # Exception classes
   class InvalidTemplateError(Exception):
       pass

   class NotificationBlockedError(Exception):
       pass
   ```

#### Step 3.2: Infrastructure Implementation

1. **Provider Adapters (Following Requirements Structure)**
   ```python
   # adapters/email.py (Email provider integration as per requirements)
   from abc import ABC, abstractmethod
   import requests
   import logging
   from typing import Dict, Any
   from opentelemetry import trace
   from infrastructure.monitoring.telemetry import metrics

   logger = logging.getLogger(__name__)
   tracer = trace.get_tracer(__name__)

   class EmailProvider(ABC):
       @abstractmethod
       def send(self, to: str, subject: str, content: str) -> Dict[str, Any]:
           pass

   class SendGridEmailProvider(EmailProvider):
       def __init__(self, api_key: str, from_email: str):
           self.api_key = api_key
           self.from_email = from_email
           
       @tracer.start_as_current_span("sendgrid_send_email")
       def send(self, to: str, subject: str, content: str) -> Dict[str, Any]:
           span = trace.get_current_span()
           span.set_attributes({
               "email.provider": "sendgrid",
               "email.recipient": to,
               "email.subject": subject
           })
           
           headers = {
               'Authorization': f'Bearer {self.api_key}',
               'Content-Type': 'application/json'
           }
           
           payload = {
               'personalizations': [{'to': [{'email': to}]}],
               'from': {'email': self.from_email},
               'subject': subject,
               'content': [{'type': 'text/html', 'value': content}]
           }
           
           try:
               response = requests.post(
                   'https://api.sendgrid.com/v3/mail/send',
                   headers=headers,
                   json=payload,
                   timeout=30
               )
               
               if response.status_code == 202:
                   metrics.counter('email_sent_total', {'provider': 'sendgrid', 'status': 'success'}).inc()
                   return {
                       'success': True, 
                       'message_id': response.headers.get('X-Message-Id'),
                       'provider': 'sendgrid'
                   }
               else:
                   metrics.counter('email_sent_total', {'provider': 'sendgrid', 'status': 'failed'}).inc()
                   return {
                       'success': False, 
                       'error': response.text,
                       'status_code': response.status_code
                   }
                   
           except requests.RequestException as e:
               metrics.counter('email_sent_total', {'provider': 'sendgrid', 'status': 'error'}).inc()
               span.record_exception(e)
               span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
               logger.exception(f"SendGrid API error: {e}")
               return {'success': False, 'error': str(e)}

   # adapters/sms.py (SMS provider integration as per requirements)
   import requests
   from typing import Dict, Any
   from opentelemetry import trace

   tracer = trace.get_tracer(__name__)

   class SMSProvider(ABC):
       @abstractmethod
       def send(self, to: str, message: str) -> Dict[str, Any]:
           pass

   class TwilioSMSProvider(SMSProvider):
       def __init__(self, account_sid: str, auth_token: str, from_phone: str):
           self.account_sid = account_sid
           self.auth_token = auth_token
           self.from_phone = from_phone
           
       @tracer.start_as_current_span("twilio_send_sms")
       def send(self, to: str, message: str) -> Dict[str, Any]:
           span = trace.get_current_span()
           span.set_attributes({
               "sms.provider": "twilio",
               "sms.recipient": to
           })
           
           try:
               url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
               
               data = {
                   'From': self.from_phone,
                   'To': to,
                   'Body': message
               }
               
               response = requests.post(
                   url,
                   data=data,
                   auth=(self.account_sid, self.auth_token),
                   timeout=30
               )
               
               if response.status_code == 201:
                   result = response.json()
                   metrics.counter('sms_sent_total', {'provider': 'twilio', 'status': 'success'}).inc()
                   return {
                       'success': True,
                       'message_id': result.get('sid'),
                       'provider': 'twilio'
                   }
               else:
                   metrics.counter('sms_sent_total', {'provider': 'twilio', 'status': 'failed'}).inc()
                   return {
                       'success': False,
                       'error': response.text,
                       'status_code': response.status_code
                   }
                   
           except requests.RequestException as e:
               metrics.counter('sms_sent_total', {'provider': 'twilio', 'status': 'error'}).inc()
               span.record_exception(e)
               span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
               logger.exception(f"Twilio API error: {e}")
               return {'success': False, 'error': str(e)}

   # adapters/push.py (Push notification integration as per requirements)
   import requests
   from typing import Dict, Any
   from opentelemetry import trace

   tracer = trace.get_tracer(__name__)

   class PushProvider(ABC):
       @abstractmethod
       def send(self, device_token: str, title: str, message: str) -> Dict[str, Any]:
           pass

   class FirebasePushProvider(PushProvider):
       def __init__(self, server_key: str):
           self.server_key = server_key
           
       @tracer.start_as_current_span("firebase_send_push")
       def send(self, device_token: str, title: str, message: str) -> Dict[str, Any]:
           span = trace.get_current_span()
           span.set_attributes({
               "push.provider": "firebase",
               "push.device_token": device_token[:10] + "..."  # Truncate for privacy
           })
           
           headers = {
               'Authorization': f'key={self.server_key}',
               'Content-Type': 'application/json'
           }
           
           payload = {
               'to': device_token,
               'notification': {
                   'title': title,
                   'body': message
               },
               'data': {
                   'timestamp': timezone.now().isoformat()
               }
           }
           
           try:
               response = requests.post(
                   'https://fcm.googleapis.com/fcm/send',
                   headers=headers,
                   json=payload,
                   timeout=30
               )
               
               if response.status_code == 200:
                   result = response.json()
                   if result.get('success', 0) > 0:
                       metrics.counter('push_sent_total', {'provider': 'firebase', 'status': 'success'}).inc()
                       return {
                           'success': True,
                           'message_id': result.get('multicast_id'),
                           'provider': 'firebase'
                       }
                   else:
                       metrics.counter('push_sent_total', {'provider': 'firebase', 'status': 'failed'}).inc()
                       return {
                           'success': False,
                           'error': result.get('results', [{}])[0].get('error', 'Unknown error')
                       }
               else:
                   metrics.counter('push_sent_total', {'provider': 'firebase', 'status': 'failed'}).inc()
                   return {
                       'success': False,
                       'error': response.text,
                       'status_code': response.status_code
                   }
                   
           except requests.RequestException as e:
               metrics.counter('push_sent_total', {'provider': 'firebase', 'status': 'error'}).inc()
               span.record_exception(e)
               span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
               logger.exception(f"Firebase API error: {e}")
               return {'success': False, 'error': str(e)}

   # adapters/__init__.py (Factory pattern for provider selection)
   from django.conf import settings
   from .email import SendGridEmailProvider
   from .sms import TwilioSMSProvider
   from .push import FirebasePushProvider

   class ProviderFactory:
       @staticmethod
       def get_email_provider():
           return SendGridEmailProvider(
               api_key=settings.SENDGRID_API_KEY,
               from_email=settings.FROM_EMAIL
           )
           
       @staticmethod
       def get_sms_provider():
           return TwilioSMSProvider(
               account_sid=settings.TWILIO_ACCOUNT_SID,
               auth_token=settings.TWILIO_AUTH_TOKEN,
               from_phone=settings.TWILIO_FROM_PHONE
           )
           
       @staticmethod
       def get_push_provider():
           return FirebasePushProvider(
               server_key=settings.FIREBASE_SERVER_KEY
           )
   ```

2. **Circuit Breaker Implementation**
   ```python
   # infrastructure/resilience/circuit_breaker.py
   import time
   import threading
   from datetime import datetime, timedelta
   from enum import Enum
   from typing import Callable, Any
   from functools import wraps
   from opentelemetry import trace
   from infrastructure.monitoring.telemetry import metrics

   tracer = trace.get_tracer(__name__)

   class CircuitBreakerState(Enum):
       CLOSED = "closed"
       OPEN = "open"
       HALF_OPEN = "half_open"

   class CircuitBreaker:
       def __init__(self, 
                    failure_threshold: int = 5,
                    timeout_seconds: int = 60,
                    half_open_max_calls: int = 3):
           self.failure_threshold = failure_threshold
           self.timeout = timedelta(seconds=timeout_seconds)
           self.half_open_max_calls = half_open_max_calls
           
           self.failure_count = 0
           self.last_failure_time = None
           self.state = CircuitBreakerState.CLOSED
           self.half_open_calls = 0
           self._lock = threading.Lock()
           
       def __call__(self, func: Callable) -> Callable:
           @wraps(func)
           def wrapper(*args, **kwargs):
               return self.call(func, *args, **kwargs)
           return wrapper
           
       @tracer.start_as_current_span("circuit_breaker_call")
       def call(self, func: Callable, *args, **kwargs) -> Any:
           span = trace.get_current_span()
           span.set_attributes({
               "circuit_breaker.state": self.state.value,
               "circuit_breaker.failure_count": self.failure_count
           })
           
           with self._lock:
               if self.state == CircuitBreakerState.OPEN:
                   if self._should_attempt_reset():
                       self.state = CircuitBreakerState.HALF_OPEN
                       self.half_open_calls = 0
                       metrics.counter('circuit_breaker_state_changes_total', 
                                     {'from_state': 'open', 'to_state': 'half_open'}).inc()
                   else:
                       metrics.counter('circuit_breaker_calls_total', {'result': 'rejected'}).inc()
                       raise CircuitBreakerOpenError("Circuit breaker is open")
                       
               if self.state == CircuitBreakerState.HALF_OPEN:
                   if self.half_open_calls >= self.half_open_max_calls:
                       metrics.counter('circuit_breaker_calls_total', {'result': 'rejected'}).inc()
                       raise CircuitBreakerOpenError("Circuit breaker half-open limit exceeded")
                   self.half_open_calls += 1
                   
           try:
               result = func(*args, **kwargs)
               self._on_success()
               metrics.counter('circuit_breaker_calls_total', {'result': 'success'}).inc()
               span.set_status(trace.Status(trace.StatusCode.OK))
               return result
           except Exception as e:
               self._on_failure()
               metrics.counter('circuit_breaker_calls_total', {'result': 'failure'}).inc()
               span.record_exception(e)
               span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
               raise e
               
       def _should_attempt_reset(self) -> bool:
           return (self.last_failure_time and 
                   datetime.utcnow() - self.last_failure_time > self.timeout)
                   
       def _on_success(self):
           with self._lock:
               if self.state == CircuitBreakerState.HALF_OPEN:
                   metrics.counter('circuit_breaker_state_changes_total', 
                                 {'from_state': 'half_open', 'to_state': 'closed'}).inc()
               self.failure_count = 0
               self.state = CircuitBreakerState.CLOSED
               self.half_open_calls = 0
               
       def _on_failure(self):
           with self._lock:
               self.failure_count += 1
               self.last_failure_time = datetime.utcnow()
               
               if self.failure_count >= self.failure_threshold:
                   old_state = self.state.value
                   self.state = CircuitBreakerState.OPEN
                   metrics.counter('circuit_breaker_state_changes_total', 
                                 {'from_state': old_state, 'to_state': 'open'}).inc()

   class CircuitBreakerOpenError(Exception):
       pass
   ```

### Phase 4: API Layer & Integration

#### Step 4.1: API Implementation

1. **Database Layer (Following Requirements Structure)**
   ```python
   # database/connection.py (Database configuration as per requirements)
   import os
   from django.conf import settings
   from django.db import connections
   from django.core.cache import cache
   import logging

   logger = logging.getLogger(__name__)

   class DatabaseHealthChecker:
       """Database health and connection management"""
       
       @staticmethod
       def check_database_health():
           """Check database connection health"""
           try:
               from django.db import connection
               with connection.cursor() as cursor:
                   cursor.execute("SELECT 1")
                   return True
           except Exception as e:
               logger.error(f"Database health check failed: {e}")
               return False
               
       @staticmethod
       def get_connection_info():
           """Get database connection information"""
           from django.db import connection
           return {
               'vendor': connection.vendor,
               'database': connection.settings_dict.get('NAME'),
               'host': connection.settings_dict.get('HOST'),
               'port': connection.settings_dict.get('PORT'),
           }

   # database/migrations/ (Database migration files as per requirements)
   # This directory contains Django migration files
   # Example migration for initial notification service schema:

   # database/migrations/0001_initial.py
   from django.db import migrations, models
   import django.contrib.postgres.fields.jsonb
   import uuid

   class Migration(migrations.Migration):
       initial = True

       dependencies = []

       operations = [
           migrations.CreateModel(
               name='NotificationTemplate',
               fields=[
                   ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                   ('name', models.CharField(max_length=100, unique=True)),
                   ('subject', models.CharField(blank=True, max_length=255)),
                   ('body', models.TextField()),
                   ('type', models.CharField(choices=[('email', 'Email'), ('sms', 'SMS'), ('push', 'Push Notification')], max_length=20)),
                   ('variables', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict)),
                   ('is_active', models.BooleanField(default=True)),
                   ('created_at', models.DateTimeField(auto_now_add=True)),
                   ('updated_at', models.DateTimeField(auto_now=True)),
                   ('version', models.IntegerField(default=1)),
               ],
               options={
                   'db_table': 'notification_templates',
               },
           ),
           migrations.CreateModel(
               name='UserPreference',
               fields=[
                   ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                   ('user_id', models.IntegerField(unique=True)),
                   ('email_enabled', models.BooleanField(default=True)),
                   ('sms_enabled', models.BooleanField(default=True)),
                   ('push_enabled', models.BooleanField(default=True)),
                   ('quiet_hours_start', models.TimeField(blank=True, null=True)),
                   ('quiet_hours_end', models.TimeField(blank=True, null=True)),
                   ('timezone', models.CharField(default='UTC', max_length=50)),
                   ('max_emails_per_day', models.IntegerField(default=10)),
                   ('max_sms_per_day', models.IntegerField(default=5)),
                   ('language_code', models.CharField(default='en', max_length=10)),
                   ('updated_at', models.DateTimeField(auto_now=True)),
               ],
               options={
                   'db_table': 'user_preferences',
               },
           ),
           migrations.CreateModel(
               name='NotificationLog',
               fields=[
                   ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                   ('user_id', models.IntegerField()),
                   ('type', models.CharField(choices=[('email', 'Email'), ('sms', 'SMS'), ('push', 'Push Notification')], max_length=20)),
                   ('status', models.CharField(choices=[('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed'), ('bounced', 'Bounced'), ('retry', 'Retry')], default='pending', max_length=20)),
                   ('recipient', models.CharField(max_length=255)),
                   ('subject', models.CharField(blank=True, max_length=255)),
                   ('content', models.TextField()),
                   ('provider_response', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                   ('sent_at', models.DateTimeField(blank=True, null=True)),
                   ('error_message', models.TextField(blank=True)),
                   ('retry_count', models.IntegerField(default=0)),
                   ('max_retries', models.IntegerField(default=3)),
                   ('metadata', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                   ('correlation_id', models.UUIDField(blank=True, null=True)),
                   ('created_at', models.DateTimeField(auto_now_add=True)),
                   ('template', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.notificationtemplate')),
               ],
               options={
                   'db_table': 'notification_logs',
               },
           ),
           # Add indexes for performance
           migrations.RunSQL(
               "CREATE INDEX idx_notification_templates_name_active ON notification_templates(name, is_active);",
               reverse_sql="DROP INDEX IF EXISTS idx_notification_templates_name_active;"
           ),
           migrations.RunSQL(
               "CREATE INDEX idx_notification_templates_type_active ON notification_templates(type, is_active);",
               reverse_sql="DROP INDEX IF EXISTS idx_notification_templates_type_active;"
           ),
           migrations.RunSQL(
               "CREATE INDEX idx_notification_logs_user_created ON notification_logs(user_id, created_at DESC);",
               reverse_sql="DROP INDEX IF EXISTS idx_notification_logs_user_created;"
           ),
           migrations.RunSQL(
               "CREATE INDEX idx_notification_logs_status_type ON notification_logs(status, type);",
               reverse_sql="DROP INDEX IF EXISTS idx_notification_logs_status_type;"
           ),
           migrations.RunSQL(
               "CREATE INDEX idx_notification_logs_correlation_id ON notification_logs(correlation_id);",
               reverse_sql="DROP INDEX IF EXISTS idx_notification_logs_correlation_id;"
           ),
           migrations.RunSQL(
               "CREATE INDEX idx_notification_logs_retry ON notification_logs(status, retry_count) WHERE status = 'failed';",
               reverse_sql="DROP INDEX IF EXISTS idx_notification_logs_retry;"
           ),
       ]

   # Django Settings Configuration for Database
   # notification_service/settings/base.py
   import os

   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': os.getenv('DB_NAME', 'notifications'),
           'USER': os.getenv('DB_USER', 'notifications_user'),
           'PASSWORD': os.getenv('DB_PASSWORD', 'notifications_pass'),
           'HOST': os.getenv('DB_HOST', 'localhost'),
           'PORT': os.getenv('DB_PORT', '5432'),
           'OPTIONS': {
               'application_name': 'notification-service',
           },
           'CONN_MAX_AGE': 60,  # Connection pooling
       }
   }

   # Database connection pooling with django-db-pool (optional)
   if os.getenv('USE_DB_POOL', 'false').lower() == 'true':
       DATABASES['default']['ENGINE'] = 'django_db_pool.backends.postgresql'
       DATABASES['default']['POOL_OPTIONS'] = {
           'POOL_SIZE': 10,
           'MAX_OVERFLOW': 20,
           'RECYCLE': 300,
       }

   # Cache configuration for Redis
   CACHES = {
       'default': {
           'BACKEND': 'django_redis.cache.RedisCache',
           'LOCATION': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
           'OPTIONS': {
               'CLIENT_CLASS': 'django_redis.client.DefaultClient',
               'CONNECTION_POOL_KWARGS': {
                   'max_connections': 50,
                   'retry_on_timeout': True,
               },
           },
           'KEY_PREFIX': 'notification_service',
           'TIMEOUT': 300,  # 5 minutes default
       }
   }

   # RabbitMQ Configuration
   RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://notifications_user:notifications_pass@localhost:5672/')

   # Logging configuration
   LOGGING = {
       'version': 1,
       'disable_existing_loggers': False,
       'formatters': {
           'verbose': {
               'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
               'style': '{',
           },
           'simple': {
               'format': '{levelname} {message}',
               'style': '{',
           },
       },
       'handlers': {
           'file': {
               'level': 'INFO',
               'class': 'logging.FileHandler',
               'filename': 'notification_service.log',
               'formatter': 'verbose',
           },
           'console': {
               'level': 'INFO',
               'class': 'logging.StreamHandler',
               'formatter': 'simple',
           },
       },
       'root': {
           'handlers': ['console', 'file'],
           'level': 'INFO',
       },
       'loggers': {
           'django.db.backends': {
               'level': 'WARNING',
               'handlers': ['console'],
               'propagate': False,
           },
       },
   }
   ```

2. **Middleware & Authentication**
   ```python
   # infrastructure/monitoring/middleware.py
   from django.utils.deprecation import MiddlewareMixin
   from opentelemetry import trace, baggage
   from opentelemetry.instrumentation.django import DjangoInstrumentor
   from opentelemetry.propagate import extract
   import uuid
   import time

   class OpenTelemetryMiddleware(MiddlewareMixin):
       def __init__(self, get_response):
           self.get_response = get_response
           super().__init__(get_response)

       def process_request(self, request):
           # Extract trace context from headers
           carrier = dict(request.META)
           ctx = extract(carrier)
           
           # Set correlation ID
           correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
           request.correlation_id = correlation_id
           
           # Set baggage for correlation ID
           ctx = baggage.set_baggage("correlation_id", correlation_id, context=ctx)
           
           # Start timing
           request._start_time = time.time()
           
           return None

       def process_response(self, request, response):
           # Add correlation ID to response headers
           if hasattr(request, 'correlation_id'):
               response['X-Correlation-ID'] = request.correlation_id
               
           # Record request duration
           if hasattr(request, '_start_time'):
               duration = time.time() - request._start_time
               # This will be automatically recorded by OpenTelemetry Django instrumentation
               
           return response

   # notification_service/settings/base.py
   MIDDLEWARE = [
       'infrastructure.monitoring.middleware.OpenTelemetryMiddleware',
       'django.middleware.security.SecurityMiddleware',
       'django.contrib.sessions.middleware.SessionMiddleware',
       'corsheaders.middleware.CorsMiddleware',
       'django.middleware.common.CommonMiddleware',
       'django.middleware.csrf.CsrfViewMiddleware',
       'django.contrib.auth.middleware.AuthenticationMiddleware',
       'django.contrib.messages.middleware.MessageMiddleware',
       'django.middleware.clickjacking.XFrameOptionsMiddleware',
   ]

   # OpenTelemetry Configuration
   from opentelemetry import trace
   from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
   from opentelemetry.sdk.trace import TracerProvider
   from opentelemetry.sdk.trace.export import BatchSpanProcessor
   from opentelemetry.instrumentation.django import DjangoInstrumentor
   from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
   from opentelemetry.instrumentation.redis import RedisInstrumentor
   from opentelemetry.instrumentation.celery import CeleryInstrumentor

   # Set up tracing
   trace.set_tracer_provider(TracerProvider())
   tracer = trace.get_tracer(__name__)

   # Configure OTLP exporter
   otlp_exporter = OTLPSpanExporter(
       endpoint=os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://jaeger:14250'),
       insecure=True
   )

   span_processor = BatchSpanProcessor(otlp_exporter)
   trace.get_tracer_provider().add_span_processor(span_processor)

   # Auto-instrument Django, PostgreSQL, Redis, and Celery
   DjangoInstrumentor().instrument()
   Psycopg2Instrumentor().instrument()
   RedisInstrumentor().instrument()
   CeleryInstrumentor().instrument()
   ```

#### Step 4.2: Event Publishing

1. **Event System (Following Requirements Structure)**
   ```python
   # events/publisher.py (Event publishing as per requirements)
   import pika
   import json
   import logging
   from dataclasses import dataclass, asdict
   from typing import Any, Dict, Optional
   from uuid import UUID, uuid4
   from datetime import datetime
   from django.conf import settings
   from opentelemetry import trace

   logger = logging.getLogger(__name__)
   tracer = trace.get_tracer(__name__)

   @dataclass
   class DomainEvent:
       event_id: UUID
       event_type: str
       aggregate_id: str
       user_id: int
       correlation_id: Optional[UUID]
       payload: Dict[str, Any]
       timestamp: datetime
       version: int = 1

   class EventPublisher:
       """Event publisher for notification domain events"""
       
       def __init__(self):
           self.connection = None
           self.channel = None
           self._connect()
           
       def _connect(self):
           """Establish connection to RabbitMQ"""
           try:
               connection_params = pika.URLParameters(settings.RABBITMQ_URL)
               self.connection = pika.BlockingConnection(connection_params)
               self.channel = self.connection.channel()
               
               # Declare exchanges and queues
               self.channel.exchange_declare(
                   exchange='notification.events',
                   exchange_type='topic',
                   durable=True
               )
               
               # Declare queue for notification processing
               self.channel.queue_declare(
                   queue='notification.processing',
                   durable=True
               )
               
               # Bind queue to exchange
               self.channel.queue_bind(
                   exchange='notification.events',
                   queue='notification.processing',
                   routing_key='notification.*'
               )
               
               logger.info("EventPublisher connected to RabbitMQ successfully")
               
           except Exception as e:
               logger.error(f"Failed to connect to RabbitMQ: {e}")
               raise
               
       @tracer.start_as_current_span("publish_event")
       def _publish_event(self, event: DomainEvent, routing_key: str):
           """Publish event to RabbitMQ"""
           span = trace.get_current_span()
           span.set_attributes({
               "messaging.system": "rabbitmq",
               "messaging.destination": "notification.events",
               "messaging.routing_key": routing_key,
               "event.type": event.event_type,
               "event.id": str(event.event_id)
           })
           
           try:
               if not self.connection or self.connection.is_closed:
                   self._connect()
                   
               message_body = json.dumps(asdict(event), default=str)
               
               self.channel.basic_publish(
                   exchange='notification.events',
                   routing_key=routing_key,
                   body=message_body,
                   properties=pika.BasicProperties(
                       delivery_mode=2,  # Make message persistent
                       correlation_id=str(event.correlation_id) if event.correlation_id else None,
                       timestamp=int(event.timestamp.timestamp()),
                       headers={
                           'event_type': event.event_type,
                           'version': event.version
                       }
                   )
               )
               
               logger.info(f"Published event {event.event_type} with ID {event.event_id}")
               span.set_status(trace.Status(trace.StatusCode.OK))
               
           except Exception as e:
               logger.error(f"Failed to publish event: {e}")
               span.record_exception(e)
               span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
               raise
               
       def publish_notification_requested(self, notification):
           """Publish notification requested event"""
           event = DomainEvent(
               event_id=uuid4(),
               event_type="notification.requested",
               aggregate_id=str(notification.id),
               user_id=notification.user_id,
               correlation_id=notification.correlation_id,
               payload={
                   "notification_id": str(notification.id),
                   "user_id": notification.user_id,
                   "template_name": notification.template.name if notification.template else None,
                   "type": notification.type,
                   "recipient": notification.recipient,
                   "priority": "normal"
               },
               timestamp=datetime.utcnow()
           )
           
           self._publish_event(event, "notification.requested")
           
       def publish_notification_sent(self, notification):
           """Publish notification sent event"""
           event = DomainEvent(
               event_id=uuid4(),
               event_type="notification.sent",
               aggregate_id=str(notification.id),
               user_id=notification.user_id,
               correlation_id=notification.correlation_id,
               payload={
                   "notification_id": str(notification.id),
                   "user_id": notification.user_id,
                   "type": notification.type,
                   "status": notification.status,
                   "recipient": notification.recipient,
                   "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
                   "provider_response": notification.provider_response
               },
               timestamp=datetime.utcnow()
           )
           
           self._publish_event(event, "notification.sent")
           
       def close(self):
           """Close RabbitMQ connection"""
           if self.connection and not self.connection.is_closed:
               self.connection.close()

   # events/consumer.py (Event consumption as per requirements)
   import pika
   import json
   import logging
   from django.conf import settings
   from core.models import NotificationLog
   from core.repositories import NotificationRepository
   from adapters import ProviderFactory
   from opentelemetry import trace

   logger = logging.getLogger(__name__)
   tracer = trace.get_tracer(__name__)

   class EventConsumer:
       """Event consumer for processing notification events"""
       
       def __init__(self):
           self.connection = None
           self.channel = None
           self.notification_repo = NotificationRepository()
           self._connect()
           
       def _connect(self):
           """Establish connection to RabbitMQ"""
           try:
               connection_params = pika.URLParameters(settings.RABBITMQ_URL)
               self.connection = pika.BlockingConnection(connection_params)
               self.channel = self.connection.channel()
               logger.info("EventConsumer connected to RabbitMQ successfully")
           except Exception as e:
               logger.error(f"Failed to connect to RabbitMQ: {e}")
               raise
               
       @tracer.start_as_current_span("process_notification_event")
       def _process_notification_requested(self, event_data: dict):
           """Process notification.requested event"""
           span = trace.get_current_span()
           
           try:
               notification_id = event_data['payload']['notification_id']
               notification_type = event_data['payload']['type']
               
               span.set_attributes({
                   "notification.id": notification_id,
                   "notification.type": notification_type
               })
               
               # Get notification from database
               notification = self.notification_repo.get_by_id(notification_id)
               if not notification:
                   logger.error(f"Notification {notification_id} not found")
                   return
               
               # Get appropriate provider
               if notification_type == 'email':
                   provider = ProviderFactory.get_email_provider()
                   result = provider.send(notification.recipient, notification.subject, notification.content)
               elif notification_type == 'sms':
                   provider = ProviderFactory.get_sms_provider()
                   result = provider.send(notification.recipient, notification.content)
               elif notification_type == 'push':
                   provider = ProviderFactory.get_push_provider()
                   result = provider.send(notification.recipient, notification.subject, notification.content)
               else:
                   logger.error(f"Unknown notification type: {notification_type}")
                   return
               
               # Update notification status
               if result['success']:
                   self.notification_repo.update_status(
                       notification_id, 
                       'sent',
                       sent_at=timezone.now(),
                       provider_response=result
                   )
                   logger.info(f"Notification {notification_id} sent successfully")
               else:
                   self.notification_repo.update_status(
                       notification_id,
                       'failed',
                       error_message=result.get('error', 'Unknown error'),
                       provider_response=result
                   )
                   logger.error(f"Failed to send notification {notification_id}: {result.get('error')}")
                   
               span.set_status(trace.Status(trace.StatusCode.OK))
               
           except Exception as e:
               logger.exception(f"Error processing notification event: {e}")
               span.record_exception(e)
               span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
               raise
               
       def start_consuming(self):
           """Start consuming messages from notification processing queue"""
           def callback(ch, method, properties, body):
               try:
                   event_data = json.loads(body.decode('utf-8'))
                   logger.info(f"Received event: {event_data.get('event_type')}")
                   
                   # Process based on event type
                   if event_data.get('event_type') == 'notification.requested':
                       self._process_notification_requested(event_data)
                       
                   # Acknowledge message
                   ch.basic_ack(delivery_tag=method.delivery_tag)
                   
               except Exception as e:
                   logger.error(f"Error processing message: {e}")
                   # Reject message and requeue
                   ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                   
           self.channel.basic_qos(prefetch_count=1)
           self.channel.basic_consume(
               queue='notification.processing',
               on_message_callback=callback
           )
           
           logger.info("Starting to consume notification events...")
           self.channel.start_consuming()
           
       def close(self):
           """Close RabbitMQ connection"""
           if self.connection and not self.connection.is_closed:
               self.connection.close()
   ```

### Phase 5: Testing Strategy

#### Step 5.1: Unit Testing

1. **Domain Service Tests**
   ```python
   # tests/unit/test_notification_service.py
   import pytest
   from unittest.mock import Mock, patch
   from django.test import TestCase
   from django.utils import timezone
   from uuid import uuid4

   from apps.notifications.models import NotificationTemplate, NotificationLog, UserPreference
   from apps.notifications.services import NotificationService

   class TestNotificationService(TestCase):
       def setUp(self):
           self.service = NotificationService()
           
           # Create test template
           self.template = NotificationTemplate.objects.create(
               name="welcome_email",
               subject="Welcome to MyBambu",
               body="Hello {name}, welcome to MyBambu!",
               type="email",
               variables={"name": "string"},
               is_active=True
           )
           
           # Create test user preferences
           self.preferences = UserPreference.objects.create(
               user_id=123,
               email_enabled=True,
               sms_enabled=True,
               push_enabled=True
           )

       @patch('apps.notifications.services.NotificationService._get_recipient')
       @patch('infrastructure.messaging.publisher.RabbitMQEventPublisher.publish_notification_requested')
       def test_send_notification_success(self, mock_publish, mock_get_recipient):
           # Arrange
           mock_get_recipient.return_value = "test@example.com"
           
           # Act
           result = self.service.send_notification(
               user_id=123,
               template_name="welcome_email",
               context={"name": "John Doe"}
           )
           
           # Assert
           self.assertIsInstance(result, NotificationLog)
           self.assertEqual(result.user_id, 123)
           self.assertEqual(result.type, "email")
           self.assertIn("John Doe", result.content)
           self.assertEqual(result.status, "pending")
           
           # Verify notification was saved to database
           saved_notification = NotificationLog.objects.get(id=result.id)
           self.assertEqual(saved_notification.user_id, 123)
           
           # Verify event was published
           mock_publish.assert_called_once()

       def test_send_notification_invalid_template(self):
           # Act & Assert
           with self.assertRaises(Exception):  # Should be InvalidTemplateError
               self.service.send_notification(
                   user_id=123,
                   template_name="nonexistent_template",
                   context={"name": "John Doe"}
               )

       def test_send_notification_blocked_by_preferences(self):
           # Arrange
           self.preferences.email_enabled = False
           self.preferences.save()
           
           # Act & Assert
           with self.assertRaises(Exception):  # Should be NotificationBlockedError
               self.service.send_notification(
                   user_id=123,
                   template_name="welcome_email",
                   context={"name": "John Doe"}
               )

       def test_template_caching(self):
           # Arrange
           with patch('django.core.cache.cache.get') as mock_cache_get, \
                patch('django.core.cache.cache.set') as mock_cache_set:
               
               mock_cache_get.return_value = None  # Cache miss
               
               # Act
               template = self.service._get_template_cached("welcome_email")
               
               # Assert
               self.assertEqual(template.name, "welcome_email")
               mock_cache_set.assert_called_once()

       def test_user_preferences_caching(self):
           # Arrange
           with patch('django.core.cache.cache.get') as mock_cache_get, \
                patch('django.core.cache.cache.set') as mock_cache_set:
               
               mock_cache_get.return_value = None  # Cache miss
               
               # Act
               preferences = self.service._get_user_preferences_cached(123)
               
               # Assert
               self.assertEqual(preferences.user_id, 123)
               mock_cache_set.assert_called_once()
   ```

2. **Integration Tests**
   ```python
   # tests/integration/test_api.py
   import json
   from django.test import TestCase, TransactionTestCase
   from django.urls import reverse
   from rest_framework.test import APIClient
   from rest_framework import status
   from django.contrib.auth.models import User
   from apps.notifications.models import NotificationTemplate, NotificationLog

   class NotificationAPITestCase(TestCase):
       def setUp(self):
           self.client = APIClient()
           
           # Create test user
           self.user = User.objects.create_user(
               username='testuser',
               email='test@example.com',
               password='testpass123'
           )
           
           # Create test template
           self.template = NotificationTemplate.objects.create(
               name="test_email",
               subject="Test Subject",
               body="Hello {name}!",
               type="email",
               is_active=True
           )
           
           # Authenticate client
           self.client.force_authenticate(user=self.user)

       def test_send_notification_success(self):
           # Arrange
           url = reverse('send-notification')
           data = {
               'user_id': 123,
               'template_name': 'test_email',
               'context': {'name': 'John Doe'}
           }
           
           # Act
           response = self.client.post(url, data, format='json')
           
           # Assert
           self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
           self.assertIn('id', response.data)
           self.assertEqual(response.data['status'], 'queued')
           
           # Verify notification was created in database
           notification = NotificationLog.objects.get(id=response.data['id'])
           self.assertEqual(notification.user_id, 123)
           self.assertEqual(notification.type, 'email')

       def test_send_notification_invalid_template(self):
           # Arrange
           url = reverse('send-notification')
           data = {
               'user_id': 123,
               'template_name': 'nonexistent_template',
               'context': {'name': 'John Doe'}
           }
           
           # Act
           response = self.client.post(url, data, format='json')
           
           # Assert
           self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

       def test_get_notification_success(self):
           # Arrange
           notification = NotificationLog.objects.create(
               user_id=123,
               template=self.template,
               type='email',
               status='sent',
               recipient='test@example.com',
               content='Hello John!',
               provider_response={'success': True}
           )
           
           url = reverse('notification-detail', kwargs={'notification_id': notification.id})
           
           # Act
           response = self.client.get(url)
           
           # Assert
           self.assertEqual(response.status_code, status.HTTP_200_OK)
           self.assertEqual(response.data['id'], str(notification.id))
           self.assertEqual(response.data['user_id'], 123)

       def test_get_notification_not_found(self):
           # Arrange
           from uuid import uuid4
           url = reverse('notification-detail', kwargs={'notification_id': uuid4()})
           
           # Act
           response = self.client.get(url)
           
           # Assert
           self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

   class NotificationRabbitMQIntegrationTest(TransactionTestCase):
       """Integration tests with RabbitMQ"""
       
       def setUp(self):
           # Only run if RabbitMQ is available
           try:
               import pika
               connection = pika.BlockingConnection(pika.URLParameters('amqp://localhost'))
               connection.close()
           except:
               self.skipTest("RabbitMQ not available")
               
           self.template = NotificationTemplate.objects.create(
               name="integration_test_email",
               subject="Integration Test",
               body="Hello {name}!",
               type="email",
               is_active=True
           )

       def test_notification_event_publishing(self):
           # This would test the actual RabbitMQ integration
           # Implementation depends on test environment setup
           pass
   ```

#### Step 5.2: Performance Testing

1. **Load Testing with Locust**
   ```python
   # tests/performance/locustfile.py
   from locust import HttpUser, task, between
   import json
   import random

   class NotificationUser(HttpUser):
       wait_time = between(1, 3)
       
       def on_start(self):
           # Login and get auth token (assuming token-based auth)
           response = self.client.post("/api/auth/login/", json={
               "username": "test_service",
               "password": "test_password"
           })
           if response.status_code == 200:
               self.token = response.json().get("access_token")
               self.headers = {"Authorization": f"Bearer {self.token}"}
           else:
               self.headers = {}
       
       @task(3)
       def send_email_notification(self):
           user_id = random.randint(1, 10000)
           self.client.post("/api/v1/notifications/send/", 
               json={
                   "user_id": user_id,
                   "template_name": "welcome_email",
                   "context": {"name": f"User{user_id}"}
               },
               headers=self.headers
           )
       
       @task(2)
       def send_sms_notification(self):
           user_id = random.randint(1, 10000)
           self.client.post("/api/v1/notifications/send/", 
               json={
                   "user_id": user_id,
                   "template_name": "sms_verification",
                   "context": {"code": "123456"}
               },
               headers=self.headers
           )
       
       @task(1)
       def get_notification_status(self):
           # This would require storing notification IDs from previous requests
           # For simplicity, we'll just test with a mock UUID
           import uuid
           notification_id = str(uuid.uuid4())
           self.client.get(f"/api/v1/notifications/{notification_id}/",
               headers=self.headers,
               name="/api/v1/notifications/[id]"  # Group similar requests in stats
           )

   # Performance test configuration
   # Run with: locust -f tests/performance/locustfile.py --host=http://localhost:8001
   ```

### Phase 6: Deployment & Monitoring

#### Step 6.1: Production Deployment

1. **Kubernetes Manifests**
   ```yaml
   # k8s/notification-service.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: notification-service
     labels:
       app: notification-service
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: notification-service
     template:
       metadata:
         labels:
           app: notification-service
       spec:
         containers:
         - name: notification-service
           image: mybambu/notification-service:latest
           ports:
           - containerPort: 8000
           env:
           - name: DATABASE_URL
             valueFrom:
               secretKeyRef:
                 name: notification-secrets
                 key: database-url
           - name: REDIS_URL
             valueFrom:
               secretKeyRef:
                 name: notification-secrets
                 key: redis-url
           resources:
             requests:
               memory: "256Mi"
               cpu: "250m"
             limits:
               memory: "512Mi"
               cpu: "500m"
           livenessProbe:
             httpGet:
               path: /health/live
               port: 8000
             initialDelaySeconds: 30
             periodSeconds: 10
           readinessProbe:
             httpGet:
               path: /health/ready
               port: 8000
             initialDelaySeconds: 5
             periodSeconds: 5
   ```

2. **Health Checks**
   ```python
   # apps/health/views.py
   from django.http import JsonResponse
   from django.db import connection
   from django.core.cache import cache
   from django.utils import timezone
   import pika
   import logging
   from django.conf import settings

   logger = logging.getLogger(__name__)

   def liveness_check(request):
       """Kubernetes liveness probe - basic service availability"""
       return JsonResponse({
           "status": "alive",
           "timestamp": timezone.now().isoformat(),
           "service": "notification-service"
       })

   def readiness_check(request):
       """Kubernetes readiness probe - service ready to accept traffic"""
       checks = {
           "database": _check_database_health(),
           "redis": _check_redis_health(),
           "rabbitmq": _check_rabbitmq_health(),
           "external_providers": _check_provider_health()
       }
       
       all_healthy = all(checks.values())
       status_code = 200 if all_healthy else 503
       
       response_data = {
           "status": "ready" if all_healthy else "not_ready",
           "checks": checks,
           "timestamp": timezone.now().isoformat()
       }
       
       return JsonResponse(response_data, status=status_code)

   def startup_check(request):
       """Kubernetes startup probe - service initialization complete"""
       # Check if all necessary components are initialized
       checks = {
           "database_migrations": _check_migrations(),
           "cache_connection": _check_redis_health(),
           "message_broker": _check_rabbitmq_health()
       }
       
       all_ready = all(checks.values())
       status_code = 200 if all_ready else 503
       
       return JsonResponse({
           "status": "started" if all_ready else "starting",
           "checks": checks,
           "timestamp": timezone.now().isoformat()
       }, status=status_code)

   def _check_database_health():
       """Check PostgreSQL database connection"""
       try:
           with connection.cursor() as cursor:
               cursor.execute("SELECT 1")
               return True
       except Exception as e:
           logger.error(f"Database health check failed: {e}")
           return False

   def _check_redis_health():
       """Check Redis connection"""
       try:
           cache.set('health_check', 'ok', timeout=10)
           result = cache.get('health_check')
           return result == 'ok'
       except Exception as e:
           logger.error(f"Redis health check failed: {e}")
           return False

   def _check_rabbitmq_health():
       """Check RabbitMQ connection"""
       try:
           connection_params = pika.URLParameters(settings.RABBITMQ_URL)
           connection = pika.BlockingConnection(connection_params)
           connection.close()
           return True
       except Exception as e:
           logger.error(f"RabbitMQ health check failed: {e}")
           return False

   def _check_provider_health():
       """Check external notification providers"""
       # Simplified check - in production, this would ping actual providers
       return True

   def _check_migrations():
       """Check if database migrations are up to date"""
       try:
           from django.db.migrations.executor import MigrationExecutor
           executor = MigrationExecutor(connection)
           plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
           return len(plan) == 0  # No pending migrations
       except Exception as e:
           logger.error(f"Migration check failed: {e}")
           return False

   # apps/health/urls.py
   from django.urls import path
   from . import views

   urlpatterns = [
       path('live/', views.liveness_check, name='health-live'),
       path('ready/', views.readiness_check, name='health-ready'),
       path('startup/', views.startup_check, name='health-startup'),
   ]
   ```

#### Step 6.2: Monitoring & Observability

1. **OpenTelemetry Metrics Integration**
   ```python
   # infrastructure/monitoring/telemetry.py
   import os
   from opentelemetry import metrics
   from opentelemetry.exporter.prometheus import PrometheusMetricReader
   from opentelemetry.sdk.metrics import MeterProvider
   from opentelemetry.sdk.resources import SERVICE_NAME, Resource
   from prometheus_client import start_http_server, Counter, Histogram, Gauge
   import time
   import threading

   # Configure OpenTelemetry metrics
   resource = Resource(attributes={
       SERVICE_NAME: "notification-service"
   })

   # Set up Prometheus metrics reader
   prometheus_reader = PrometheusMetricReader()
   provider = MeterProvider(resource=resource, metric_readers=[prometheus_reader])
   metrics.set_meter_provider(provider)

   # Get meter for our service
   meter = metrics.get_meter("notification-service")

   # Define metrics using OpenTelemetry
   class OpenTelemetryMetrics:
       def __init__(self):
           # Counters
           self.notifications_sent_total = meter.create_counter(
               name="notifications_sent_total",
               description="Total number of notifications sent",
               unit="1"
           )
           
           self.notifications_failed_total = meter.create_counter(
               name="notifications_failed_total",
               description="Total number of failed notifications",
               unit="1"
           )
           
           self.api_requests_total = meter.create_counter(
               name="api_requests_total",
               description="Total number of API requests",
               unit="1"
           )
           
           # Histograms
           self.notification_processing_duration = meter.create_histogram(
               name="notification_processing_duration_seconds",
               description="Time spent processing notifications",
               unit="s"
           )
           
           self.api_request_duration = meter.create_histogram(
               name="api_request_duration_seconds",
               description="API request duration",
               unit="s"
           )
           
           # Gauges (using UpDownCounter for OpenTelemetry)
           self.notification_queue_size = meter.create_up_down_counter(
               name="notification_queue_size",
               description="Current size of notification queue",
               unit="1"
           )
           
           self.active_connections = meter.create_up_down_counter(
               name="active_connections",
               description="Number of active connections",
               unit="1"
           )

       def counter(self, name: str, labels: dict = None):
           """Get counter metric with labels"""
           if name == 'notifications_sent_total':
               return CounterWrapper(self.notifications_sent_total, labels or {})
           elif name == 'notifications_failed_total':
               return CounterWrapper(self.notifications_failed_total, labels or {})
           elif name == 'api_requests_total':
               return CounterWrapper(self.api_requests_total, labels or {})
           else:
               raise ValueError(f"Unknown counter metric: {name}")

       def histogram(self, name: str, labels: dict = None):
           """Get histogram metric with labels"""
           if name == 'notification_processing_duration_seconds':
               return HistogramWrapper(self.notification_processing_duration, labels or {})
           elif name == 'api_request_duration_seconds':
               return HistogramWrapper(self.api_request_duration, labels or {})
           else:
               raise ValueError(f"Unknown histogram metric: {name}")

       def gauge(self, name: str, labels: dict = None):
           """Get gauge metric with labels"""
           if name == 'notification_queue_size':
               return GaugeWrapper(self.notification_queue_size, labels or {})
           elif name == 'active_connections':
               return GaugeWrapper(self.active_connections, labels or {})
           else:
               raise ValueError(f"Unknown gauge metric: {name}")

   class CounterWrapper:
       def __init__(self, counter, labels):
           self.counter = counter
           self.labels = labels
           
       def inc(self, amount=1):
           self.counter.add(amount, self.labels)

   class HistogramWrapper:
       def __init__(self, histogram, labels):
           self.histogram = histogram
           self.labels = labels
           
       def observe(self, value):
           self.histogram.record(value, self.labels)

   class GaugeWrapper:
       def __init__(self, gauge, labels):
           self.gauge = gauge
           self.labels = labels
           
       def set(self, value):
           # For UpDownCounter, we need to track the difference
           # This is a simplified implementation
           self.gauge.add(value, self.labels)

   # Global metrics instance
   metrics = OpenTelemetryMetrics()

   # Start Prometheus HTTP server for metrics scraping
   def start_metrics_server(port=8080):
       """Start Prometheus metrics server"""
       start_http_server(port)
       print(f"Metrics server started on port {port}")

   # Django integration
   class MetricsMiddleware:
       def __init__(self, get_response):
           self.get_response = get_response

       def __call__(self, request):
           start_time = time.time()
           
           response = self.get_response(request)
           
           # Record request metrics
           duration = time.time() - start_time
           labels = {
               'method': request.method,
               'endpoint': request.path,
               'status_code': str(response.status_code)
           }
           
           metrics.counter('api_requests_total', labels).inc()
           metrics.histogram('api_request_duration_seconds', labels).observe(duration)
           
           return response

   # Celery integration for queue metrics
   from celery.signals import task_prerun, task_postrun, task_failure

   @task_prerun.connect
   def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
       """Called before task execution"""
       labels = {'task_name': task.__name__ if task else 'unknown'}
       metrics.gauge('active_tasks', labels).set(1)

   @task_postrun.connect
   def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
       """Called after task execution"""
       labels = {'task_name': task.__name__ if task else 'unknown', 'state': state}
       metrics.counter('celery_tasks_total', labels).inc()

   @task_failure.connect
   def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
       """Called when task fails"""
       labels = {'task_name': sender.__name__ if sender else 'unknown'}
       metrics.counter('celery_task_failures_total', labels).inc()
   ```

### Phase 7: Migration Execution

#### Step 7.1: Traffic Routing

1. **Feature Flag Implementation**
   ```python
   # src/infrastructure/feature_flags/flags.py
   import os
   from typing import Dict, Any

   class FeatureFlags:
       def __init__(self):
           self.flags = {
               'use_microservice_for_sending': os.getenv('USE_MICROSERVICE_FOR_SENDING', 'false').lower() == 'true',
               'dual_write_enabled': os.getenv('DUAL_WRITE_ENABLED', 'true').lower() == 'true',
               'microservice_read_percentage': int(os.getenv('MICROSERVICE_READ_PERCENTAGE', '0')),
           }
           
       def should_use_microservice_for_sending(self, user_id: int) -> bool:
           if not self.flags['use_microservice_for_sending']:
               return False
           
           # Gradual rollout based on user_id hash
           return (user_id % 100) < int(os.getenv('MICROSERVICE_ROLLOUT_PERCENTAGE', '0'))
           
       def should_read_from_microservice(self, user_id: int) -> bool:
           return (user_id % 100) < self.flags['microservice_read_percentage']
   ```

2. **API Gateway Configuration**
   ```yaml
   # nginx/notification-routing.conf
   upstream monolith_backend {
       server monolith:8000;
   }

   upstream microservice_backend {
       server notification-service:8000;
   }

   map $http_x_use_microservice $backend {
       default monolith_backend;
       "true" microservice_backend;
   }

   server {
       listen 80;
       
       location /api/v1/notifications/ {
           # Route based on feature flag header
           proxy_pass http://$backend;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       }
   }
   ```

#### Step 7.2: Data Cutover

1. **Migration Execution Script**
   ```python
   # scripts/execute_migration.py
   import asyncio
   from typing import Dict, List
   from datetime import datetime
   import logging

   class MigrationExecutor:
       def __init__(self):
           self.data_migrator = DataMigrator()
           self.validator = MigrationValidator()
           
       async def execute_full_migration(self) -> Dict[str, Any]:
           """Execute complete migration with rollback capability"""
           
           migration_log = {
               'started_at': datetime.utcnow(),
               'phases': [],
               'status': 'in_progress'
           }
           
           try:
               # Phase 1: Migrate templates
               logger.info("Starting template migration...")
               template_result = await self.data_migrator.migrate_templates()
               migration_log['phases'].append({
                   'phase': 'templates',
                   'status': 'completed',
                   'result': template_result
               })
               
               # Phase 2: Migrate user preferences
               logger.info("Starting user preferences migration...")
               preference_result = await self.data_migrator.migrate_user_preferences()
               migration_log['phases'].append({
                   'phase': 'preferences',
                   'status': 'completed',
                   'result': preference_result
               })
               
               # Phase 3: Migrate notification logs (in batches)
               logger.info("Starting notification logs migration...")
               logs_result = await self.data_migrator.migrate_notification_logs(batch_size=5000)
               migration_log['phases'].append({
                   'phase': 'logs',
                   'status': 'completed',
                   'result': logs_result
               })
               
               # Phase 4: Validate migration
               logger.info("Validating migration...")
               validation_result = await self.validator.generate_migration_report()
               migration_log['validation'] = validation_result
               
               # Check if validation passed
               if self._is_migration_valid(validation_result):
                   migration_log['status'] = 'completed'
                   logger.info("Migration completed successfully!")
               else:
                   migration_log['status'] = 'validation_failed'
                   logger.error("Migration validation failed!")
                   
           except Exception as e:
               migration_log['status'] = 'failed'
               migration_log['error'] = str(e)
               logger.exception(f"Migration failed: {e}")
               
           migration_log['completed_at'] = datetime.utcnow()
           return migration_log
   ```

## Rollback Strategy

### Emergency Rollback Procedures

#### 1. Traffic Rollback (< 5 minutes)
```bash
# Immediate traffic routing back to monolith
kubectl patch configmap nginx-config --patch '{"data":{"USE_MICROSERVICE":"false"}}'
kubectl rollout restart deployment/nginx-gateway

# Disable feature flags
kubectl set env deployment/monolith-app USE_MICROSERVICE_FOR_SENDING=false
```

#### 2. Database Rollback (15-30 minutes)
```sql
-- If dual-write was enabled, data should be consistent
-- If not, restore from backup

-- 1. Stop microservice
-- 2. Restore monolith database from backup
-- 3. Re-enable monolith notification service

BEGIN;

-- Restore notification_template table
DROP TABLE IF EXISTS notifications_notificationtemplate_backup;
ALTER TABLE notifications_notificationtemplate RENAME TO notifications_notificationtemplate_backup;
-- Restore from backup...

-- Restore notification_log table  
DROP TABLE IF EXISTS notifications_notificationlog_backup;
ALTER TABLE notifications_notificationlog RENAME TO notifications_notificationlog_backup;
-- Restore from backup...

-- Restore user_preference table
DROP TABLE IF EXISTS notifications_userpreference_backup;
ALTER TABLE notifications_userpreference RENAME TO notifications_userpreference_backup;
-- Restore from backup...

COMMIT;
```

### Rollback Decision Matrix

| Issue Type | Severity | Rollback Required | Time to Rollback |
|------------|----------|-------------------|------------------|
| High Error Rate (>5%) | Critical | Yes | Immediate |
| Performance Degradation (>2x latency) | High | Yes | < 5 minutes |
| Data Inconsistency | Critical | Yes | < 15 minutes |
| Feature Flag Failure | Medium | Partial | < 2 minutes |
| External Provider Issues | Low | No | Monitor |

## Monitoring & Success Criteria

### Key Performance Indicators (KPIs)

#### 1. Functional Metrics
- **Notification Success Rate**: >99.5%
- **End-to-End Latency**: <2 seconds (95th percentile)
- **Data Consistency**: 100% between monolith and microservice
- **API Availability**: >99.9%

#### 2. Performance Metrics
- **Throughput**: Support 50,000+ notifications/day
- **Response Time**: <500ms for API requests
- **Queue Processing**: <30 seconds for non-urgent notifications
- **Resource Usage**: <500MB RAM, <0.5 CPU per instance

#### 3. Business Metrics
- **Zero Data Loss**: No notifications lost during migration
- **Zero Downtime**: Service remains available throughout migration
- **Feature Parity**: All existing functionality preserved
- **Improved Scalability**: Ability to scale notification service independently

### Monitoring Dashboard

```yaml
# grafana/notification-service-dashboard.json
{
  "dashboard": {
    "title": "Notification Service Migration",
    "panels": [
      {
        "title": "Notification Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(notifications_sent_total{status=\"sent\"}[5m]) / rate(notifications_sent_total[5m]) * 100",
            "legendFormat": "Success Rate %"
          }
        ]
      },
      {
        "title": "API Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Queue Size",
        "type": "graph",
        "targets": [
          {
            "expr": "notification_queue_size",
            "legendFormat": "{{priority}} priority"
          }
        ]
      }
    ]
  }
}
```

## Risk Assessment & Mitigation

### High-Risk Areas

#### 1. Data Migration Risks
**Risk**: Data loss or corruption during migration
**Mitigation**: 
- Comprehensive backup strategy
- Dual-write pattern with validation
- Batch processing with checkpoints
- Automated rollback procedures

#### 2. Performance Risks
**Risk**: Increased latency or decreased throughput
**Mitigation**:
- Load testing before production deployment
- Gradual traffic migration
- Circuit breaker patterns
- Auto-scaling configuration

#### 3. Integration Risks
**Risk**: Breaking existing integrations
**Mitigation**:
- Maintain API compatibility
- Comprehensive integration testing
- Feature flags for gradual rollout
- Real-time monitoring and alerting

### Contingency Plans

#### Plan A: Full Rollback
- Immediate traffic routing to monolith
- Database restoration from backup
- Service restart procedures

#### Plan B: Partial Rollback
- Route only problematic operations to monolith
- Keep successful migrations active
- Investigate and fix issues

#### Plan C: Forward Fix
- Rapid deployment of fixes
- Hot-swapping of service instances
- Real-time configuration updates

## Timeline Summary

| Week | Phase | Key Deliverables | Risk Level |
|------|-------|------------------|------------|
| 1 | Preparation | Infrastructure setup, API design | Low |
| 2 | Data Migration | Migration scripts, validation tools | Medium |
| 3-4 | Service Implementation | Core domain, infrastructure layer | Medium |
| 5 | API & Integration | REST API, event publishing | High |
| 6 | Testing | Unit tests, integration tests, performance tests | Medium |
| 7 | Deployment | Production deployment, monitoring setup | High |
| 8 | Migration Execution | Traffic routing, data cutover | Critical |

**Critical Path**: Data migration → Service implementation → Production deployment
**Key Milestones**: 
- Milestone 1: Migration validation complete
- Milestone 2: API feature complete  
- Milestone 3: Production ready
- Milestone 4: Migration complete

## Conclusion

This migration plan provides a comprehensive, risk-mitigated approach to extracting the notification service from the MyBambu monolith. The strategy emphasizes:

1. **Zero-downtime migration** through dual-write patterns and gradual rollout
2. **Data integrity** through comprehensive validation and backup procedures
3. **Performance optimization** through proper architecture and monitoring
4. **Risk mitigation** through feature flags, circuit breakers, and rollback procedures
5. **Production readiness** through comprehensive testing and monitoring

The 8-week timeline allows for thorough implementation and testing while maintaining aggressive delivery goals. Success will be measured through clear KPIs and monitored through comprehensive observability tools.

By following this plan, MyBambu will achieve:
- Independent scalability of the notification service
- Improved system resilience and fault tolerance
- Better separation of concerns and maintainability
- Foundation for future microservice extractions
