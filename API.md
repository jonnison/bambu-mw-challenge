# API Documentation
# Notification Microservice REST API

## 🌐 API Overview

The Notification Microservice provides a comprehensive REST API for managing multi-channel notifications. All endpoints follow REST conventions with proper HTTP status codes and JSON responses.

**Base URL**: `http://localhost:8000/api/v1/`  
**Authentication**: JWT Bearer tokens  
**Content-Type**: `application/json`  
**API Version**: v1

## 🔐 Authentication

All API endpoints require JWT authentication except health checks. Include the token in the Authorization header:

```http
Authorization: Bearer your-jwt-token
```

### Getting Access Tokens

```bash
# Development - Create superuser first
docker-compose exec notification-service python manage.py createsuperuser

# Then get token via Django admin or implement token endpoint
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

## 📨 Notification Endpoints

### Send Notification

Send a notification through any supported channel (email, SMS, push, in-app).

**Endpoint**: `POST /api/v1/notifications/send/`

**Request Body**:
```json
{
  "user_id": 123,
  "template_name": "welcome_email",
  "recipient": "user@example.com",
  "type": "email",
  "variables": {
    "name": "John Doe",
    "verification_link": "https://app.com/verify/abc123"
  },
  "priority": "normal",
  "scheduled_at": "2025-01-15T14:30:00Z"
}
```

**Response**: `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "type": "email",
  "recipient": "user@example.com",
  "template_name": "welcome_email",
  "priority": "normal",
  "created_at": "2025-01-15T10:30:00Z",
  "scheduled_at": "2025-01-15T14:30:00Z",
  "estimated_delivery": "2025-01-15T14:30:05Z"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Missing or invalid token
- `404 Not Found`: Template not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: System error

### Get Notification Status

Retrieve the current status and delivery details of a notification.

**Endpoint**: `GET /api/v1/notifications/{notification_id}/`

**Response**: `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 123,
  "status": "sent",
  "type": "email",
  "recipient": "user@example.com",
  "template_name": "welcome_email",
  "priority": "normal",
  "created_at": "2025-01-15T10:30:00Z",
  "sent_at": "2025-01-15T10:30:05Z",
  "delivery_details": {
    "provider": "ses",
    "message_id": "0000014a-f896-4c07-b62f-d65cdf35e537",
    "provider_response": {
      "MessageId": "0000014a-f896-4c07-b62f-d65cdf35e537",
      "ResponseMetadata": {
        "HTTPStatusCode": 200
      }
    }
  },
  "variables": {
    "name": "John Doe",
    "verification_link": "https://app.com/verify/abc123"
  }
}
```

### List User Notifications

Get paginated list of notifications for a specific user.

**Endpoint**: `GET /api/v1/notifications/`

**Query Parameters**:
- `user_id` (required): User ID to filter notifications
- `status`: Filter by status (pending, sent, failed, bounced)
- `type`: Filter by type (email, sms, push, in_app)
- `page`: Page number (default: 1)
- `page_size`: Results per page (default: 20, max: 100)
- `date_from`: Start date (ISO 8601)
- `date_to`: End date (ISO 8601)

**Example**: `GET /api/v1/notifications/?user_id=123&status=sent&page=1&page_size=20`

**Response**: `200 OK`
```json
{
  "count": 45,
  "next": "http://localhost:8000/api/v1/notifications/?page=2&user_id=123",
  "previous": null,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "sent",
      "type": "email",
      "recipient": "user@example.com",
      "template_name": "welcome_email",
      "created_at": "2025-01-15T10:30:00Z",
      "sent_at": "2025-01-15T10:30:05Z"
    }
  ]
}
```

### Update Notification Status

Update notification status (primarily for webhook callbacks from providers).

**Endpoint**: `PATCH /api/v1/notifications/{notification_id}/status/`

**Request Body**:
```json
{
  "status": "bounced",
  "provider_response": {
    "bounce_type": "Permanent",
    "bounce_reason": "Invalid recipient"
  }
}
```

**Response**: `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "bounced",
  "updated_at": "2025-01-15T10:35:00Z"
}
```

## 📋 Template Management

### List Templates

Get all available notification templates.

**Endpoint**: `GET /api/v1/templates/`

