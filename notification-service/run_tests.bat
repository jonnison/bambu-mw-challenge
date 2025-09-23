@echo off
REM Test runner script for Windows

echo Starting comprehensive test suite...

REM Set environment variables
set DJANGO_SETTINGS_MODULE=notification_service.settings
set PYTHONDONTWRITEBYTECODE=1

REM Create test database
echo Setting up test database...
python manage.py migrate --run-syncdb

REM Run unit tests
echo Running unit tests...
pytest tests/unit/ -v --cov=core --cov=api --cov=adapters -m unit

REM Run integration tests
echo Running integration tests...
pytest tests/integration/ -v --cov-append -m integration

REM Run all tests with coverage
echo Running complete test suite with coverage...
pytest tests/ --cov=core --cov=api --cov=adapters --cov=events --cov=infrastructure --cov=health_check --cov-report=html:htmlcov --cov-report=term-missing --cov-report=xml --cov-fail-under=80 -v

echo Test suite completed!
echo Coverage report available at: htmlcov/index.html