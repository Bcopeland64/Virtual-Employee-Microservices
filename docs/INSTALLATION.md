# Customer Service Platform Installation Guide

This guide provides step-by-step instructions for deploying the AI Customer Service Platform using Docker containers and AWS Fargate.

## Prerequisites

- Docker installed locally
- AWS CLI configured with appropriate permissions
- An AWS account with access to Amazon ECR, ECS, Fargate, and related services
- An SSL certificate in AWS Certificate Manager (ACM) for HTTPS

## Deployment Architecture

The Customer Service Platform runs as a set of containerized microservices:

1. **Chatbot Service** - Handles customer interactions and conversational interface
2. **Sentiment Analysis Service** - Analyzes sentiment in customer messages
3. **Routing Service** - Routes customer inquiries to appropriate handlers
4. **Knowledge Base Service** - Manages and retrieves knowledge base content
5. **Analytics Service** - Provides analytics and reporting
6. **Escalation Service** - Handles customer issue escalation
7. **Audit Service** - Logs and tracks compliance

## Step 1: Set Up Environment Variables

```bash
# Set required environment variables
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REPOSITORY_URI=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
```

## Step 2: Build Docker Images

Create a Dockerfile for each service in the customer service platform:

### Chatbot Service Dockerfile

```dockerfile
# chatbot-service/Dockerfile
FROM amazon/aws-lambda-python:3.11

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Set health check command
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Expose the port that the application will run on
EXPOSE 8080

CMD ["app.handler"]
```

Create similar Dockerfiles for all services. Here's an example for the remaining services:

```dockerfile
# sentiment-service/Dockerfile
FROM amazon/aws-lambda-python:3.11

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Set health check command
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Expose the port that the application will run on
EXPOSE 8080

CMD ["app.handler"]
```

Build the Docker images:

```bash
# Create required directories and copy code
mkdir -p chatbot-service sentiment-service routing-service knowledge-service analytics-service escalation-service audit-service

# Create requirements.txt
cat > requirements.txt << EOF
boto3==1.35.51
botocore==1.35.51
requests==2.32.3
PyYAML==6.0.2
redis==5.0.0
uuid==1.30
flask==2.3.3
EOF

# Copy to all service directories
for service in chatbot-service sentiment-service routing-service knowledge-service analytics-service escalation-service audit-service; do
  cp requirements.txt $service/
  
  # Create a basic app.py starter file in each directory
  cat > $service/app.py << EOFPY
import os
import json
import boto3
import logging
import flask

# Set up logging
logger = logging.getLogger('${service}')
logger.setLevel(logging.INFO)

# Create Flask app
app = flask.Flask(__name__)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.route('/ready')
def readiness_check():
    """Readiness check endpoint"""
    return {"status": "ready"}

def handler(event, context):
    """Main Lambda handler function"""
    try:
        # Process the request
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'success',
                'service': '${service}'
            })
        }
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'message': str(e)
            })
        }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
EOFPY
done

# Build the images
for service in chatbot-service sentiment-service routing-service knowledge-service analytics-service escalation-service audit-service; do
  docker build -t ai-employee/$service:latest $service/
done
```

## Step 3: Create ECR Repositories and Push Images

```bash
# Create ECR repositories for all services
for service in chatbot-service sentiment-service routing-service knowledge-service analytics-service escalation-service audit-service; do
  aws ecr create-repository \
    --repository-name ai-employee/$service \
    --image-scanning-configuration scanOnPush=true \
    --region $AWS_REGION
done

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Tag and push all images
for service in chatbot-service sentiment-service routing-service knowledge-service analytics-service escalation-service audit-service; do
  docker tag ai-employee/$service:latest $ECR_REPOSITORY_URI/ai-employee/$service:latest
  docker push $ECR_REPOSITORY_URI/ai-employee/$service:latest
done
```

## Step 4: Create AWS Resources

### Set Up CloudWatch Log Groups

```bash
# Create CloudWatch log groups for each service
for service in chatbot-service sentiment-service routing-service knowledge-service analytics-service escalation-service audit-service; do
  aws logs create-log-group --log-group-name "/ecs/customer-service/$service" --region $AWS_REGION
done
```

### Create S3 Bucket

