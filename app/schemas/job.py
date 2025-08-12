from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class JobData(BaseModel):
    job_title: Optional[str] = Field(None, description="Job title or position name")
    department: Optional[str] = Field(None, description="Department or organization")
    vacancies: Optional[str] = Field(None, description="Number of vacancies")
    eligibility: Optional[str] = Field(None, description="Eligibility criteria")
    salary: Optional[str] = Field(None, description="Salary or pay scale")
    application_deadline: Optional[str] = Field(None, description="Application deadline")
    application_url: Optional[str] = Field(None, description="Application URL or website")
    raw_text: Optional[str] = Field(None, description="Raw extracted text (first 1000 chars)")

class JobSummaryResponse(BaseModel):
    success: bool
    data: Optional[JobData] = None
    error: Optional[str] = None
    extraction_summary: Optional[Dict[str, Any]] = None
    """Summary of the extraction process including file details and extracted fields."""