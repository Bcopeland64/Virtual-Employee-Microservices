import boto3
import json
import os
# from analyze_sales_ import analyze_sales_data
from f_marketing_plan import createMarketingPlan
from f_report_generator import generate_report


def lambda_handler(event, context):
    
    intent_name = event['sessionState']['intent']['name']
    
    if intent_name == 'MarketingPlanIntent':
        response = createMarketingPlan(event)
    elif intent_name== 'GenerateReportIntent':
        response = generate_report(event)
    else:
        response = default_response()
        
    return response
    
def default_response():
    return {
        "sessionState": {
            "dialogAction": {
                "type": "Close"
            },
            "intent": {
                "name": "FallbackIntent",
                "state": "Fulfilled"
            }
        },
        "messages": [
            {
                "contentType": "PlainText",
                "content": "I’m not sure how to handle that request."
            }
        ]
    }
