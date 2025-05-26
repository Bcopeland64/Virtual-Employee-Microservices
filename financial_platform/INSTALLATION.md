# Financial Platform Installation Guide

This guide provides step-by-step instructions for deploying the AI Financial Platform using Docker containers and AWS Fargate.

## Prerequisites

- Docker installed locally
- AWS CLI configured with appropriate permissions
- An AWS account with access to:
  - ECR (Elastic Container Registry)
  - ECS (Elastic Container Service)
  - Fargate
  - IAM
  - CloudFormation
  - Systems Manager Parameter Store
  - CloudWatch
  - Application Load Balancer
  - DynamoDB
  - S3
  - RDS
  - Timestream

## Deployment Architecture

The Financial Platform runs as a set of containerized microservices:

1. **Financial Data Processing Service** - Handles data ingestion and normalization
2. **Financial Analysis Service** - Analyzes financial statements and generates insights
3. **Financial Forecasting Service** - Generates projections and what-if scenarios
4. **Risk Assessment Service** - Evaluates financial risks
5. **Transaction Management Service** - Processes financial transactions

## Step 1: Build Docker Images

Create a Dockerfile for each service in the financial platform:

### Financial Data Processing Service Dockerfile

```dockerfile
# data-processor/Dockerfile
FROM amazon/aws-lambda-python:3.11

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["app.handler"]
```

### Financial Analysis Service Dockerfile

```dockerfile
# financial-analyzer/Dockerfile
FROM amazon/aws-lambda-python:3.11

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["app.handler"]
```

### Financial Forecasting Service Dockerfile

```dockerfile
# financial-forecaster/Dockerfile
FROM amazon/aws-lambda-python:3.11

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["app.handler"]
```

### Risk Assessment Service Dockerfile

```dockerfile
# risk-assessment/Dockerfile
FROM amazon/aws-lambda-python:3.11

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["app.handler"]
```

### Transaction Management Service Dockerfile

```dockerfile
# transaction-manager/Dockerfile
FROM amazon/aws-lambda-python:3.11

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["app.handler"]
```

Build the Docker images:

```bash
# Create required directories and copy code
mkdir -p data-processor financial-analyzer financial-forecaster risk-assessment transaction-manager

# Copy code to appropriate directories
cp financial_platform/integration.py data-processor/app.py
cp financial_platform/integration.py financial-analyzer/app.py
cp financial_platform/integration.py financial-forecaster/app.py
cp financial_platform/integration.py risk-assessment/app.py
cp financial_platform/integration.py transaction-manager/app.py

# Create requirements.txt
cat > requirements.txt << EOF
boto3==1.35.51
botocore==1.35.51
requests==2.32.3
numpy==1.26.0
pandas==2.2.0
matplotlib==3.8.0
scikit-learn==1.4.0
PyYAML==6.0.2
uuid==1.30
EOF

cp requirements.txt data-processor/
cp requirements.txt financial-analyzer/
cp requirements.txt financial-forecaster/
cp requirements.txt risk-assessment/
cp requirements.txt transaction-manager/

# Build the images
docker build -t ai-employee/data-processor:latest data-processor/
docker build -t ai-employee/financial-analyzer:latest financial-analyzer/
docker build -t ai-employee/financial-forecaster:latest financial-forecaster/
docker build -t ai-employee/risk-assessment:latest risk-assessment/
docker build -t ai-employee/transaction-manager:latest transaction-manager/
```

## Step 2: Push Images to Amazon ECR

Create ECR repositories and push the images:

```bash
# Create ECR repositories
aws ecr create-repository --repository-name ai-employee/data-processor
aws ecr create-repository --repository-name ai-employee/financial-analyzer
aws ecr create-repository --repository-name ai-employee/financial-forecaster
aws ecr create-repository --repository-name ai-employee/risk-assessment
aws ecr create-repository --repository-name ai-employee/transaction-manager

# Get the ECR login command
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Tag images for ECR
docker tag ai-employee/data-processor:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-employee/data-processor:latest
docker tag ai-employee/financial-analyzer:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-employee/financial-analyzer:latest
docker tag ai-employee/financial-forecaster:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-employee/financial-forecaster:latest
docker tag ai-employee/risk-assessment:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-employee/risk-assessment:latest
docker tag ai-employee/transaction-manager:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-employee/transaction-manager:latest

# Push images to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-employee/data-processor:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-employee/financial-analyzer:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-employee/financial-forecaster:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-employee/risk-assessment:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-employee/transaction-manager:latest
```

