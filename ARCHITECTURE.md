# Architecture Decision Records (ADRs)
# Notification Service Microservice

## Overview

This document captures the key architectural decisions made during the extraction of the notification service from the MyBambu Django monolith. Each decision is documented with context, options considered, and rationale.

---

## ADR-001: Microservice Architecture Pattern

**Status**: ✅ Accepted  
**Date**: 2025-09-15  
**Deciders**: Platform Team, Technical Lead

### Context
The existing Django monolith handles 50,000+ daily notifications with increasing complexity and coupling. The notification system requires independent scaling and technology choices.

### Decision
Extract notifications into a standalone microservice using Domain-Driven Design (DDD) principles.

### Options Considered
1. **Keep in Monolith**: Simple but limits scalability and technology choices
2. **Modular Monolith**: Intermediate step but still coupled deployment
3. **Microservice**: Full independence but higher operational complexity
4. **Serverless Functions**: Event-driven but limited execution time

### Rationale
- **Scalability**: Independent horizontal scaling based on notification volume
- **Technology Freedom**: Choose optimal tools for notification processing
- **Fault Isolation**: Notification failures don't impact core business functions
- **Team Autonomy**: Dedicated team can iterate faster on notification features

### Consequences
- **Positive**: Independent deployments, better fault isolation, technology flexibility
- **Negative**: Increased operational complexity, network latency, distributed system challenges

---

## ADR-002: Django REST Framework for API Layer

**Status**: ✅ Accepted  
**Date**: 2025-09-16  
**Deciders**: Development Team

### Context
Need to choose API framework for the notification microservice with consideration for team expertise and ecosystem compatibility.

### Decision
Use Django REST Framework (DRF) with PostgreSQL database.

### Options Considered
1. **Django REST Framework**: Familiar to team, rich ecosystem
2. **FastAPI**: Higher performance, modern async support
3. **Flask + Marshmallow**: Lightweight, flexible
4. **Node.js + Express**: JavaScript ecosystem
5. **Go + Gin**: High performance, compiled language

### Rationale
- **Team Expertise**: Existing Django knowledge reduces development time
- **Ecosystem**: Rich third-party packages and documentation
- **ORM**: Django ORM provides good abstraction for PostgreSQL
- **Admin Interface**: Built-in admin for operational tasks
- **Testing**: Excellent testing framework integration

### Implementation Details
```python
# API Structure
# /api/v1/notifications/send/          - Send notification
# /api/v1/notifications/{id}/          - Get notification details
# /api/v1/notifications/{id}/status/   - Get delivery status
# /api/v1/templates/                   - Template management
# /api/v1/preferences/user/{id}/       - User preferences
# /api/v1/health/                      - Health checks
```

### Consequences
- **Positive**: Fast development, good documentation, team familiarity
- **Negative**: Potentially lower performance than compiled languages

---

## ADR-003: RabbitMQ as Message Broker

**Status**: ✅ Accepted  
**Date**: 2025-09-17  
**Deciders**: Platform Team

### Context
Notifications require asynchronous processing, retry mechanisms, and reliable delivery. Need to choose message broker for Celery task queue.

### Decision
Use RabbitMQ as primary message broker with Celery for task processing.

### Options Considered
1. **Redis**: Simple, fast, but less reliable for critical messages
2. **RabbitMQ**: AMQP protocol, message persistence, reliable delivery
3. **Apache Kafka**: High throughput, but complex for simple use cases
4. **AWS SQS**: Managed service, but vendor lock-in
5. **PostgreSQL**: Using database as queue, simpler but less performant

### Rationale
- **Reliability**: Message persistence and acknowledgments
- **Dead Letter Queues**: Handle failed message processing
- **Message Routing**: Flexible routing capabilities
- **Monitoring**: Rich management interface and metrics
- **Celery Integration**: Excellent support for Celery workers

### Implementation Details
```python
# Celery Configuration
CELERY_BROKER_URL = 'amqp://admin:admin123@rabbitmq:5672//'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

# Queue Structure
queues = {
    'notifications.high_priority': {'routing_key': 'notifications.high'},
    'notifications.normal': {'routing_key': 'notifications.normal'},
    'notifications.low_priority': {'routing_key': 'notifications.low'}
}
```

### Consequences
- **Positive**: Reliable message delivery, good monitoring, flexible routing
- **Negative**: Additional operational complexity, resource overhead

---

## ADR-004: External Service Adapter Pattern

**Status**: ✅ Accepted  
**Date**: 2025-09-17  
**Deciders**: Development Team

