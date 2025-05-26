# AI Ethics & Compliance Platform Setup Guide

This guide provides step-by-step instructions for deploying the AI Ethics & Compliance Platform using AWS Fargate.

## Prerequisites

Before you begin, ensure you have the following:

- AWS CLI installed and configured with appropriate permissions
- Docker installed locally for building container images
- AWS ECR repositories created for each microservice
- An SSL certificate in AWS Certificate Manager (ACM) for HTTPS
- A VPC with at least two public subnets in different Availability Zones

## Step 1: Set Up AWS Environment

First, set up the required environment variables:

```bash
# Set environment variables
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REPOSITORY_URI=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
```

## Step 2: Create ECR Repositories

```bash
# Create ECR repositories for each microservice
for service in regulatory-intelligence web-scraping compliance-analysis ethics-assessment policy-management reporting-dashboard; do
  aws ecr create-repository \
    --repository-name compliance-platform/${service} \
    --image-scanning-configuration scanOnPush=true
done
```

## Step 3: Build and Push Docker Images

For each microservice, build and push the Docker image to ECR:

```bash
# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPOSITORY_URI}

# Build and push each microservice image
for service in regulatory-intelligence web-scraping compliance-analysis ethics-assessment policy-management reporting-dashboard; do
  # Navigate to the service directory
  cd ${service}
  
  # Build the Docker image
  docker build -t ${ECR_REPOSITORY_URI}/compliance-platform/${service}:latest .
  
  # Push the image to ECR
  docker push ${ECR_REPOSITORY_URI}/compliance-platform/${service}:latest
  
  # Return to the root directory
  cd ..
done
```

## Step 4: Create Required AWS Resources

Create the necessary AWS resources:

```bash
# Create S3 bucket for regulation documents
aws s3 mb s3://ai-compliance-regulation-storage --region ${AWS_REGION}

# Enable versioning for the bucket
aws s3api put-bucket-versioning \
  --bucket ai-compliance-regulation-storage \
  --versioning-configuration Status=Enabled

# Create SSM Parameter for microservice configuration
aws ssm put-parameter \
  --name /ai-compliance/prod/config \
  --type String \
  --value '{"REGULATION_BUCKET":"ai-compliance-regulation-storage","COMPLIANCE_KNOWLEDGE_INDEX":"compliance-knowledge-index","LOG_LEVEL":"INFO"}' \
  --region ${AWS_REGION}
```

## Step 5: Gather VPC and Subnet Information

Obtain the necessary VPC and subnet information for the CloudFormation template:

```bash
# Get the default VPC ID
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text)

# Get subnet IDs in the VPC
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=${VPC_ID}" --query "Subnets[?MapPublicIpOnLaunch==\`true\`].SubnetId" --output text | tr '\t' ',')

echo "VPC ID: ${VPC_ID}"
echo "Subnet IDs: ${SUBNET_IDS}"
```

## Step 6: Get SSL Certificate ARN

If you already have a certificate in ACM:

```bash
# Get the ARN of an existing certificate
CERTIFICATE_ARN=$(aws acm list-certificates --query "CertificateSummaryList[0].CertificateArn" --output text)
echo "Certificate ARN: ${CERTIFICATE_ARN}"
```

If you need to create a new certificate:

```bash
# Request a new certificate
CERTIFICATE_ARN=$(aws acm request-certificate \
  --domain-name compliance-platform.example.com \
  --validation-method DNS \
  --query CertificateArn \
  --output text)
echo "Certificate ARN: ${CERTIFICATE_ARN}"
```

## Step 7: Deploy with CloudFormation

Deploy the AWS Fargate infrastructure using the CloudFormation template:

