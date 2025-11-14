# Webhook System

The webhook system enables integrations with external systems by sending HTTP requests when specific events occur in TimeTracker.

## Overview

Webhooks allow you to:
- Receive real-time notifications when events occur (project created, task completed, etc.)
- Integrate with external services (Slack, Discord, custom APIs, etc.)
- Automate workflows based on TimeTracker events
- Build custom integrations without polling the API

## Features

- **Event Subscriptions**: Subscribe to specific events or all events using wildcards
- **Secure Signatures**: HMAC-SHA256 signatures for webhook verification
- **Automatic Retries**: Failed deliveries are automatically retried with exponential backoff
- **Delivery Tracking**: View delivery history, success rates, and error details
- **Customizable**: Configure HTTP method, headers, timeouts, and retry behavior
- **REST API**: Full CRUD API for managing webhooks programmatically

## Available Events

### Project Events
- `project.created` - A project is created
- `project.updated` - A project is updated
- `project.deleted` - A project is deleted
- `project.archived` - A project is archived
- `project.unarchived` - A project is unarchived

### Task Events
- `task.created` - A task is created
- `task.updated` - A task is updated
- `task.deleted` - A task is deleted
- `task.completed` - A task is completed
- `task.assigned` - A task is assigned to a user
- `task.status_changed` - A task's status changes

### Time Entry Events
- `time_entry.created` - A time entry is created
- `time_entry.updated` - A time entry is updated
- `time_entry.deleted` - A time entry is deleted
- `time_entry.started` - A timer is started
- `time_entry.stopped` - A timer is stopped

### Invoice Events
- `invoice.created` - An invoice is created
- `invoice.updated` - An invoice is updated
- `invoice.deleted` - An invoice is deleted
- `invoice.sent` - An invoice is sent to a client
- `invoice.paid` - An invoice is paid
- `invoice.overdue` - An invoice becomes overdue

### Client Events
- `client.created` - A client is created
- `client.updated` - A client is updated
- `client.deleted` - A client is deleted

### User Events
- `user.created` - A user is created
- `user.updated` - A user is updated
- `user.deleted` - A user is deleted

### Comment Events
- `comment.created` - A comment is created
- `comment.updated` - A comment is updated
- `comment.deleted` - A comment is deleted

### Wildcard Subscription
- `*` - Subscribe to all events

## Webhook Payload Format

All webhook payloads follow this structure:

```json
{
  "event_type": "project.created",
  "timestamp": "2025-01-23T10:30:00Z",
  "user": {
    "id": 1,
    "username": "john",
    "display_name": "John Doe"
  },
  "entity": {
    "type": "project",
    "id": 123,
    "name": "My Project"
  },
  "action": "created",
  "description": "Created project \"My Project\"",
  "data": {
    // Additional event-specific data
  }
}
```

## Security

### HMAC Signature Verification

Each webhook includes an HMAC-SHA256 signature in the `X-Webhook-Signature` header:

```
X-Webhook-Signature: sha256=<signature>
```

To verify the signature:

```python
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Remove 'sha256=' prefix if present
    if signature.startswith('sha256='):
        signature = signature[7:]
    
    return hmac.compare_digest(expected_signature, signature)
```

### Headers

Each webhook request includes these headers:

- `Content-Type`: The configured content type (default: `application/json`)
- `User-Agent`: `TimeTracker-Webhook/1.0`
- `X-Webhook-Event`: The event type (e.g., `project.created`)
- `X-Webhook-ID`: The webhook ID
- `X-Webhook-Signature`: HMAC signature (if secret is configured)

## Configuration

### Creating a Webhook

1. Navigate to **Admin → Webhooks**
2. Click **Create Webhook**
3. Configure:
   - **Name**: Descriptive name for the webhook
   - **URL**: Endpoint URL to receive webhooks
   - **Events**: Select which events to subscribe to
   - **HTTP Method**: POST, PUT, or PATCH
   - **Retry Settings**: Max retries, delay, timeout
4. Save the webhook

The webhook secret will be generated automatically. **Save this secret** - it's only shown once!

### Webhook Settings

- **Max Retries**: Number of retry attempts (default: 3)
- **Retry Delay**: Seconds between retries (default: 60, uses exponential backoff)
- **Timeout**: Request timeout in seconds (default: 30)
- **Active**: Enable/disable the webhook

## Delivery & Retries

### Delivery Status

- **pending**: Initial delivery attempt
- **success**: Successfully delivered (HTTP 2xx)
- **failed**: Delivery failed (exceeded max retries)
- **retrying**: Scheduled for retry

### Retry Logic

Failed deliveries are automatically retried with exponential backoff:
- 1st retry: After `retry_delay_seconds`
- 2nd retry: After `retry_delay_seconds * 2`
- 3rd retry: After `retry_delay_seconds * 4`
- etc.