```bash
# Create S3 bucket for customer service data
aws s3 mb s3://ai-employee-customer-service --region $AWS_REGION

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket ai-employee-customer-service \
  --versioning-configuration Status=Enabled
```

### Set Up Amazon ElastiCache for Redis

```bash
# Create ElastiCache subnet group
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name customer-service-cache-subnet \
  --cache-subnet-group-description "Subnet group for Customer Service Redis" \
  --subnet-ids $(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text)" --query "Subnets[?MapPublicIpOnLaunch==\`true\`].SubnetId" --output text | tr '\t' ' ')

# Create ElastiCache security group
REDIS_SG=$(aws ec2 create-security-group \
  --group-name CustomerServiceRedisSecurityGroup \
  --description "Security group for Customer Service Redis" \
  --vpc-id $(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text) \
  --query "GroupId" --output text)

# Allow Redis port from within VPC
aws ec2 authorize-security-group-ingress \
  --group-id $REDIS_SG \
  --protocol tcp \
  --port 6379 \
  --cidr $(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].CidrBlock" --output text)

# Create Redis cluster
aws elasticache create-replication-group \
  --replication-group-id customer-service-redis \
  --replication-group-description "Redis for Customer Service" \
  --engine redis \
  --cache-node-type cache.t3.small \
  --num-cache-clusters 2 \
  --automatic-failover-enabled \
  --cache-subnet-group-name customer-service-cache-subnet \
  --security-group-ids $REDIS_SG \
  --tags Key=Environment,Value=Production

# Get Redis endpoint
REDIS_ENDPOINT=$(aws elasticache describe-replication-groups \
  --replication-group-id customer-service-redis \
  --query "ReplicationGroups[0].NodeGroups[0].PrimaryEndpoint.Address" \
  --output text)

echo "Redis Endpoint: $REDIS_ENDPOINT"
```

### Set Up OpenSearch Service

```bash
# Create OpenSearch domain
aws opensearch create-domain \
  --domain-name customer-service-kb \
  --engine-version OpenSearch_2.5 \
  --cluster-config InstanceType=t3.small.search,InstanceCount=1 \
  --ebs-options EBSEnabled=true,VolumeType=gp2,VolumeSize=10 \
  --node-to-node-encryption-options Enabled=true \
  --encryption-at-rest-options Enabled=true \
  --domain-endpoint-options EnforceHTTPS=true \
  --access-policies '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "AWS": "*"
        },
        "Action": "es:*",
        "Resource": "arn:aws:es:'$AWS_REGION':'$AWS_ACCOUNT_ID':domain/customer-service-kb/*",
        "Condition": {
          "IpAddress": {
            "aws:SourceIp": [
              "'$(curl -s http://checkip.amazonaws.com)/32'"
            ]
          }
        }
      }
    ]
  }'

# Get OpenSearch endpoint
OPENSEARCH_ENDPOINT=$(aws opensearch describe-domain \
  --domain-name customer-service-kb \
  --query "DomainStatus.Endpoint" \
  --output text)

echo "OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"
```

### Set Up Amazon SNS for Notifications

```bash
# Create SNS topic for escalations
ESCALATION_TOPIC_ARN=$(aws sns create-topic --name customer-service-escalations --query "TopicArn" --output text)

# Create SNS topic for alerts
ALERTS_TOPIC_ARN=$(aws sns create-topic --name customer-service-alerts --query "TopicArn" --output text)

echo "Escalation Topic ARN: $ESCALATION_TOPIC_ARN"
echo "Alerts Topic ARN: $ALERTS_TOPIC_ARN"
```

### Set Up Amazon SQS for Message Routing

```bash
# Create SQS queue for message routing
ROUTING_QUEUE_URL=$(aws sqs create-queue --queue-name customer-service-routing --query "QueueUrl" --output text)

# Create SQS queue for escalations
ESCALATION_QUEUE_URL=$(aws sqs create-queue --queue-name customer-service-escalations --query "QueueUrl" --output text)

# Create SQS queue for analytics
ANALYTICS_QUEUE_URL=$(aws sqs create-queue --queue-name customer-service-analytics --query "QueueUrl" --output text)

echo "Routing Queue URL: $ROUTING_QUEUE_URL"
echo "Escalation Queue URL: $ESCALATION_QUEUE_URL"
echo "Analytics Queue URL: $ANALYTICS_QUEUE_URL"
```

