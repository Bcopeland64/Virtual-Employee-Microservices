# Legal Platform Installation Guide

This guide provides step-by-step instructions for deploying the AI Legal Platform using AWS Fargate.

## Prerequisites

- AWS CLI configured with appropriate permissions
- Docker installed locally
- An AWS account with access to Amazon ECR, ECS, Fargate, and related services
- An SSL certificate in AWS Certificate Manager (ACM) for HTTPS

## Deployment Architecture

The Legal Platform runs as a set of containerized microservices:

1. **Document Processing Service** - Handles document ingestion and OCR
2. **Legal Analysis Service** - Performs contract analysis and risk assessment 
3. **Compliance Monitoring Service** - Monitors regulatory changes and compliance

## Step 1: Set Up Environment Variables

```bash
# Set required environment variables
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REPOSITORY_URI=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
```

## Step 2: Build Docker Images

Create a Dockerfile for each service in the legal platform:

### Document Processing Service Dockerfile

```dockerfile
# document-processor/Dockerfile
FROM amazon/aws-lambda-python:3.11

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Add health check endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

CMD ["app.handler"]
```

### Legal Analysis Service Dockerfile

```dockerfile
# legal-analyzer/Dockerfile
FROM amazon/aws-lambda-python:3.11

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Add health check endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

CMD ["app.handler"]
```

### Compliance Monitoring Service Dockerfile

```dockerfile
# compliance-monitor/Dockerfile
FROM amazon/aws-lambda-python:3.11

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Add health check endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

CMD ["app.handler"]
```

Build the Docker images:

```bash
# Create required directories and copy code
mkdir -p document-processor legal-analyzer compliance-monitor

# Copy code to appropriate directories
cp legal_platform/integration.py document-processor/app.py
cp legal_platform/integration.py legal-analyzer/app.py
cp legal_platform/integration.py compliance-monitor/app.py

# Create requirements.txt
cat > requirements.txt << EOF
boto3==1.35.51
botocore==1.35.51
requests==2.32.3
PyYAML==6.0.2
uuid==1.30
flask==2.3.3
EOF

# Add health check endpoint code
for service in document-processor legal-analyzer compliance-monitor; do
  # Add health check route
  echo '
import flask
from flask import jsonify

app = flask.Flask(__name__)

@app.route("/health")
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
' >> $service/app.py

  cp requirements.txt $service/
done

# Build the images
docker build -t ai-employee/document-processor:latest document-processor/
docker build -t ai-employee/legal-analyzer:latest legal-analyzer/
docker build -t ai-employee/compliance-monitor:latest compliance-monitor/
```

## Step 3: Create ECR Repositories and Push Images

```bash
# Create ECR repositories
aws ecr create-repository --repository-name ai-employee/document-processor --image-scanning-configuration scanOnPush=true
aws ecr create-repository --repository-name ai-employee/legal-analyzer --image-scanning-configuration scanOnPush=true
aws ecr create-repository --repository-name ai-employee/compliance-monitor --image-scanning-configuration scanOnPush=true

# Get the ECR login command
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URI

# Tag images for ECR
docker tag ai-employee/document-processor:latest $ECR_REPOSITORY_URI/ai-employee/document-processor:latest
docker tag ai-employee/legal-analyzer:latest $ECR_REPOSITORY_URI/ai-employee/legal-analyzer:latest
docker tag ai-employee/compliance-monitor:latest $ECR_REPOSITORY_URI/ai-employee/compliance-monitor:latest

# Push images to ECR
docker push $ECR_REPOSITORY_URI/ai-employee/document-processor:latest
docker push $ECR_REPOSITORY_URI/ai-employee/legal-analyzer:latest
docker push $ECR_REPOSITORY_URI/ai-employee/compliance-monitor:latest
```

## Step 4: Create AWS Resources

### Set Up CloudWatch Log Groups

```bash
# Create CloudWatch log groups for each service
aws logs create-log-group --log-group-name "/ecs/legal-platform/document-processor" --region $AWS_REGION
aws logs create-log-group --log-group-name "/ecs/legal-platform/legal-analyzer" --region $AWS_REGION
aws logs create-log-group --log-group-name "/ecs/legal-platform/compliance-monitor" --region $AWS_REGION
```

### Create S3 Bucket for Document Storage