## Step 3: Store Configuration in AWS Systems Manager Parameter Store

Store configuration values securely:

```bash
# Store configuration parameters
aws ssm put-parameter --name "/financial-platform/FINANCIAL_DATA_BUCKET" --type "String" --value "ai-employee-financial-data" --overwrite
aws ssm put-parameter --name "/financial-platform/FINANCIAL_DATABASE" --type "String" --value "ai_employee_financial" --overwrite
aws ssm put-parameter --name "/financial-platform/TIMESTREAM_DB" --type "String" --value "financial_metrics" --overwrite
aws ssm put-parameter --name "/financial-platform/TIMESTREAM_TABLE" --type "String" --value "financial_data" --overwrite

# Store sensitive values securely
aws ssm put-parameter --name "/financial-platform/DATABASE_PASSWORD" --type "SecureString" --value "YOUR_SECURE_PASSWORD" --overwrite
```

## Step 4: Deploy AWS Resources with CloudFormation

Use CloudFormation to deploy all required resources:

```bash
# Deploy CloudFormation stack
aws cloudformation create-stack \
  --stack-name financial-platform \
  --template-body file://financial-platform-fargate.yml \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --parameters \
    ParameterKey=DockerImageDataProcessor,ParameterValue=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-employee/data-processor:latest \
    ParameterKey=DockerImageFinancialAnalyzer,ParameterValue=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-employee/financial-analyzer:latest \
    ParameterKey=DockerImageFinancialForecaster,ParameterValue=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-employee/financial-forecaster:latest \
    ParameterKey=DockerImageRiskAssessment,ParameterValue=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-employee/risk-assessment:latest \
    ParameterKey=DockerImageTransactionManager,ParameterValue=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/ai-employee/transaction-manager:latest
```

## Step 5: Wait for Deployment and Get Service Endpoints

```bash
# Wait for stack creation to complete
aws cloudformation wait stack-create-complete --stack-name financial-platform

# Get the load balancer DNS name
LOAD_BALANCER_DNS=$(aws cloudformation describe-stacks --stack-name financial-platform --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerDNS'].OutputValue" --output text)
echo "Financial Platform Endpoint: $LOAD_BALANCER_DNS"
```

## Step 6: Create Required AWS Database Resources

```bash
# Create S3 bucket for financial data (if not already created by CloudFormation)
aws s3 mb s3://ai-employee-financial-data --region $AWS_REGION

# Create DynamoDB tables (if not already created by CloudFormation)
aws dynamodb create-table \
  --table-name FinancialDatasets \
  --attribute-definitions AttributeName=DatasetId,AttributeType=S \
  --key-schema AttributeName=DatasetId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

aws dynamodb create-table \
  --table-name FinancialAnalyses \
  --attribute-definitions AttributeName=AnalysisId,AttributeType=S \
  --key-schema AttributeName=AnalysisId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

aws dynamodb create-table \
  --table-name FinancialForecasts \
  --attribute-definitions AttributeName=ForecastId,AttributeType=S \
  --key-schema AttributeName=ForecastId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

aws dynamodb create-table \
  --table-name RiskAssessments \
  --attribute-definitions AttributeName=RiskId,AttributeType=S \
  --key-schema AttributeName=RiskId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

aws dynamodb create-table \
  --table-name TransactionBatches \
  --attribute-definitions AttributeName=BatchId,AttributeType=S \
  --key-schema AttributeName=BatchId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# Create Amazon Timestream database and table (if not created by CloudFormation)
aws timestream-write create-database --database-name financial_metrics
aws timestream-write create-table --database-name financial_metrics --table-name financial_data
```

## Step 7: Set Up Monitoring and Logging

The CloudFormation template automatically configures:
- CloudWatch logs for all containers
- CloudWatch alarms for service health monitoring
- CPU and memory utilization metrics
- Container insights for advanced monitoring

