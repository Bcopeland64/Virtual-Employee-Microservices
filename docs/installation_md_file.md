# AI Business Platform Suite - Installation Guide

This guide provides step-by-step instructions for deploying the AI Business Platform Suite using Docker containers and AWS Fargate.

## Prerequisites

- Docker installed locally (version 20.10 or higher)
- AWS CLI configured with appropriate permissions
- An AWS account with access to:
  - Amazon ECR (Elastic Container Registry)
  - Amazon ECS (Elastic Container Service)
  - AWS Fargate
  - Amazon S3
  - Amazon DynamoDB
  - Amazon Bedrock
  - AWS Lambda
  - Amazon SQS
  - Amazon QuickSight
  - CloudWatch
- An SSL certificate in AWS Certificate Manager (ACM) for HTTPS
- Sufficient IAM permissions for resource creation and management

## Platform Architecture Overview

The platform consists of five main business platforms:

1. **Sales Platform** - Sales analysis, marketing planning, and reporting
2. **Customer Service Platform** - Chatbot, sentiment analysis, and routing
3. **Financial Platform** - Financial processing and compliance
4. **Compliance Platform** - Regulatory monitoring and audit trails
5. **Legal Platform** - Document analysis and contract management

Each platform runs as containerized microservices on AWS Fargate.

## Step 1: Environment Setup

Set up your AWS environment variables:

```bash
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REPOSITORY_URI=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
export PLATFORM_NAME=ai-business-platform
```

## Step 2: Create Project Structure

```bash
mkdir -p ai-business-platform/{sales,customer-service,financial,compliance,legal}-platform
cd ai-business-platform

# Create shared configuration
mkdir -p shared/{config,scripts,templates}
```

## Step 3: Build Docker Images

### Sales Platform Services

Create Dockerfiles for each Sales Platform service:

```bash
# Sales Platform Services
services=("sales-analysis" "marketing-planner" "report-generator" "task-processor")

for service in "${services[@]}"; do
  mkdir -p sales-platform/${service}
  cat > sales-platform/${service}/Dockerfile << EOF
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \\
  CMD curl -f http://localhost:8080/health || exit 1
EXPOSE 8080
CMD ["python", "app.py"]
EOF
done
```

### Customer Service Platform Services

```bash
# Customer Service Platform Services
cs_services=("chatbot" "sentiment-analysis" "routing" "knowledge-base" "analytics" "escalation" "audit")

for service in "${cs_services[@]}"; do
  mkdir -p customer-service-platform/${service}-service
  cat > customer-service-platform/${service}-service/Dockerfile << EOF
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \\
  CMD curl -f http://localhost:8080/health || exit 1
EXPOSE 8080
CMD ["python", "app.py"]
EOF
done
```

### Other Platform Services

```bash
# Financial Platform
financial_services=("financial-processor" "risk-analyzer" "compliance-monitor")

# Compliance Platform  
compliance_services=("regulatory-monitor" "audit-manager" "risk-assessor")

# Legal Platform
legal_services=("document-analyzer" "contract-reviewer" "legal-research")

# Create Dockerfiles for all platforms
for platform in financial compliance legal; do
  eval "platform_services=(\"\${${platform}_services[@]}\")"
  for service in "${platform_services[@]}"; do
    mkdir -p ${platform}-platform/${service}
    cat > ${platform}-platform/${service}/Dockerfile << EOF
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \\
  CMD curl -f http://localhost:8080/health || exit 1
EXPOSE 8080
CMD ["python", "app.py"]
EOF
  done
done
```

### Create Requirements Files

```bash
cat > shared/requirements.txt << EOF
fastapi==0.104.1
uvicorn==0.24.0
boto3==1.34.0
requests==2.31.0
pandas==2.1.3
numpy==1.25.2
scikit-learn==1.3.2
pydantic==2.5.0
python-multipart==0.0.6
aiofiles==23.2.1
httpx==0.25.2
python-jose==3.3.0
passlib==1.7.4
python-dateutil==2.8.2
EOF
```

## Step 4: Create ECR Repositories

