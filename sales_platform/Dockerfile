FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY f_analyze_sales_data.py .
COPY f_marketing_plan.py .
COPY f_report_generator.py .
COPY f_task_processor.py .
COPY lambda_handler.py .
COPY app.py .

# Expose port
EXPOSE 8080

# Run application
CMD ["python", "app.py"]