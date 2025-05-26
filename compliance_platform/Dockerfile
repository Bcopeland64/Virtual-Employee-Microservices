FROM python:3.11-slim

WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    REGULATION_BUCKET=ai-compliance-regulation-storage \
    COMPLIANCE_KNOWLEDGE_INDEX=compliance-knowledge-index

# Expose the service port
EXPOSE 8080

# Command to run the application
CMD ["python", "app.py"]