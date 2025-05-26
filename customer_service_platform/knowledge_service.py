import boto3
import json
import os
import datetime

# Initialize clients
opensearch_client = boto3.client('opensearch')
s3_client = boto3.client('s3')
bedrock_client = boto3.client('bedrock-runtime')

# Configuration
OPENSEARCH_DOMAIN = os.environ.get('OPENSEARCH_DOMAIN', 'your-opensearch-domain')
KNOWLEDGE_BUCKET = os.environ.get('KNOWLEDGE_BUCKET', 'your-s3-bucket')
KNOWLEDGE_INDEX = os.environ.get('KNOWLEDGE_INDEX', 'knowledge_base')

def search_knowledge_base(query, max_results=5):
    """
    Search the knowledge base for relevant documents
    """
    try:
        # Construct the OpenSearch query
        search_query = {
            "size": max_results,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^2", "content", "keywords^1.5"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "highlight": {
                "fields": {
                    "content": {},
                    "title": {}
                }
            }
        }
        
        # Make the search request
        response = opensearch_client.search(
            Body=json.dumps(search_query),
            Index=KNOWLEDGE_INDEX
        )
        
        # Format the results
        results = []
        if 'hits' in response and 'hits' in response['hits']:
            for hit in response['hits']['hits']:
                result = {
                    'id': hit['_id'],
                    'title': hit['_source'].get('title', 'Untitled'),
                    'score': hit['_score'],
                    'content': hit['_source'].get('content', '')[:300] + '...' if len(hit['_source'].get('content', '')) > 300 else hit['_source'].get('content', ''),
                    'url': hit['_source'].get('url', '')
                }
                
                # Add highlights if available
                if 'highlight' in hit:
                    result['highlights'] = hit['highlight']
                
                results.append(result)
        
        return results
    
    except Exception as e:
        print(f"Error searching knowledge base: {str(e)}")
        return []

def get_article(article_id):
    """
    Retrieve a full knowledge base article by ID
    """
    try:
        response = opensearch_client.get(
            Index=KNOWLEDGE_INDEX,
            Id=article_id
        )
        
        if '_source' in response:
            return response['_source']
        else:
            return None
    
    except Exception as e:
        print(f"Error retrieving article {article_id}: {str(e)}")
        return None

def add_article(title, content, category, tags=None):
    """
    Add a new article to the knowledge base
    """
    if tags is None:
        tags = []
    
    try:
        # Create document in OpenSearch
        document = {
            'title': title,
            'content': content,
            'category': category,
            'tags': tags,
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        # Generate a document ID
        doc_id = f"{category}-{title.lower().replace(' ', '-')}-{int(datetime.datetime.now().timestamp())}"
        
        # Index the document
        response = opensearch_client.index(
            Index=KNOWLEDGE_INDEX,
            Id=doc_id,
            Body=json.dumps(document)
        )
        
        # Also store a copy in S3 for backup/archiving
        s3_client.put_object(
            Bucket=KNOWLEDGE_BUCKET,
            Key=f"articles/{category}/{doc_id}.json",
            Body=json.dumps(document),
            ContentType='application/json'
        )
        
        return {
            'id': doc_id,
            'status': 'success',
            'message': 'Article added successfully'
        }
    
    except Exception as e:
        print(f"Error adding article: {str(e)}")
        return {
            'status': 'error',
            'message': f"Failed to add article: {str(e)}"
        }

def update_article(article_id, updates):
    """
    Update an existing article in the knowledge base
    """
    try:
        # First get the current article
        current_article = get_article(article_id)
        
        if not current_article:
            return {
                'status': 'error',
                'message': f"Article with ID {article_id} not found"
            }
        
        # Update the fields
        for key, value in updates.items():
            current_article[key] = value
        
        # Update the 'updated_at' timestamp
        current_article['updated_at'] = datetime.datetime.now().isoformat()
        
        # Update the document in OpenSearch
        response = opensearch_client.index(
            Index=KNOWLEDGE_INDEX,
            Id=article_id,
            Body=json.dumps(current_article)
        )
        
        # Also update the copy in S3
        category = current_article.get('category', 'uncategorized')
        s3_client.put_object(
            Bucket=KNOWLEDGE_BUCKET,
            Key=f"articles/{category}/{article_id}.json",
            Body=json.dumps(current_article),
            ContentType='application/json'
        )
        
        return {
            'id': article_id,
            'status': 'success',
            'message': 'Article updated successfully'
        }
    
    except Exception as e:
        print(f"Error updating article: {str(e)}")
        return {
            'status': 'error',
            'message': f"Failed to update article: {str(e)}"
        }

def delete_article(article_id):
    """
    Delete an article from the knowledge base
    """
    try:
        # Get the article first to know its category for S3 deletion
        article = get_article(article_id)
        
        if not article:
            return {
                'status': 'error',
                'message': f"Article with ID {article_id} not found"
            }
        
        # Delete from OpenSearch
        response = opensearch_client.delete(
            Index=KNOWLEDGE_INDEX,
            Id=article_id
        )
        
        # Delete from S3
        category = article.get('category', 'uncategorized')
        s3_client.delete_object(
            Bucket=KNOWLEDGE_BUCKET,
            Key=f"articles/{category}/{article_id}.json"
        )
        
        return {
            'status': 'success',
            'message': f"Article {article_id} deleted successfully"
        }
    
    except Exception as e:
        print(f"Error deleting article: {str(e)}")
        return {
            'status': 'error',
            'message': f"Failed to delete article: {str(e)}"
        }

def get_suggested_answers(question, max_results=3):
    """
    Get suggested answers for a customer question
    """
    # First, search the knowledge base
    kb_results = search_knowledge_base(question, max_results=5)
    
    if not kb_results:
        return []
    
    # Combine the most relevant knowledge base results
    context = "\n\n".join([
        f"Title: {result['title']}\nContent: {result['content']}"
        for result in kb_results[:3]
    ])
    
    # Use Bedrock to generate a suggested answer
    try:
        prompt = f"""
        Customer Question: {question}
        
        Knowledge Base Information:
        {context}
        
        Based on the above information, provide a concise, accurate answer to the customer's question.
        If the information is not sufficient to answer the question, say so and suggest what additional information would be needed.
        
        Answer:
        """
        
        payload = {
            "prompt": prompt,
            "max_tokens_to_sample": 300,
            "temperature": 0.1,
            "top_p": 0.9,
        }
        
        response = bedrock_client.invoke_model(
            modelId="amazon.bedrock-nova-12b",
            body=json.dumps(payload)
        )
        
        response_body = json.loads(response['body'].read().decode())
        suggested_answer = response_body.get('completion', '').strip()
        
        # Return the suggested answer along with the source references
        return {
            'answer': suggested_answer,
            'sources': [
                {
                    'id': result['id'],
                    'title': result['title'],
                    'url': result.get('url', '')
                }
                for result in kb_results[:3]
            ]
        }
    
    except Exception as e:
        print(f"Error generating suggested answer: {str(e)}")
        # Fall back to just returning the knowledge base results
        return {
            'answer': "Based on our knowledge base, you might find the following articles helpful.",
            'sources': [
                {
                    'id': result['id'],
                    'title': result['title'],
                    'url': result.get('url', '')
                }
                for result in kb_results[:3]
            ]
        }