**Query Parameters**:
- `type`: Filter by type (email, sms, push, in_app)
- `active`: Filter by active status (true/false)
- `search`: Search in name and content

**Response**: `200 OK`
```json
{
  "count": 12,
  "results": [
    {
      "id": "template-uuid-1",
      "name": "welcome_email",
      "type": "email",
      "subject": "Welcome to {{app_name}}!",
      "content": "Hi {{name}}, welcome to our platform!",
      "variables": ["name", "app_name"],
      "active": true,
      "created_at": "2025-01-10T12:00:00Z",
      "updated_at": "2025-01-10T12:00:00Z"
    }
  ]
}
```

### Get Template Details

Retrieve detailed information about a specific template.

**Endpoint**: `GET /api/v1/templates/{template_id}/`

**Response**: `200 OK`
```json
{
  "id": "template-uuid-1",
  "name": "welcome_email",
  "type": "email",
  "subject": "Welcome to {{app_name}}!",
  "content": "Hi {{name}},\n\nWelcome to our platform! Click here to verify: {{verification_link}}",
  "variables": ["name", "app_name", "verification_link"],
  "metadata": {
    "description": "Welcome email sent to new users",
    "category": "user_onboarding",
    "tags": ["welcome", "verification"]
  },
  "active": true,
  "usage_stats": {
    "total_sent": 1247,
    "last_used": "2025-01-15T09:15:00Z"
  },
  "created_at": "2025-01-10T12:00:00Z",
  "updated_at": "2025-01-10T12:00:00Z"
}
```

### Create Template

Create a new notification template.

**Endpoint**: `POST /api/v1/templates/`

**Request Body**:
```json
{
  "name": "password_reset",
  "type": "email",
  "subject": "Reset your password",
  "content": "Hi {{name}}, click here to reset: {{reset_link}}",
  "variables": ["name", "reset_link"],
  "metadata": {
    "description": "Password reset email",
    "category": "security"
  }
}
```

**Response**: `201 Created`
```json
{
  "id": "template-uuid-new",
  "name": "password_reset",
  "type": "email",
  "subject": "Reset your password",
  "content": "Hi {{name}}, click here to reset: {{reset_link}}",
  "variables": ["name", "reset_link"],
  "active": true,
  "created_at": "2025-01-15T10:40:00Z"
}
```

### Update Template

Update an existing template.

**Endpoint**: `PUT /api/v1/templates/{template_id}/`

**Request Body**: Same as create template

**Response**: `200 OK` (same format as create response)

### Delete Template

Soft delete a template (marks as inactive).

**Endpoint**: `DELETE /api/v1/templates/{template_id}/`

**Response**: `204 No Content`

## 👤 User Preferences

### Get User Preferences

Retrieve notification preferences for a user.

**Endpoint**: `GET /api/v1/preferences/user/{user_id}/`

**Response**: `200 OK`
```json
{
  "id": "pref-uuid-1",
  "user_id": 123,
  "email_enabled": true,
  "sms_enabled": true,
  "push_enabled": false,
  "in_app_enabled": true,
  "quiet_hours": {
    "enabled": true,
    "start": "22:00",
    "end": "08:00",
    "timezone": "UTC"
  },
  "frequency_limits": {
    "email": {
      "max_per_hour": 5,
      "max_per_day": 50
    },
    "sms": {
      "max_per_hour": 2,
      "max_per_day": 10
    }
  },
  "categories": {
    "marketing": false,
    "security": true,
    "product_updates": true,
    "system_notifications": true
  },
  "updated_at": "2025-01-10T15:30:00Z"
}
```

### Update User Preferences

Update notification preferences for a user.

**Endpoint**: `PUT /api/v1/preferences/user/{user_id}/`

**Request Body**:
```json
{
  "email_enabled": false,
  "quiet_hours": {
    "enabled": true,
    "start": "20:00",
    "end": "09:00"
  },
  "categories": {
    "marketing": false,
    "security": true
  }
}
```

**Response**: `200 OK` (same format as get preferences)

## 📊 System Endpoints

### Health Check

Basic health check endpoint (no authentication required).

**Endpoint**: `GET /api/v1/health/`

