from fastapi import APIRouter, UploadFile
from app.services.pdf_parser import extract_job_data_from_pdf

router = APIRouter()

@router.post("/parse-pdf")
async def parse_pdf(file: UploadFile):
    file_path = f"temp_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    job_data = extract_job_data_from_pdf(file_path)
    return job_data.dict()