```bash
# Create S3 bucket for legal documents
aws s3 mb s3://legal-document-storage --region $AWS_REGION

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket legal-document-storage \
  --versioning-configuration Status=Enabled
```

### Create SSM Parameters for Configuration

```bash
# Create SSM parameter for service configuration
aws ssm put-parameter \
  --name "/legal-platform/config" \
  --type "String" \
  --value "{\"DOCUMENT_BUCKET\":\"legal-document-storage\",\"LEGAL_KNOWLEDGE_INDEX\":\"legal-knowledge-index\"}" \
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
        "ssm:GetParameters"
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
        "dynamodb:*",
        "bedrock:*",
        "comprehend:*",
        "textract:*",
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
  --role-name LegalPlatformECSExecutionRole \
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
  --role-name LegalPlatformECSExecutionRole \
  --policy-name LegalPlatformECSExecutionPolicy \
  --policy-document file://task-execution-policy.json

aws iam attach-role-policy \
  --role-name LegalPlatformECSExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Create IAM Task Role
aws iam create-role \
  --role-name LegalPlatformECSTaskRole \
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
  --role-name LegalPlatformECSTaskRole \
  --policy-name LegalPlatformECSTaskPolicy \
  --policy-document file://task-role-policy.json

# Get ARNs for the roles
EXECUTION_ROLE_ARN=$(aws iam get-role --role-name LegalPlatformECSExecutionRole --query "Role.Arn" --output text)
TASK_ROLE_ARN=$(aws iam get-role --role-name LegalPlatformECSTaskRole --query "Role.Arn" --output text)

echo "Execution Role ARN: $EXECUTION_ROLE_ARN"
echo "Task Role ARN: $TASK_ROLE_ARN"
```

## Step 6: Create ECS Cluster and Fargate Resources

```bash
# Create ECS Cluster
aws ecs create-cluster \
  --cluster-name legal-platform-cluster \
  --capacity-providers FARGATE FARGATE_SPOT \
  --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 \
  --region $AWS_REGION

# Get VPC and subnet information
VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text)
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[?MapPublicIpOnLaunch==\`true\`].SubnetId" --output text)
SUBNET_LIST=$(echo $SUBNET_IDS | tr '\t' ',')

# Create Security Group for Fargate tasks
TASK_SG_ID=$(aws ec2 create-security-group \
  --group-name LegalPlatformTasksSecurityGroup \
  --description "Security group for Legal Platform Fargate tasks" \
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
  --group-name LegalPlatformALBSecurityGroup \
  --description "Security group for Legal Platform ALB" \
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

## Step 7: Create Task Definitions

```bash
# Create Task Definition for Document Processor
cat > document-processor-taskdef.json << EOF
{
  "family": "document-processor",
  "taskRoleArn": "${TASK_ROLE_ARN}",
  "executionRoleArn": "${EXECUTION_ROLE_ARN}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "document-processor",
      "image": "${ECR_REPOSITORY_URI}/ai-employee/document-processor:latest",
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
          "awslogs-group": "/ecs/legal-platform/document-processor",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "secrets": [
        {
          "name": "CONFIG",
          "valueFrom": "/legal-platform/config"
        }
      ]
    }
  ]
}
EOF

# Create Task Definition for Legal Analyzer
cat > legal-analyzer-taskdef.json << EOF
{
  "family": "legal-analyzer",
  "taskRoleArn": "${TASK_ROLE_ARN}",
  "executionRoleArn": "${EXECUTION_ROLE_ARN}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "legal-analyzer",
      "image": "${ECR_REPOSITORY_URI}/ai-employee/legal-analyzer:latest",
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
          "awslogs-group": "/ecs/legal-platform/legal-analyzer",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "secrets": [
        {
          "name": "CONFIG",
          "valueFrom": "/legal-platform/config"
        }
      ]
    }
  ]
}
EOF

# Create Task Definition for Compliance Monitor
cat > compliance-monitor-taskdef.json << EOF
{
  "family": "compliance-monitor",
  "taskRoleArn": "${TASK_ROLE_ARN}",
  "executionRoleArn": "${EXECUTION_ROLE_ARN}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "compliance-monitor",
      "image": "${ECR_REPOSITORY_URI}/ai-employee/compliance-monitor:latest",
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
          "awslogs-group": "/ecs/legal-platform/compliance-monitor",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "secrets": [
        {
          "name": "CONFIG",
          "valueFrom": "/legal-platform/config"
        }
      ]
    }
  ]
}
EOF

