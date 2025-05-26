import json
import boto3
import time
import config
from botocore.exceptions import ClientError

# Initialize AWS clients
lambda_client = boto3.client('lambda', region_name=config.AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
conversation_table = dynamodb.Table(config.DYNAMODB_TABLES['Conversations'])

def lambda_handler(event, context):
    """
    Main handler for Lex intents
    """
    try:
        print("Received Lex event:", json.dumps(event))
        
        # Extract intent information
        intent_name = event['sessionState']['intent']['name']
        slots = event['sessionState']['intent']['slots']
        
        # Store conversation in DynamoDB
        conversation_item = {
            'conversationId': f"lex_{int(time.time())}",
            'timestamp': int(time.time()),
            'type': 'lex_interaction',
            'intent': intent_name,
            'slots': slots,
            'status': 'processing'
        }
        conversation_table.put_item(Item=conversation_item)
        
        # Process different intents
        response = process_intent(intent_name, slots, conversation_item['conversationId'])
        
        # Update conversation with response
        conversation_table.update_item(
            Key={'conversationId': conversation_item['conversationId']},
            UpdateExpression="set #status = :s, #output = :o",
            ExpressionAttributeNames={
                '#status': 'status',
                '#output': 'output'
            },
            ExpressionAttributeValues={
                ':s': 'completed',
                ':o': response
            }
        )
        
        # Format response for Lex
        return format_lex_response(response, intent_name)
        
    except Exception as e:
        print(f"Error in lex_handler: {str(e)}")
        return format_lex_response(
            {"error": str(e)},
            intent_name,
            success=False
        )

def process_intent(intent_name, slots, conversation_id):
    """
    Routes intents to appropriate Lambda functions
    """
    try:
        if intent_name == "AnalyzeSalesIntent":
            return invoke_sales_analysis(slots)
        elif intent_name == "CreateMarketingPlanIntent":
            return invoke_marketing_plan(slots)
        elif intent_name == "GenerateReportIntent":
            return invoke_report_generation(slots)
        else:
            return {"error": f"Unknown intent: {intent_name}"}
    except Exception as e:
        print(f"Error processing intent {intent_name}: {str(e)}")
        return {"error": str(e)}

def invoke_sales_analysis(slots):
    """
    Invokes the sales analysis Lambda
    """
    period = slots.get('Period', {}).get('value', {}).get('originalValue', 'current')
    response = lambda_client.invoke(
        FunctionName=config.LAMBDA_FUNCTIONS['AnalyzeSalesData'],
        InvocationType='RequestResponse',
        Payload=json.dumps({
            "transcript": f"Analyze sales data for {period}",
            "period": period
        })
    )
    return json.loads(response['Payload'].read())

def invoke_marketing_plan(slots):
    """
    Invokes the marketing plan Lambda
    """
    product = slots.get('Product', {}).get('value', {}).get('originalValue', 'product')
    audience = slots.get('Audience', {}).get('value', {}).get('originalValue', 'general')
    response = lambda_client.invoke(
        FunctionName=config.LAMBDA_FUNCTIONS['CreateMarketingPlan'],
        InvocationType='RequestResponse',
        Payload=json.dumps({
            "task": f"Create marketing plan for {product} targeting {audience}",
            "product": product,
            "target_audience": audience
        })
    )
    return json.loads(response['Payload'].read())

def invoke_report_generation(slots):
    """
    Invokes the report generation Lambda
    """
    report_type = slots.get('ReportType', {}).get('value', {}).get('originalValue', 'general')
    response = lambda_client.invoke(
        FunctionName=config.LAMBDA_FUNCTIONS['GenerateReport'],
        InvocationType='RequestResponse',
        Payload=json.dumps({
            "report_type": report_type
        })
    )
    return json.loads(response['Payload'].read())

def format_lex_response(response, intent_name, success=True):
    """
    Formats the response for Lex
    """
    if success:
        message = format_success_message(response, intent_name)
    else:
        message = "I encountered an error processing your request. Please try again."
    
    return {
        "sessionState": {
            "dialogAction": {
                "type": "Close"
            },
            "intent": {
                "name": intent_name,
                "state": "Fulfilled" if success else "Failed"
            }
        },
        "messages": [
            {
                "contentType": "PlainText",
                "content": message
            }
        ]
    }

def format_success_message(response, intent_name):
    """
    Formats success messages based on intent
    """
    if 'error' in response:
        return f"Sorry, there was an error: {response['error']}"
        
    if intent_name == "AnalyzeSalesIntent":
        return "I've analyzed the sales data. Here are the key findings: " + \
               json.dumps(response.get('body', {}), indent=2)
    
    elif intent_name == "CreateMarketingPlanIntent":
        return "I've created a marketing plan. Here are the details: " + \
               json.dumps(response.get('body', {}), indent=2)
    
    elif intent_name == "GenerateReportIntent":
        return "I've generated the report. Here are the highlights: " + \
               json.dumps(response.get('body', {}), indent=2)
    
    return json.dumps(response)
