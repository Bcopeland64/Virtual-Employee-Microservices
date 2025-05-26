# Customer Service Platform User Guide

This guide provides instructions for using the AI Customer Service Platform deployed with AWS Fargate.

## Overview

The AI Customer Service Platform is a comprehensive solution for handling customer inquiries, analyzing sentiment, routing requests, and managing knowledge. The platform is built on AWS Fargate, providing a serverless, scalable architecture that automatically adjusts to demand.

## Architecture

The platform consists of seven microservices:

1. **Chatbot Service**: Provides conversational interfaces for customers
2. **Sentiment Analysis Service**: Analyzes customer message sentiment
3. **Routing Service**: Directs inquiries to appropriate handlers
4. **Knowledge Base Service**: Manages and retrieves knowledge content
5. **Analytics Service**: Provides reporting and insights
6. **Escalation Service**: Handles escalation of complex issues
7. **Audit Service**: Logs and tracks compliance

## Accessing the Platform

The platform is accessible through the following endpoints:

```
https://<load-balancer-dns>/chatbot
https://<load-balancer-dns>/sentiment
https://<load-balancer-dns>/routing
https://<load-balancer-dns>/knowledge
https://<load-balancer-dns>/analytics
https://<load-balancer-dns>/escalation
https://<load-balancer-dns>/audit
```

Replace `<load-balancer-dns>` with the DNS name of your Application Load Balancer, or your custom domain if configured.

## Authentication

All API requests require authentication using AWS Signature Version 4 (SigV4). Most AWS SDKs handle this automatically.

Example in Python:

```python
import boto3
import requests
from requests_aws4auth import AWS4Auth

region = 'us-east-1'
service = 'execute-api'

credentials = boto3.Session().get_credentials()
auth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    region,
    service,
    session_token=credentials.token
)

response = requests.get(
    'https://your-alb-dns/chatbot/conversation',
    auth=auth,
    params={'conversation_id': '12345'}
)
```

## API Reference

### Chatbot Service

The Chatbot Service provides conversational interfaces for customer interactions.

#### Start Conversation

```
POST /chatbot/conversation
```

Request Body:
```json
{
  "user_id": "user123",
  "initial_message": "I need help with my order",
  "channel": "web",
  "metadata": {
    "browser": "Chrome",
    "device": "desktop"
  }
}
```

Response:
```json
{
  "conversation_id": "conv-12345",
  "response": "Hi there! I'd be happy to help you with your order. Could you please provide your order number?",
  "suggested_actions": [
    {
      "type": "text",
      "text": "I don't have my order number"
    },
    {
      "type": "link",
      "text": "Find my order",
      "url": "https://example.com/orders"
    }
  ]
}
```

#### Send Message

```
POST /chatbot/conversation/{conversation_id}/message
```

Request Body:
```json
{
  "message": "My order number is ORD-9876",
  "attachments": []
}
```

Response:
```json
{
  "response": "Thank you! I can see your order ORD-9876 was placed on March 15 and is currently being processed. It should ship within 2 business days. Is there anything specific about this order you'd like to know?",
  "suggested_actions": [
    {
      "type": "text",
      "text": "When will it arrive?"
    },
    {
      "type": "text",
      "text": "Can I modify the order?"
    }
  ]
}
```

### Sentiment Analysis Service

The Sentiment Analysis Service analyzes the sentiment of customer messages.

#### Analyze Sentiment

```
POST /sentiment/analyze
```

Request Body:
```json
{
  "text": "I've been waiting for 3 days and still haven't received any update on my order. This is frustrating.",
  "conversation_id": "conv-12345",
  "user_id": "user123"
}
```

Response:
```json
{
  "analysis_id": "sent-67890",
  "sentiment": "negative",
  "sentiment_score": 0.28,
  "dominant_emotions": ["frustration", "disappointment"],
  "keywords": ["waiting", "frustrating", "order", "update"],
  "action_recommendations": [
    {
      "type": "escalate",
      "confidence": 0.75,
      "reasoning": "Strong negative sentiment with frustration about order delays"
    }
  ]
}
```

### Routing Service

The Routing Service directs customer inquiries to appropriate handlers.

#### Route Inquiry

```
POST /routing/inquiries
```

Request Body:
```json
{
  "conversation_id": "conv-12345",
  "user_id": "user123",
  "source": "chatbot",
  "inquiry_text": "I need to return a damaged product",
  "sentiment_score": 0.35,
  "metadata": {
    "product_id": "PROD-1234",
    "purchase_date": "2025-02-15"
  }
}
```

Response:
```json
{
  "routing_id": "route-54321",
  "destination": "returns_department",
  "priority": "medium",
  "estimated_response_time": 300,
  "suggested_responses": [
    "I understand you need to return a damaged product. I'll connect you with our returns department who can help process this for you.",
    "I'll need a few details about your return. Could you tell me what's damaged about the product?"
  ]
}
```

### Knowledge Base Service

