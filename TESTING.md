# Testing Strategy and Guidelines
# Notification Microservice

## 🧪 Testing Overview

This document outlines the comprehensive testing strategy for the Notification Microservice, including unit tests, integration tests, performance tests, and end-to-end testing scenarios.

## 🏗️ Testing Architecture

### Test Pyramid Structure

```
                 E2E Tests
               (API + Docker)
              ┌─────────────┐
             │   12 tests   │
            └─────────────────┘
           Integration Tests
          (API + Database + Services)
         ┌─────────────────────┐
        │      45 tests        │
       └───────────────────────┘
      Unit Tests
     (Services + Models + Adapters)
    ┌─────────────────────────────┐
   │          120 tests           │
  └───────────────────────────────┘
```

### Test Categories

1. **Unit Tests** (80% coverage target)
   - Service layer logic
   - Model validations
   - Adapter implementations
   - Utility functions

2. **Integration Tests** (API endpoints)
   - REST API functionality
   - Database operations
   - External service mocking
   - Authentication/authorization

3. **End-to-End Tests** (Critical user flows)
   - Complete notification workflows
   - Docker container orchestration
   - Monitoring stack validation

4. **Performance Tests** (Load scenarios)
   - High-volume notification handling
   - Concurrent request processing
   - Database query optimization

## 📂 Test Directory Structure

```
tests/
├── __init__.py
├── conftest.py                     # Test configuration and fixtures
├── unit/                          # Unit tests
│   ├── __init__.py
│   ├── test_models.py            # Model validation tests
│   ├── test_services.py          # Service layer tests
│   ├── test_adapters.py          # External adapter tests
│   └── test_repositories.py     # Data access tests
├── integration/                   # Integration tests
│   ├── __init__.py
│   ├── test_api_endpoints.py     # API endpoint tests
│   ├── test_api_comprehensive.py # Enhanced API testing
│   ├── test_database.py          # Database integration
│   └── test_external_services.py # External service mocking
├── e2e/                          # End-to-end tests
│   ├── __init__.py
│   ├── test_notification_flow.py # Complete workflows
│   └── test_docker_stack.py     # Container testing
├── performance/                   # Performance tests
│   ├── __init__.py
│   ├── test_load_scenarios.py   # Load testing
│   └── test_concurrent_access.py # Concurrency tests
└── fixtures/                     # Test data
    ├── __init__.py
    ├── factories.py              # Factory Boy factories
    ├── notification_logs.json    # Sample notification data
    ├── notification_templates.json # Template fixtures
    ├── user_preferences.json     # User preference data
    └── notification_quotas.json  # Quota test data
```

## 🔧 Test Configuration

### pytest Configuration (pyproject.toml)

```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "notification_service.settings"
python_files = ["tests.py", "test_*.py", "*_tests.py"]
python_classes = ["Test*", "*Tests", "*Test"]
python_functions = ["test_*"]
addopts = [
    "--verbose",
    "--tb=short",
    "--strict-markers",
    "--strict-config",
    "--cov=core",
    "--cov=api",
    "--cov=adapters",
    "--cov-report=html:htmlcov",
    "--cov-report=term-missing",
    "--cov-fail-under=80"
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "performance: Performance tests",
    "slow: Tests that run slowly",
    "external: Tests requiring external services"
]
```

### Test Database Configuration

```python
# settings_test.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'test_notification_service',
        'USER': 'postgres',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
        'TEST': {
            'NAME': 'test_notification_service',
        }
    }
}

# Use in-memory cache for testing
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Disable Celery task execution in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
```

## 🧪 Test Categories Detail

### Unit Tests

#### Service Layer Tests (`test_services.py`)

```python
class NotificationServiceTest(TestCase):
    """Test core notification service logic."""
    
    def test_send_notification_success(self):
        """Test successful notification sending."""
        
    def test_send_notification_invalid_template(self):
        """Test handling of invalid template."""
        
    def test_send_notification_quota_exceeded(self):
        """Test quota enforcement."""
        
    def test_send_notification_user_preferences(self):
        """Test user preference filtering."""
        
    def test_retry_logic_exponential_backoff(self):
        """Test retry mechanism with exponential backoff."""
```

#### Model Tests (`test_models.py`)

```python
class NotificationTemplateTest(TestCase):
    """Test notification template model."""
    
    def test_template_validation(self):
        """Test template field validation."""
        
    def test_variable_extraction(self):
        """Test automatic variable extraction from content."""
        
    def test_template_rendering(self):
        """Test template rendering with variables."""
        
    def test_unique_name_constraint(self):
        """Test unique template name enforcement."""
```

#### Adapter Tests (`test_adapters.py`)