### Set Up SSM Parameters

```bash
# Create SSM parameters for configuration
aws ssm put-parameter \
  --name "/customer-service/config" \
  --type "String" \
  --value "{
    \"REDIS_HOST\": \"$REDIS_ENDPOINT\",
    \"REDIS_PORT\": \"6379\",
    \"S3_BUCKET\": \"ai-employee-customer-service\",
    \"OPENSEARCH_URL\": \"https://$OPENSEARCH_ENDPOINT\",
    \"ESCALATION_TOPIC_ARN\": \"$ESCALATION_TOPIC_ARN\",
    \"ALERTS_TOPIC_ARN\": \"$ALERTS_TOPIC_ARN\",
    \"ROUTING_QUEUE_URL\": \"$ROUTING_QUEUE_URL\",
    \"ESCALATION_QUEUE_URL\": \"$ESCALATION_QUEUE_URL\",
    \"ANALYTICS_QUEUE_URL\": \"$ANALYTICS_QUEUE_URL\"
  }" \
  --overwrite
```

## Step 5: Create IAM Roles for Fargate Tasks

```bash
# Create IAM Policy for Task Execution Role
cat > task-execution-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "ssm:GetParameters",
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create IAM Policy for Task Role
cat > task-role-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "sqs:*",
        "sns:*",
        "dynamodb:*",
        "es:*",
        "bedrock:*",
        "lex:*",
        "comprehend:*",
        "ssm:GetParameters",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create IAM Task Execution Role
aws iam create-role \
  --role-name CustomerServiceECSExecutionRole \
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
  }'

# Attach policies to Task Execution Role
aws iam put-role-policy \
  --role-name CustomerServiceECSExecutionRole \
  --policy-name CustomerServiceECSExecutionPolicy \
  --policy-document file://task-execution-policy.json

aws iam attach-role-policy \
  --role-name CustomerServiceECSExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Create IAM Task Role
aws iam create-role \
  --role-name CustomerServiceECSTaskRole \
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
  }'

# Attach policy to Task Role
aws iam put-role-policy \
  --role-name CustomerServiceECSTaskRole \
  --policy-name CustomerServiceECSTaskPolicy \
  --policy-document file://task-role-policy.json

# Get ARNs for the roles
EXECUTION_ROLE_ARN=$(aws iam get-role --role-name CustomerServiceECSExecutionRole --query "Role.Arn" --output text)
TASK_ROLE_ARN=$(aws iam get-role --role-name CustomerServiceECSTaskRole --query "Role.Arn" --output text)

echo "Execution Role ARN: $EXECUTION_ROLE_ARN"
echo "Task Role ARN: $TASK_ROLE_ARN"
```

## Step 6: Create ECS Cluster and Fargate Resources

```bash
# Create ECS Cluster
aws ecs create-cluster \
  --cluster-name customer-service-cluster \
  --capacity-providers FARGATE FARGATE_SPOT \
  --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 \
  --region $AWS_REGION

# Create VPC and Subnets if needed, or use existing ones
# Note: In this example, we're using the default VPC for simplicity
VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text)
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[?MapPublicIpOnLaunch==\`true\`].SubnetId" --output text)
SUBNET_LIST=$(echo $SUBNET_IDS | tr '\t' ',')

# Create Security Group for Fargate tasks
TASK_SG_ID=$(aws ec2 create-security-group \
  --group-name CustomerServiceTasksSecurityGroup \
  --description "Security group for Customer Service Fargate tasks" \
  --vpc-id $VPC_ID \
  --query "GroupId" \
  --output text)

# Allow inbound traffic on port 8080
aws ec2 authorize-security-group-ingress \
  --group-id $TASK_SG_ID \
  --protocol tcp \
  --port 8080 \
  --cidr 0.0.0.0/0

# Create Security Group for ALB
ALB_SG_ID=$(aws ec2 create-security-group \
  --group-name CustomerServiceALBSecurityGroup \
  --description "Security group for Customer Service ALB" \
  --vpc-id $VPC_ID \
  --query "GroupId" \
  --output text)

# Allow HTTP and HTTPS traffic
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

echo "Task Security Group: $TASK_SG_ID"
echo "ALB Security Group: $ALB_SG_ID"
```

## Step 7: Create Task Definitions for Each Service

