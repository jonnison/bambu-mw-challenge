#!/bin/bash
# Complete system validation script for Notification Microservice
# Tests all components and validates the complete setup

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
    fi
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

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

# Test 1: Core service endpoints
echo ""
echo "🌐 Testing core service endpoints..."
echo "-------------------------------------"

# Health check endpoint
print_info "Testing health endpoint..."
if curl -sf http://localhost:8000/health/ > /dev/null; then
    health_response=$(curl -s http://localhost:8000/health/)
    if echo "$health_response" | grep -q '"status": "healthy"'; then
        print_status 0 "Health endpoint is healthy"
    else
        print_status 1 "Health endpoint is not healthy"
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

# Test 2: Database connectivity
echo ""
echo "🗄️  Testing database connectivity..."
echo "------------------------------------"

if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    print_status 0 "PostgreSQL database is ready"
else
    print_status 1 "PostgreSQL database is not ready"
fi

# Test 3: Message queue connectivity
echo ""
echo "📬 Testing message queue connectivity..."
echo "---------------------------------------"

if curl -sf http://localhost:15672/ > /dev/null; then
    print_status 0 "RabbitMQ management interface accessible"
else
    print_status 1 "RabbitMQ management interface not accessible"
fi

# Test 4: Cache connectivity
echo ""
echo "⚡ Testing cache connectivity..."
echo "-------------------------------"

if docker-compose exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
    print_status 0 "Redis cache is responding"
else
    print_status 1 "Redis cache is not responding"
fi

# Test 5: Monitoring stack
echo ""
echo "📊 Testing monitoring stack..."
echo "------------------------------"

# Prometheus
if curl -sf http://localhost:9090/ > /dev/null; then
    print_status 0 "Prometheus is accessible"
else
    print_status 1 "Prometheus is not accessible"
fi

# Grafana
if curl -sf http://localhost:3000/ > /dev/null; then
    print_status 0 "Grafana is accessible"
else
    print_status 1 "Grafana is not accessible"
fi

# Test 6: Django application functionality
echo ""
echo "🐍 Testing Django application functionality..."
echo "----------------------------------------------"

if docker-compose exec -T notification-service python manage.py check > /dev/null 2>&1; then
    print_status 0 "Django system check passed"
else
    print_status 1 "Django system check failed"
fi

# Test 7: API endpoints functionality
echo ""
echo "🔗 Testing API endpoints functionality..."
echo "----------------------------------------"

if curl -sf http://localhost:8000/api/schema/ > /dev/null; then
    print_status 0 "API schema endpoint accessible"
else
    print_status 1 "API schema endpoint not accessible"
fi

# Test 8: Container status summary
echo ""
echo "📦 Docker containers summary..."
echo "-------------------------------"

docker-compose ps

echo ""
echo "📋 Validation Summary"
echo "===================="
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
echo -e "${GREEN}🎉 Notification Microservice validation completed!${NC}"