You can access these resources in the AWS Management Console:
1. CloudWatch > Log Groups (search for "/ecs/financial-platform")
2. CloudWatch > Alarms to view service health alarms
3. CloudWatch > Metrics to explore detailed service metrics

## Step 8: Configure AI Employee Integration

Update the AI Employee configuration to use the new Fargate service endpoints:

```bash
# Get the service endpoints
DATA_PROCESSOR_ENDPOINT="http://$LOAD_BALANCER_DNS/data-processor"
FINANCIAL_ANALYZER_ENDPOINT="http://$LOAD_BALANCER_DNS/financial-analyzer" 
FINANCIAL_FORECASTER_ENDPOINT="http://$LOAD_BALANCER_DNS/financial-forecaster"
RISK_ASSESSMENT_ENDPOINT="http://$LOAD_BALANCER_DNS/risk-assessment"
TRANSACTION_MANAGER_ENDPOINT="http://$LOAD_BALANCER_DNS/transaction-manager"

# Store these endpoints in SSM for the AI Employee to use
aws ssm put-parameter --name "/ai-employee/FINANCIAL_DATA_PROCESSOR_URL" --type "String" --value "$DATA_PROCESSOR_ENDPOINT" --overwrite
aws ssm put-parameter --name "/ai-employee/FINANCIAL_ANALYZER_URL" --type "String" --value "$FINANCIAL_ANALYZER_ENDPOINT" --overwrite
aws ssm put-parameter --name "/ai-employee/FINANCIAL_FORECASTER_URL" --type "String" --value "$FINANCIAL_FORECASTER_ENDPOINT" --overwrite
aws ssm put-parameter --name "/ai-employee/RISK_ASSESSMENT_URL" --type "String" --value "$RISK_ASSESSMENT_ENDPOINT" --overwrite
aws ssm put-parameter --name "/ai-employee/TRANSACTION_MANAGER_URL" --type "String" --value "$TRANSACTION_MANAGER_ENDPOINT" --overwrite
```

## Step 9: Test the Deployment

Send test requests to verify the services are working:

```bash
# Test Data Processor Endpoint
curl -X POST "$DATA_PROCESSOR_ENDPOINT/process" \
  -H "Content-Type: application/json" \
  -d '{"data": {"sample": "data"}, "data_type": "transactions"}'

# Test Financial Analyzer Endpoint
curl -X POST "$FINANCIAL_ANALYZER_ENDPOINT/analyze" \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "test-dataset-123"}'
```

## Troubleshooting

### Common Issues and Solutions

1. **Container Health Check Failures**:
   - Check container logs in CloudWatch: `aws logs get-log-events --log-group-name /ecs/financial-platform/data-processor --log-stream-name <log-stream-name>`
   - Verify environment variables are correctly set in the task definition
   - Check if containers can access required AWS services (S3, DynamoDB, etc.)

2. **Service Discovery Issues**:
   - Verify that the load balancer target groups are healthy
   - Check that the service task definitions have correct ports exposed
   - Ensure network ACLs and security groups allow required traffic

3. **Scaling Problems**:
   - Review CloudWatch metrics for CPU and memory utilization
   - Check the auto-scaling policies and thresholds in the CloudFormation template
   - Verify that the ECS service has the correct desired count and maximum count settings

4. **Integration Issues**:
   - Confirm the correct endpoint URLs are stored in SSM
   - Verify the AI Employee has appropriate IAM permissions to access the SSM parameters
   - Check network connectivity between the AI Employee and the Financial Platform services

## Next Steps

1. **Set up CI/CD Pipeline**: Create a CI/CD pipeline using AWS CodePipeline to automate deployments.
2. **Configure Custom Domain**: Set up Route 53 and obtain an SSL certificate for a custom domain.
3. **Implement Disaster Recovery**: Configure cross-region replication for critical data stores.
4. **Enhance Security**: Implement AWS WAF for additional API security.
5. **Set up Advanced Monitoring**: Implement X-Ray for distributed tracing.

For advanced configuration and optimization, refer to the architecture document in the Sprint_2 documentation.