```bash
# Create Task Definition for each service
for service in chatbot-service sentiment-service routing-service knowledge-service analytics-service escalation-service audit-service; do
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
      "image": "${ECR_REPOSITORY_URI}/ai-employee/${service}:latest",
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
          "awslogs-group": "/ecs/customer-service/${service}",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "secrets": [
        {
          "name": "CONFIG",
          "valueFrom": "/customer-service/config"
        }
      ]
    }
  ]
}
EOF

  # Register Task Definition
  aws ecs register-task-definition \
    --cli-input-json file://${service}-taskdef.json \
    --region $AWS_REGION
done
```

## Step 8: Create Application Load Balancer

```bash
# Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name customer-service-alb \
  --subnets $(echo $SUBNET_IDS | tr '\t' ' ') \
  --security-groups $ALB_SG_ID \
  --scheme internet-facing \
  --type application \
  --query "LoadBalancers[0].LoadBalancerArn" \
  --output text)

# Get certificate ARN - assumes you already have one in ACM
CERTIFICATE_ARN=$(aws acm list-certificates --query "CertificateSummaryList[0].CertificateArn" --output text)

# Create HTTPS listener
HTTPS_LISTENER_ARN=$(aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=$CERTIFICATE_ARN \
  --default-actions Type=fixed-response,FixedResponseConfig="{ContentType=text/plain,StatusCode=404,MessageBody=Not Found}" \
  --query "Listeners[0].ListenerArn" \
  --output text)

# Create HTTP listener (redirects to HTTPS)
HTTP_LISTENER_ARN=$(aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=redirect,RedirectConfig="{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}" \
  --query "Listeners[0].ListenerArn" \
  --output text)

# Create target groups for each service
for service in chatbot-service sentiment-service routing-service knowledge-service analytics-service escalation-service audit-service; do
  TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
    --name ${service}-tg \
    --protocol HTTP \
    --port 8080 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path "/health" \
    --health-check-protocol HTTP \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --health-check-healthy-threshold-count 2 \
    --health-check-unhealthy-threshold-count 3 \
    --query "TargetGroups[0].TargetGroupArn" \
    --output text)
  
  echo "${service} Target Group ARN: $TARGET_GROUP_ARN"
  
  # Create path-based routing rule
  PRIORITY=$((10#$(echo $service | md5sum | cut -c 1-2) % 50 + 1))
  
  aws elbv2 create-rule \
    --listener-arn $HTTPS_LISTENER_ARN \
    --priority $PRIORITY \
    --conditions Field=path-pattern,Values="/${service}*" \
    --actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN
done
```

## Step 9: Create ECS Services

```bash
# Get the ALB DNS name
ALB_DNS_NAME=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query "LoadBalancers[0].DNSName" \
  --output text)

echo "ALB DNS Name: $ALB_DNS_NAME"

# Create ECS services
for service in chatbot-service sentiment-service routing-service knowledge-service analytics-service escalation-service audit-service; do
  TARGET_GROUP_ARN=$(aws elbv2 describe-target-groups \
    --names ${service}-tg \
    --query "TargetGroups[0].TargetGroupArn" \
    --output text)
  
  aws ecs create-service \
    --cluster customer-service-cluster \
    --service-name $service \
    --task-definition $service \
    --desired-count 2 \
    --launch-type FARGATE \
    --platform-version LATEST \
    --health-check-grace-period-seconds 60 \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_LIST],securityGroups=[$TASK_SG_ID],assignPublicIp=ENABLED}" \
    --load-balancers "targetGroupArn=$TARGET_GROUP_ARN,containerName=$service,containerPort=8080" \
    --scheduling-strategy REPLICA \
    --deployment-configuration "maximumPercent=200,minimumHealthyPercent=100" \
    --region $AWS_REGION
done
```

## Step 10: Set Up Auto Scaling

```bash
# Set up Auto Scaling for each service
for service in chatbot-service sentiment-service routing-service knowledge-service analytics-service escalation-service audit-service; do
  # Register a scalable target
  aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --resource-id service/customer-service-cluster/$service \
    --scalable-dimension ecs:service:DesiredCount \
    --min-capacity 2 \
    --max-capacity 10
  
  # Create scaling policy
  aws application-autoscaling put-scaling-policy \
    --service-namespace ecs \
    --resource-id service/customer-service-cluster/$service \
    --scalable-dimension ecs:service:DesiredCount \
    --policy-name cpu-tracking-scaling-policy \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration '{
      "PredefinedMetricSpecification": {
        "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
      },
      "TargetValue": 70.0,
      "ScaleInCooldown": 300,
      "ScaleOutCooldown": 60
    }'
done
```

