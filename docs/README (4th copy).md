# AI Legal Platform Integration

This directory contains the core components for integrating the AI Legal Platform with the AI Employee system.

## Overview

The AI Legal Platform provides advanced legal functionality powered by AWS AI services, enabling document processing, contract analysis, compliance monitoring, and regulatory updates. It helps organizations manage legal documents, assess compliance with regulations, and stay informed about regulatory changes.

## Features

- **Document Processing**: Extract text and entities from legal documents using AWS Textract and Comprehend
- **Contract Analysis**: Analyze contracts for key terms, risks, and compliance issues using AWS Bedrock
- **Compliance Assessment**: Check document compliance with regulations like GDPR, CCPA, HIPAA, and SOX
- **Compliance Monitoring**: Track overall compliance status across the organization
- **Regulatory Updates**: Stay informed about relevant regulatory changes

## Components

- **integration.py**: Core implementation of Legal Platform services:
  - `DocumentProcessor`: Processes legal documents using OCR and entity extraction
  - `LegalAnalyzer`: Analyzes legal documents and assesses compliance
  - `ComplianceMonitor`: Monitors regulatory changes and compliance status

## Integration with AI Employee

The Legal Platform integrates with the AI Employee through the `legal_platform_handler.py` file in the root directory, which maps Lex intents to Legal Platform functionality:

| Intent | Function | Description |
|--------|----------|-------------|
| `ProcessLegalDocument` | `handle_document_processing` | Process and store legal documents |
| `AnalyzeContract` | `handle_contract_analysis` | Analyze contracts for key terms and risks |
| `CheckCompliance` | `handle_compliance_check` | Check document compliance with regulations |
| `GetRegulatoryUpdates` | `handle_regulatory_updates` | Get recent regulatory updates |
| `GetComplianceStatus` | `handle_compliance_status` | Get overall compliance status |

## Required AWS Services

- **Amazon Bedrock**: For legal reasoning and analysis
- **Amazon Comprehend**: For entity recognition in legal documents
- **Amazon Textract**: For document OCR
- **Amazon S3**: For document storage
- **Amazon DynamoDB**: For metadata storage
- **Amazon Kendra**: For legal knowledge base
- **Amazon EventBridge**: For scheduling compliance checks
- **Amazon SNS**: For notifications

## Setup

### 1. Create Required AWS Resources

```bash
# Create S3 bucket for document storage
aws s3 mb s3://legal-document-storage --region us-east-1

# Create DynamoDB tables
aws dynamodb create-table \
  --table-name LegalDocuments \
  --attribute-definitions AttributeName=DocumentId,AttributeType=S \
  --key-schema AttributeName=DocumentId,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

aws dynamodb create-table \
  --table-name LegalAnalyses \
  --attribute-definitions AttributeName=AnalysisId,AttributeType=S \
  --key-schema AttributeName=AnalysisId,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

aws dynamodb create-table \
  --table-name ComplianceAssessments \
  --attribute-definitions AttributeName=AssessmentId,AttributeType=S \
  --key-schema AttributeName=AssessmentId,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

# Create Amazon Kendra index for legal knowledge
aws kendra create-index \
  --name legal-knowledge-index \
  --edition ENTERPRISE_EDITION \
  --role-arn arn:aws:iam::<ACCOUNT_ID>:role/KendraRole
```

### 2. Configure Environment Variables

Add these environment variables to your deployment environment:

```bash
export DOCUMENT_BUCKET=legal-document-storage
export LEGAL_KNOWLEDGE_INDEX=<KENDRA_INDEX_ID>
```

### 3. Update the AI Employee Main Orchestrator

Integrate the Legal Platform with the main orchestrator by adding the following intents to the orchestrator's routing logic:

```python
# Legal Platform intents
elif intent_name == 'ProcessLegalDocument':
    response = handle_document_processing(event, session_attributes)
elif intent_name == 'AnalyzeContract':
    response = handle_contract_analysis(event, session_attributes)
elif intent_name == 'CheckCompliance':
    response = handle_compliance_check(event, session_attributes)
elif intent_name == 'GetRegulatoryUpdates':
    response = handle_regulatory_updates(event, session_attributes)
elif intent_name == 'GetComplianceStatus':
    response = handle_compliance_status(event, session_attributes)
```

## Usage

### Processing Legal Documents

```
User: "I need to process a legal document"
AI: "What type of document is it? (contract, policy, agreement)"
User: "It's a contract"
AI: "Your document has been successfully processed and stored with ID: doc-1637582946.123. You can now analyze this document or check its compliance."
```

### Analyzing Contracts

```
User: "Analyze contract doc-1637582946.123"
AI: [Returns structured analysis of key terms, risks, recommendations, and compliance assessment]
```

### Checking Compliance

```
User: "Check GDPR compliance for document doc-1637582946.123"
AI: [Returns compliance assessment including compliance status, risk level, issues, and recommendations]
```

### Getting Regulatory Updates

```
User: "Show me recent regulatory updates for the EU"
AI: [Returns list of recent regulatory updates relevant to the specified region/industry]
```

### Checking Compliance Status

```
User: "What's our overall compliance status?"
AI: [Returns summary of compliance status across regulations with attention areas highlighted]
```

## Security and Data Privacy

- All document data is encrypted at rest in S3 using SSE-KMS
- DynamoDB tables are encrypted using AWS owned keys
- IAM roles follow least privilege principle
- PII detection and handling using Amazon Comprehend PII detection

## Error Handling

The platform implements comprehensive error handling:

- Document processing errors are logged and reported to the user
- Analysis failures include specific error messages
- Network and service disruptions are gracefully handled

## Extending the Platform

To add new capabilities:

1. Add new methods to the appropriate class in `integration.py`
2. Create new handler functions in `legal_platform_handler.py`
3. Add new intents to the Lex bot and update the main orchestrator

## Reference Architecture

The Legal Platform follows a microservices architecture with clear separation of concerns:

- Document Processing Service: Handles document ingestion and OCR
- Legal Analysis Service: Performs contract analysis and compliance checks
- Compliance Monitoring Service: Tracks regulatory changes

For deployment details, refer to the detailed architecture diagram in the Sprint_2 documentation.