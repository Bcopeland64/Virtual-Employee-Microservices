# Setup Guide

This document provides instructions for deploying the AI Employee Platform using AWS Fargate.

## Prerequisites

Before deployment, ensure you have the following:

- AWS account with administrator access
- AWS CLI installed and configured
- Docker installed on your development machine
- Git repository access

## Initial Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd AI_Employee_Test_Setup
```

### 2. Configure AWS Credentials

Ensure your AWS credentials are properly configured:

```bash
aws configure
```

### 3. Create ECR Repositories

```bash
# Create ECR repositories for each service
aws ecr create-repository --repository-name financial-platform/data-processor
aws ecr create-repository --repository-name financial-platform/financial-analyzer
aws ecr create-repository --repository-name financial-platform/financial-forecaster
aws ecr create-repository --repository-name financial-platform/risk-assessment
aws ecr create-repository --repository-name financial-platform/transaction-manager

aws ecr create-repository --repository-name compliance-platform/regulatory-intelligence
aws ecr create-repository --repository-name compliance-platform/web-scraping
aws ecr create-repository --repository-name compliance-platform/compliance-analysis
aws ecr create-repository --repository-name compliance-platform/ethics-assessment
aws ecr create-repository --repository-name compliance-platform/policy-management
aws ecr create-repository --repository-name compliance-platform/reporting-dashboard

aws ecr create-repository --repository-name customer-service/chatbot-service
aws ecr create-repository --repository-name customer-service/knowledge-service
aws ecr create-repository --repository-name customer-service/ticket-management
aws ecr create-repository --repository-name customer-service/analytics-service

aws ecr create-repository --repository-name legal-platform/contract-analysis
aws ecr create-repository --repository-name legal-platform/compliance-checker
aws ecr create-repository --repository-name legal-platform/legal-research
aws ecr create-repository --repository-name legal-platform/legal-doc-gen
```

### 4. Build and Push Docker Images

For each service, build and push the Docker image to ECR:

```bash
# Log in to ECR
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com

# Example for Financial Platform services
cd financial_platform
docker build -t <account-id>.dkr.ecr.<region>.amazonaws.com/financial-platform/data-processor:latest .
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/financial-platform/data-processor:latest

# Repeat for each service
```

### 5. Create Parameter Store Values

Create necessary SSM Parameter Store values:

```bash
# Financial Platform parameters
aws ssm put-parameter --name "/financial-platform/FINANCIAL_DATA_BUCKET" --value "financial-data-bucket-name" --type "String"
aws ssm put-parameter --name "/financial-platform/FINANCIAL_DATABASE" --value "financial-database-name" --type "String"
aws ssm put-parameter --name "/financial-platform/TIMESTREAM_DB" --value "financial-timestream-db" --type "String"
aws ssm put-parameter --name "/financial-platform/TIMESTREAM_TABLE" --value "financial-metrics" --type "String"

# Compliance Platform parameters
# (Created through CloudFormation template)

# Customer Service Platform parameters
aws ssm put-parameter --name "/customer-service/CUSTOMER_DATA_BUCKET" --value "customer-data-bucket-name" --type "String"
aws ssm put-parameter --name "/customer-service/BEDROCK_MODEL_ID" --value "amazon.bedrock-nova-12b" --type "String"
aws ssm put-parameter --name "/customer-service/KENDRA_INDEX_ID" --value "kendra-index-id" --type "String"
aws ssm put-parameter --name "/customer-service/OPENSEARCH_DOMAIN" --value "customer-service-domain" --type "String"
aws ssm put-parameter --name "/customer-service/TICKETS_DYNAMODB_TABLE" --value "customer-tickets" --type "String"
aws ssm put-parameter --name "/customer-service/SQS_QUEUE_URL" --value "https://sqs.region.amazonaws.com/account-id/customer-service-queue" --type "String"
aws ssm put-parameter --name "/customer-service/ANALYTICS_BUCKET" --value "customer-analytics-bucket" --type "String"
aws ssm put-parameter --name "/customer-service/DYNAMODB_ANALYTICS_TABLE" --value "customer-analytics" --type "String"