The Knowledge Base Service manages and retrieves knowledge content.

#### Search Knowledge

```
GET /knowledge/search
```

Query Parameters:
- `query`: Search query (required)
- `category`: Category filter (optional)
- `limit`: Maximum number of results (default: 10)
- `offset`: Pagination offset (default: 0)

Response:
```json
{
  "results": [
    {
      "id": "kb-12345",
      "title": "How to Return a Damaged Product",
      "content": "To return a damaged product, please follow these steps...",
      "category": "returns",
      "relevance_score": 0.92,
      "metadata": {
        "last_updated": "2025-01-15T10:30:00Z",
        "views": 1245
      }
    },
    {
      "id": "kb-12346",
      "title": "Refund Policy for Damaged Items",
      "content": "Our policy for damaged items ensures you receive...",
      "category": "returns",
      "relevance_score": 0.84,
      "metadata": {
        "last_updated": "2025-02-02T14:15:00Z",
        "views": 987
      }
    }
  ],
  "total": 12,
  "page": 1,
  "limit": 10
}
```

#### Get Knowledge Article

```
GET /knowledge/articles/{article_id}
```

Response:
```json
{
  "id": "kb-12345",
  "title": "How to Return a Damaged Product",
  "content": "To return a damaged product, please follow these steps...",
  "category": "returns",
  "metadata": {
    "last_updated": "2025-01-15T10:30:00Z",
    "views": 1245,
    "author": "support_team",
    "related_articles": ["kb-12346", "kb-12350"]
  },
  "steps": [
    {
      "step": 1,
      "title": "Contact Customer Service",
      "description": "Reach out to our team through chat, email, or phone."
    },
    {
      "step": 2,
      "title": "Provide Order Details",
      "description": "Have your order number ready for faster service."
    }
  ]
}
```

### Analytics Service

The Analytics Service provides reporting and insights.

#### Get Dashboard Data

```
GET /analytics/dashboard
```

Query Parameters:
- `start_date`: Start date (ISO format)
- `end_date`: End date (ISO format)
- `metrics`: Comma-separated list of metrics (e.g., "conversations,sentiment,resolution_time")

Response:
```json
{
  "time_period": {
    "start": "2025-02-01T00:00:00Z",
    "end": "2025-02-28T23:59:59Z"
  },
  "summary": {
    "total_conversations": 12458,
    "average_sentiment_score": 0.72,
    "average_resolution_time": 345,
    "escalation_rate": 0.12
  },
  "trends": {
    "conversations": [
      {"date": "2025-02-01", "count": 423},
      {"date": "2025-02-02", "count": 412}
    ],
    "sentiment": [
      {"date": "2025-02-01", "score": 0.71},
      {"date": "2025-02-02", "score": 0.73}
    ]
  },
  "top_issues": [
    {"issue": "product_returns", "count": 2456},
    {"issue": "order_status", "count": 1872}
  ]
}
```

#### Generate Report

```
POST /analytics/reports
```

Request Body:
```json
{
  "report_type": "conversation_analysis",
  "time_period": {
    "start": "2025-02-01T00:00:00Z",
    "end": "2025-02-28T23:59:59Z"
  },
  "filters": {
    "sentiment": "negative",
    "resolution_time_min": 600
  },
  "format": "pdf"
}
```

Response:
```json
{
  "report_id": "rep-78901",
  "status": "generating",
  "estimated_completion_time": "2025-03-19T14:25:00Z",
  "download_url": null
}
```

### Escalation Service

The Escalation Service handles escalation of complex issues.

#### Create Escalation

```
POST /escalation/cases
```

Request Body:
```json
{
  "conversation_id": "conv-12345",
  "user_id": "user123",
  "priority": "high",
  "issue_summary": "Customer received damaged product and needs immediate replacement",
  "source": "chatbot",
  "sentiment_score": 0.25,
  "relevant_data": {
    "order_id": "ORD-9876",
    "product_id": "PROD-1234"
  }
}
```

Response:
```json
{
  "escalation_id": "esc-24680",
  "status": "created",
  "assigned_to": "support_team_lead",
  "expected_response_time": "2025-03-19T16:30:00Z",
  "tracking_url": "https://your-alb-dns/escalation/cases/esc-24680"
}
```

#### Get Escalation Status

```
GET /escalation/cases/{escalation_id}
```

Response:
```json
{
  "escalation_id": "esc-24680",
  "status": "in_progress",
  "created_at": "2025-03-19T14:15:00Z",
  "assigned_to": "john.smith",
  "priority": "high",
  "issue_summary": "Customer received damaged product and needs immediate replacement",
  "resolution_notes": "Contacted warehouse to prepare replacement shipment. Will process expedited shipping.",
  "expected_completion": "2025-03-20T12:00:00Z",
  "actions": [
    {
      "action": "replacement_initiated",
      "timestamp": "2025-03-19T14:30:00Z",
      "by": "john.smith"
    }
  ]
}
```