# Register the task definitions
aws ecs register-task-definition --cli-input-json file://document-processor-taskdef.json
aws ecs register-task-definition --cli-input-json file://legal-analyzer-taskdef.json
aws ecs register-task-definition --cli-input-json file://compliance-monitor-taskdef.json
```

## Step 8: Create Application Load Balancer and Target Groups

```bash
# Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name legal-platform-alb \
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
DOCUMENT_PROCESSOR_TG_ARN=$(aws elbv2 create-target-group \
  --name document-processor-tg \
  --protocol HTTP \
  --port 8080 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path "/health" \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --query "TargetGroups[0].TargetGroupArn" \
  --output text)

LEGAL_ANALYZER_TG_ARN=$(aws elbv2 create-target-group \
  --name legal-analyzer-tg \
  --protocol HTTP \
  --port 8080 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path "/health" \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --query "TargetGroups[0].TargetGroupArn" \
  --output text)

COMPLIANCE_MONITOR_TG_ARN=$(aws elbv2 create-target-group \
  --name compliance-monitor-tg \
  --protocol HTTP \
  --port 8080 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path "/health" \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --query "TargetGroups[0].TargetGroupArn" \
  --output text)

# Create path-based routing rules
aws elbv2 create-rule \
  --listener-arn $HTTPS_LISTENER_ARN \
  --priority 10 \
  --conditions Field=path-pattern,Values="/document-processor*" \
  --actions Type=forward,TargetGroupArn=$DOCUMENT_PROCESSOR_TG_ARN

aws elbv2 create-rule \
  --listener-arn $HTTPS_LISTENER_ARN \
  --priority 20 \
  --conditions Field=path-pattern,Values="/legal-analyzer*" \
  --actions Type=forward,TargetGroupArn=$LEGAL_ANALYZER_TG_ARN

aws elbv2 create-rule \
  --listener-arn $HTTPS_LISTENER_ARN \
  --priority 30 \
  --conditions Field=path-pattern,Values="/compliance-monitor*" \
  --actions Type=forward,TargetGroupArn=$COMPLIANCE_MONITOR_TG_ARN
```

## Step 9: Create ECS Services

```bash
# Create ECS service for Document Processor
aws ecs create-service \
  --cluster legal-platform-cluster \
  --service-name document-processor \
  --task-definition document-processor \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_LIST],securityGroups=[$TASK_SG_ID],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=$DOCUMENT_PROCESSOR_TG_ARN,containerName=document-processor,containerPort=8080" \
  --health-check-grace-period-seconds 60 \
  --region $AWS_REGION

# Create ECS service for Legal Analyzer
aws ecs create-service \
  --cluster legal-platform-cluster \
  --service-name legal-analyzer \
  --task-definition legal-analyzer \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_LIST],securityGroups=[$TASK_SG_ID],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=$LEGAL_ANALYZER_TG_ARN,containerName=legal-analyzer,containerPort=8080" \
  --health-check-grace-period-seconds 60 \
  --region $AWS_REGION

# Create ECS service for Compliance Monitor
aws ecs create-service \
  --cluster legal-platform-cluster \
  --service-name compliance-monitor \
  --task-definition compliance-monitor \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_LIST],securityGroups=[$TASK_SG_ID],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=$COMPLIANCE_MONITOR_TG_ARN,containerName=compliance-monitor,containerPort=8080" \
  --health-check-grace-period-seconds 60 \
  --region $AWS_REGION
```

## Step 10: Set Up Auto Scaling

```bash
# Register scalable targets
for service in document-processor legal-analyzer compliance-monitor; do
  aws application-autoscaling register-scalable-target \
    --service-namespace ecs \
    --resource-id service/legal-platform-cluster/$service \
    --scalable-dimension ecs:service:DesiredCount \
    --min-capacity 2 \
    --max-capacity 10
    
  # Create scaling policies
  aws application-autoscaling put-scaling-policy \
    --service-namespace ecs \
    --resource-id service/legal-platform-cluster/$service \
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
# Create SNS topic for alerts
SNS_TOPIC_ARN=$(aws sns create-topic --name legal-platform-alerts --query 'TopicArn' --output text)

