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


def analyze_sales_data(event):
    print("before")
    print(event['sessionState']['intent']['slots'])
    slots = event.get('sessionState', {}).get('intent', {}).get('slots', {})
    # List of required slots
    required_slots = ["FileName"]
    validation_result = validate(slots, required_slots)
    if not validation_result['isValid']:
        return {
            'sessionState':{
                'dialogAction': {
                    'slotToElicit': validation_result['violatedSlot'],
                    'type': "ElicitSlot"
                },
                'intent': {
                    'name': 'AnalyzeSalesIntent',
                    'slots': slots
                }
            }
        }

    file_name = event['sessionState']['intent']['slots'].get('FileName', {}).get('value', {}).get('interpretedValue')
    print(file_name)
    
    
    if not file_name:
          return {
        "sessionState": {
            "dialogAction": {
                "type": "ElicitSlot",
                "slotToElicit": "FileName"
            },
            "intent": {
                "name": "AnalyzeSalesIntent",  # Replace with your intent name
                "slots":event['sessionState']['intent']['slots'] ,
                "state": "InProgress"
            }
        },
        "messages": [
            {
                "contentType": "PlainText",
                "content": "Please provide correct  file name to analyze."
            }
        ]
    }

        
    bucket_name = 'ai-employee'

    s3_client = boto3.client('s3')
    try:        
        response = s3_client.get_object(Bucket=bucket_name, Key=file_name)
        file_content = response['Body'].read().decode('utf-8')
        sales_data =  json.loads(file_content)
        print(sales_data)

        prompt = (
                f"""Analyze the following sales data and provide insights:
                ${sales_data}
                
            Please provide key insights and any recommendations based on the data."""
            )
        native_request = {            
            "prompt": f"<s>[INST] {prompt} [/INST]",
            "max_tokens": 512,
            "temperature": 0.5,
            "top_p": 0.9,
            "top_k": 50 
        }
        request = json.dumps(native_request)  
        # Invoke the Bedrock model
        
        # print(prompt)
        bedrock_response = bedrock_client.invoke_model(
            modelId='amazon.bedrock-nova-12b',
            contentType='application/json',
            accept='application/json',
            body=request
        )
        # Parse Bedrock's response
        analysis_response = bedrock_response['body'].read().decode('utf-8')
        print(analysis_response)
        # Parse the JSON response
        response_data = json.loads(analysis_response)

        output_text = response_data["outputs"][0]["text"].encode('utf-8').decode('unicode_escape')
        print(output_text)
          
        return {
            "sessionState": {
                "dialogAction": {
                    "type": "Close"
                },
                "intent": {
                    "name": "AnalyzeSalesIntent",
                    "state": "Fulfilled"
                }
            },
            "messages": [
                {
                    "contentType": "PlainText",
                    "content": f"Here is the analysis: {output_text}"
                }
            ]
        }

    except s3_client.exceptions.NoSuchKey:
            # print(f"Error invoking Bedrock model: {e}")
            return {
                "sessionState": {
                    "dialogAction": {
                        "type": "Close"
                    },
                    "intent": {
                        "name": "AnalyzeSalesIntent",
                        "state": "Failed"
                    }
                },
                "messages": [
                    {
                        "contentType": "PlainText",
                        "content": "The file name you provided does not exist in the storage. Please provide a valid file name."
                    }
                ]
            }
    except Exception as e:
        return {
            "dialogAction": {
                "type": "Close",
                "fulfillmentState": "Failed",
                "message": {"contentType": "PlainText", "content": f"Error processing the file: {str(e)}"}
            }
        }