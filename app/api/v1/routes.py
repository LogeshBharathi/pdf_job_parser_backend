from fastapi import APIRouter, UploadFile, File, HTTPException
from app.schemas.job import JobSummaryResponse, JobData
from app.services.pdf_parser import JobPDFParser
from datetime import datetime
from typing import Dict, Any, Optional

# Initialize the API router
router = APIRouter()

# Initialize PDF parser
pdf_parser = JobPDFParser()

@router.post("/parse-pdf", response_model=JobSummaryResponse)
async def parse_pdf(file: UploadFile = File(...)):
    """
    Parses an uploaded PDF file and extracts key job information using a generative model.
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file uploaded")
        
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="File size too large (max 10MB)")
        
        job_info_dict = pdf_parser.parse_pdf_with_llm(content)
        
        extraction_summary = {
            "file_name": file.filename,
            "file_size_bytes": len(content),
            "text_length": len(job_info_dict.get('raw_text', '')),
            "extracted_fields": {
                field: bool(value and str(value).strip()) 
                for field, value in job_info_dict.items() 
                if field != 'raw_text'
            },
            "parsing_timestamp": datetime.now().isoformat()
        }
        
        job_data = JobData(**job_info_dict)
        
        return JobSummaryResponse(
            success=True,
            data=job_data,
            extraction_summary=extraction_summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error parsing PDF: {str(e)}"
        return JobSummaryResponse(
            success=False,
            error=error_msg
        )