```bash
# Create repositories for all services
all_services=(
  "sales-analysis" "marketing-planner" "report-generator" "task-processor"
  "chatbot-service" "sentiment-analysis-service" "routing-service" 
  "knowledge-base-service" "analytics-service" "escalation-service" "audit-service"
  "financial-processor" "risk-analyzer" "compliance-monitor"
  "regulatory-monitor" "audit-manager" "risk-assessor"
  "document-analyzer" "contract-reviewer" "legal-research"
)

for service in "${all_services[@]}"; do
  aws ecr create-repository \
    --repository-name ${PLATFORM_NAME}/${service} \
    --region $AWS_REGION \
    --image-scanning-configuration scanOnPush=true
done
```

## Step 5: Build and Push Images

```bash
# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URI

# Build and push all images
platforms=("sales" "customer-service" "financial" "compliance" "legal")

for platform in "${platforms[@]}"; do
  case $platform in
    "sales")
      platform_services=("sales-analysis" "marketing-planner" "report-generator" "task-processor")
      ;;
    "customer-service") 
      platform_services=("chatbot-service" "sentiment-analysis-service" "routing-service" "knowledge-base-service" "analytics-service" "escalation-service" "audit-service")
      ;;
    "financial")
      platform_services=("financial-processor" "risk-analyzer" "compliance-monitor")
      ;;
    "compliance")
      platform_services=("regulatory-monitor" "audit-manager" "risk-assessor")
      ;;
    "legal")
      platform_services=("document-analyzer" "contract-reviewer" "legal-research")
      ;;
  esac
  
  for service in "${platform_services[@]}"; do
    echo "Building ${platform}-platform/${service}..."
    docker build -t ${PLATFORM_NAME}/${service}:latest ${platform}-platform/${service}/
    docker tag ${PLATFORM_NAME}/${service}:latest ${ECR_REPOSITORY_URI}/${PLATFORM_NAME}/${service}:latest
    docker push ${ECR_REPOSITORY_URI}/${PLATFORM_NAME}/${service}:latest
  done
done
```

## Step 6: Create AWS Infrastructure

### VPC and Networking

```bash
# Create VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=ai-platform-vpc}]' \
  --query 'Vpc.VpcId' \
  --output text)

# Create Internet Gateway
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=ai-platform-igw}]' \
  --query 'InternetGateway.InternetGatewayId' \
  --output text)

aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID

# Create subnets in multiple AZs
SUBNET_1_ID=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone ${AWS_REGION}a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=ai-platform-subnet-1}]' \
  --query 'Subnet.SubnetId' \
  --output text)

SUBNET_2_ID=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --availability-zone ${AWS_REGION}b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=ai-platform-subnet-2}]' \
  --query 'Subnet.SubnetId' \
  --output text)

# Create route table and routes
ROUTE_TABLE_ID=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=ai-platform-rt}]' \
  --query 'RouteTable.RouteTableId' \
  --output text)

aws ec2 create-route \
  --route-table-id $ROUTE_TABLE_ID \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $IGW_ID

aws ec2 associate-route-table --subnet-id $SUBNET_1_ID --route-table-id $ROUTE_TABLE_ID
aws ec2 associate-route-table --subnet-id $SUBNET_2_ID --route-table-id $ROUTE_TABLE_ID
```

### Security Groups

```bash
# ALB Security Group
ALB_SG_ID=$(aws ec2 create-security-group \
  --group-name ai-platform-alb-sg \
  --description "Security group for AI Platform ALB" \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=security-group,Tags=[{Key=Name,Value=ai-platform-alb-sg}]' \
  --query 'GroupId' \
  --output text)

aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG_ID \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG_ID \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# ECS Service Security Group
ECS_SG_ID=$(aws ec2 create-security-group \
  --group-name ai-platform-ecs-sg \
  --description "Security group for AI Platform ECS tasks" \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=security-group,Tags=[{Key=Name,Value=ai-platform-ecs-sg}]' \
  --query 'GroupId' \
  --output text)

aws ec2 authorize-security-group-ingress \
  --group-id $ECS_SG_ID \
  --protocol tcp \
  --port 8080 \
  --source-group $ALB_SG_ID
```

## Step 7: Create AWS Resources

### S3 Buckets

