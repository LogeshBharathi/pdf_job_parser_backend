from fastapi import FastAPI
from app.api.v1.routes import router
from datetime import datetime

# Initialize the FastAPI application
app = FastAPI(
    title="Job Notification PDF Summarizer",
    description="FastAPI backend to extract and summarize key information from government job notification PDFs",
    version="1.0.0"
)

# Include the router for version 1 of the API
app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    """Returns a welcome message and API details."""
    return {
        "message": "Job Notification PDF Summarizer API",
        "version": "1.0.0",
        "status": "active",
        "endpoints": {
            "/api/v1/parse-pdf": "POST - Upload and parse a PDF file",
        },
        "features": [
            "PDF text extraction using PyMuPDF",
            "Generative model-based parsing for job details",
            "Structured JSON output"
        ]
    }
