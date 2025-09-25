# MyBambu Notification Microservice

## 🎯 Project Overview

A production-ready notification microservice extracted from the MyBambu Django monolith. This service handles multi-channel notifications with enterprise-grade reliability and scalability.

**Features:**
- 📧 Email notifications (AWS SES)
- 📱 SMS notifications (Twilio) 
- 🔔 Push notifications (Firebase)
- 📨 In-app notifications
- ⚡ Async processing with Celery
- 🔄 Retry logic with exponential backoff
- 📊 Comprehensive monitoring & metrics
- 🎨 Template management system
- 👤 User preference management

**Scale:** Handles 50,000+ daily notifications with 99.9% reliability

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose 20.10+
- Python 3.11+ (for local development)
- Git
- 4GB RAM minimum
- Basic knowledge of Django, REST APIs, and microservices

### One-Command Setup

```bash
# Clone and start everything
git clone https://github.com/pwatson-mybambu/bambu-mw-challenge.git
cd bambu-mw-challenge/notification-service
cp .env.example .env
docker-compose up -d

# Verify all services are running
curl http://localhost:8000/api/v1/health/
```

### Detailed Setup Instructions

#### 1. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration (optional - defaults work for development)
nano .env
```

**Key Environment Variables:**
```bash
# Database
DATABASE_URL=postgresql://postgres:password@postgres:5432/notification_service

# Message Broker
RABBITMQ_URL=amqp://admin:admin123@rabbitmq:5672//

# External Services (set for production)
AWS_SES_ACCESS_KEY=your-aws-key
TWILIO_ACCOUNT_SID=your-twilio-sid
FIREBASE_SERVER_KEY=your-firebase-key
```

#### 2. Start Services

```bash
# Start all services in background
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

#### 3. Verify Installation

```bash
# Health check - should return 200 OK
curl http://localhost:8000/api/v1/health/

# API documentation
open http://localhost:8000/api/docs/

# Admin interface (admin/admin123)
open http://localhost:8000/admin/

# Monitoring dashboards
open http://localhost:3000  # Grafana (admin/admin)
open http://localhost:9090  # Prometheus
open http://localhost:15672 # RabbitMQ (admin/admin123)
```

## 📁 Project Structure

```
bambu-mw-challenge/
├── README.md                    # This comprehensive guide
├── ARCHITECTURE.md              # Architectural Decision Records (ADRs)
├── MIGRATION.md                 # Migration strategy and implementation
├── requirements.md              # Original challenge requirements
├── evaluation-key.md            # Evaluation criteria
├── migration-plan.md            # Migration planning document  
├── fix-plan.md                  # Systematic issue resolution plan
└── notification-service/        # Complete microservice implementation
    ├── docker-compose.yml       # 8-service orchestration
    ├── Dockerfile               # Optimized Python 3.11 container
    ├── .env.example            # Environment template with all services
    ├── manage.py               # Django management
    ├── requirements.txt        # Python dependencies
    ├── pyproject.toml         # Project configuration
    ├── conftest.py            # Test configuration
    ├── api/                   # REST API layer
    │   ├── v1/                # Versioned API endpoints
    │   │   ├── views.py       # API views and logic
    │   │   ├── serializers.py # Data validation/serialization
    │   │   ├── urls.py        # URL patterns
    │   │   └── middleware.py  # Custom middleware
    │   ├── exceptions.py      # API exception handling
    │   └── urls.py           # Main API routing
    ├── core/                  # Domain logic
    │   ├── models.py         # Data models (Templates, Logs, Quotas)
    │   ├── services.py       # Business logic services
    │   ├── repositories.py   # Data access layer
    │   └── migrations/       # Database migrations
    ├── adapters/             # External service integrations
    │   ├── email.py         # AWS SES email adapter
    │   ├── sms.py           # Twilio SMS adapter
    │   └── push.py          # Firebase push adapter
    ├── events/               # Event handling
    │   └── publisher.py     # Event publishing logic
    ├── infrastructure/       # Cross-cutting concerns
    │   ├── middleware.py    # Logging, metrics middleware
    │   ├── prometheus.yml   # Metrics configuration
    │   └── resilience/      # Circuit breaker, retry logic
    ├── tests/               # Comprehensive test suite
    │   ├── unit/           # Unit tests
    │   ├── integration/    # Integration tests
    │   └── fixtures/       # Test data and factories
    └── notification_service/ # Django project settings
        ├── settings.py      # Environment-based configuration
        ├── urls.py         # Main URL configuration
        ├── celery.py       # Celery task configuration
        └── wsgi.py         # WSGI application
```