```bash
# Deploy the CloudFormation stack
aws cloudformation create-stack \
  --stack-name ai-compliance-platform \
  --template-body file://k8s-deployment.yaml \
  --capabilities CAPABILITY_IAM \
  --parameters \
    ParameterKey=EcrRepositoryUri,ParameterValue=${ECR_REPOSITORY_URI} \
    ParameterKey=EnvironmentName,ParameterValue=prod \
    ParameterKey=VpcId,ParameterValue=${VPC_ID} \
    ParameterKey=SubnetIds,ParameterValue=\"${SUBNET_IDS}\" \
    ParameterKey=CertificateArn,ParameterValue=${CERTIFICATE_ARN}
```

Monitor the stack creation:

```bash
# Check the stack status
aws cloudformation describe-stacks \
  --stack-name ai-compliance-platform \
  --query "Stacks[0].StackStatus"
```

## Step 8: Configure DNS (Optional)

If you're using a custom domain, update your DNS records to point to the ALB:

```bash
# Get the ALB DNS name
ALB_DNS=$(aws cloudformation describe-stacks \
  --stack-name ai-compliance-platform \
  --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerDNS'].OutputValue" \
  --output text)

echo "ALB DNS: ${ALB_DNS}"
```

Create a CNAME record in your DNS provider pointing your custom domain to the ALB DNS name.

## Step 9: Verify Deployment

Verify that all services are running correctly:

```bash
# List the ECS services
aws ecs list-services --cluster ai-compliance-prod

# Describe a specific service to check its status
aws ecs describe-services \
  --cluster ai-compliance-prod \
  --services ai-compliance-prod-regulatory-intelligence \
  --query "services[0].deployments[0].rolloutState"

# Check the health of the ALB target groups
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --names RegulatoryIntelligenceTargetGroup \
    --query "TargetGroups[0].TargetGroupArn" \
    --output text)
```

## Step 10: Set Up CI/CD Pipeline (Optional)

For continuous integration and deployment, set up an AWS CodePipeline:

```bash
# Create a CodeCommit repository
aws codecommit create-repository \
  --repository-name ai-compliance-platform \
  --repository-description "AI Ethics & Compliance Platform"

# Create a CodeBuild project (simplified example)
aws codebuild create-project \
  --name ai-compliance-platform-build \
  --source-type CODECOMMIT \
  --source-location https://git-codecommit.${AWS_REGION}.amazonaws.com/v1/repos/ai-compliance-platform \
  --artifacts-type NO_ARTIFACTS \
  --environment-type LINUX_CONTAINER \
  --environment-image aws/codebuild/amazonlinux2-x86_64-standard:3.0 \
  --environment-compute-type BUILD_GENERAL1_SMALL \
  --service-role codebuild-service-role

# Create a CodePipeline pipeline (simplified example)
aws codepipeline create-pipeline \
  --pipeline-name ai-compliance-platform-pipeline \
  --role-arn arn:aws:iam::${AWS_ACCOUNT_ID}:role/codepipeline-service-role \
  --artifact-store type=S3,location=codepipeline-${AWS_REGION}-${AWS_ACCOUNT_ID}
```

## Troubleshooting

If you encounter issues during deployment:

1. **Service Deployment Failures**:
   - Check CloudWatch Logs for container errors:
     ```bash
     aws logs get-log-events --log-group-name /ecs/ai-compliance/prod/regulatory-intelligence
     ```
   - Verify that the ECR images exist and are accessible

2. **Network Issues**:
   - Check security group rules to ensure traffic can reach the containers
   - Verify that the ALB target groups have healthy targets

3. **Permission Issues**:
   - Verify that the task execution and task roles have the necessary permissions
   - Check that SSM parameters can be accessed by the containers

4. **CloudFormation Stack Failures**:
   - Check the stack events for detailed error messages:
     ```bash
     aws cloudformation describe-stack-events --stack-name ai-compliance-platform
     ```

## Next Steps

- Set up monitoring and alerting with CloudWatch Alarms
- Configure automated backups for persistent data
- Set up AWS X-Ray for distributed tracing across microservices
- Implement AWS Secrets Manager for sensitive credentials

For user instructions, refer to the [USER_GUIDE.md](./USER_GUIDE.md) file.