```python
class EmailAdapterTest(TestCase):
    """Test email adapter implementations."""
    
    @patch('boto3.client')
    def test_ses_adapter_success(self, mock_boto):
        """Test successful SES email sending."""
        
    @patch('boto3.client')
    def test_ses_adapter_failure(self, mock_boto):
        """Test SES error handling."""
        
    def test_mock_adapter_development(self):
        """Test mock adapter for development."""
```

### Integration Tests

#### API Endpoint Tests (`test_api_comprehensive.py`)

```python
class NotificationAPIIntegrationTest(APITestCase):
    """Comprehensive API integration tests."""
    
    def test_send_email_notification_success(self):
        """Test complete email notification flow."""
        
    def test_send_notification_authentication(self):
        """Test API authentication requirements."""
        
    def test_send_notification_validation(self):
        """Test request validation and error responses."""
        
    def test_notification_status_tracking(self):
        """Test notification status updates."""
        
    def test_webhook_delivery_updates(self):
        """Test webhook processing for delivery updates."""
```

#### Database Integration Tests (`test_database.py`)

```python
class DatabaseIntegrationTest(TransactionTestCase):
    """Test database operations and transactions."""
    
    def test_concurrent_notification_creation(self):
        """Test handling concurrent notification creation."""
        
    def test_bulk_status_updates(self):
        """Test efficient bulk status updates."""
        
    def test_database_constraints(self):
        """Test database constraint enforcement."""
```

### End-to-End Tests

#### Complete Workflow Tests (`test_notification_flow.py`)

```python
class NotificationWorkflowE2ETest(LiveServerTestCase):
    """End-to-end notification workflow tests."""
    
    def test_complete_email_workflow(self):
        """Test: API request → Queue → Processing → Delivery → Status Update"""
        
    def test_failed_notification_retry(self):
        """Test failure handling and retry mechanism."""
        
    def test_user_preference_blocking(self):
        """Test user preference enforcement."""
```

#### Docker Stack Tests (`test_docker_stack.py`)

```python
class DockerStackE2ETest(TestCase):
    """Test complete Docker stack functionality."""
    
    def test_all_services_healthy(self):
        """Test all Docker services start and respond."""
        
    def test_service_communication(self):
        """Test inter-service communication."""
        
    def test_monitoring_stack(self):
        """Test Prometheus and Grafana functionality."""
```

### Performance Tests

#### Load Testing (`test_load_scenarios.py`)

```python
class LoadTestScenarios(TestCase):
    """Performance and load testing scenarios."""
    
    def test_high_volume_notifications(self):
        """Test handling 1000+ notifications per minute."""
        
    def test_concurrent_api_requests(self):
        """Test concurrent API request handling."""
        
    def test_database_query_performance(self):
        """Test database query optimization."""
        
    def test_memory_usage_patterns(self):
        """Test memory usage under load."""
```

## 🚀 Running Tests

### Local Development

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run specific test categories
pytest -m unit                    # Unit tests only
pytest -m integration            # Integration tests only
pytest -m "not slow"             # Skip slow tests
pytest -m "external"             # External service tests

# Run tests with coverage
pytest --cov=core --cov=api --cov=adapters

# Run specific test files
pytest tests/unit/test_services.py
pytest tests/integration/test_api_endpoints.py

# Run with parallel execution
pytest -n auto                   # Auto-detect CPU cores
pytest -n 4                      # Use 4 processes
```

### Docker-based Testing

```bash
# Run tests in Docker container
docker-compose exec notification-service pytest

# Run tests with fresh database
docker-compose run --rm notification-service pytest --create-db

# Run performance tests
docker-compose run --rm notification-service pytest -m performance

# Run with test database
docker-compose -f docker-compose.test.yml up -d
docker-compose -f docker-compose.test.yml exec notification-service pytest
```

### Continuous Integration

```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: password
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        pip install -r notification-service/requirements.txt
        pip install pytest-cov pytest-django
    - name: Run tests
      run: |
        cd notification-service
        pytest --cov --cov-report=xml
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## 📊 Test Data Management

### Factory Boy Factories