# Legal Platform parameters
aws ssm put-parameter --name "/legal-platform/CONTRACTS_BUCKET" --value "legal-contracts-bucket" --type "String"
aws ssm put-parameter --name "/legal-platform/TEXTRACT_OUTPUT_BUCKET" --value "legal-textract-output" --type "String"
aws ssm put-parameter --name "/legal-platform/REGULATIONS_INDEX_ID" --value "regulations-kendra-index" --type "String"
aws ssm put-parameter --name "/legal-platform/COMPLIANCE_DATABASE" --value "legal-compliance-db" --type "String"
aws ssm put-parameter --name "/legal-platform/LEGAL_RESEARCH_INDEX" --value "legal-research-index" --type "String"
aws ssm put-parameter --name "/legal-platform/BEDROCK_MODEL_ID" --value "amazon.bedrock-nova-12b" --type "String"
aws ssm put-parameter --name "/legal-platform/TEMPLATES_BUCKET" --value "legal-templates-bucket" --type "String"
aws ssm put-parameter --name "/legal-platform/DOCUMENTS_BUCKET" --value "legal-documents-bucket" --type "String"
```

## Deployment

### 1. Deploy VPC and Network Infrastructure

```bash
# If you need to create a new VPC
aws cloudformation create-stack \
  --stack-name ai-employee-network \
  --template-body file://infrastructure/vpc.yml \
  --capabilities CAPABILITY_IAM
```

### 2. Obtain VPC and Subnet IDs

```bash
# Get VPC and subnet IDs from the output of the network stack
aws cloudformation describe-stacks --stack-name ai-employee-network --query "Stacks[0].Outputs"
```

### 3. Deploy Service Platforms

#### Financial Platform

```bash
aws cloudformation create-stack \
  --stack-name financial-platform \
  --template-body file://financial_platform/financial-platform-fargate.yml \
  --parameters \
    ParameterKey=DockerImageDataProcessor,ParameterValue=<account-id>.dkr.ecr.<region>.amazonaws.com/financial-platform/data-processor:latest \
    ParameterKey=DockerImageFinancialAnalyzer,ParameterValue=<account-id>.dkr.ecr.<region>.amazonaws.com/financial-platform/financial-analyzer:latest \
    ParameterKey=DockerImageFinancialForecaster,ParameterValue=<account-id>.dkr.ecr.<region>.amazonaws.com/financial-platform/financial-forecaster:latest \
    ParameterKey=DockerImageRiskAssessment,ParameterValue=<account-id>.dkr.ecr.<region>.amazonaws.com/financial-platform/risk-assessment:latest \
    ParameterKey=DockerImageTransactionManager,ParameterValue=<account-id>.dkr.ecr.<region>.amazonaws.com/financial-platform/transaction-manager:latest \
    ParameterKey=EnvironmentName,ParameterValue=production \
    ParameterKey=ContainerCpu,ParameterValue=256 \
    ParameterKey=ContainerMemory,ParameterValue=512 \
    ParameterKey=DesiredCount,ParameterValue=2 \
    ParameterKey=MaxCount,ParameterValue=4 \
  --capabilities CAPABILITY_IAM
```

#### Compliance Platform

```bash
aws cloudformation create-stack \
  --stack-name compliance-platform \
  --template-body file://compliance_platform/compliance-platform-fargate.yml \
  --parameters \
    ParameterKey=EcrRepositoryUri,ParameterValue=<account-id>.dkr.ecr.<region>.amazonaws.com \
    ParameterKey=EnvironmentName,ParameterValue=prod \
    ParameterKey=VpcId,ParameterValue=<vpc-id> \
    ParameterKey=SubnetIds,ParameterValue=\"<subnet-id-1>,<subnet-id-2>\" \
    ParameterKey=CertificateArn,ParameterValue=<certificate-arn> \
  --capabilities CAPABILITY_IAM
```

#### Customer Service Platform

```bash
aws cloudformation create-stack \
  --stack-name customer-service-platform \
  --template-body file://customer_service_platform/customer-service-platform-fargate.yml \
  --parameters \
    ParameterKey=DockerImageChatbotService,ParameterValue=<account-id>.dkr.ecr.<region>.amazonaws.com/customer-service/chatbot-service:latest \
    ParameterKey=DockerImageKnowledgeService,ParameterValue=<account-id>.dkr.ecr.<region>.amazonaws.com/customer-service/knowledge-service:latest \
    ParameterKey=DockerImageTicketManagement,ParameterValue=<account-id>.dkr.ecr.<region>.amazonaws.com/customer-service/ticket-management:latest \
    ParameterKey=DockerImageAnalyticsService,ParameterValue=<account-id>.dkr.ecr.<region>.amazonaws.com/customer-service/analytics-service:latest \
    ParameterKey=EnvironmentName,ParameterValue=production \
    ParameterKey=ContainerCpu,ParameterValue=256 \
    ParameterKey=ContainerMemory,ParameterValue=512 \
    ParameterKey=DesiredCount,ParameterValue=2 \
    ParameterKey=MaxCount,ParameterValue=4 \
  --capabilities CAPABILITY_IAM
