import pdfplumber
from app.schemas.job import JobData

def extract_job_data_from_pdf(pdf_path: str) -> JobData:
    job_data = {
        "job_title": "Not found",
        "department": "Not found",
        "vacancies": "Not found",
        "eligibility": "Not found",
        "salary": "Not found",
        "application_deadline": "Not found",
        "application_url": "https://indianrailways.gov.in/"
    }

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                # Extract job title
                if "Recruitment of Technician Grade-I Signal" in text:
                    job_data["job_title"] = "Recruitment of Technician Grade-I Signal and various categories of Technician Grade-III"

                # Extract vacancies
                if "Grand Total" in text:
                    lines = text.split('\n')
                    for i, line in enumerate(lines):
                        if "Grand Total" in line:
                            job_data["vacancies"] = lines[i].split()[-1]
                            break

                # Extract application deadline
                if "Closing date for Submission of Online Application" in text:
                    lines = text.split('\n')
                    for line in lines:
                        if "Closing date for Submission of Online Application" in line:
                            job_data["application_deadline"] = line.split("Application")[-1].strip()
                            break

            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and len(row) > 1:
                        # Extract eligibility and salary from tables
                        if row[0] and "EDUCATIONAL QUALIFICATIONS" in row[0]:
                            job_data["eligibility"] = row[1]
                        if row[0] and "Pay Level in 7th CPC" in row[0]:
                            job_data["salary"] = row[1]

    return JobData(**job_data)
