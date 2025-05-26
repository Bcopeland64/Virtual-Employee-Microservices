import json
import boto3
import time
import config
from botocore.exceptions import ClientError

# Initialize AWS clients outside the handler
bedrock_client = boto3.client('bedrock-runtime', region_name=config.AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
s3 = boto3.client('s3', region_name=config.AWS_REGION)
conversation_table = dynamodb.Table(config.DYNAMODB_TABLES['Conversations'])

def lambda_handler(event, context):
    """
    AWS Lambda handler for creating marketing plans
    Function name in config: AIEmployee_CreateMarketingPlan
    """
    try:
        print("Received event:", json.dumps(event))
        
        # Extract parameters
        task = event.get('task', '')
        
        # Create conversation record
        conversation_item = {
            'conversationId': f"marketing_plan_{int(time.time())}",
            'timestamp': int(time.time()),
            'type': 'marketing_plan',
            'input': task,
            'status': 'processing'
        }
        
        conversation_table.put_item(Item=conversation_item)
        
        # Use Bedrock for plan generation
        bedrock_response = bedrock_client.invoke_model(
            modelId=config.BEDROCK_MODELS['TaskRefinement'],
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                'text': task,
                'type': 'marketing_plan'
            })
        )
        
        # Process and structure the marketing plan
        marketing_plan = {
            'plan_id': conversation_item['conversationId'],
            'timestamp': conversation_item['timestamp'],
            'content': json.loads(bedrock_response['body'].read()),
            'source_task': task
        }
        
        # Store in S3
        s3.put_object(
            Bucket=config.S3_BUCKETS['DataStorage'],
            Key=f"marketing_plans/{conversation_item['conversationId']}.json",
            Body=json.dumps(marketing_plan)
        )
        
        # Update conversation status
        conversation_table.update_item(
            Key={'conversationId': conversation_item['conversationId']},
            UpdateExpression="set #status = :s, #output = :o",
            ExpressionAttributeNames={
                '#status': 'status',
                '#output': 'output'
            },
            ExpressionAttributeValues={
                ':s': 'completed',
                ':o': marketing_plan
            }
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps(marketing_plan)
        }
        
    except Exception as e:
        print(f"Error in marketing_plan_lambda: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'type': str(type(e).__name__)
            })
        }