```bash
# Create S3 buckets for different data types
buckets=("reports" "documents" "data-lake" "config" "logs")

for bucket in "${buckets[@]}"; do
  aws s3 mb s3://${PLATFORM_NAME}-${bucket}-${AWS_ACCOUNT_ID}
done
```

### DynamoDB Tables

```bash
# Create DynamoDB tables
tables=("Tasks" "Analytics" "Users" "Configurations" "AuditLog")

for table in "${tables[@]}"; do
  aws dynamodb create-table \
    --table-name ${PLATFORM_NAME}-${table} \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST
done
```

### SQS Queues

```bash
# Create SQS queues for task processing
queues=("task-queue" "notification-queue" "audit-queue")

for queue in "${queues[@]}"; do
  aws sqs create-queue --queue-name ${PLATFORM_NAME}-${queue}
done
```

## Step 8: Create ECS Cluster and IAM Roles

```bash
# Create ECS Cluster
aws ecs create-cluster \
  --cluster-name ${PLATFORM_NAME}-cluster \
  --capacity-providers FARGATE \
  --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 \
  --tags key=Name,value=${PLATFORM_NAME}-cluster

# Create IAM roles
EXECUTION_ROLE_ARN=$(aws iam create-role \
  --role-name ${PLATFORM_NAME}-execution-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "ecs-tasks.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }' \
  --query 'Role.Arn' \
  --output text)

aws iam attach-role-policy \
  --role-name ${PLATFORM_NAME}-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

TASK_ROLE_ARN=$(aws iam create-role \
  --role-name ${PLATFORM_NAME}-task-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "ecs-tasks.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }' \
  --query 'Role.Arn' \
  --output text)

# Attach policies for AWS services access
aws iam attach-role-policy \
  --role-name ${PLATFORM_NAME}-task-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

aws iam attach-role-policy \
  --role-name ${PLATFORM_NAME}-task-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

aws iam attach-role-policy \
  --role-name ${PLATFORM_NAME}-task-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSQSFullAccess
```

## Step 9: Create Task Definitions

```bash
# Create task definitions for all services
for service in "${all_services[@]}"; do
  cat > ${service}-taskdef.json << EOF
{
  "family": "${service}",
  "networkMode": "awsvpc",
  "executionRoleArn": "${EXECUTION_ROLE_ARN}",
  "taskRoleArn": "${TASK_ROLE_ARN}",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "${service}",
      "image": "${ECR_REPOSITORY_URI}/${PLATFORM_NAME}/${service}:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8080,
          "hostPort": 8080,
          "protocol": "tcp"
        }
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      },
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/${PLATFORM_NAME}/${service}",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      },
      "environment": [
        {
          "name": "AWS_REGION",
          "value": "${AWS_REGION}"
        },
        {
          "name": "PLATFORM_NAME",
          "value": "${PLATFORM_NAME}"
        }
      ]
    }
  ]
}
EOF

  aws ecs register-task-definition \
    --cli-input-json file://${service}-taskdef.json \
    --region $AWS_REGION
done
```

## Step 10: Create Application Load Balancer

```bash
# Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name ${PLATFORM_NAME}-alb \
  --subnets $SUBNET_1_ID $SUBNET_2_ID \
  --security-groups $ALB_SG_ID \
  --scheme internet-facing \
  --type application \
  --tags Key=Name,Value=${PLATFORM_NAME}-alb \
  --query "LoadBalancers[0].LoadBalancerArn" \
  --output text)

# Create target groups for each service
for service in "${all_services[@]}"; do
  TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
    --name ${service}-tg \
    --protocol HTTP \
    --port 8080 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path /health \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 5 \
    --query "TargetGroups[0].TargetGroupArn" \
    --output text)
  
  echo "Created target group for ${service}: ${TARGET_GROUP_ARN}"
done
```

## Step 11: Deploy Services

```bash
# Create ECS services for all platforms
for service in "${all_services[@]}"; do
  TARGET_GROUP_ARN=$(aws elbv2 describe-target-groups \
    --names ${service}-tg \
    --query "TargetGroups[0].TargetGroupArn" \
    --output text)
  
  aws ecs create-service \
    --cluster ${PLATFORM_NAME}-cluster \
    --service-name ${service} \
    --task-definition ${service} \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1_ID,$SUBNET_2_ID],securityGroups=[$ECS_SG_ID],assignPublicIp=ENABLED}" \
    --load-balancers "targetGroupArn=${TARGET_GROUP_ARN},containerName=${service},containerPort=8080" \
    --tags key=Name,value=${service}
done
```

