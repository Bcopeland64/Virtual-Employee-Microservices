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
performance_table = dynamodb.Table(config.DYNAMODB_TABLES['Performance'])

def lambda_handler(event, context):
    """
    AWS Lambda handler for generating reports
    Function name in config: AIEmployee_GenerateReport
    """
    try:
        print("Received event:", json.dumps(event))
        
        # Extract parameters
        report_type = event.get('report_type', '')
        
        # Create conversation record
        conversation_item = {
            'conversationId': f"report_{int(time.time())}",
            'timestamp': int(time.time()),
            'type': 'report_generation',
            'input': report_type,
            'status': 'processing'
        }
        
        conversation_table.put_item(Item=conversation_item)
        
        # Get performance data if needed
        performance_data = None
        if report_type == 'performance':
            try:
                performance_response = performance_table.get_item(
                    Key={'reportId': 'latest'}
                )
                performance_data = performance_response.get('Item', {}).get('report', {})
            except ClientError as e:
                print(f"Error getting performance data: {str(e)}")
        
        # Use Bedrock for report generation
        bedrock_response = bedrock_client.invoke_model(
            modelId=config.BEDROCK_MODELS['TaskRefinement'],
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                'text': f"Generate {report_type} report",
                'type': 'report_generation',
                'performance_data': performance_data
            })
        )
        
        # Process and structure the report
        report = {
            'report_id': conversation_item['conversationId'],
            'timestamp': conversation_item['timestamp'],
            'type': report_type,
            'content': json.loads(bedrock_response['body'].read()),
            'includes_performance_data': performance_data is not None
        }
        
        # Store in S3
        s3.put_object(
            Bucket=config.S3_BUCKETS['DataStorage'],
            Key=f"reports/{conversation_item['conversationId']}.json",
            Body=json.dumps(report)
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
                ':o': report
            }
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps(report)
        }
        
    except Exception as e:
        print(f"Error in report_generator_lambda: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'type': str(type(e).__name__)
            })
        }
