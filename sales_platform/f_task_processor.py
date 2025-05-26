# glue_job.py
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

# Initialize Glue context
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Define source bucket - using your specific bucket
source_bucket = "aiemployeeplatform"
source_prefix = "raw-data/"
processed_prefix = "processed-data/"

# Create dynamic frame from S3 source
datasource = glueContext.create_dynamic_frame.from_options(
    "s3",
    {
        "paths": [f"s3://{source_bucket}/{source_prefix}"],
        "recurse": True
    },
    format="json"
)

# Apply transformations as needed
mapped_frame = ApplyMapping.apply(
    frame=datasource,
    mappings=[
        ("timestamp", "string", "timestamp", "timestamp"),
        ("user_input", "string", "input_text", "string"),
        ("result", "string", "output_text", "string")
    ]
)

# Write the processed data back to a different prefix in the same bucket
glueContext.write_dynamic_frame.from_options(
    frame=mapped_frame,
    connection_type="s3",
    connection_options={
        "path": f"s3://{source_bucket}/{processed_prefix}"
    },
    format="parquet"
)

job.commit()

# Modified Lambda function to integrate with your S3 bucket
import json
import boto3
import os
import time
from botocore.exceptions import ClientError

# Initialize AWS clients
lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb')
kendra = boto3.client('kendra')
s3 = boto3.client('s3')
conversation_table = dynamodb.Table(os.environ['CONVERSATIONS_TABLE'])

# S3 configuration using your bucket
S3_BUCKET = "aiemployeeplatform"
S3_RAW_PREFIX = 'raw-data/'
S3_PROCESSED_PREFIX = 'processed-data/'

def lambda_handler(event, context):
    try:
        user_input = event['user_input']
        user_id = event.get('userId', 'default_user')
        
        # Get relevant context from both Kendra and processed S3 data
        enriched_input = enrich_prompt_with_context(user_input)
        
        task_type = determine_task_type(enriched_input['optimized_prompt'])
        result = route_task(task_type, enriched_input)
        
        store_conversation(user_id, user_input, result)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'result': result,
                'userId': user_id,
                'timestamp': int(time.time()),
                'context_used': enriched_input['context_used']
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'type': str(type(e).__name__)
            })
        }

def enrich_prompt_with_context(user_input):
    """
    Enhanced context enrichment that combines Kendra and processed S3 data
    """
    # Get Kendra context
    kendra_context = enrich_prompt_with_kendra(user_input)
    
    # Get relevant S3 processed data
    s3_context = get_s3_processed_data(user_input)
    
    # Combine contexts
    combined_context = f"""Kendra Context:
{kendra_context['optimized_prompt']}

Processed Data Context:
{s3_context['context']}

User Request:
{user_input}"""

    return {
        'optimized_prompt': combined_context,
        'context_used': kendra_context['context_used'] + s3_context['sources_used'],
        'original_input': user_input
    }

def get_s3_processed_data(query):
    """
    Retrieves relevant processed data from S3
    """
    try:
        # List relevant processed files
        response = s3.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=S3_PROCESSED_PREFIX
        )
        
        relevant_data = []
        sources_used = []
        
        for obj in response.get('Contents', []):
            if obj['Key'].endswith('.parquet'):
                file_data = s3.get_object(
                    Bucket=S3_BUCKET,
                    Key=obj['Key']
                )
                sources_used.append(obj['Key'])
                
        return {
            'context': "\n".join(relevant_data),
            'sources_used': sources_used
        }
                
    except ClientError as e:
        print(f"Error accessing S3: {str(e)}")
        return {
            'context': "",
            'sources_used': []
        }

# CloudFormation/Terraform template for Glue infrastructure
INFRASTRUCTURE_TEMPLATE = {
    "Resources": {
        "GlueDatabase": {
            "Type": "AWS::Glue::Database",
            "Properties": {
                "CatalogId": {"Ref": "AWS::AccountId"},
                "DatabaseInput": {
                    "Name": "aiemployee_data_catalog"
                }
            }
        },
        "GlueJob": {
            "Type": "AWS::Glue::Job",
            "Properties": {
                "Command": {
                    "Name": "glueetl",
                    "ScriptLocation": f"s3://aiemployeeplatform/glue-scripts/glue_job.py"
                },
                "Role": {"Ref": "GlueServiceRole"},
                "DefaultArguments": {
                    "--job-language": "python",
                    "--continuous-log-logGroup": "/aws-glue/jobs",
                    "--enable-metrics": "true",
                    "--enable-spark-ui": "true"
                }
            }
        },
        "GlueServiceRole": {
            "Type": "AWS::IAM::Role",
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {
                                "Service": "glue.amazonaws.com"
                            },
                            "Action": "sts:AssumeRole"
                        }
                    ]
                },
                "ManagedPolicyArns": [
                    "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
                ],
                "Policies": [
                    {
                        "PolicyName": "S3Access",
                        "PolicyDocument": {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": [
                                        "s3:GetObject",
                                        "s3:PutObject",
                                        "s3:DeleteObject",
                                        "s3:ListBucket"
                                    ],
                                    "Resource": [
                                        "arn:aws:s3:::aiemployeeplatform",
                                        "arn:aws:s3:::aiemployeeplatform/*"
                                    ]
                                }
                            ]
                        }
                    }
                ]
            }
        }
    }
}
