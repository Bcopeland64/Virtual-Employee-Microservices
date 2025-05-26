import boto3
import json

def validate(slots, required_slots):
    """
    Validate that all required slots are filled.
    """
    for slot in required_slots:
        if not slots.get(slot):
            return {
                'isValid': False,
                'violatedSlot': slot
            }
    return {'isValid': True}

def createMarketingPlan(event):
    try:
        # Initialize the Bedrock client
        bedrock = boto3.client('bedrock-runtime', region_name='eu-west-2')
        
        # Extract request_text and slots from the event
        slots = event.get('sessionState', {}).get('intent', {}).get('slots', {})

        # List of required slots
        required_slots = ["ProductOrService", "MarketingChannel", "TargetCustomers", "BudgetRange"]

        # Validate required slots
        validation_result = validate(slots, required_slots)
        if not validation_result['isValid']:
            return {
                'sessionState':{
                    'dialogAction': {
                        'slotToElicit': validation_result['violatedSlot'],
                        'type': "ElicitSlot"
                    },
                    'intent': {
                        'name': 'CreateMarketingPlanIntent',
                        'slots': slots
                    }
                }
            }
        
        # Extract slot values
        product_or_service = event['sessionState']['intent']['slots'].get('ProductOrService', {}).get('value', {}).get('originalValue')
        marketing_channel = event['sessionState']['intent']['slots'].get('MarketingChannel', {}).get('value', {}).get('originalValue')
        target_customers = event['sessionState']['intent']['slots'].get('TargetCustomers', {}).get('value', {}).get('originalValue')
        budget_range = event['sessionState']['intent']['slots'].get('BudgetRange', {}).get('value', {}).get('originalValue')

        # Handle custom budget input
        if budget_range.lower() == "other":
            custom_budget = slots.get('CustomBudgetRange', {}).get("value", {}).get("originalValue", "").strip() if slots.get('CustomBudgetRange') else None
            if not custom_budget:
                return {
                    'sessionState': {
                        'dialogAction': {
                            'slotToElicit': "CustomBudgetRange",
                            'type': "ElicitSlot"
                        },
                        'intent': {
                            'name': 'CreateMarketingPlanIntent',
                            'slots': slots
                        }
                    },
                    'messages': [
                        {
                            'contentType': 'PlainText',
                            'content': "Please specify your Custom Budget amount."
                        }
                    ]
                }
            budget = custom_budget
        else:
            budget = budget_range

        # Construct the prompt for Bedrock
        prompt = f"""in markdown format, Create a detailed marketing plan for: {product_or_service}

                    Budget: {budget}
                    Preferred Marketing Channels: {marketing_channel}
                    Target Customers: {target_customers}

                    Please provide:
                    1. Executive Summary
                    2. Target Market Analysis (specifically Target Customers )
                    3. Marketing Strategy (Tailored to marketing channels, target customers, and budget)
                    4. Budget Breakdown (specifically Budget)
                    5. Timeline
                    6. Success Metrics"""

        
        response = bedrock.invoke_model(
            modelId='amazon.bedrock-nova-12b',
            contentType="application/json",
            body=json.dumps({
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 700,
                    "temperature": 0.7,
                    "topP": 0.9
                }
            })
        )
         
        response_body = json.loads(response['body'].read())
        
        return {
            'sessionState': {
                'dialogAction': {
                    'type': 'Close'
                },
                'intent': {
                    'name': 'CreateMarketingPlanIntent',
                    'state': 'Fulfilled'
                }
            },
            'messages': [
                {
                    'contentType': 'PlainText',
                    'content': response_body["results"][0]["outputText"]
                }
            ]
        }
        
    except Exception as e:
        print(f"Error in marketing plan: {str(e)}")
        return {
            'sessionState': {
                'dialogAction': {
                    'type': 'Close'
                },
                'intent': {
                    'name': 'CreateMarketingPlanIntent',
                    'state': 'Failed'
                }
            },
            'messages': [
                {
                    'contentType': 'PlainText',
                    'content': f"Error creating marketing plan: {str(e)}"
                }
            ]
        }
