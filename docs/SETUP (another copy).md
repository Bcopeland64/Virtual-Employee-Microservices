# Customer Service Platform Setup Guide

This guide walks through the complete setup process for the AI Customer Service Platform.

## Prerequisites

- AWS account with administrative access
- AWS CLI installed and configured
- Python 3.11 or later
- Terraform (optional, for automated infrastructure deployment)

## Infrastructure Setup

### Step 1: Create Required IAM Roles and Policies

Create a policy file named `customer-service-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lex:*",
        "comprehend:DetectSentiment",
        "es:*",
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket",
        "s3:DeleteObject",
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sns:Publish",
        "cloudwatch:PutMetricData"
      ],
      "Resource": "*"
    }
  ]
}
```

Create the policy and role:

```bash
# Create the policy
aws iam create-policy \
  --policy-name CustomerServicePolicy \
  --policy-document file://customer-service-policy.json

# Create the role (if not already existing)
aws iam create-role \
  --role-name AIEmployeeRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

# Attach the policy to the role
aws iam attach-role-policy \
  --role-name AIEmployeeRole \
  --policy-arn arn:aws:iam::<ACCOUNT_ID>:policy/CustomerServicePolicy
```

### Step 2: Set Up Amazon Lex Bot

```bash
# Create the Lex bot
BOT_ID=$(aws lexv2-models create-bot \
  --bot-name "CustomerServiceBot" \
  --data-privacy '{"ChildDirected": false}' \
  --idle-session-ttl-in-seconds 300 \
  --role-arn "arn:aws:iam::<ACCOUNT_ID>:role/AIEmployeeRole" \
  --query 'botId' --output text)

echo "Created Lex bot with ID: $BOT_ID"

# Create the CustomerService intent
aws lexv2-models create-intent \
  --bot-id "$BOT_ID" \
  --bot-version "DRAFT" \
  --locale-id "en_US" \
  --intent-name "CustomerService" \
  --description "Handle general customer service inquiries"

# Create the CustomerSupport intent
aws lexv2-models create-intent \
  --bot-id "$BOT_ID" \
  --bot-version "DRAFT" \
  --locale-id "en_US" \
  --intent-name "CustomerSupport" \
  --description "Handle customer support inquiries"

# Create the GetHelp intent
aws lexv2-models create-intent \
  --bot-id "$BOT_ID" \
  --bot-version "DRAFT" \
  --locale-id "en_US" \
  --intent-name "GetHelp" \
  --description "Provide help to customers"

# Create the ReportIssue intent
aws lexv2-models create-intent \
  --bot-id "$BOT_ID" \
  --bot-version "DRAFT" \
  --locale-id "en_US" \
  --intent-name "ReportIssue" \
  --description "Allow customers to report issues"

# Create the CustomerKnowledgeQuery intent
aws lexv2-models create-intent \
  --bot-id "$BOT_ID" \
  --bot-version "DRAFT" \
  --locale-id "en_US" \
  --intent-name "CustomerKnowledgeQuery" \
  --description "Answer customer questions using the knowledge base"

# Build the bot
aws lexv2-models build-bot-locale \
  --bot-id "$BOT_ID" \
  --bot-version "DRAFT" \
  --locale-id "en_US"

# Create a bot alias
ALIAS_ID=$(aws lexv2-models create-bot-alias \
  --bot-id "$BOT_ID" \
  --bot-alias-name "Production" \
  --bot-version "DRAFT" \
  --query 'botAliasId' --output text)

echo "Created bot alias with ID: $ALIAS_ID"
```

### Step 3: Create OpenSearch Domain

```bash
# Create OpenSearch domain
DOMAIN_NAME="customer-service-knowledge"
aws opensearch create-domain \
  --domain-name $DOMAIN_NAME \
  --engine-version "OpenSearch_2.5" \
  --cluster-config InstanceType=t3.small.search,InstanceCount=1 \
  --ebs-options EBSEnabled=true,VolumeType=gp2,VolumeSize=10

# Wait for domain to be created
echo "Waiting for OpenSearch domain to be created (this may take 10-15 minutes)..."
aws opensearch wait domain-exists --domain-name $DOMAIN_NAME

# Get the domain endpoint
DOMAIN_ENDPOINT=$(aws opensearch describe-domain \
  --domain-name $DOMAIN_NAME \
  --query 'DomainStatus.Endpoint' --output text)

echo "OpenSearch domain endpoint: $DOMAIN_ENDPOINT"
```

### Step 4: Create S3 Buckets

```bash
# Create buckets (replace with unique bucket names)
KNOWLEDGE_BUCKET="ai-employee-knowledge-base-$(date +%s)"
DATA_BUCKET="ai-employee-data-storage-$(date +%s)"

aws s3 mb s3://$KNOWLEDGE_BUCKET
aws s3 mb s3://$DATA_BUCKET

echo "Created S3 buckets:"
echo "- Knowledge bucket: $KNOWLEDGE_BUCKET"
echo "- Data bucket: $DATA_BUCKET"
```

### Step 5: Create SQS Queue for Routing

```bash
# Create SQS queue
QUEUE_URL=$(aws sqs create-queue \
  --queue-name routing-service-queue \
  --attributes '{"MessageRetentionPeriod":"86400"}' \
  --query 'QueueUrl' --output text)

echo "Created SQS queue: $QUEUE_URL"
```

### Step 6: Create SNS Topic for Escalations

```bash
# Create SNS topic
TOPIC_ARN=$(aws sns create-topic \
  --name escalation-notifications \
  --query 'TopicArn' --output text)

echo "Created SNS topic: $TOPIC_ARN"

# Optional: Subscribe an email to the topic
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint "your-email@example.com"
```

## Application Deployment

### Step 1: Set Environment Variables