## Step 11: Set Up Monitoring and Logging

```bash
# Create CloudWatch Dashboard
aws cloudwatch put-dashboard \
  --dashboard-name CustomerServiceDashboard \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "x": 0,
        "y": 0,
        "width": 12,
        "height": 6,
        "properties": {
          "metrics": [
            ["AWS/ECS", "CPUUtilization", "ServiceName", "chatbot-service", "ClusterName", "customer-service-cluster"],
            ["AWS/ECS", "CPUUtilization", "ServiceName", "sentiment-service", "ClusterName", "customer-service-cluster"],
            ["AWS/ECS", "CPUUtilization", "ServiceName", "routing-service", "ClusterName", "customer-service-cluster"],
            ["AWS/ECS", "CPUUtilization", "ServiceName", "knowledge-service", "ClusterName", "customer-service-cluster"],
            ["AWS/ECS", "CPUUtilization", "ServiceName", "analytics-service", "ClusterName", "customer-service-cluster"],
            ["AWS/ECS", "CPUUtilization", "ServiceName", "escalation-service", "ClusterName", "customer-service-cluster"],
            ["AWS/ECS", "CPUUtilization", "ServiceName", "audit-service", "ClusterName", "customer-service-cluster"]
          ],
          "period": 300,
          "stat": "Average",
          "region": "'$AWS_REGION'",
          "title": "CPU Utilization by Service"
        }
      },
      {
        "type": "metric",
        "x": 0,
        "y": 6,
        "width": 12,
        "height": 6,
        "properties": {
          "metrics": [
            ["AWS/ECS", "MemoryUtilization", "ServiceName", "chatbot-service", "ClusterName", "customer-service-cluster"],
            ["AWS/ECS", "MemoryUtilization", "ServiceName", "sentiment-service", "ClusterName", "customer-service-cluster"],
            ["AWS/ECS", "MemoryUtilization", "ServiceName", "routing-service", "ClusterName", "customer-service-cluster"],
            ["AWS/ECS", "MemoryUtilization", "ServiceName", "knowledge-service", "ClusterName", "customer-service-cluster"],
            ["AWS/ECS", "MemoryUtilization", "ServiceName", "analytics-service", "ClusterName", "customer-service-cluster"],
            ["AWS/ECS", "MemoryUtilization", "ServiceName", "escalation-service", "ClusterName", "customer-service-cluster"],
            ["AWS/ECS", "MemoryUtilization", "ServiceName", "audit-service", "ClusterName", "customer-service-cluster"]
          ],
          "period": 300,
          "stat": "Average",
          "region": "'$AWS_REGION'",
          "title": "Memory Utilization by Service"
        }
      }
    ]
  }'

# Create CloudWatch Alarms
for service in chatbot-service sentiment-service routing-service knowledge-service analytics-service escalation-service audit-service; do
  # High CPU Alarm
  aws cloudwatch put-metric-alarm \
    --alarm-name ${service}-high-cpu \
    --alarm-description "Alarm when CPU usage exceeds 80% for 5 minutes" \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --dimensions "Name=ServiceName,Value=${service}" "Name=ClusterName,Value=customer-service-cluster" \
    --evaluation-periods 1 \
    --alarm-actions $ALERTS_TOPIC_ARN

  # High Memory Alarm
  aws cloudwatch put-metric-alarm \
    --alarm-name ${service}-high-memory \
    --alarm-description "Alarm when Memory usage exceeds 80% for 5 minutes" \
    --metric-name MemoryUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --dimensions "Name=ServiceName,Value=${service}" "Name=ClusterName,Value=customer-service-cluster" \
    --evaluation-periods 1 \
    --alarm-actions $ALERTS_TOPIC_ARN
done
```

## Step 12: Configure Route 53 (Optional)

If you have a custom domain, you can set up Route 53:

