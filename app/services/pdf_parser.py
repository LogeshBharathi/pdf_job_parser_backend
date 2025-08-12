import fitz  # PyMuPDF
import re
import json
import os
import time
import google.generativeai as genai
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Note: The original code had an import 'from app.schemas.job import JobData'
# which is not used in the class. It can be removed if not needed elsewhere.

class JobPDFParser:
    """
    A robust, generic PDF parser for extracting key information from job notifications.
    This version uses Gemini 1.5 Flash in JSON mode for reliable data extraction
    and includes a regex fallback.
    """
    def __init__(self):
        load_dotenv()
        # Ensure your .env file has: GEMINI_API_KEY="your_actual_api_key"
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.retry_delays = [1, 2, 4, 8, 16] # Exponential backoff delays

        # Configure Gemini API
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    def extract_all_text(self, pdf_content: bytes) -> str:
        """Extract all text from PDF using PyMuPDF."""
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
        Extracts key job information using the Gemini model with guaranteed JSON output.
        This is the primary and most reliable parsing method.
        """
        if not self.model:
            print("Warning: Gemini API key not found or model not initialized. Falling back to regex parser.")
            return self.parse_pdf_with_regex(pdf_content)

        raw_text = self.extract_all_text(pdf_content)
        # Truncate text to avoid exceeding model token limits for very large PDFs
        truncated_text = raw_text[:30000]

        prompt = (
            f"You are an expert data extraction AI. From the following raw text extracted from a government job notification PDF, "
            f"please extract the specified details. The text might be poorly formatted due to the PDF-to-text conversion. "
            f"Your task is to find the relevant information and structure it into a clean JSON object. \n\n"
            f"JSON Keys to extract:\n"
            f"- 'job_title': The official name of the post(s).\n"
            f"- 'department': The name of the ministry or department conducting the recruitment.\n"
            f"- 'vacancies': The total number of vacancies. Extract a number if possible.\n"
            f"- 'eligibility': A combined summary of the required age limits AND educational qualifications. Search for sections like 'Age Limit' and 'Educational Qualifications'.\n"
            f"- 'salary': A summary of the pay scale, including level and initial pay. Actively look for keywords like 'Pay Level', 'Scale of Pay', 'Rs.', or 'Pay Matrix'.\n"
            f"- 'application_deadline': The closing date for applications. Format as YYYY-MM-DD if possible, otherwise keep the original text.\n"
            f"- 'application_url': The official website for applications. Look for text like 'Candidates must apply online through' or website domains ending in '.gov.in' or '.nic.in'.\n\n"
            f"Instructions:\n"
            f"- If a field is genuinely not found after a thorough search, use the string 'Not specified'.\n"
            f"- The output MUST be a valid JSON object. Do not output any other text or explanations.\n\n"
            f"--- PDF TEXT START ---\n{truncated_text}\n--- PDF TEXT END ---"
        )

        # Configure the model to output JSON directly
        generation_config = genai.types.GenerationConfig(
            response_mime_type="application/json"
        )

        for delay in self.retry_delays:
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=generation_config
                )

                # Check if the response was blocked by safety filters
                if not response.parts:
                    block_reason = response.prompt_feedback.block_reason
                    print(f"API call blocked due to: {block_reason}. This is a permanent failure for this prompt.")
                    break # No point in retrying if blocked

                # The model's response text is already a JSON string
                job_info = json.loads(response.text)

                # Sanitize all values to strings before returning
                sanitized_job_info = {k: str(v) if v is not None else 'Not specified' for k, v in job_info.items()}
                sanitized_job_info["raw_text"] = raw_text[:1000] # Include a snippet for reference
                return sanitized_job_info

            except json.JSONDecodeError as e:
                print(f"API call failed (JSONDecodeError): {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
            except Exception as e:
                print(f"An unexpected API error occurred: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)

        # If all retries fail or the prompt was blocked, fall back to regex
        print("All API retries failed. Falling back to regex parser.")
        return self.parse_pdf_with_regex(pdf_content)

    def parse_pdf_with_regex(self, pdf_content: bytes) -> Dict[str, Any]:
        """
        A fallback regex-based parsing logic. Used if the LLM fails.
        """
        raw_text = self.extract_all_text(pdf_content)
        # Basic text cleaning for better regex matching
        cleaned_text = re.sub(r'\s*\n\s*', '\n', raw_text.strip())
        cleaned_text = re.sub(r' +', ' ', cleaned_text)

        patterns = {
            'job_title': [r"recruitment for the post of\s*(.+?)(?:\n|$)", r"RECRUITMENT OF (.+?)(?:\n|$)", r"CEN NO\. \d+/\d+ \((.+?)\)"],
            'department': [r"(?i)(government of india|ministry of .+?|department of .+?|railway recruitment board)"],
            'vacancies': [r"total vacancies\s*[:\-]?\s*(\d+)", r"grand total\s*[:\-]?\s*(\d+)"],
            'eligibility': [r"(?is)(?:5.0\s+AGE LIMIT|6.0\s+EDUCATIONAL QUALIFICATIONS|essential qualifications)(.+?)(?=\n\d+\.0|\n\n[A-Z])"],
            'salary': [r"(?is)(?:SCALE OF PAY|PAY LEVEL|PAY MATRIX)(.+?)(?=\n\d+\.0|\n\n[A-Z])"],
            'application_deadline': [r"closing date.*?submission of.*?application.*?\n?([^\n]+)"],
            'application_url': [r"apply online through the website\s*([^\s]+)"]
        }

        job_info = {
            key: self.extract_field(cleaned_text, pat)
            for key, pat in patterns.items()
        }

        # Ensure all values are strings and replace None with 'Not specified'
        final_job_info = {
            key: str(value) if value is not None else 'Not specified'
            for key, value in job_info.items()
        }

        final_job_info['raw_text'] = cleaned_text[:1000]
        return final_job_info