```

#### Legal Platform

```bash
aws cloudformation create-stack \
  --stack-name legal-platform \
  --template-body file://legal_platform/legal-platform-fargate.yml \
  --parameters \
    ParameterKey=DockerImageContractAnalysis,ParameterValue=<account-id>.dkr.ecr.<region>.amazonaws.com/legal-platform/contract-analysis:latest \
    ParameterKey=DockerImageComplianceChecker,ParameterValue=<account-id>.dkr.ecr.<region>.amazonaws.com/legal-platform/compliance-checker:latest \
    ParameterKey=DockerImageLegalResearch,ParameterValue=<account-id>.dkr.ecr.<region>.amazonaws.com/legal-platform/legal-research:latest \
    ParameterKey=DockerImageLegalDocGen,ParameterValue=<account-id>.dkr.ecr.<region>.amazonaws.com/legal-platform/legal-doc-gen:latest \
    ParameterKey=EnvironmentName,ParameterValue=production \
    ParameterKey=ContainerCpu,ParameterValue=256 \
    ParameterKey=ContainerMemory,ParameterValue=512 \
    ParameterKey=DesiredCount,ParameterValue=2 \
    ParameterKey=MaxCount,ParameterValue=4 \
  --capabilities CAPABILITY_IAM
```

### 4. Deploy Lambda Functions

```bash
# Deploy Lambda function for sales analysis
cd lambda/analyze_sales
zip -r ../analyze_sales.zip *
aws lambda create-function \
  --function-name analyze-sales \
  --runtime python3.9 \
  --role arn:aws:iam::<account-id>:role/lambda-sales-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://../analyze_sales.zip

# Repeat for other Lambda functions
```

## Verification

### 1. Verify Stack Deployment

```bash
# Verify CloudFormation Stacks
aws cloudformation describe-stacks --stack-name financial-platform
aws cloudformation describe-stacks --stack-name compliance-platform
aws cloudformation describe-stacks --stack-name customer-service-platform
aws cloudformation describe-stacks --stack-name legal-platform
```

### 2. Test Service Endpoints

Once the stacks are deployed, test the service endpoints:

```bash
# Get ALB DNS names
FINANCIAL_ALB=$(aws cloudformation describe-stacks --stack-name financial-platform --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerDNS'].OutputValue" --output text)
COMPLIANCE_ALB=$(aws cloudformation describe-stacks --stack-name compliance-platform --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerDNS'].OutputValue" --output text)
CUSTOMER_ALB=$(aws cloudformation describe-stacks --stack-name customer-service-platform --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerDNS'].OutputValue" --output text)
LEGAL_ALB=$(aws cloudformation describe-stacks --stack-name legal-platform --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerDNS'].OutputValue" --output text)

# Test endpoints
curl http://$FINANCIAL_ALB/data-processor/health
curl http://$COMPLIANCE_ALB/api/v1/regulations/health
curl http://$CUSTOMER_ALB/chatbot/health
curl http://$LEGAL_ALB/contracts/health
```

## Troubleshooting

If you encounter issues during deployment:

1. **CloudFormation Stack Failures**:
   ```bash
   aws cloudformation describe-stack-events --stack-name <stack-name>
   ```

2. **Service Container Issues**:
   ```bash
   # Find the service name
   aws ecs list-services --cluster <cluster-name>
   
   # Get task details
   aws ecs list-tasks --cluster <cluster-name> --service-name <service-name>
   aws ecs describe-tasks --cluster <cluster-name> --tasks <task-id>
   ```

3. **View Logs**:
   Check CloudWatch Logs for container logs:
   ```bash
   aws logs get-log-events --log-group-name /ecs/<stack-name>/<service-name> --log-stream-name <log-stream>
   ```

## Next Steps

After successful deployment:

1. **Set up CI/CD Pipeline**: Configure AWS CodePipeline for continuous deployment
2. **Set up Monitoring**: Configure additional CloudWatch alarms and dashboards
3. **Implement Backup Strategy**: Configure backups for persistent data
4. **Implement Security Scan**: Regularly scan containers for vulnerabilities

See the [User Guide](USER_GUIDE.md) for details on how to use the platform.