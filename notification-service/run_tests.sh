#!/bin/bash
# Test runner script for comprehensive testing

echo "Starting comprehensive test suite..."

# Set environment variables
export DJANGO_SETTINGS_MODULE=notification_service.settings
export PYTHONDONTWRITEBYTECODE=1

# Create test database
echo "Setting up test database..."
python manage.py migrate --run-syncdb

# Run unit tests
echo "Running unit tests..."
pytest tests/unit/ -v --cov=core --cov=api --cov=adapters -m unit

# Run integration tests
echo "Running integration tests..."
pytest tests/integration/ -v --cov-append -m integration

# Run all tests with coverage
echo "Running complete test suite with coverage..."
pytest tests/ --cov=core --cov=api --cov=adapters --cov=events --cov=infrastructure --cov=health_check \
    --cov-report=html:htmlcov \
    --cov-report=term-missing \
    --cov-report=xml \
    --cov-fail-under=80 \
    -v

# Generate coverage badge
echo "Generating coverage badge..."
coverage-badge -o coverage.svg

echo "Test suite completed!"
echo "Coverage report available at: htmlcov/index.html"