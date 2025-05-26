import os
import logging
import json
import uvicorn
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import platform components
from compliance_platform.integration import (
    RegulatoryIntelligence,
    WebScraping,
    ComplianceAnalysis,
    EthicsAssessment,
    PolicyManagement,
    ReportingDashboard
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("compliance_platform_api")

# Initialize FastAPI app
app = FastAPI(
    title="AI Ethics & Compliance Platform API",
    description="API for interacting with the AI Ethics & Compliance Platform",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize platform components
regulatory_intelligence = RegulatoryIntelligence()
web_scraping = WebScraping()
compliance_analysis = ComplianceAnalysis()
ethics_assessment = EthicsAssessment()
policy_management = PolicyManagement()
reporting_dashboard = ReportingDashboard()

# Define API routes

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AI Ethics & Compliance Platform"}

# Regulatory Intelligence endpoints
@app.get("/api/v1/regulations")
async def get_regulations(country: Optional[str] = None, domain: Optional[str] = None):
    result = regulatory_intelligence.get_regulations(country=country, domain=domain)
    if result["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.get("/api/v1/regulations/updates")
async def get_regulatory_updates(since: Optional[str] = None):
    result = regulatory_intelligence.get_regulatory_updates(since=since)
    if result["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.get("/api/v1/regulations/{regulation_id}")
async def get_regulation_details(regulation_id: str):
    result = regulatory_intelligence.get_regulation_details(regulation_id)
    if result["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

# Web Scraping & Monitoring endpoints
@app.post("/api/v1/crawl/schedule")
async def schedule_crawl(data: Dict[str, Any] = None):
    if data is None:
        data = {}
    result = web_scraping.schedule_crawl(
        sources=data.get("sources"),
        frequency=data.get("frequency")
    )
    if result["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.get("/api/v1/crawl/status/{job_id}")
async def get_crawl_status(job_id: str):
    result = web_scraping.get_crawl_status(job_id)
    if result["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.post("/api/v1/crawl/source")
async def add_source(data: Dict[str, Any]):
    result = web_scraping.add_source(
        url=data.get("url"),
        source_type=data.get("source_type"),
        crawl_frequency=data.get("crawl_frequency")
    )
    if result["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

# Compliance Analysis endpoints
@app.post("/api/v1/compliance/analyze")
async def analyze_document(document: UploadFile = File(...)):
    document_data = await document.read()
    result = compliance_analysis.analyze_document(
        document_data=document_data,
        document_name=document.filename
    )
    if result["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.post("/api/v1/compliance/gap-analysis")
async def gap_analysis(data: Dict[str, Any]):
    result = compliance_analysis.gap_analysis(
        policies=data.get("policies"),
        domain=data.get("domain"),
        regulation=data.get("regulation")
    )
    if result["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.get("/api/v1/compliance/requirements")
async def get_compliance_requirements(domain: str):
    result = compliance_analysis.get_compliance_requirements(domain=domain)
    if result["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

# Ethics Assessment endpoints
@app.post("/api/v1/ethics/assess")
async def assess_ai_system(data: Dict[str, Any]):
    result = ethics_assessment.assess_ai_system(
        system_description=data.get("system_description"),
        framework=data.get("framework")
    )
    if result["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.get("/api/v1/ethics/frameworks")
async def get_frameworks():
    result = ethics_assessment.get_frameworks()
    if result["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.post("/api/v1/ethics/bias-check")
async def check_bias(data: Dict[str, Any]):
    result = ethics_assessment.check_bias(
        model_data=data.get("model_data"),
        dataset=data.get("dataset")
    )
    if result["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

# Policy Management endpoints
@app.post("/api/v1/policies")
async def create_policy(data: Dict[str, Any]):
    result = policy_management.create_policy(policy_data=data)
    if result["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.put("/api/v1/policies/{policy_id}")
async def update_policy(policy_id: str, data: Dict[str, Any]):
    result = policy_management.update_policy(policy_id=policy_id, policy_data=data)
    if result["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.get("/api/v1/policies")
async def get_policies(category: Optional[str] = None, status: Optional[str] = None):
    result = policy_management.get_policies(category=category, status=status)
    if result["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.post("/api/v1/policies/validate")
async def validate_policy(data: Dict[str, Any]):
    result = policy_management.validate_policy(
        policy_data=data.get("policy_data"),
        regulations=data.get("regulations")
    )
    if result["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

# Reporting & Dashboard endpoints
@app.post("/api/v1/reports/generate")
async def generate_report(data: Dict[str, Any]):
    result = reporting_dashboard.generate_report(
        report_type=data.get("report_type"),
        parameters=data.get("parameters")
    )
    if result["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.get("/api/v1/reports")
async def get_reports(
    report_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    result = reporting_dashboard.get_reports(
        report_type=report_type,
        start_date=start_date,
        end_date=end_date
    )
    if result["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.get("/api/v1/dashboards")
async def get_dashboard_data(dashboard_type: str = "compliance_overview"):
    result = reporting_dashboard.get_dashboard_data(dashboard_type=dashboard_type)
    if result["status"] == "ERROR":
        raise HTTPException(status_code=500, detail=result["error"])
    return result

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "ERROR", "error": str(exc)}
    )

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    
    logger.info(f"Starting AI Ethics & Compliance Platform API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)