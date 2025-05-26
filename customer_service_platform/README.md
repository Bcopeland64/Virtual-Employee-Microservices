# Customer Service Platform Integration

This directory contains the integration of the AI Customer Service Platform with the AI Employee system.

## Overview

The Customer Service Platform enables the AI Employee to handle customer service inquiries, manage a knowledge base, analyze sentiment, and escalate issues when necessary.

## Components

- **integration.py**: Core functionality for processing customer messages
- **knowledge_service.py**: Knowledge base search and retrieval services
- **__init__.py**: Package initialization

## Features

- AI-powered chatbot interactions
- Real-time sentiment analysis using Amazon Comprehend
- Intelligent routing and escalation
- Knowledge base integration with OpenSearch
- Audit logging for compliance
- Analytics for customer interaction insights

## Integration with AI Employee

The integration happens in the main-orchestrator.py file, which routes intent requests to the appropriate handlers:

- CustomerService, CustomerSupport, GetHelp intents: handle_customer_service_intent()
- ReportIssue intent: handle_report_issue_intent()
- CustomerKnowledgeQuery intent: handle_customer_service_intent() (with knowledge base lookup)

## Required AWS Services

- Amazon Lex for natural language understanding
- Amazon Comprehend for sentiment analysis
- Amazon OpenSearch for knowledge base
- Amazon S3 for knowledge article storage
- Amazon SNS for notifications
- Amazon SQS for message routing
- Amazon CloudWatch for monitoring

## Environment Variables

The following environment variables must be set:

```
LEX_BOT_ID - Amazon Lex bot ID
LEX_BOT_ALIAS_ID - Amazon Lex bot alias ID
ROUTING_QUEUE_URL - SQS queue URL for routing
ESCALATION_TOPIC_ARN - SNS topic ARN for escalations
OPENSEARCH_DOMAIN - OpenSearch domain endpoint
KNOWLEDGE_BUCKET - S3 bucket for knowledge articles
KNOWLEDGE_INDEX - OpenSearch index name for knowledge base
```

## Deployment

When deploying the AI Employee, ensure that the necessary IAM permissions are granted to access all required services.