### Audit Service

The Audit Service logs and tracks compliance.

#### Query Audit Logs

```
GET /audit/logs
```

Query Parameters:
- `start_time`: Start time (ISO format)
- `end_time`: End time (ISO format)
- `user_id`: Filter by user ID (optional)
- `conversation_id`: Filter by conversation ID (optional)
- `action_type`: Filter by action type (optional)
- `limit`: Maximum number of results (default: 100)
- `offset`: Pagination offset (default: 0)

Response:
```json
{
  "logs": [
    {
      "log_id": "audit-12345",
      "timestamp": "2025-03-19T14:15:30Z",
      "user_id": "user123",
      "service": "chatbot",
      "action": "message_sent",
      "resource_id": "conv-12345",
      "request_ip": "192.168.1.1",
      "details": {
        "message_id": "msg-98765",
        "contains_pii": false,
        "sentiment_score": 0.65
      }
    }
  ],
  "total": 1458,
  "limit": 100,
  "offset": 0
}
```

## SDK

The Customer Service Platform provides a Python SDK for easier integration:

```python
from customer_service_sdk import CustomerServiceClient

# Initialize client
client = CustomerServiceClient(
    base_url="https://your-alb-dns",
    region="us-east-1"
)

# Start a conversation
conversation = client.chatbot.start_conversation(
    user_id="user123",
    initial_message="I need help with my order",
    channel="web"
)

# Send a message
response = client.chatbot.send_message(
    conversation_id=conversation["conversation_id"],
    message="My order number is ORD-9876"
)

# Analyze sentiment
sentiment = client.sentiment.analyze(
    text="I've been waiting for 3 days and no update.",
    conversation_id=conversation["conversation_id"]
)

# Search knowledge base
knowledge_results = client.knowledge.search(
    query="return damaged product",
    category="returns"
)
```

## AWS Console Access

To monitor and manage the platform through the AWS Console:

1. **ECS Console**:
   - Navigate to Amazon ECS > Clusters > customer-service-cluster
   - View services, tasks, and deployments

2. **CloudWatch**:
   - Navigate to CloudWatch > Dashboards > CustomerServiceDashboard
   - View metrics and alarms for the platform

3. **Logs**:
   - Navigate to CloudWatch > Log groups
   - Find log groups with names like "/ecs/customer-service/chatbot-service"

## Integration with Other Systems

### Webhook Integration

You can configure webhooks to receive notifications:

```
POST /webhook/configure
```

Request Body:
```json
{
  "url": "https://your-system.example.com/webhooks/customer-service",
  "events": ["conversation.created", "escalation.created", "sentiment.negative"],
  "secret": "your-webhook-secret"
}
```

### Email Integration

Configure email notifications:

```
POST /notifications/email/configure
```

Request Body:
```json
{
  "email": "support@example.com",
  "events": ["escalation.created", "high_priority_case"],
  "format": "html"
}
```

## Best Practices

1. **Regular Monitoring**:
   - Check the CloudWatch dashboard daily
   - Review conversation analytics weekly
   - Monitor sentiment trends to identify issues

2. **Knowledge Base Management**:
   - Update knowledge articles based on common queries
   - Review and refresh content quarterly
   - Add new articles based on escalation patterns

3. **Security Recommendations**:
   - Rotate access keys every 90 days
   - Use IAM roles with least privilege
   - Enable AWS CloudTrail for additional auditing

4. **Performance Optimization**:
   - Monitor CPU and memory usage
   - Adjust auto-scaling parameters as needed
   - Consider FARGATE_SPOT for cost optimization

## Troubleshooting

### Common Issues

1. **API Response Errors**:
   - Check CloudWatch Logs for error details
   - Verify IAM permissions are correctly configured
   - Ensure SigV4 authentication is properly implemented

2. **High Latency**:
   - Check ECS service metrics for CPU/memory pressure
   - Review Fargate task placement
   - Consider increasing task resources

3. **Escalation Issues**:
   - Verify SNS topics and subscriptions
   - Check SQS queue for backed-up messages
   - Review IAM permissions for the escalation service

### Support

For additional support or questions:

1. Check the CloudWatch logs for specific error messages
2. Open the AWS Console to review service health
3. Contact your system administrator or AWS support

## Maintenance Schedule

Regular maintenance includes:

- Weekly review of CloudWatch alarms
- Monthly review of service performance
- Quarterly update of knowledge base content
- Semi-annual review of security configurations

## Updates and Releases

New releases are deployed through the CI/CD pipeline. Release notes are available at:

```
GET /api/release-notes
```

## Compliance and Security

The platform is designed with security and compliance in mind:

- All data is encrypted in transit and at rest
- PII is handled according to data protection regulations
- Audit logs are retained according to compliance requirements
- Access is controlled through IAM policies

## Further Resources

- [AWS Fargate Documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
- [Amazon ECS Documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html)
- [AWS CloudWatch Documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html)