**Response**: `200 OK`
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:45:00Z",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "rabbitmq": "healthy"
  },
  "metrics": {
    "notifications_sent_24h": 1247,
    "queue_size": 3,
    "active_templates": 12,
    "error_rate_1h": 0.02
  }
}
```

### Detailed Health Check

Comprehensive health check with detailed service status.

**Endpoint**: `GET /api/v1/health/detailed/`

**Response**: `200 OK`
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:45:00Z",
  "services": {
    "database": {
      "status": "healthy",
      "response_time_ms": 12,
      "connection_pool": {
        "active": 2,
        "idle": 8,
        "max": 10
      }
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 1,
      "memory_usage": "45MB",
      "connected_clients": 3
    },
    "rabbitmq": {
      "status": "healthy",
      "response_time_ms": 5,
      "queues": {
        "notifications.high": 0,
        "notifications.normal": 2,
        "notifications.low": 1
      }
    },
    "external_providers": {
      "ses": {
        "status": "healthy",
        "last_check": "2025-01-15T10:44:30Z"
      },
      "twilio": {
        "status": "healthy",
        "last_check": "2025-01-15T10:44:28Z"
      },
      "firebase": {
        "status": "degraded",
        "last_check": "2025-01-15T10:44:25Z",
        "error": "High latency detected"
      }
    }
  }
}
```

### Metrics Endpoint

Prometheus-compatible metrics endpoint.

**Endpoint**: `GET /metrics/`

**Response**: `200 OK` (Prometheus format)
```
# HELP notifications_sent_total Total notifications sent
# TYPE notifications_sent_total counter
notifications_sent_total{type="email",status="sent"} 845
notifications_sent_total{type="email",status="failed"} 12
notifications_sent_total{type="sms",status="sent"} 234
notifications_sent_total{type="push",status="sent"} 456

# HELP notification_processing_seconds Time spent processing notifications
# TYPE notification_processing_seconds histogram
notification_processing_seconds_bucket{type="email",le="0.1"} 500
notification_processing_seconds_bucket{type="email",le="0.5"} 800
notification_processing_seconds_bucket{type="email",le="1.0"} 850
```

## 🔄 Webhook Endpoints

### Provider Webhooks

Endpoints for receiving delivery status updates from external providers.

#### AWS SES Webhook

**Endpoint**: `POST /api/v1/webhooks/ses/`

**Headers**: `X-Amz-Sns-Message-Type`, `X-Amz-Sns-Topic-Arn`

**Request Body**: AWS SNS notification format

#### Twilio Webhook

**Endpoint**: `POST /api/v1/webhooks/twilio/`

**Headers**: `X-Twilio-Signature`

**Request Body**: Twilio status callback format

#### Firebase Webhook

**Endpoint**: `POST /api/v1/webhooks/firebase/`

**Headers**: `Authorization: key=server-key`

**Request Body**: Firebase delivery report format

## 📝 Request/Response Examples

### Complete Email Notification Flow

```bash
# 1. Send email notification
curl -X POST http://localhost:8000/api/v1/notifications/send/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
  -d '{
    "user_id": 123,
    "template_name": "order_confirmation",
    "recipient": "customer@example.com",
    "type": "email",
    "variables": {
      "customer_name": "Alice Johnson",
      "order_number": "ORD-2025-001",
      "order_total": "$129.99",
      "tracking_link": "https://track.example.com/ORD-2025-001"
    },
    "priority": "high"
  }'

# Response
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "type": "email",
  "recipient": "customer@example.com",
  "template_name": "order_confirmation",
  "priority": "high",
  "created_at": "2025-01-15T14:22:00Z",
  "estimated_delivery": "2025-01-15T14:22:15Z"
}

# 2. Check notification status
curl -X GET http://localhost:8000/api/v1/notifications/550e8400-e29b-41d4-a716-446655440000/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# Response
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "sent",
  "type": "email",
  "recipient": "customer@example.com",
  "sent_at": "2025-01-15T14:22:12Z",
  "delivery_details": {
    "provider": "ses",
    "message_id": "0000014a-f896-4c07-b62f-d65cdf35e537"
  }
}
```

### Bulk SMS Campaign