```bash
# Get Hosted Zone ID (assumes you already have it set up)
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones --query "HostedZones[0].Id" --output text | sed 's|/hostedzone/||')

# Create DNS Record Set
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "customer-service.example.com",
          "Type": "A",
          "AliasTarget": {
            "HostedZoneId": "Z35SXDOTRQ7X7K",
            "DNSName": "'$ALB_DNS_NAME'",
            "EvaluateTargetHealth": true
          }
        }
      }
    ]
  }'
```

## Step 13: Set Up CI/CD Pipeline (Optional)

```bash
# Create CodeCommit repository
aws codecommit create-repository \
  --repository-name customer-service-platform \
  --repository-description "Customer Service Platform Repository"

# Create CodeBuild project
aws codebuild create-project \
  --name customer-service-build \
  --source-type CODECOMMIT \
  --source-location https://git-codecommit.$AWS_REGION.amazonaws.com/v1/repos/customer-service-platform \
  --artifacts-type NO_ARTIFACTS \
  --environment-type LINUX_CONTAINER \
  --environment-image aws/codebuild/amazonlinux2-x86_64-standard:3.0 \
  --environment-compute-type BUILD_GENERAL1_SMALL \
  --service-role codebuild-service-role

# Create S3 bucket for artifacts
aws s3 mb s3://customer-service-codepipeline-$AWS_ACCOUNT_ID --region $AWS_REGION

# Create CodePipeline
aws codepipeline create-pipeline \
  --pipeline-name customer-service-pipeline \
  --role-arn arn:aws:iam::$AWS_ACCOUNT_ID:role/CodePipelineServiceRole \
  --artifact-store type=S3,location=customer-service-codepipeline-$AWS_ACCOUNT_ID
```

## Step 14: Verify Deployment

```bash
# Check ECS services status
aws ecs describe-services \
  --cluster customer-service-cluster \
  --services chatbot-service sentiment-service routing-service knowledge-service analytics-service escalation-service audit-service \
  --query "services[*].[serviceName,status,runningCount,desiredCount]" \
  --output table

# Check ALB target groups health
for service in chatbot-service sentiment-service routing-service knowledge-service analytics-service escalation-service audit-service; do
  aws elbv2 describe-target-health \
    --target-group-arn $(aws elbv2 describe-target-groups --names ${service}-tg --query "TargetGroups[0].TargetGroupArn" --output text) \
    --query "TargetHealthDescriptions[*].[Target.Id,TargetHealth.State]" \
    --output table
done

# Test API endpoints
curl -k https://$ALB_DNS_NAME/chatbot/health
curl -k https://$ALB_DNS_NAME/sentiment/health
curl -k https://$ALB_DNS_NAME/routing/health
curl -k https://$ALB_DNS_NAME/knowledge/health
curl -k https://$ALB_DNS_NAME/analytics/health
curl -k https://$ALB_DNS_NAME/escalation/health
curl -k https://$ALB_DNS_NAME/audit/health
```

## Troubleshooting

### Common Issues and Solutions

1. **Service Deployment Failures**:
   - Check CloudWatch Logs:
     ```bash
     aws logs get-log-events --log-group-name /ecs/customer-service/chatbot-service --log-stream-name ecs/chatbot-service/latest
     ```
   - Verify that ECR images are built and pushed correctly:
     ```bash
     aws ecr describe-images --repository-name ai-employee/chatbot-service
     ```

2. **Container Health Check Failures**:
   - Make sure health check endpoints are working in the container:
     ```bash
     # Add a test endpoint in the Flask app
     @app.route('/health')
     def health():
         return jsonify({"status": "healthy"})
     ```

3. **Permission Issues**:
   - Verify that the task execution and task roles have the necessary permissions
   - Check that SSM parameters can be accessed by the containers

4. **Load Balancer Routing Issues**:
   - Check target group health:
     ```bash
     aws elbv2 describe-target-health --target-group-arn <TARGET_GROUP_ARN>
     ```
   - Verify security group settings allow traffic to the containers

## Next Steps

1. Set up user authentication with Amazon Cognito
2. Implement a custom domain name with Route 53
3. Set up automated testing for customer service scenarios
4. Implement a staging environment for testing changes before production
5. Set up automated backups for all persistent data

For advanced configuration and optimization, refer to the [USER_GUIDE.md](./USER_GUIDE.md) file.