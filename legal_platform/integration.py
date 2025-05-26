import boto3
import json
import os
import datetime
import logging

# Set up logging
logger = logging.getLogger('legal_platform')
logger.setLevel(logging.INFO)

# Initialize AWS clients
bedrock_client = boto3.client('bedrock-runtime')
comprehend_client = boto3.client('comprehend')
lex_client = boto3.client('lexv2-runtime')
s3_client = boto3.client('s3')
dynamodb_client = boto3.client('dynamodb')
textract_client = boto3.client('textract')
sagemaker_client = boto3.client('sagemaker')
eventbridge_client = boto3.client('events')
kendra_client = boto3.client('kendra')

# Get environment variables
DOCUMENT_BUCKET = os.environ.get('DOCUMENT_BUCKET', 'legal-document-storage')
LEGAL_KNOWLEDGE_INDEX = os.environ.get('LEGAL_KNOWLEDGE_INDEX', 'legal-knowledge-index')

class DocumentProcessor:
    """Handle document processing, OCR, and entity extraction"""
    
    def process_document(self, document_data, document_name, document_type="contract"):
        """
        Process a legal document through OCR and entity extraction
        
        Args:
            document_data (bytes): The document binary data
            document_name (str): The name of the document
            document_type (str): Type of document (contract, policy, etc.)
            
        Returns:
            dict: Processed document information
        """
        try:
            # Upload document to S3
            document_key = f"documents/{document_type}/{document_name}"
            s3_client.put_object(
                Bucket=DOCUMENT_BUCKET,
                Key=document_key,
                Body=document_data
            )
            
            # Run Textract to extract text
            textract_response = textract_client.detect_document_text(
                Document={
                    'S3Object': {
                        'Bucket': DOCUMENT_BUCKET,
                        'Name': document_key
                    }
                }
            )
            
            # Extract text from Textract response
            extracted_text = ""
            for item in textract_response.get('Blocks', []):
                if item.get('BlockType') == 'LINE':
                    extracted_text += item.get('Text', '') + "\n"
            
            # Save extracted text to S3
            text_key = f"extracted_text/{document_type}/{document_name}.txt"
            s3_client.put_object(
                Bucket=DOCUMENT_BUCKET,
                Key=text_key,
                Body=extracted_text,
                ContentType='text/plain'
            )
            
            # Extract entities using Comprehend
            comprehend_response = comprehend_client.detect_entities(
                Text=extracted_text[:5000],  # API limits text size
                LanguageCode='en'
            )
            
            # Process entities
            entities = {}
            for entity in comprehend_response.get('Entities', []):
                entity_type = entity.get('Type')
                if entity_type not in entities:
                    entities[entity_type] = []
                entities[entity_type].append({
                    'text': entity.get('Text'),
                    'score': entity.get('Score')
                })
            
            # Store metadata in DynamoDB
            document_id = str(datetime.datetime.now().timestamp())
            dynamodb_client.put_item(
                TableName='LegalDocuments',
                Item={
                    'DocumentId': {'S': document_id},
                    'DocumentName': {'S': document_name},
                    'DocumentType': {'S': document_type},
                    'S3Key': {'S': document_key},
                    'TextS3Key': {'S': text_key},
                    'EntitiesDetected': {'S': json.dumps(entities)},
                    'ProcessedDate': {'S': datetime.datetime.now().isoformat()},
                    'Status': {'S': 'PROCESSED'}
                }
            )
            
            return {
                'document_id': document_id,
                'document_name': document_name,
                'document_type': document_type,
                's3_key': document_key,
                'text_s3_key': text_key,
                'entities': entities,
                'status': 'PROCESSED'
            }
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            return {
                'document_name': document_name,
                'status': 'ERROR',
                'error': str(e)
            }
    
    def get_document(self, document_id):
        """
        Retrieve a document by ID
        
        Args:
            document_id (str): The document ID
            
        Returns:
            dict: Document information
        """
        try:
            # Get document metadata from DynamoDB
            response = dynamodb_client.get_item(
                TableName='LegalDocuments',
                Key={
                    'DocumentId': {'S': document_id}
                }
            )
            
            if 'Item' not in response:
                return {'status': 'ERROR', 'error': 'Document not found'}
            
            item = response['Item']
            
            # Get document text from S3
            text_s3_key = item['TextS3Key']['S']
            text_response = s3_client.get_object(
                Bucket=DOCUMENT_BUCKET,
                Key=text_s3_key
            )
            
            document_text = text_response['Body'].read().decode('utf-8')
            
            return {
                'document_id': item['DocumentId']['S'],
                'document_name': item['DocumentName']['S'],
                'document_type': item['DocumentType']['S'],
                's3_key': item['S3Key']['S'],
                'text_s3_key': text_s3_key,
                'entities': json.loads(item['EntitiesDetected']['S']),
                'text': document_text,
                'processed_date': item['ProcessedDate']['S'],
                'status': item['Status']['S']
            }
            
        except Exception as e:
            logger.error(f"Error retrieving document: {str(e)}")
            return {
                'document_id': document_id,
                'status': 'ERROR',
                'error': str(e)
            }