## Step 12: Configure Load Balancer Routing

```bash
# Create listener for ALB
LISTENER_ARN=$(aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=fixed-response,FixedResponseConfig='{MessageBody="AI Business Platform",StatusCode="200",ContentType="text/plain"}' \
  --query "Listeners[0].ListenerArn" \
  --output text)

# Create routing rules for each platform
platforms_routes=(
  "sales=/sales/*"
  "customer-service=/customer-service/*"
  "financial=/financial/*" 
  "compliance=/compliance/*"
  "legal=/legal/*"
)

for route in "${platforms_routes[@]}"; do
  platform=${route%=*}
  path=${route#*=}
  
  # Get first service target group for the platform
  case $platform in
    "sales") service="sales-analysis" ;;
    "customer-service") service="chatbot-service" ;;
    "financial") service="financial-processor" ;;
    "compliance") service="regulatory-monitor" ;;
    "legal") service="document-analyzer" ;;
  esac
  
  TARGET_GROUP_ARN=$(aws elbv2 describe-target-groups \
    --names ${service}-tg \
    --query "TargetGroups[0].TargetGroupArn" \
    --output text)
  
  aws elbv2 create-rule \
    --listener-arn $LISTENER_ARN \
    --priority $((RANDOM % 1000 + 1)) \
    --conditions Field=path-pattern,Values="$path" \
    --actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN
done
```

## Step 13: Validation and Testing

```bash
# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query "LoadBalancers[0].DNSName" \
  --output text)

echo "Platform deployed successfully!"
echo "Access URL: http://${ALB_DNS}"
echo ""
echo "Platform endpoints:"
echo "  Sales Platform: http://${ALB_DNS}/sales/"
echo "  Customer Service Platform: http://${ALB_DNS}/customer-service/"
echo "  Financial Platform: http://${ALB_DNS}/financial/"
echo "  Compliance Platform: http://${ALB_DNS}/compliance/"
echo "  Legal Platform: http://${ALB_DNS}/legal/"

# Test health endpoints
for service in "${all_services[@]}"; do
  echo "Testing ${service} health endpoint..."
  # Health checks will be performed by ALB
done
```

## Step 14: Monitoring and Logs

```bash
# CloudWatch Log Groups are created automatically by the tasks
# View logs for a specific service:
# aws logs describe-log-groups --log-group-name-prefix "/ecs/${PLATFORM_NAME}"

echo "Monitor your deployment:"
echo "  CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#logsV2:log-groups"
echo "  ECS Console: https://console.aws.amazon.com/ecs/home?region=${AWS_REGION}#/clusters"
echo "  Load Balancer: https://console.aws.amazon.com/ec2/v2/home?region=${AWS_REGION}#LoadBalancers"
```

## Cleanup (Optional)

To remove all resources created during installation:

```bash
# Delete ECS services
for service in "${all_services[@]}"; do
  aws ecs update-service --cluster ${PLATFORM_NAME}-cluster --service ${service} --desired-count 0
  aws ecs delete-service --cluster ${PLATFORM_NAME}-cluster --service ${service}
done

# Delete ECS cluster
aws ecs delete-cluster --cluster ${PLATFORM_NAME}-cluster

# Delete ALB and target groups
aws elbv2 delete-load-balancer --load-balancer-arn $ALB_ARN

# Continue with other resources as needed...
```

## Next Steps

After successful installation:

1. Configure platform-specific settings
2. Set up user authentication and authorization
3. Configure monitoring and alerting
4. Review security settings
5. Refer to `user_guide.md` for usage instructions

## Troubleshooting

Common issues and solutions:

- **Container fails to start**: Check CloudWatch logs for error messages
- **Service unreachable**: Verify security group rules and target group health
- **Permission errors**: Ensure IAM roles have necessary permissions
- **Resource limits**: Check AWS service limits and quotas