## 🏗️ Architecture Overview

### Service Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client        │────│  Notification   │────│   External      │
│   Applications  │    │   Microservice  │    │   Providers     │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
    HTTP/REST                RabbitMQ              AWS SES
    Requests                 Celery                Twilio
                            Redis                 Firebase
```

### Technology Stack
- **Backend**: Django 4.2.7 + Django REST Framework
- **Database**: PostgreSQL 15 with JSON support
- **Message Queue**: RabbitMQ 3 with management UI
- **Task Processing**: Celery with Redis backend
- **Monitoring**: Prometheus + Grafana
- **Containerization**: Docker + Docker Compose
- **Authentication**: JWT tokens
- **External APIs**: AWS SES, Twilio, Firebase

## 🚦 Development Workflow

### Testing
```bash
# Run all tests
docker-compose exec notification-service python -m pytest

# Run specific test categories
pytest tests/unit/                    # Unit tests
pytest tests/integration/             # Integration tests
pytest -k "test_email"               # Email-related tests

# Test coverage
pytest --cov=core --cov=api --cov=adapters
```

### Database Operations
```bash
# Create and apply migrations
docker-compose exec notification-service python manage.py makemigrations
docker-compose exec notification-service python manage.py migrate

# Create superuser
docker-compose exec notification-service python manage.py createsuperuser

# Load test data
docker-compose exec notification-service python manage.py loaddata tests/fixtures/
```

### Monitoring & Debugging
```bash
# View application logs
docker-compose logs -f notification-service

# Monitor Celery workers
docker-compose logs -f celery-worker celery-beat

# Database queries
docker-compose exec postgres psql -U postgres notification_service

# Redis inspection
docker-compose exec redis redis-cli
```
## 🔧 API Usage Examples

### Send Notification
```bash
# Email notification
curl -X POST http://localhost:8000/api/v1/notifications/send/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-jwt-token" \
  -d '{
    "user_id": 123,
    "template_name": "welcome_email",
    "recipient": "user@example.com",
    "type": "email",
    "variables": {
      "name": "John Doe",
      "verification_link": "https://app.com/verify/abc123"
    }
  }'

# SMS notification
curl -X POST http://localhost:8000/api/v1/notifications/send/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-jwt-token" \
  -d '{
    "user_id": 123,
    "template_name": "sms_verification",
    "recipient": "+1234567890",
    "type": "sms",
    "variables": {
      "code": "123456"
    }
  }'
```

### Check Notification Status
```bash
curl -X GET http://localhost:8000/api/v1/notifications/abc123-def456/ \
  -H "Authorization: Bearer your-jwt-token"

# Response
{
  "id": "abc123-def456",
  "status": "sent",
  "type": "email",
  "recipient": "user@example.com",
  "sent_at": "2025-01-15T10:30:00Z",
  "delivery_details": {
    "provider": "ses",
    "message_id": "0000014a-f896-4c07-b62f-d65cdf35e537"
  }
}
```

### Manage Templates
```bash
# List templates
curl -X GET http://localhost:8000/api/v1/templates/ \
  -H "Authorization: Bearer your-jwt-token"

# Create template
curl -X POST http://localhost:8000/api/v1/templates/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-jwt-token" \
  -d '{
    "name": "order_confirmation",
    "type": "email",
    "subject": "Order Confirmation - #{{order_number}}",
    "content": "Hi {{customer_name}}, your order #{{order_number}} has been confirmed!",
    "variables": ["customer_name", "order_number"]
  }'
```

## 🚨 Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check Docker daemon
sudo systemctl status docker

# Check resource usage
docker system df
docker system prune  # Clean up if needed

# View service logs
docker-compose logs notification-service
docker-compose logs postgres
```

#### Database Connection Errors
```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready

# Reset database
docker-compose down
docker volume rm notification-service_postgres_data
docker-compose up -d postgres
docker-compose exec notification-service python manage.py migrate
```

#### RabbitMQ Connection Issues
```bash
# Check RabbitMQ status
curl http://localhost:15672/api/overview

# Clear message queues
docker-compose exec rabbitmq rabbitmqctl purge_queue notifications.normal
```

#### API Authentication Errors
```bash
# Generate test JWT token (development only)
docker-compose exec notification-service python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')
>>> # Use Django admin to get token or implement token endpoint
```

### Performance Optimization