class LegalAnalyzer:
    """Analyze legal documents, perform contract review, and risk assessment"""
    
    def analyze_contract(self, document_id):
        """
        Analyze a contract document
        
        Args:
            document_id (str): The document ID
            
        Returns:
            dict: Analysis results
        """
        try:
            # Get document processor
            doc_processor = DocumentProcessor()
            document = doc_processor.get_document(document_id)
            
            if document.get('status') == 'ERROR':
                return document
            
            document_text = document.get('text', '')
            
            # Use Bedrock to analyze the contract
            prompt = f"""
            You are a legal expert analyzing a contract. Please review the following contract and provide:
            1. A summary of key terms
            2. Identification of potential risks or issues
            3. Recommendations for improvements
            4. Assessment of compliance with standard legal practices
            
            CONTRACT TEXT:
            {document_text[:4000]}  # Truncate text for API limits
            
            Please provide your analysis in a structured format.
            """
            
            payload = {
                "prompt": prompt,
                "max_tokens_to_sample": 1000,
                "temperature": 0.2,
                "top_p": 0.9,
            }
            
            response = bedrock_client.invoke_model(
                modelId="amazon.bedrock-nova-12b",
                body=json.dumps(payload)
            )
            
            response_body = json.loads(response['body'].read().decode())
            analysis_text = response_body.get('completion', '')
            
            # Store analysis in DynamoDB
            analysis_id = str(datetime.datetime.now().timestamp())
            dynamodb_client.put_item(
                TableName='LegalAnalyses',
                Item={
                    'AnalysisId': {'S': analysis_id},
                    'DocumentId': {'S': document_id},
                    'AnalysisType': {'S': 'CONTRACT_REVIEW'},
                    'AnalysisText': {'S': analysis_text},
                    'AnalysisDate': {'S': datetime.datetime.now().isoformat()}
                }
            )
            
            # Parse structured information from the analysis
            try:
                # Just a simple extraction approach - in a real system, 
                # use more sophisticated parsing
                summary_start = analysis_text.find("1. A summary of key terms")
                risks_start = analysis_text.find("2. Identification of potential risks")
                recommendations_start = analysis_text.find("3. Recommendations")
                compliance_start = analysis_text.find("4. Assessment of compliance")
                
                summary = analysis_text[summary_start:risks_start].strip() if summary_start >= 0 and risks_start >= 0 else ""
                risks = analysis_text[risks_start:recommendations_start].strip() if risks_start >= 0 and recommendations_start >= 0 else ""
                recommendations = analysis_text[recommendations_start:compliance_start].strip() if recommendations_start >= 0 and compliance_start >= 0 else ""
                compliance = analysis_text[compliance_start:].strip() if compliance_start >= 0 else ""
                
                structured_analysis = {
                    'summary': summary,
                    'risks': risks,
                    'recommendations': recommendations,
                    'compliance': compliance
                }
            except Exception as parsing_error:
                logger.warning(f"Error parsing structured analysis: {str(parsing_error)}")
                structured_analysis = {'full_analysis': analysis_text}
            
            return {
                'analysis_id': analysis_id,
                'document_id': document_id,
                'document_name': document.get('document_name'),
                'analysis_type': 'CONTRACT_REVIEW',
                'analysis': structured_analysis,
                'analysis_date': datetime.datetime.now().isoformat(),
                'status': 'COMPLETED'
            }
            
        except Exception as e:
            logger.error(f"Error analyzing contract: {str(e)}")
            return {
                'document_id': document_id,
                'status': 'ERROR',
                'error': str(e)
            }
    
    def assess_compliance(self, document_id, regulation_type="GDPR"):
        """
        Check document for regulatory compliance
        
        Args:
            document_id (str): The document ID
            regulation_type (str): The type of regulation to check against
            
        Returns:
            dict: Compliance assessment results
        """
        try:
            # Get document processor
            doc_processor = DocumentProcessor()
            document = doc_processor.get_document(document_id)
            
            if document.get('status') == 'ERROR':
                return document
            
            document_text = document.get('text', '')
            
            # Get knowledge about the regulation from Kendra
            try:
                kendra_response = kendra_client.query(
                    IndexId=LEGAL_KNOWLEDGE_INDEX,
                    QueryText=f"{regulation_type} compliance requirements",
                    AttributeFilter={
                        "EqualsTo": {
                            "Key": "RegulationType",
                            "Value": {"StringValue": regulation_type}
                        }
                    }
                )
                
                regulation_knowledge = "\n".join([
                    result.get('DocumentExcerpt', {}).get('Text', '')
                    for result in kendra_response.get('ResultItems', [])
                ])
            except Exception as kendra_error:
                logger.warning(f"Error retrieving knowledge from Kendra: {str(kendra_error)}")
                regulation_knowledge = f"Standard {regulation_type} compliance requirements"
            
            # Use Bedrock to assess compliance
            prompt = f"""
            You are a legal compliance expert specializing in {regulation_type}. 
            Please review the following document and assess its compliance with {regulation_type} requirements.
            
            REGULATION KNOWLEDGE:
            {regulation_knowledge}
            
            DOCUMENT TEXT:
            {document_text[:4000]}  # Truncate text for API limits
            
            Please provide:
            1. Compliance assessment (compliant, partially compliant, or non-compliant)
            2. Identified compliance issues
            3. Recommendations for achieving full compliance
            4. Risk level (low, medium, high)
            
            Format your response in a structured way.
            """
            
            payload = {
                "prompt": prompt,
                "max_tokens_to_sample": 1000,
                "temperature": 0.2,
                "top_p": 0.9,
            }
            
            response = bedrock_client.invoke_model(
                modelId="amazon.bedrock-nova-12b",
                body=json.dumps(payload)
            )
            
            response_body = json.loads(response['body'].read().decode())
            analysis_text = response_body.get('completion', '')
            
            # Store compliance assessment in DynamoDB
            assessment_id = str(datetime.datetime.now().timestamp())
            dynamodb_client.put_item(
                TableName='ComplianceAssessments',
                Item={
                    'AssessmentId': {'S': assessment_id},
                    'DocumentId': {'S': document_id},
                    'RegulationType': {'S': regulation_type},
                    'AssessmentText': {'S': analysis_text},
                    'AssessmentDate': {'S': datetime.datetime.now().isoformat()}
                }
            )
            
            # Parse assessment details
            try:
                # Extract compliance level
                if 'non-compliant' in analysis_text.lower():
                    compliance_level = 'NON_COMPLIANT'
                elif 'partially compliant' in analysis_text.lower():
                    compliance_level = 'PARTIALLY_COMPLIANT'
                elif 'compliant' in analysis_text.lower():
                    compliance_level = 'COMPLIANT'
                else:
                    compliance_level = 'UNKNOWN'
                
                # Extract risk level
                if 'high risk' in analysis_text.lower() or 'risk level: high' in analysis_text.lower():
                    risk_level = 'HIGH'
                elif 'medium risk' in analysis_text.lower() or 'risk level: medium' in analysis_text.lower():
                    risk_level = 'MEDIUM'
                elif 'low risk' in analysis_text.lower() or 'risk level: low' in analysis_text.lower():
                    risk_level = 'LOW'
                else:
                    risk_level = 'UNKNOWN'
                
                # Find issues and recommendations sections
                issues_start = analysis_text.find("2. Identified compliance issues")
                recommendations_start = analysis_text.find("3. Recommendations")
                
                if issues_start >= 0 and recommendations_start >= 0:
                    issues = analysis_text[issues_start:recommendations_start].strip()
                else:
                    issues = "Could not extract specific issues"
                
                if recommendations_start >= 0:
                    recommendations = analysis_text[recommendations_start:].strip()
                else:
                    recommendations = "Could not extract specific recommendations"
                
                structured_assessment = {
                    'compliance_level': compliance_level,
                    'risk_level': risk_level,
                    'issues': issues,
                    'recommendations': recommendations
                }
            except Exception as parsing_error:
                logger.warning(f"Error parsing structured assessment: {str(parsing_error)}")
                structured_assessment = {'full_assessment': analysis_text}
            
            return {
                'assessment_id': assessment_id,
                'document_id': document_id,
                'document_name': document.get('document_name'),
                'regulation_type': regulation_type,
                'assessment': structured_assessment,
                'assessment_date': datetime.datetime.now().isoformat(),
                'status': 'COMPLETED'
            }
            
        except Exception as e:
            logger.error(f"Error assessing compliance: {str(e)}")
            return {
                'document_id': document_id,
                'regulation_type': regulation_type,
                'status': 'ERROR',
                'error': str(e)
            }