Create a .env file with your infrastructure values:

```bash
cat > .env << EOF
LEX_BOT_ID=$BOT_ID
LEX_BOT_ALIAS_ID=$ALIAS_ID
ROUTING_QUEUE_URL=$QUEUE_URL
ESCALATION_TOPIC_ARN=$TOPIC_ARN
OPENSEARCH_DOMAIN=https://$DOMAIN_ENDPOINT
KNOWLEDGE_BUCKET=$KNOWLEDGE_BUCKET
KNOWLEDGE_INDEX=knowledge_base
EOF

# Source the environment variables
source .env
```

### Step 2: Initialize the Knowledge Base

Create a Python script to initialize the knowledge base index:

```bash
cat > initialize_kb.py << EOF
import boto3
import json
import os
import requests
from requests.auth import AWS4Auth

# Get environment variables
opensearch_domain = os.environ.get('OPENSEARCH_DOMAIN')
knowledge_index = os.environ.get('KNOWLEDGE_INDEX', 'knowledge_base')

# Create AWS auth for OpenSearch
region = 'us-east-1'  # Change to your region
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, 
                  region, service, session_token=credentials.token)

# Create the index
url = f"{opensearch_domain}/{knowledge_index}"
headers = {"Content-Type": "application/json"}
mapping = {
    "mappings": {
        "properties": {
            "title": {"type": "text"},
            "content": {"type": "text"},
            "category": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"}
        }
    }
}

# Delete index if it exists
response = requests.delete(url, auth=awsauth)
print(f"Delete index response: {response.status_code}")

# Create the index with mapping
response = requests.put(url, auth=awsauth, json=mapping, headers=headers)
print(f"Create index response: {response.status_code}")
print(response.text)

# Add a sample article
sample_article = {
    "title": "How to Reset Your Password",
    "content": "To reset your password, go to the login page and click on 'Forgot Password'. Follow the instructions sent to your email.",
    "category": "account",
    "tags": ["password", "account", "login"],
    "created_at": "2025-01-01T00:00:00",
    "updated_at": "2025-01-01T00:00:00"
}

doc_url = f"{url}/_doc/account-how-to-reset-your-password-1"
response = requests.put(doc_url, auth=awsauth, json=sample_article, headers=headers)
print(f"Add sample article response: {response.status_code}")
print(response.text)
EOF

# Run the initialization script
python initialize_kb.py
```

### Step 3: Deploy the Application

Option 1: Deploy as AWS Lambda Functions:

```bash
# Package the code
mkdir -p deployment
zip -r deployment/customer_service.zip \
  main-orchestrator.py \
  customer_service_handler.py \
  f_analyze_sales_data.py \
  customer_service_platform/

# Create Lambda function
aws lambda create-function \
  --function-name AI-Employee-Platform \
  --runtime python3.11 \
  --role arn:aws:iam::<ACCOUNT_ID>:role/AIEmployeeRole \
  --handler main-orchestrator.lambda_handler \
  --zip-file fileb://deployment/customer_service.zip \
  --timeout 30 \
  --environment "Variables={LEX_BOT_ID=$BOT_ID,LEX_BOT_ALIAS_ID=$ALIAS_ID,ROUTING_QUEUE_URL=$QUEUE_URL,ESCALATION_TOPIC_ARN=$TOPIC_ARN,OPENSEARCH_DOMAIN=https://$DOMAIN_ENDPOINT,KNOWLEDGE_BUCKET=$KNOWLEDGE_BUCKET,KNOWLEDGE_INDEX=knowledge_base}"
```

Option 2: Deploy on EC2:

```bash
# Set up an EC2 instance (instructions vary based on your needs)
# Install Python and dependencies, then run:
python main-orchestrator.py
```

## Testing the Platform

### Test using AWS CLI:

```bash
# Simulate a customer service request with Lex
aws lexv2-runtime recognize-text \
  --bot-id $BOT_ID \
  --bot-alias-id $ALIAS_ID \
  --locale-id "en_US" \
  --session-id "test-session-1" \
  --text "I need help with my account"
```

### Test using the Lambda function:

```bash
aws lambda invoke \
  --function-name AI-Employee-Platform \
  --payload '{"sessionState": {"intent": {"name": "CustomerService", "slots": {"CustomerMessage": {"value": {"interpretedValue": "I need help with my account"}}}}}, "sessionAttributes": {}}' \
  response.json

# Check the response
cat response.json
```

## Monitoring and Maintenance

### Set up CloudWatch Alarms

```bash
# Create an alarm for failed interactions
aws cloudwatch put-metric-alarm \
  --alarm-name CustomerServiceFailedInteractions \
  --alarm-description "Alarm for excessive failed customer service interactions" \
  --metric-name FailedInteractions \
  --namespace CustomerService \
  --statistic Sum \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --period 300 \
  --evaluation-periods 1 \
  --alarm-actions $TOPIC_ARN
```

### Regular Maintenance Tasks

1. Update knowledge base articles regularly
2. Review sentiment analysis results to improve customer experience
3. Analyze escalation patterns to identify common issues
4. Monitor AWS resource usage and costs

## Troubleshooting

### Common Issues and Solutions

1. **Lex bot not understanding intents**:
   - Review and improve training phrases
   - Check slot configuration

2. **OpenSearch connectivity issues**:
   - Verify network access and permissions
   - Check authentication settings

3. **Lambda function timeouts**:
   - Increase the timeout limit
   - Optimize code for better performance

4. **Missing environment variables**:
   - Check that all required variables are set
   - Verify variable names match what the code expects

## Resources and Support

- AWS Documentation: https://docs.aws.amazon.com/
- Support Contact: your-team-email@example.com

---

Save this document for reference during setup and maintenance of the AI Customer Service Platform.