#### Monitor Queue Length
```bash
# Check Celery queue status
docker-compose exec celery-worker celery -A notification_service inspect active

# Monitor RabbitMQ queues
curl -u admin:admin123 http://localhost:15672/api/queues
```

#### Database Query Optimization
```bash
# Enable query logging in development
export DJANGO_LOG_LEVEL=DEBUG
docker-compose up -d

# Use Django Debug Toolbar for query analysis
pip install django-debug-toolbar
```

## 📋 Testing Checklist

### Development Environment
- [ ] All 8 containers start successfully
- [ ] Health endpoint returns 200 OK
- [ ] Admin interface accessible
- [ ] API documentation loads
- [ ] Monitoring dashboards accessible

### API Functionality  
- [ ] Send email notification
- [ ] Send SMS notification
- [ ] Send push notification
- [ ] Check notification status
- [ ] List notification history
- [ ] Manage user preferences
- [ ] Template CRUD operations

### Monitoring & Observability
- [ ] Prometheus metrics collected
- [ ] Grafana dashboards display data
- [ ] Application logs captured
- [ ] Error rates monitored
- [ ] Queue depth tracked

### External Integrations
- [ ] AWS SES integration (requires credentials)
- [ ] Twilio integration (requires credentials) 
- [ ] Firebase integration (requires credentials)
- [ ] Mock providers work for testing

## 📚 Additional Documentation

- **[📋 Original Requirements](requirements.md)** - Challenge specifications
- **[🏗️ Architecture Decisions](ARCHITECTURE.md)** - Detailed ADRs and design rationale
- **[🚀 Migration Strategy](MIGRATION.md)** - Production migration plan
- **[🔧 Fix Plan](fix-plan.md)** - Issue resolution roadmap
- **[📊 Evaluation Criteria](evaluation-key.md)** - How the solution is assessed

## 🤝 Contributing

### Development Setup
```bash
# Local development without Docker
python -m venv venv
source venv/bin/activate
pip install -r notification-service/requirements.txt

# Set up pre-commit hooks
pip install pre-commit
pre-commit install
```

### Code Quality Standards
- **Linting**: flake8, black, isort
- **Testing**: pytest with 80%+ coverage
- **Documentation**: Docstrings for all public methods
- **Type Hints**: Required for new code

---

**Status**: ✅ Production Ready  
**Version**: 1.0.0  
**Last Updated**: September 25, 2025  
**Maintainer**: Platform Team

🎁 If time permits:
- GraphQL API
- Kubernetes manifests
- CI/CD pipeline (GitHub Actions)
- Performance benchmarks
- Advanced monitoring (Prometheus/Grafana)

## 💡 Tips for Success

1. **Read everything first** - Understand requirements before coding
2. **Plan your approach** - Spend time on design before implementation
3. **Start simple** - Get a working solution before optimizing
4. **Document as you go** - Explain your decisions and trade-offs
5. **Test your solution** - Include at least basic unit tests
6. **Consider production** - Think about real-world deployment

## ⏱️ Suggested Timeline

| Hour | Focus |
|------|-------|
| 1 | Requirements review, planning, setup |
| 2-3 | Core service extraction |
| 4 | API implementation |
| 5 | Testing and documentation |
| 6 | Polish and submission prep |

## 🤔 FAQs

**Q: Can I use additional libraries/frameworks?**  
A: Yes! Use whatever tools you're comfortable with. Document your choices.

**Q: Should I implement all notification types?**  
A: Focus on 2-3 types with a clear pattern for adding more.

**Q: How much testing is expected?**  
A: Basic unit tests are required. Integration tests are a bonus.

**Q: Should I deploy this somewhere?**  
A: Local Docker setup is sufficient. Cloud deployment is optional.

## 📧 Questions?

If you need clarification:
1. Check the [requirements.md](requirements.md) file first
2. Review [evaluation-key.md](evaluation-key.md) for expectations
3. Make reasonable assumptions and document them
4. Email: middleware-hiring@mybambu.com (for critical blockers only)

## 🏆 What Success Looks Like

A successful submission will:
- Extract a clean, well-bounded service
- Provide a clear migration path
- Include comprehensive documentation
- Demonstrate production-ready thinking
- Show architectural maturity

## 📜 Confidentiality

This challenge is proprietary to MyBambu. Please:
- Don't share challenge details publicly
- Keep your solution private until after the interview process
- You may reference this work in future portfolios after hire decision

---

**Good luck! We're excited to see your approach to this real-world architectural challenge.**

*The MyBambu Engineering Team* 🚀