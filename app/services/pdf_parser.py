import pdfplumber
from app.schemas.job import JobData

def extract_job_data_from_pdf(pdf_path: str) -> JobData:
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(
            page.extract_text() for page in pdf.pages if page.extract_text()
        )

    # TODO: Implement actual parsing logic here
    return JobData(
        job_title="Not found",
        department="Not found",
        vacancies="Not found",
        eligibility="Not found",
        salary="Not found",
        application_deadline="Not found",
        application_url="Not found"
    )