### Context
The service needs to integrate with multiple external notification providers (AWS SES, Twilio, Firebase) with potential for future additions.

### Decision
Implement Adapter Pattern for external service integration with configurable providers.

### Options Considered
1. **Direct Integration**: Simple but tightly coupled
2. **Adapter Pattern**: Flexible, testable, but more complex
3. **Plugin Architecture**: Maximum flexibility, high complexity
4. **Third-party Library**: Less control, dependency risk

### Rationale
- **Testability**: Easy to mock adapters for unit testing
- **Flexibility**: Switch providers without code changes
- **Maintainability**: Clear separation of concerns
- **Extensibility**: Add new providers with minimal impact

### Implementation Details
```python
# Base Adapter Interface
class NotificationAdapter(ABC):
    @abstractmethod
    def send(self, recipient: str, subject: str, content: str) -> DeliveryResult:
        pass

# Concrete Implementations
class EmailAdapter(NotificationAdapter):
    def __init__(self, provider: str = 'ses'):
        self.provider = SESProvider() if provider == 'ses' else MockProvider()
    
    def send(self, recipient: str, subject: str, content: str) -> DeliveryResult:
        return self.provider.send_email(recipient, subject, content)

class SMSAdapter(NotificationAdapter):
    def __init__(self, provider: str = 'twilio'):
        self.provider = TwilioProvider() if provider == 'twilio' else MockProvider()
    
    def send(self, recipient: str, subject: str, content: str) -> DeliveryResult:
        return self.provider.send_sms(recipient, content)
```

### Consequences
- **Positive**: Flexible provider switching, easy testing, clean interfaces
- **Negative**: Additional abstraction layers, more initial development time

---

## ADR-005: PostgreSQL as Primary Database

**Status**: ✅ Accepted  
**Date**: 2025-09-16  
**Deciders**: Platform Team

### Context
Need to choose database for notification service considering data consistency, query patterns, and operational requirements.

### Decision
Use PostgreSQL as primary database with potential for read replicas.

### Options Considered
1. **PostgreSQL**: ACID compliance, rich feature set, team expertise
2. **MongoDB**: Document storage, flexible schema
3. **MySQL**: Popular, good performance
4. **DynamoDB**: Managed NoSQL, vendor lock-in
5. **Cassandra**: High scalability, complex operations

### Rationale
- **ACID Compliance**: Critical for notification delivery guarantees
- **JSON Support**: Native JSON columns for flexible data storage
- **Full-text Search**: Built-in search capabilities for templates
- **Ecosystem**: Excellent Django ORM support
- **Operational Expertise**: Team familiar with PostgreSQL operations

### Schema Design
```sql
-- Core notification tables
CREATE TABLE notification_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    type VARCHAR(20) NOT NULL, -- email, sms, push, in_app
    subject VARCHAR(200),
    content TEXT NOT NULL,
    variables JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE notification_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL,
    template_id UUID REFERENCES notification_templates(id),
    recipient VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- pending, sent, failed, bounced
    provider_response JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    sent_at TIMESTAMP,
    failed_at TIMESTAMP
);

CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER UNIQUE NOT NULL,
    email_enabled BOOLEAN DEFAULT true,
    sms_enabled BOOLEAN DEFAULT true,
    push_enabled BOOLEAN DEFAULT true,
    quiet_hours_start TIME DEFAULT '22:00',
    quiet_hours_end TIME DEFAULT '08:00',
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_notification_logs_user_id ON notification_logs(user_id);
CREATE INDEX idx_notification_logs_status ON notification_logs(status);
CREATE INDEX idx_notification_logs_created_at ON notification_logs(created_at);
```

### Consequences
- **Positive**: Strong consistency, rich query capabilities, team expertise
- **Negative**: Potential scaling limitations at very high volumes

---

## ADR-006: Container Orchestration with Docker Compose

**Status**: ✅ Accepted  
**Date**: 2025-09-18  
**Deciders**: Platform Team

### Context
Need container orchestration solution for development and potential production deployment.

### Decision
Use Docker Compose for development environment with Kubernetes readiness.

### Options Considered
1. **Docker Compose**: Simple, good for development
2. **Kubernetes**: Production-ready, complex setup
3. **Docker Swarm**: Simple clustering, limited features
4. **AWS ECS**: Managed service, vendor lock-in

### Rationale
- **Development Simplicity**: Easy local environment setup
- **Service Discovery**: Automatic service networking
- **Scalability**: Can run multiple instances of services
- **Production Path**: Easy migration to Kubernetes when needed

