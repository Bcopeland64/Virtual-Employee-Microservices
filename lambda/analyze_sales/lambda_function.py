import json
import boto3
import time
import config
from botocore.exceptions import ClientError
from decimal import Decimal

# Initialize AWS clients outside the handler
bedrock_client = boto3.client('bedrock-runtime', region_name=config.AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
s3 = boto3.client('s3', region_name=config.AWS_REGION)
conversation_table = dynamodb.Table(config.DYNAMODB_TABLES['Conversations'])

def lambda_handler(event, context):
    """
    AWS Lambda handler for analyzing sales data using Bedrock
    """
    try:
        print("Received event:", json.dumps(event))
        
        # Extract parameters
        period = event.get('period', 'current')
        transcript = event.get('transcript', '')
        raw_data = event.get('sales_data', {})
        
        # Create conversation record
        conversation_id = f"sales_analysis_{int(time.time())}"
        
        # Prepare the prompt for Bedrock
        prompt = create_analysis_prompt(period, transcript, raw_data)
        
        # Call Bedrock for analysis
        bedrock_response = bedrock_client.invoke_model(
            modelId=config.BEDROCK_MODELS['TaskRefinement'],
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                "prompt": prompt,
                "max_tokens": 2000,
                "temperature": 0.7,
                "top_p": 1,
                "stop_sequences": []
            })
        )
        
        # Process Bedrock response
        response_body = json.loads(bedrock_response['body'].read())
        analysis_results = process_bedrock_response(response_body)
        
        # Store results in S3
        s3_key = f"sales_analysis/{conversation_id}.json"
        s3.put_object(
            Bucket=config.S3_BUCKETS['DataStorage'],
            Key=s3_key,
            Body=json.dumps(analysis_results)
        )
        
        # Store in DynamoDB
        store_analysis_results(conversation_id, analysis_results)
        
        return {
            'statusCode': 200,
            'body': json.dumps(analysis_results)
        }
        
    except Exception as e:
        print(f"Error in analyze_sales_lambda: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'type': str(type(e).__name__)
            })
        }

def create_analysis_prompt(period, transcript, raw_data):
    """
    Creates a detailed prompt for Bedrock analysis
    """
    prompt = f"""
    Please analyze the following sales data and provide a comprehensive report.
    
    Period: {period}
    Context: {transcript}
    
    Raw Data: {json.dumps(raw_data, indent=2)}
    
    Please provide:
    1. Executive Summary
    2. Key Performance Indicators
    3. Trend Analysis
    4. Comparative Analysis
    5. Actionable Insights
    6. Recommendations
    
    Focus on:
    - Revenue trends
    - Growth patterns
    - Customer behavior
    - Product performance
    - Market conditions
    - Risk factors
    - Opportunities for improvement
    
    Format the response as a structured JSON with these sections.
    """
    return prompt

def process_bedrock_response(response):
    """
    Processes and structures the Bedrock response
    """
    try:
        # Extract the completion from Bedrock response
        analysis_text = response.get('completions', [{}])[0].get('data', '')
        
        # Parse the analysis into structured format
        structured_analysis = {
            'timestamp': int(time.time()),
            'analysis_version': '2.0',
            'sections': {
                'executive_summary': extract_section(analysis_text, 'Executive Summary'),
                'kpis': extract_and_format_kpis(analysis_text),
                'trend_analysis': extract_section(analysis_text, 'Trend Analysis'),
                'comparative_analysis': extract_section(analysis_text, 'Comparative Analysis'),
                'insights': extract_insights(analysis_text),
                'recommendations': extract_recommendations(analysis_text)
            },
            'metadata': {
                'model_id': config.BEDROCK_MODELS['TaskRefinement'],
                'analysis_type': 'sales_performance'
            }
        }
        
        return structured_analysis
    except Exception as e:
        print(f"Error processing Bedrock response: {str(e)}")
        raise

def extract_section(text, section_name):
    """
    Extracts and formats a specific section from the analysis text
    """
    try:
        # Implementation would vary based on actual Bedrock response format
        return {
            'content': f"Extracted {section_name} content",
            'highlights': []
        }
    except Exception as e:
        print(f"Error extracting section {section_name}: {str(e)}")
        return {'error': str(e)}

def extract_and_format_kpis(text):
    """
    Extracts and formats KPIs from the analysis text
    """
    try:
        # Implementation would vary based on actual Bedrock response format
        return {
            'revenue': {
                'value': 0,
                'change': 0,
                'trend': 'stable'
            },
            'growth': {
                'value': 0,
                'change': 0,
                'trend': 'stable'
            },
            'customer_metrics': {
                'value': 0,
                'change': 0,
                'trend': 'stable'
            }
        }
    except Exception as e:
        print(f"Error extracting KPIs: {str(e)}")
        return {'error': str(e)}

def extract_insights(text):
    """
    Extracts key insights from the analysis text
    """
    try:
        # Implementation would vary based on actual Bedrock response format
        return [
            {'category': 'revenue', 'insight': 'Sample insight 1'},
            {'category': 'growth', 'insight': 'Sample insight 2'}
        ]
    except Exception as e:
        print(f"Error extracting insights: {str(e)}")
        return [{'error': str(e)}]

def extract_recommendations(text):
    """
    Extracts recommendations from the analysis text
    """
    try:
        # Implementation would vary based on actual Bedrock response format
        return [
            {
                'priority': 'high',
                'recommendation': 'Sample recommendation 1',
                'impact': 'high'
            }
        ]
    except Exception as e:
        print(f"Error extracting recommendations: {str(e)}")
        return [{'error': str(e)}]

def store_analysis_results(conversation_id, analysis_results):
    """
    Stores the analysis results in DynamoDB
    """
    try:
        conversation_table.put_item(
            Item={
                'conversationId': conversation_id,
                'timestamp': analysis_results['timestamp'],
                'type': 'sales_analysis',
                'status': 'completed',
                'analysis': analysis_results
            }
        )
    except Exception as e:
        print(f"Error storing analysis results: {str(e)}")
        raise