class ComplianceMonitor:
    """Monitor regulatory changes and compliance requirements"""
    
    def check_compliance_status(self, business_domain="general"):
        """
        Check current compliance status across regulations
        
        Args:
            business_domain (str): Business area to check compliance for
            
        Returns:
            dict: Compliance status information
        """
        try:
            # In a real implementation, this would query a database of compliance
            # requirements and check them against the organization's current status
            
            # For demonstration, return a mock response
            return {
                'status': 'SUCCESS',
                'business_domain': business_domain,
                'compliance_summary': {
                    'compliant': 8,
                    'partially_compliant': 2,
                    'non_compliant': 1,
                    'unknown': 0
                },
                'regulations': [
                    {
                        'name': 'GDPR',
                        'status': 'COMPLIANT',
                        'last_assessed': '2023-10-15T14:30:00Z',
                        'risk_level': 'LOW'
                    },
                    {
                        'name': 'CCPA',
                        'status': 'COMPLIANT',
                        'last_assessed': '2023-09-22T10:15:00Z',
                        'risk_level': 'LOW'
                    },
                    {
                        'name': 'HIPAA',
                        'status': 'PARTIALLY_COMPLIANT',
                        'last_assessed': '2023-11-05T16:45:00Z',
                        'risk_level': 'MEDIUM',
                        'issues': ['Data retention policy needs updating', 'Access controls need enhancement']
                    },
                    {
                        'name': 'SOX',
                        'status': 'NON_COMPLIANT',
                        'last_assessed': '2023-10-30T09:20:00Z',
                        'risk_level': 'HIGH',
                        'issues': ['Financial reporting controls inadequate', 'Audit trail incomplete']
                    }
                ],
                'assessment_date': datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking compliance status: {str(e)}")
            return {
                'status': 'ERROR',
                'error': str(e)
            }
    
    def get_regulatory_updates(self, regions=None, industries=None):
        """
        Get recent regulatory updates relevant to the organization
        
        Args:
            regions (list): Geographic regions of interest
            industries (list): Industry sectors of interest
            
        Returns:
            dict: Recent regulatory updates
        """
        if regions is None:
            regions = ['US', 'EU']
        
        if industries is None:
            industries = ['Technology', 'Finance']
        
        try:
            # In a real implementation, this would query a regulatory database
            # or use an API to get recent updates
            
            # For demonstration, return a mock response
            return {
                'status': 'SUCCESS',
                'regions': regions,
                'industries': industries,
                'updates': [
                    {
                        'title': 'EU AI Act Updates',
                        'description': 'New provisions regarding AI system transparency requirements.',
                        'effective_date': '2023-12-01T00:00:00Z',
                        'regions': ['EU'],
                        'industries': ['Technology', 'Healthcare', 'Finance'],
                        'impact_level': 'HIGH',
                        'source_url': 'https://example.com/eu-ai-act-updates'
                    },
                    {
                        'title': 'California Privacy Rights Act Amendments',
                        'description': 'Expanded consumer rights and business obligations.',
                        'effective_date': '2024-01-15T00:00:00Z',
                        'regions': ['US'],
                        'industries': ['All'],
                        'impact_level': 'MEDIUM',
                        'source_url': 'https://example.com/cpra-amendments'
                    },
                    {
                        'title': 'SEC Cybersecurity Disclosure Rules',
                        'description': 'New requirements for reporting material cybersecurity incidents.',
                        'effective_date': '2023-11-10T00:00:00Z',
                        'regions': ['US'],
                        'industries': ['Finance', 'Public Companies'],
                        'impact_level': 'HIGH',
                        'source_url': 'https://example.com/sec-cybersecurity-rules'
                    }
                ],
                'retrieved_date': datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting regulatory updates: {str(e)}")
            return {
                'status': 'ERROR',
                'error': str(e)
            }