### Implementation Details
```yaml
# docker-compose.yml structure
services:
  notification-service:
    build: .
    ports: ["8000:8000"]
    depends_on: [postgres, redis, rabbitmq]
    
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: notification_service
      
  redis:
    image: redis:7-alpine
    
  rabbitmq:
    image: rabbitmq:3-management
    
  celery-worker:
    build: .
    command: celery -A notification_service worker
    
  celery-beat:
    build: .
    command: celery -A notification_service beat
    
  prometheus:
    image: prom/prometheus:latest
    
  grafana:
    image: grafana/grafana:latest
```

### Consequences
- **Positive**: Easy development setup, service orchestration, monitoring stack
- **Negative**: Not production-ready for high availability

---

## ADR-007: Monitoring and Observability Stack

**Status**: ✅ Accepted  
**Date**: 2025-09-18  
**Deciders**: Platform Team, DevOps

### Context
Need comprehensive monitoring solution for microservice health, performance, and business metrics.

### Decision
Implement Prometheus + Grafana stack with custom Django metrics and structured logging.

### Options Considered
1. **Prometheus + Grafana**: Open source, flexible, learning curve
2. **DataDog**: Comprehensive SaaS, expensive
3. **New Relic**: APM focused, good for Django
4. **ELK Stack**: Logging focused, resource intensive
5. **AWS CloudWatch**: Simple, basic features

### Rationale
- **Cost**: Open source solution
- **Flexibility**: Custom metrics and dashboards
- **Integration**: Good Django/Python ecosystem support
- **Alerting**: Built-in alerting capabilities
- **Community**: Large community and documentation

### Implementation Details
```python
# Custom Django metrics
from prometheus_client import Counter, Histogram, Gauge

notification_sent_total = Counter(
    'notifications_sent_total',
    'Total notifications sent',
    ['type', 'status']
)

notification_processing_time = Histogram(
    'notification_processing_seconds',
    'Time spent processing notifications',
    ['type']
)

# Health check metrics
@api_view(['GET'])
def health_metrics(request):
    return Response({
        'notifications_sent_24h': get_notifications_count_24h(),
        'active_templates': get_active_templates_count(),
        'queue_size': get_queue_size(),
        'error_rate': get_error_rate_1h()
    })
```

### Consequences
- **Positive**: Comprehensive monitoring, customizable, cost-effective
- **Negative**: Setup complexity, resource overhead

---

## ADR-008: API Versioning Strategy

**Status**: ✅ Accepted  
**Date**: 2025-09-19  
**Deciders**: Development Team

### Context
API needs versioning strategy to support backward compatibility during evolution.

### Decision
Use URL path versioning with semantic versioning (v1, v2, etc.).

### Options Considered
1. **URL Path Versioning**: `/api/v1/notifications/` - Clear, cacheable
2. **Header Versioning**: `Accept: application/vnd.api+json;version=1` - Clean URLs
3. **Query Parameter**: `/api/notifications/?version=1` - Simple
4. **No Versioning**: Risky for breaking changes

### Rationale
- **Clarity**: Version explicit in URL
- **Caching**: HTTP caches work correctly
- **Documentation**: Easy to document different versions
- **Client Support**: All HTTP clients support URL versioning

### Implementation Details
```python
# URL configuration
urlpatterns = [
    path('api/v1/', include('api.v1.urls')),
    path('api/v2/', include('api.v2.urls')),  # Future version
]

# Deprecation strategy
class NotificationViewV1(APIView):
    """
    DEPRECATED: This endpoint will be removed in v3.
    Please migrate to /api/v2/notifications/send/
    """
    def post(self, request):
        # Add deprecation header
        response = process_notification(request.data)
        response['Deprecation'] = 'version="v1"'
        response['Sunset'] = 'Mon, 01 Jan 2026 00:00:00 GMT'
        return response
```

### Consequences
- **Positive**: Clear versioning, backward compatibility support
- **Negative**: URL proliferation, maintenance overhead

---

## ADR-009: Authentication and Authorization

**Status**: ✅ Accepted  
**Date**: 2025-09-19  
**Deciders**: Security Team, Development Team

### Context
Microservice needs secure authentication for API access while integrating with existing monolith authentication.

### Decision
Use JWT token-based authentication with role-based access control (RBAC).

### Options Considered
1. **JWT Tokens**: Stateless, scalable, standard
2. **Session Cookies**: Simple, requires shared storage
3. **API Keys**: Simple, less secure
4. **OAuth 2.0**: Complex, industry standard
5. **mTLS**: High security, operational complexity

### Rationale
- **Stateless**: No session storage required
- **Scalability**: Tokens can be validated independently
- **Integration**: Works with existing authentication system
- **Standards**: Industry standard approach

