import fitz  # PyMuPDF
import re
import json
import requests
import os
import time
from typing import Dict, Any, Optional, List
from app.schemas.job import JobData
from dotenv import load_dotenv

class JobPDFParser:
    """
    A robust, generic PDF parser for extracting key information from government job notifications.
    This version uses a generative model for more reliable data extraction and has an improved regex fallback.
    """
    def __init__(self):
        load_dotenv()
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.retry_delays = [1, 2, 4, 8, 16] # Exponential backoff delays

    def extract_all_text(self, pdf_content: bytes) -> str:
        """Extract all text from PDF using pymupdf."""
        text = ""
        try:
            with fitz.open(stream=pdf_content, filetype="pdf") as doc:
                for page in doc:
                    text += page.get_text("text") + "\n" # Add a newline between pages
        except Exception as e:
            raise Exception(f"Critical error in PyMuPDF text extraction: {str(e)}")
        return text

    def extract_field(self, text: str, patterns: List[str], group_index: int = 1) -> Optional[str]:
        """A generic function to try a list of regex patterns until a match is found."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return re.sub(r'\s+', ' ', match.group(group_index)).strip()
        return None

    def parse_pdf_with_llm(self, pdf_content: bytes) -> Dict[str, Any]:
        """
        Extracts key job information by sending the raw text to the OpenRouter generative model.
        This is the primary parsing method.
        """
        raw_text = self.extract_all_text(pdf_content)
        truncated_text = raw_text[:25000]

        if not self.openrouter_api_key:
            print("Warning: OpenRouter API key not found. Falling back to regex parser.")
            return self.parse_pdf_with_regex(pdf_content)

        prompt = (
            f"You are an expert data extraction AI. From the following raw text extracted from a government job notification PDF, "
            f"please extract the specified details. The text might be poorly formatted due to the PDF-to-text conversion. "
            f"Your task is to find the relevant information and structure it into a clean JSON object. \n\n"
            f"JSON Keys to extract:\n"
            f"- 'job_title': The official name of the post(s).\n"
            f"- 'department': The name of the ministry or department conducting the recruitment.\n"
            f"- 'vacancies': The total number of vacancies.\n"
            f"- 'eligibility': A combined summary of the required age limits AND educational qualifications. Search for sections like 'Age Limit' and 'Educational Qualifications'.\n"
            f"- 'salary': A summary of the pay scale, including level and initial pay. Actively look for keywords like 'Pay Level', 'Scale of Pay', 'Rs.', or 'Pay Matrix'.\n"
            f"- 'application_deadline': The closing date for applications.\n"
            f"- 'application_url': The official website for applications. Look for text like 'Candidates must apply online through' or website domains ending in '.gov.in' or '.nic.in'.\n\n"
            f"Instructions:\n"
            f"- If a field is genuinely not found after a thorough search, use the string 'Not specified'. Do not use null.\n"
            f"- The output MUST be a valid JSON object, without any other text or explanations. \n\n"
            f"--- PDF TEXT START ---\n{truncated_text}\n--- PDF TEXT END ---"
        )
        
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "openai/gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are an expert at extracting information from job notification PDFs and returning it in a clean JSON format."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"}
        }
        api_url = "https://openrouter.ai/api/v1/chat/completions"

        for delay in self.retry_delays:
            try:
                response = requests.post(api_url, headers=headers, json=payload, timeout=90)
                response.raise_for_status()
                result = response.json()

                if result.get("choices") and result["choices"][0]["message"]["content"]:
                    llm_response_text = result["choices"][0]["message"]["content"]
                    job_info = json.loads(llm_response_text)

                    # --- FIX: Sanitize all values to strings before returning ---
                    sanitized_job_info = {}
                    for key, value in job_info.items():
                        if value is not None:
                            sanitized_job_info[key] = str(value)
                        else:
                            sanitized_job_info[key] = 'Not specified'

                    sanitized_job_info["raw_text"] = raw_text[:1000]
                    return sanitized_job_info
                else:
                    raise ValueError("OpenRouter response did not contain valid content.")
            except (requests.exceptions.RequestException, json.JSONDecodeError, ValueError) as e:
                print(f"API call failed: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
        
        # If all retries fail, fall back to regex
        print("All API retries failed. Falling back to regex parser.")
        return self.parse_pdf_with_regex(pdf_content)

    def parse_pdf_with_regex(self, pdf_content: bytes) -> Dict[str, Any]:
        """
        A fallback regex-based parsing logic with more robust patterns.
        """
        raw_text = self.extract_all_text(pdf_content)
        cleaned_text = re.sub(r' +', ' ', raw_text)
        cleaned_text = re.sub(r'\s*\n\s*', '\n', cleaned_text)
        cleaned_text = cleaned_text.strip()
        
        patterns = {
            'job_title': [r"recruitment for the post of\s*(.+?)(?:\n|$)", r"RECRUITMENT OF (.+?)(?:\n|$)", r"CEN NO\. \d+/\d+ \((.+?)\)"],
            'department': [r"(?i)(government of india|ministry of .+?|department of .+?|railway recruitment board)"],
            'vacancies': [r"total vacancies\s*[:\-]?\s*(\d+)", r"grand total\s*[:\-]?\s*(\d+)"],
            'eligibility': [r"(?is)(?:5.0\s+AGE LIMIT|6.0\s+EDUCATIONAL QUALIFICATIONS)(.+?)(?=\n\d+\.0|\n\n[A-Z])"],
            'salary': [r"(?is)(?:SCALE OF PAY|PAY LEVEL)(.+?)(?=\n\d+\.0|\n\n[A-Z])"],
            'application_deadline': [r"closing date.*?submission of.*?application.*?\n?([^\n]+)"],
            'application_url': [r"apply online through the website\s*([^\s]+)"]
        }
        
        job_info = {
            'job_title': self.extract_field(cleaned_text, patterns['job_title']),
            'department': self.extract_field(cleaned_text, patterns['department']),
            'vacancies': self.extract_field(cleaned_text, patterns['vacancies']),
            'eligibility': self.extract_field(cleaned_text, patterns['eligibility']),
            'salary': self.extract_field(cleaned_text, patterns['salary']),
            'application_deadline': self.extract_field(cleaned_text, patterns['application_deadline']),
            'application_url': self.extract_field(cleaned_text, patterns['application_url']),
        }
        
        final_job_info = {}
        for key, value in job_info.items():
            if value is None:
                final_job_info[key] = 'Not specified'
            else:
                final_job_info[key] = str(value)
        
        final_job_info['raw_text'] = cleaned_text[:1000]
        return final_job_info
