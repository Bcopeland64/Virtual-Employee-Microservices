from flask import Flask, request, jsonify
import os
import logging
from f_analyze_sales_data import analyze_sales_data
from f_marketing_plan import generate_marketing_plan
from f_report_generator import generate_report
from f_task_processor import process_task

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for load balancer"""
    return jsonify({"status": "healthy"}), 200

@app.route('/sales-analysis/analyze', methods=['POST'])
def sales_analysis():
    """Analyze sales data"""
    try:
        data = request.json
        logger.info(f"Received sales analysis request: {data}")
        result = analyze_sales_data(
            data.get('data_source'),
            data.get('time_period'),
            data.get('metrics', []),
            data.get('filters', {})
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error in sales analysis: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/marketing-plan/generate', methods=['POST'])
def marketing_plan():
    """Generate marketing plan"""
    try:
        data = request.json
        logger.info(f"Received marketing plan request: {data}")
        result = generate_marketing_plan(
            data.get('target_audience'),
            data.get('objectives', []),
            data.get('budget'),
            data.get('timeline')
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error in marketing plan generation: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/reports/generate', methods=['POST'])
def report_generation():
    """Generate report"""
    try:
        data = request.json
        logger.info(f"Received report generation request: {data}")
        result = generate_report(
            data.get('report_type'),
            data.get('time_period'),
            data.get('format', 'pdf'),
            data.get('recipients', [])
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error in report generation: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/tasks/process', methods=['POST'])
def task_processing():
    """Process sales task"""
    try:
        data = request.json
        logger.info(f"Received task processing request: {data}")
        result = process_task(
            data.get('task_type'),
            data.get('task_data', {}),
            data.get('priority', 'medium'),
            data.get('deadline')
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error in task processing: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)