```python
# tests/fixtures/factories.py
import factory
from factory.django import DjangoModelFactory
from core.models import NotificationTemplate, NotificationLog, UserPreference

class NotificationTemplateFactory(DjangoModelFactory):
    class Meta:
        model = NotificationTemplate
    
    name = factory.Sequence(lambda n: f"template_{n}")
    type = factory.Iterator(['email', 'sms', 'push', 'in_app'])
    subject = factory.Faker('sentence', nb_words=4)
    content = factory.Faker('text', max_nb_chars=200)
    variables = factory.List(['name', 'message'])
    active = True

class NotificationLogFactory(DjangoModelFactory):
    class Meta:
        model = NotificationLog
    
    user_id = factory.Faker('random_int', min=1, max=1000)
    template = factory.SubFactory(NotificationTemplateFactory)
    recipient = factory.Faker('email')
    status = factory.Iterator(['pending', 'sent', 'failed', 'bounced'])
    type = factory.LazyAttribute(lambda obj: obj.template.type)
    
class UserPreferenceFactory(DjangoModelFactory):
    class Meta:
        model = UserPreference
    
    user_id = factory.Faker('random_int', min=1, max=1000)
    email_enabled = True
    sms_enabled = True
    push_enabled = False
    preferences = factory.Dict({
        'quiet_hours': {
            'enabled': True,
            'start': '22:00',
            'end': '08:00'
        }
    })
```

### Test Fixtures

```python
# tests/conftest.py
import pytest
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

@pytest.fixture
def test_user():
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )

@pytest.fixture
def authenticated_client(test_user):
    """Create an authenticated API client."""
    from rest_framework.test import APIClient
    
    client = APIClient()
    refresh = RefreshToken.for_user(test_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client

@pytest.fixture
def notification_template():
    """Create a test notification template."""
    from tests.fixtures.factories import NotificationTemplateFactory
    return NotificationTemplateFactory()

@pytest.fixture
def mock_email_adapter():
    """Mock email adapter for testing."""
    with patch('adapters.email.EmailAdapter.send') as mock:
        mock.return_value = Mock(
            success=True,
            provider_response={'MessageId': 'test-id'}
        )
        yield mock
```

## 🔍 Test Quality Metrics

### Coverage Targets

- **Overall Coverage**: 80% minimum
- **Core Services**: 90% minimum
- **API Endpoints**: 85% minimum
- **Models**: 95% minimum
- **Critical Paths**: 100% (notification sending, user preferences)

### Quality Metrics

```bash
# Generate coverage report
pytest --cov --cov-report=html

# Check test quality
pytest --cov --cov-fail-under=80

# Mutation testing (optional)
pip install mutmut
mutmut run --paths-to-mutate=core/,api/,adapters/
```

### Performance Benchmarks

```python
# Performance test example
def test_notification_processing_performance(self):
    """Test notification processing stays under performance thresholds."""
    import time
    
    start_time = time.time()
    
    # Process 100 notifications
    for i in range(100):
        self.send_test_notification()
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    # Should process 100 notifications in under 5 seconds
    self.assertLess(processing_time, 5.0)
    
    # Average processing time should be under 50ms per notification
    avg_time = processing_time / 100
    self.assertLess(avg_time, 0.05)
```

## 🐛 Test Debugging

### Debugging Failed Tests

```bash
# Run with detailed output
pytest -vvv --tb=long

# Run with pdb on failure
pytest --pdb

# Run specific failing test
pytest tests/unit/test_services.py::NotificationServiceTest::test_send_notification -vvv

# Print statements (use capfd fixture)
def test_with_debug_output(capfd):
    print("Debug info here")
    # ... test code ...
    captured = capfd.readouterr()
    assert "Debug info" in captured.out
```

### Test Data Inspection

```python
# Inspect test database state
def test_with_data_inspection(self):
    # ... test operations ...
    
    # Print current database state
    from core.models import NotificationLog
    logs = NotificationLog.objects.all()
    for log in logs:
        print(f"Log {log.id}: {log.status}")
    
    # Use Django's testing client to inspect responses
    response = self.client.get('/api/v1/notifications/')
    print(f"Response data: {response.data}")
```

## 📈 Test Automation

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
- repo: local
  hooks:
  - id: pytest
    name: pytest
    entry: pytest
    language: system
    types: [python]
    args: [--maxfail=1, -q]
    pass_filenames: false
```

### Test Automation Scripts

```bash
#!/bin/bash
# scripts/run_tests.sh

set -e

echo "Starting test suite..."

# Setup test environment
export DJANGO_SETTINGS_MODULE=notification_service.settings_test

# Run linting
echo "Running linting..."
flake8 core/ api/ adapters/
black --check core/ api/ adapters/

# Run tests with coverage
echo "Running tests..."
pytest --cov --cov-report=term-missing --cov-fail-under=80

# Run security checks
echo "Running security checks..."
bandit -r core/ api/ adapters/

echo "All tests passed! ✅"
```

---

**Testing Framework**: pytest + Django Test Framework  
**Coverage Tool**: pytest-cov  
**Factories**: Factory Boy  
**Mocking**: unittest.mock + pytest-mock  
**Performance**: pytest-benchmark  
**Last Updated**: September 25, 2025