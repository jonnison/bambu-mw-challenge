#!/bin/bash
# Complete system validation script for Notification Microservice
# Tests all components and validates the complete setup

set -e

# Change to notification-service directory if not already there
if [ ! -f "docker-compose.yml" ]; then
    if [ -f "notification-service/docker-compose.yml" ]; then
        cd notification-service
        echo "🔄 Changed to notification-service directory"
    else
        echo "❌ Could not find docker-compose.yml file"
        exit 1
    fi
fi

echo "🚀 Starting complete system validation..."
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        exit 1
    fi
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Test 1: Docker containers status
echo ""
echo "📦 Testing Docker containers..."
echo "--------------------------------"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_status 1 "docker-compose command not found"
fi

# Check container status
containers=$(docker-compose ps --services)
total_services=8

running_count=0
for service in $containers; do
    if docker-compose ps $service | grep -q "Up"; then
        print_status 0 "$service container is running"
        ((running_count++))
    else
        print_warning "$service container is not running properly"
    fi
done

print_info "Running containers: $running_count/$total_services"

# Test 2: Core service endpoints
echo ""
echo "🌐 Testing core service endpoints..."
echo "-------------------------------------"

# Health check endpoint
print_info "Testing health endpoint..."
if curl -sf http://localhost:8000/health/ > /dev/null; then
    print_status 0 "Health endpoint responding"
    
    # Get health status details
    health_response=$(curl -s http://localhost:8000/health/)
    if echo "$health_response" | grep -q '"status": "healthy"'; then
        print_status 0 "Health status is healthy"
    else
        print_status 1 "Health status is not healthy"
    fi
else
    print_status 1 "Health endpoint not responding"
fi

# API documentation
print_info "Testing API documentation..."
if curl -sf http://localhost:8000/api/docs/ > /dev/null; then
    print_status 0 "API documentation accessible"
else
    print_status 1 "API documentation not accessible"
fi

# Django admin
print_info "Testing Django admin interface..."
if curl -sf http://localhost:8000/admin/ > /dev/null; then
    print_status 0 "Django admin interface accessible"
else
    print_status 1 "Django admin interface not accessible"
fi

# Test 3: Database connectivity
echo ""
echo "🗄️  Testing database connectivity..."
echo "------------------------------------"

# PostgreSQL health check
if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    print_status 0 "PostgreSQL database is ready"
else
    print_status 1 "PostgreSQL database is not ready"
fi

# Test Django database connection
print_info "Testing Django database connection..."
if docker-compose exec -T notification-service python manage.py check --database default > /dev/null 2>&1; then
    print_status 0 "Django database connection successful"
else
    print_status 1 "Django database connection failed"
fi

# Test 4: Message queue connectivity
echo ""
echo "📬 Testing message queue connectivity..."
echo "---------------------------------------"

# RabbitMQ management interface
if curl -sf http://localhost:15672/ > /dev/null; then
    print_status 0 "RabbitMQ management interface accessible"
else
    print_status 1 "RabbitMQ management interface not accessible"
fi

# Test RabbitMQ API
print_info "Testing RabbitMQ API..."
rabbitmq_status=$(curl -s -u admin:admin123 http://localhost:15672/api/overview | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('node', 'unknown'))" 2>/dev/null || echo "failed")

if [ "$rabbitmq_status" != "failed" ] && [ "$rabbitmq_status" != "unknown" ]; then
    print_status 0 "RabbitMQ API responding (node: $rabbitmq_status)"
else
    print_status 1 "RabbitMQ API not responding properly"
fi

# Test 5: Cache connectivity
echo ""
echo "⚡ Testing cache connectivity..."
echo "-------------------------------"

# Redis ping
if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
    print_status 0 "Redis cache is responding"
else
    print_status 1 "Redis cache is not responding"
fi

# Test 6: Monitoring stack
echo ""
echo "📊 Testing monitoring stack..."
echo "------------------------------"

# Prometheus
if curl -sf http://localhost:9090/-/healthy > /dev/null; then
    print_status 0 "Prometheus is healthy"
else
    # Try alternative endpoint
    if curl -sf http://localhost:9090/ > /dev/null; then
        print_status 0 "Prometheus is accessible"
    else
        print_status 1 "Prometheus is not accessible"
    fi
fi

# Grafana
if curl -sf http://localhost:3000/api/health > /dev/null; then
    print_status 0 "Grafana is healthy"
else
    # Try main endpoint
    if curl -sf http://localhost:3000/ > /dev/null; then
        print_status 0 "Grafana is accessible"
    else
        print_status 1 "Grafana is not accessible"
    fi
fi

# Test 7: Django application functionality
echo ""
echo "🐍 Testing Django application functionality..."
echo "----------------------------------------------"

# Test Django check command
if docker-compose exec -T notification-service python manage.py check > /dev/null 2>&1; then
    print_status 0 "Django system check passed"
else
    print_status 1 "Django system check failed"
fi

# Test Django migrations
print_info "Checking Django migrations status..."
migration_output=$(docker-compose exec -T notification-service python manage.py showmigrations --plan 2>/dev/null || echo "error")
if [ "$migration_output" != "error" ]; then
    print_status 0 "Django migrations check completed"
else
    print_status 1 "Django migrations check failed"
fi

# Test 8: API endpoints functionality
echo ""
echo "🔗 Testing API endpoints functionality..."
echo "----------------------------------------"

# Test metrics endpoint
if curl -sf http://localhost:8000/metrics/ > /dev/null; then
    print_status 0 "Metrics endpoint accessible"
else
    print_warning "Metrics endpoint not accessible (optional)"
fi

# Test API schema endpoint
if curl -sf http://localhost:8000/api/schema/ > /dev/null; then
    print_status 0 "API schema endpoint accessible"
else
    print_status 1 "API schema endpoint not accessible"
fi

# Test 9: File system and permissions
echo ""
echo "📁 Testing file system and permissions..."
echo "----------------------------------------"

# Test static files directory
if docker-compose exec -T notification-service ls -la /app/staticfiles > /dev/null 2>&1; then
    print_status 0 "Static files directory accessible"
else
    print_warning "Static files directory not found (may be normal)"
fi

# Test log directory
if docker-compose exec -T notification-service python -c "import logging; logging.info('test')" > /dev/null 2>&1; then
    print_status 0 "Logging system functional"
else
    print_status 1 "Logging system not functional"
fi

# Test 10: Performance check
echo ""
echo "⚡ Basic performance check..."
echo "----------------------------"

# Test response time
print_info "Measuring API response time..."
response_time=$(curl -w "%{time_total}" -o /dev/null -s http://localhost:8000/health/)
response_time_ms=$(echo "$response_time * 1000" | bc 2>/dev/null || echo "unknown")

if [ "$response_time_ms" != "unknown" ]; then
    print_status 0 "Health endpoint response time: ${response_time_ms}ms"
    
    # Check if response time is reasonable (under 1 second)
    if (( $(echo "$response_time < 1.0" | bc -l 2>/dev/null || echo 0) )); then
        print_status 0 "Response time is acceptable"
    else
        print_warning "Response time might be high"
    fi
else
    print_warning "Could not measure response time"
fi

# Summary
echo ""
echo "📋 Validation Summary"
echo "===================="
echo -e "${GREEN}✅ All critical systems are operational!${NC}"
echo ""
echo "📍 Service URLs:"
echo "  • Main Application: http://localhost:8000/"
echo "  • API Documentation: http://localhost:8000/api/docs/"
echo "  • Django Admin: http://localhost:8000/admin/"
echo "  • RabbitMQ Management: http://localhost:15672/ (admin/admin123)"
echo "  • Prometheus: http://localhost:9090/"
echo "  • Grafana: http://localhost:3000/ (admin/admin)"
echo ""
echo "🎯 Next Steps:"
echo "  1. Access API documentation at http://localhost:8000/api/docs/"
echo "  2. Create a superuser: docker-compose exec notification-service python manage.py createsuperuser"
echo "  3. Configure external providers (AWS SES, Twilio, Firebase) in production"
echo "  4. Set up monitoring alerts in Grafana"
echo ""
echo -e "${GREEN}🎉 Notification Microservice validation completed successfully!${NC}"