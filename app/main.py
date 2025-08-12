from fastapi import FastAPI
from app.api.v1.routes import router
from fastapi.openapi.docs import get_swagger_ui_html
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

# Create the app without the default Swagger/Redoc
app = FastAPI(
    docs_url=None,
    redoc_url=None,
    title="Job Notification PDF Summarizer API",
    description="Extract job details from PDF notifications using AI-powered parsing.",
    version="1.0.0"
)

# Custom Swagger UI with dark theme and branding
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="📄 Job Parser API Docs",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,  # hide schemas by default
            "defaultModelRendering": "model",  # render as model first
            "docExpansion": "none",  # collapse endpoints by default
            "syntaxHighlight.theme": "monokai",  # dark syntax highlight
            "persistAuthorization": True  # keep auth token between refresh
        }
    )

# API v1 routes
app.include_router(router, prefix="/api/v1")

# Root endpoint
@app.get("/")
async def root():
    """Returns a welcome message and API details."""
    return {
        "message": "Job Notification PDF Summarizer API",
        "version": "1.0.0",
        "status": "active",
        "last_updated": datetime.now().isoformat(),
        "endpoints": {
            "/api/v1/parse-pdf": "POST - Upload and parse a PDF file",
            "/docs": "Swagger UI - API Documentation",
            "/redoc": "ReDoc - Alternative API Documentation"
        },
        "features": [
            "PDF text extraction using PyMuPDF",
            "Generative model-based parsing for job details",
            "Structured JSON output"
        ]
    }