```bash
# 1. Create SMS template
curl -X POST http://localhost:8000/api/v1/templates/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
  -d '{
    "name": "flash_sale_sms",
    "type": "sms",
    "content": "🔥 Flash Sale! {{discount}}% off everything. Use code {{promo_code}}. Valid until {{expiry}}. Shop now: {{link}}",
    "variables": ["discount", "promo_code", "expiry", "link"],
    "metadata": {
      "description": "Flash sale promotional SMS",
      "category": "marketing"
    }
  }'

# 2. Send SMS to multiple users (would typically be done via bulk endpoint or queue)
for user in 123 124 125; do
  curl -X POST http://localhost:8000/api/v1/notifications/send/ \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
    -d "{
      \"user_id\": $user,
      \"template_name\": \"flash_sale_sms\",
      \"recipient\": \"+1555000$user\",
      \"type\": \"sms\",
      \"variables\": {
        \"discount\": \"25\",
        \"promo_code\": \"FLASH25\",
        \"expiry\": \"midnight\",
        \"link\": \"bit.ly/flash25\"
      },
      \"priority\": \"normal\"
    }"
done
```

## ⚠️ Error Handling

### Standard Error Response Format

```json
{
  "error": {
    "code": "TEMPLATE_NOT_FOUND",
    "message": "Template 'invalid_template' does not exist",
    "details": {
      "template_name": "invalid_template",
      "available_templates": ["welcome_email", "order_confirmation"]
    },
    "timestamp": "2025-01-15T14:30:00Z",
    "request_id": "req-550e8400-e29b-41d4-a716"
  }
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `INVALID_REQUEST` | 400 | Request validation failed |
| `UNAUTHORIZED` | 401 | Invalid or missing authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `TEMPLATE_NOT_FOUND` | 404 | Template does not exist |
| `USER_NOT_FOUND` | 404 | User does not exist |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `QUOTA_EXCEEDED` | 429 | Notification quota exceeded |
| `PROVIDER_ERROR` | 502 | External provider failure |
| `SERVICE_UNAVAILABLE` | 503 | System temporarily unavailable |

## 🔒 Rate Limiting & Quotas

### Rate Limits

- **Default**: 100 requests per minute per user
- **Send notifications**: 20 requests per minute per user  
- **Template management**: 10 requests per minute per user
- **Webhooks**: 1000 requests per minute (no user limit)

### Notification Quotas

- **Free tier**: 1,000 notifications per month
- **Professional**: 50,000 notifications per month
- **Enterprise**: Unlimited with fair usage

### Headers

Rate limit information is included in response headers:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 85
X-RateLimit-Reset: 1642345678
X-Quota-Limit: 50000
X-Quota-Remaining: 47234
X-Quota-Reset: 1643587200
```

## 📚 SDKs and Examples

### Python SDK Example

```python
from notification_client import NotificationClient

client = NotificationClient(
    base_url="http://localhost:8000/api/v1/",
    token="your-jwt-token"
)

# Send notification
response = client.send_notification(
    user_id=123,
    template_name="welcome_email",
    recipient="user@example.com",
    type="email",
    variables={
        "name": "John Doe",
        "verification_link": "https://app.com/verify/abc123"
    }
)

print(f"Notification sent: {response.id}")

# Check status
status = client.get_notification_status(response.id)
print(f"Status: {status.status}")
```

### JavaScript/Node.js Example

```javascript
const NotificationClient = require('@mybambu/notification-client');

const client = new NotificationClient({
  baseURL: 'http://localhost:8000/api/v1/',
  token: 'your-jwt-token'
});

// Send notification
const response = await client.sendNotification({
  userId: 123,
  templateName: 'welcome_email',
  recipient: 'user@example.com',
  type: 'email',
  variables: {
    name: 'John Doe',
    verificationLink: 'https://app.com/verify/abc123'
  }
});

console.log(`Notification sent: ${response.id}`);

// Check status
const status = await client.getNotificationStatus(response.id);
console.log(`Status: ${status.status}`);
```

---

**API Version**: v1.0.0  
**Last Updated**: September 25, 2025  
**Interactive Documentation**: http://localhost:8000/api/docs/  
**OpenAPI Schema**: http://localhost:8000/api/schema/