# Create CloudWatch Dashboard
aws cloudwatch put-dashboard \
  --dashboard-name LegalPlatformDashboard \
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
            ["AWS/ECS", "CPUUtilization", "ServiceName", "document-processor", "ClusterName", "legal-platform-cluster"],
            ["AWS/ECS", "CPUUtilization", "ServiceName", "legal-analyzer", "ClusterName", "legal-platform-cluster"],
            ["AWS/ECS", "CPUUtilization", "ServiceName", "compliance-monitor", "ClusterName", "legal-platform-cluster"]
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
            ["AWS/ECS", "MemoryUtilization", "ServiceName", "document-processor", "ClusterName", "legal-platform-cluster"],
            ["AWS/ECS", "MemoryUtilization", "ServiceName", "legal-analyzer", "ClusterName", "legal-platform-cluster"],
            ["AWS/ECS", "MemoryUtilization", "ServiceName", "compliance-monitor", "ClusterName", "legal-platform-cluster"]
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
for service in document-processor legal-analyzer compliance-monitor; do
  # High CPU Alarm
  aws cloudwatch put-metric-alarm \
    --alarm-name ${service}-high-cpu \
    --alarm-description "Alarm when CPU exceeds 80% for 5 minutes" \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --dimensions "Name=ServiceName,Value=${service}" "Name=ClusterName,Value=legal-platform-cluster" \
    --evaluation-periods 1 \
    --alarm-actions $SNS_TOPIC_ARN
    
  # High Memory Alarm
  aws cloudwatch put-metric-alarm \
    --alarm-name ${service}-high-memory \
    --alarm-description "Alarm when Memory exceeds 80% for 5 minutes" \
    --metric-name MemoryUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --dimensions "Name=ServiceName,Value=${service}" "Name=ClusterName,Value=legal-platform-cluster" \
    --evaluation-periods 1 \
    --alarm-actions $SNS_TOPIC_ARN
done
```

## Step 12: Verify Deployment

```bash
# Get ALB DNS name
ALB_DNS_NAME=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query "LoadBalancers[0].DNSName" \
  --output text)

echo "Legal Platform is accessible at: https://$ALB_DNS_NAME"

# Check service status
aws ecs describe-services \
  --cluster legal-platform-cluster \
  --services document-processor legal-analyzer compliance-monitor \
  --query "services[*].[serviceName,status,runningCount,desiredCount]" \
  --output table

# Test endpoints
curl -k https://$ALB_DNS_NAME/document-processor/health
curl -k https://$ALB_DNS_NAME/legal-analyzer/health
curl -k https://$ALB_DNS_NAME/compliance-monitor/health
```

## Step 13: Configure DNS (Optional)

If you have a custom domain, you can create a Route 53 record:

```bash
# Assuming you have a hosted zone in Route 53
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones --query "HostedZones[0].Id" --output text | sed 's|/hostedzone/||')

aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "legal-platform.example.com",
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

## Troubleshooting

### Common Issues and Solutions

1. **Service Deployment Failures**:
   - Check CloudWatch Logs for container errors:
     ```bash
     aws logs get-log-events --log-group-name /ecs/legal-platform/document-processor
     ```
   - Verify that container health checks are working

2. **Load Balancer Issues**:
   - Check target group health:
     ```bash
     aws elbv2 describe-target-health --target-group-arn $DOCUMENT_PROCESSOR_TG_ARN
     ```
   - Verify security group rules allow traffic from the ALB to containers

3. **Permission Issues**:
   - Verify IAM roles have correct permissions
   - Check that task execution role can pull from ECR and access SSM parameters

4. **Resource Limitations**:
   - Check CPU and memory utilization in CloudWatch
   - Adjust task definition resource allocations if needed

## Next Steps

1. Set up CI/CD pipeline for automated deployments
2. Implement additional security measures (WAF, Shield, etc.)
3. Configure backup and disaster recovery
4. Set up AWS X-Ray for distributed tracing
5. Implement AWS Secrets Manager for sensitive credentials

For advanced configuration and optimization, refer to the [USER_GUIDE.md](./USER_GUIDE.md) file.