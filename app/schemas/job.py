from pydantic import BaseModel

class JobData(BaseModel):
    job_title: str
    department: str
    vacancies: str
    eligibility: str
    salary: str
    application_deadline: str
    application_url: str

