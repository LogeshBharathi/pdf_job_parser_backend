import fitz  # PyMuPDF
import re
import json
import requests
import os
from typing import Dict, Any, Optional, List
from app.schemas.job import JobData

class JobPDFParser:
    """
    A robust, generic PDF parser for extracting key information from government job notifications.
    This version uses a generative model for more reliable data extraction and has an improved regex fallback.
    """
    def __init__(self):
        # It's recommended to use environment variables for API keys for better security.
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "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")

    def extract_all_text(self, pdf_content: bytes) -> str:
        """Extract all text from PDF using pymupdf."""
        text = ""
        try:
            # Open the PDF from the byte stream
            with fitz.open(stream=pdf_content, filetype="pdf") as doc:
                # Iterate through each page and extract text
                for page in doc:
                    text += page.get_text("text") + "\n" # Add a newline between pages
        except Exception as e:
            # Raise a more informative exception
            raise Exception(f"Critical error in PyMuPDF text extraction: {str(e)}")
        return text

    def extract_field(self, text: str, patterns: List[str], group_index: int = 1) -> Optional[str]:
        """A generic function to try a list of regex patterns until a match is found."""
        for pattern in patterns:
            # Search for the pattern, ignoring case and allowing '.' to match newlines
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                # Return the cleaned-up matched group
                return re.sub(r'\s+', ' ', match.group(group_index)).strip()
        return None

    def parse_pdf_with_llm(self, pdf_content: bytes) -> Dict[str, Any]:
        """
        Extracts key job information by sending the raw text to a generative model.
        This is the primary parsing method.
        """
        raw_text = self.extract_all_text(pdf_content)

        if not self.openrouter_api_key:
            print("Warning: OpenRouter API key not found. Falling back to regex parser.")
            return self.parse_pdf_with_regex(pdf_content)

        # A more directive and robust prompt for the generative model
        prompt = (
            "You are an expert data extraction AI. From the following raw text extracted from a government job notification PDF, "
            "please extract the specified details. The text might be poorly formatted due to the PDF-to-text conversion. "
            "Your task is to find the relevant information and structure it into a clean JSON object. \n\n"
            "JSON Keys to extract:\n"
            "- 'job_title': The official name of the post(s).\n"
            "- 'department': The name of the ministry or department conducting the recruitment.\n"
            "- 'vacancies': The total number of vacancies.\n"
            "- 'eligibility': A combined summary of the required age limits AND educational qualifications. Search for sections like 'Age Limit' and 'Educational Qualifications'.\n"
            "- 'salary': A summary of the pay scale, including level and initial pay. Actively look for keywords like 'Pay Level', 'Scale of Pay', 'Rs.', or 'Pay Matrix'.\n"
            "- 'application_deadline': The closing date for applications.\n"
            "- 'application_url': The official website for applications. Look for text like 'Candidates must apply online through' or website domains ending in '.gov.in' or '.nic.in'.\n\n"
            "Instructions:\n"
            "- If a field is genuinely not found after a thorough search, use the string 'Not specified'. Do not use null.\n"
            "- Combine related information into a single string for 'eligibility' and 'salary'.\n"
            "- The output MUST be only the JSON object, without any other text or explanations.\n\n"
            f"--- PDF TEXT START ---\n{raw_text[:25000]}\n--- PDF TEXT END ---" # Increased context length
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
            "response_format": {"type": "json_object"} # Request JSON output directly
        }
        api_url = "https://openrouter.ai/api/v1/chat/completions"

        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=90) # Increased timeout
            response.raise_for_status()
            result = response.json()

            if result.get("choices") and result["choices"][0]["message"]["content"]:
                llm_response_text = result["choices"][0]["message"]["content"]
                job_info = json.loads(llm_response_text)

                # --- FIX: Convert all values to strings to prevent Pydantic validation errors ---
                sanitized_job_info = {}
                for key, value in job_info.items():
                    if value is not None:
                        sanitized_job_info[key] = str(value)
                    else:
                        sanitized_job_info[key] = 'Not specified'
                
                sanitized_job_info["raw_text"] = raw_text[:1000] # For summary purposes
                return sanitized_job_info
            else:
                raise ValueError("LLM response did not contain valid content.")

        except Exception as e:
            print(f"LLM extraction failed: {e}. Falling back to regex parser.")
            return self.parse_pdf_with_regex(pdf_content)

    def parse_pdf_with_regex(self, pdf_content: bytes) -> Dict[str, Any]:
        """
        A fallback regex-based parsing logic with more robust patterns.
        """
        raw_text = self.extract_all_text(pdf_content)
        # Perform basic text cleaning
        cleaned_text = re.sub(r' +', ' ', raw_text)
        cleaned_text = re.sub(r'\s*\n\s*', '\n', cleaned_text)
        cleaned_text = cleaned_text.strip()
        
        # More flexible and comprehensive regex patterns
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
        
        # Ensure all values are strings and handle None cases for consistency
        final_job_info = {}
        for key, value in job_info.items():
            if value is None:
                final_job_info[key] = 'Not specified'
            else:
                final_job_info[key] = str(value) # Convert to string
        
        final_job_info['raw_text'] = cleaned_text[:1000]
                
        return final_job_info

def extract_job_data_from_pdf(pdf_content: bytes) -> JobData:
    """
    High-level function to orchestrate PDF parsing and data validation.
    """
    parser = JobPDFParser()
    job_info_dict = parser.parse_pdf_with_llm(pdf_content)
    return JobData(**job_info_dict)