### Implementation Details
```python
# JWT Authentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

class NotificationPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method == 'POST':
            return request.user.has_perm('notifications.send')
        elif request.method in ['GET', 'HEAD']:
            return request.user.has_perm('notifications.view')
        return False

# API View with authentication
class SendNotificationView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, NotificationPermission]
    
    def post(self, request):
        # Process authenticated notification request
        pass
```

### Consequences
- **Positive**: Scalable, stateless, secure
- **Negative**: Token management complexity, potential replay attacks

---

## ADR-010: Error Handling and Retry Strategy

**Status**: ✅ Accepted  
**Date**: 2025-09-20  
**Deciders**: Development Team

### Context
Notification delivery can fail due to external service issues, network problems, or rate limits. Need robust error handling and retry mechanism.

### Decision
Implement exponential backoff retry strategy with dead letter queue for failed messages.

### Options Considered
1. **No Retries**: Simple but unreliable
2. **Fixed Interval Retries**: Predictable but may cause thundering herd
3. **Exponential Backoff**: Reduces load, good for rate limits
4. **Immediate Retries**: Fast but may overwhelm failing services

### Rationale
- **Reliability**: Handles transient failures automatically
- **Rate Limit Handling**: Exponential backoff respects rate limits
- **System Protection**: Prevents overwhelming failing external services
- **Monitoring**: Failed messages collected for analysis

### Implementation Details
```python
# Celery retry configuration
@shared_task(bind=True, max_retries=5)
def send_notification_task(self, notification_data):
    try:
        # Attempt to send notification
        adapter = get_notification_adapter(notification_data['type'])
        result = adapter.send(**notification_data)
        
        if not result.success:
            # Retry with exponential backoff
            countdown = 2 ** self.request.retries
            raise self.retry(countdown=countdown, exc=result.error)
            
        return result
        
    except Exception as exc:
        # Log error and retry
        logger.error(f"Notification failed: {exc}")
        countdown = 2 ** self.request.retries  # 2, 4, 8, 16, 32 seconds
        raise self.retry(countdown=countdown, exc=exc)

# Dead letter queue handling
@shared_task
def handle_failed_notification(notification_data, error_info):
    """Process notifications that failed all retry attempts"""
    NotificationLog.objects.filter(
        id=notification_data['log_id']
    ).update(
        status='permanently_failed',
        error_details=error_info,
        failed_at=timezone.now()
    )
```

### Consequences
- **Positive**: Improved reliability, graceful failure handling
- **Negative**: Increased complexity, delayed error feedback

---

## System Architecture Overview

### High-Level Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Django        │    │  Notification   │    │   External      │
│   Monolith      │────│   Microservice  │────│   Providers     │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
    ┌────▼────┐             ┌────▼────┐             ┌────▼────┐
    │ User    │             │ Message │             │ AWS SES │
    │ Actions │             │ Queue   │             │ Twilio  │
    │         │             │(RabbitMQ│             │Firebase │
    └─────────┘             └─────────┘             └─────────┘
```

### Service Interaction Flow
```
1. Client Request → API Gateway → Notification Service
2. Notification Service → Database (Templates, Preferences)
3. Notification Service → Message Queue (Async Processing)
4. Celery Worker → External Provider (SES/Twilio/Firebase)
5. Delivery Status → Database Update → Client Response
```

### Data Flow Architecture
```
┌───────────────┐    ┌────────────────┐    ┌──────────────┐
│   REST API    │────│  Business      │────│   External   │
│   Layer       │    │  Logic Layer   │    │   Adapters   │
└───────────────┘    └────────────────┘    └──────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌────────────────┐    ┌──────────────┐
│   Django      │    │   PostgreSQL   │    │   Message    │
│   Models      │    │   Database     │    │   Queue      │
└───────────────┘    └────────────────┘    └──────────────┘
```

## Technology Stack Summary

### Core Services
- **Application**: Django 4.2.7 + Django REST Framework
- **Database**: PostgreSQL 15
- **Message Queue**: RabbitMQ 3 with Celery
- **Cache**: Redis 7

### External Integrations
- **Email**: AWS SES
- **SMS**: Twilio
- **Push**: Firebase Cloud Messaging
- **Monitoring**: Prometheus + Grafana

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Authentication**: JWT tokens
- **API Documentation**: OpenAPI/Swagger
- **Testing**: pytest + Django Test Framework

---

**Document Version**: 1.0  
**Last Updated**: September 25, 2025  
**Status**: Active Implementation  
**Next Review**: October 25, 2025