The retry task runs every 5 minutes.

## REST API

### List Webhooks

```http
GET /api/v1/webhooks
Authorization: Bearer <token>
```

### Create Webhook

```http
POST /api/v1/webhooks
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "My Webhook",
  "url": "https://example.com/webhook",
  "events": ["project.created", "task.completed"],
  "max_retries": 3,
  "retry_delay_seconds": 60,
  "timeout_seconds": 30
}
```

### Get Webhook

```http
GET /api/v1/webhooks/<webhook_id>
Authorization: Bearer <token>
```

### Update Webhook

```http
PATCH /api/v1/webhooks/<webhook_id>
Authorization: Bearer <token>
Content-Type: application/json

{
  "is_active": false,
  "events": ["project.created"]
}
```

### Delete Webhook

```http
DELETE /api/v1/webhooks/<webhook_id>
Authorization: Bearer <token>
```

### List Deliveries

```http
GET /api/v1/webhooks/<webhook_id>/deliveries?status=failed
Authorization: Bearer <token>
```

### Get Available Events

```http
GET /api/v1/webhooks/events
Authorization: Bearer <token>
```

## API Scopes

Webhook API endpoints require these scopes:
- `read:webhooks` - View webhooks and deliveries
- `write:webhooks` - Create, update, delete webhooks

## Example Integration

### Node.js/Express

```javascript
const express = require('express');
const crypto = require('crypto');

const app = express();
const WEBHOOK_SECRET = 'your-webhook-secret';

app.use(express.raw({ type: 'application/json' }));

app.post('/webhook', (req, res) => {
  const signature = req.headers['x-webhook-signature'];
  const eventType = req.headers['x-webhook-event'];
  
  // Verify signature
  const expectedSignature = crypto
    .createHmac('sha256', WEBHOOK_SECRET)
    .update(req.body)
    .digest('hex');
  
  const providedSignature = signature.replace('sha256=', '');
  
  if (expectedSignature !== providedSignature) {
    return res.status(401).send('Invalid signature');
  }
  
  // Parse payload
  const payload = JSON.parse(req.body);
  
  // Handle event
  console.log(`Received ${eventType}:`, payload);
  
  // Process based on event type
  switch (eventType) {
    case 'project.created':
      console.log('New project:', payload.entity.name);
      break;
    case 'task.completed':
      console.log('Task completed:', payload.entity.name);
      break;
  }
  
  res.status(200).send('OK');
});

app.listen(3000);
```

### Python/Flask

```python
import hmac
import hashlib
from flask import Flask, request, jsonify

app = Flask(__name__)
WEBHOOK_SECRET = 'your-webhook-secret'

def verify_signature(payload, signature):
    expected = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    if signature.startswith('sha256='):
        signature = signature[7:]
    
    return hmac.compare_digest(expected, signature)

@app.route('/webhook', methods=['POST'])
def webhook():
    signature = request.headers.get('X-Webhook-Signature')
    event_type = request.headers.get('X-Webhook-Event')
    
    if not verify_signature(request.data.decode('utf-8'), signature):
        return jsonify({'error': 'Invalid signature'}), 401
    
    payload = request.get_json()
    
    # Handle event
    print(f"Received {event_type}: {payload}")
    
    return jsonify({'status': 'ok'}), 200
```

## Best Practices

1. **Always verify signatures** - Never trust webhook payloads without verification
2. **Handle idempotency** - Use `event_id` to prevent duplicate processing
3. **Respond quickly** - Return HTTP 200 quickly, process asynchronously if needed
4. **Monitor deliveries** - Check delivery status regularly
5. **Use HTTPS** - Always use HTTPS endpoints for webhooks
6. **Test webhooks** - Use the test feature before going live
7. **Set appropriate timeouts** - Match your endpoint's processing time
8. **Handle errors gracefully** - Return appropriate HTTP status codes

## Troubleshooting

### Webhook Not Firing

- Check if webhook is active
- Verify event subscription
- Check delivery logs for errors

### Delivery Failures

- Verify endpoint URL is accessible
- Check endpoint returns HTTP 2xx
- Review error messages in delivery logs
- Ensure endpoint responds within timeout

### Signature Verification Fails

- Verify secret matches webhook secret
- Check payload encoding (UTF-8)
- Ensure signature header format is correct
- Compare signatures byte-by-byte (use `hmac.compare_digest`)

## Limitations

- Maximum payload size: 10MB
- Maximum retries: 10
- Retry task runs every 5 minutes
- Webhooks are delivered synchronously (may affect response time for triggering actions)

## Related Documentation

- [REST API Documentation](REST_API.md)
- [Activity Logging](activity_feed.md)
- [API Authentication](API_AUTHENTICATION.md)

