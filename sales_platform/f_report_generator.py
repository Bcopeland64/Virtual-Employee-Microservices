import boto3
import json
import os

# Initialize Bedrock client
bedrock_client = boto3.client('bedrock-runtime')

def validate(slots, required_slots):
    for slot in required_slots:
        if not slots.get(slot):
            return {
                'isValid': False,
                'violatedSlot': slot
            }
    return {'isValid': True}


def generate_report(event):


   
    required_slots = ["CustomReportType"]

    slots = event.get("sessionState", {}).get("intent", {}).get("slots", {})
    
    

    validation_result = validate(slots, required_slots)
    if not validation_result['isValid']:
        return {
            'sessionState':{
                'dialogAction': {
                    'slotToElicit': validation_result['violatedSlot'],
                    'type': "ElicitSlot"
                },
                'intent': {
                    'name': 'GenerateReportIntent',
                    'slots': slots
                }
                     
            }
        }


        
    report_type = slots.get('CustomReportType', {}).get("value", {}).get("originalValue", "").strip() or "Generate report"
    # Dummy data for the report generation
    report_data = {
        "summary": f"{report_type.capitalize()} report for whole year in the North region",
            "details": (
                f"The {report_type} saw significant changes over the whole year. "
                "Notable trends include increased sales in the East region and a decrease in the South. "
                "Region-specific breakdowns show a 15% increase in the North, while the South region faced a 5% decline."
            ),
            "nextSteps": (
                "1. Review regional strategies for improvement.\n"
                "2. Expand successful marketing campaigns in the North.\n"
                "3. Conduct further analysis on the South region decline."
            )
    }

    # Construct a prompt for the Bedrock model
    prompt = (
        f"""Generate a {report_type} report with the following fields based on the data provided:

    Summary: {report_data['summary']}

    Details: {report_data['details']}

    Next Steps: {report_data['nextSteps']}
    """
        )

    native_request = {
        "inputText": prompt,
        "textGenerationConfig": {
            "maxTokenCount": 512,
            "temperature": 0.5,
        },
    }
    request = json.dumps(native_request)

    # Invoke the Bedrock model
    try:
        bedrock_response = bedrock_client.invoke_model(
            modelId='amazon.bedrock-nova-12b', body=request
        )

        # Parse Bedrock's response
        report_response = bedrock_response['body'].read().decode('utf-8')
        # Parse the JSON response
        response_data = json.loads(report_response)

        output_text = response_data["results"][0]["outputText"].encode('utf-8').decode('unicode_escape')

        return {
            "sessionState": {
                "dialogAction": {
                    "type": "Close"
                },
                "intent": {
                    "name": "GenerateReportIntent",
                    "state": "Fulfilled"
                }
            },
            "messages": [
                {
                    "contentType": "PlainText",
                    "content": f"Here is the generated report: {output_text}"
                }
            ]
        }

    except Exception as e:
        print(f"Error invoking Bedrock model: {e}")
        return {
            "sessionState": {
                "dialogAction": {
                    "type": "Close"
                },
                "intent": {
                    "name": "GenerateReportIntent",
                    "state": "Failed"
                }
            },
            "messages": [
                {
                    "contentType": "PlainText",
                    "content": "Something went wrong while generating the report."
                }
            ]
        }

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
