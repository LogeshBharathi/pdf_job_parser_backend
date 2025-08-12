# Job Notification PDF Parser Backend

This project is a robust FastAPI backend designed to intelligently extract and summarize key information from government job notification PDFs. It uses a hybrid parsing approach, combining the power of a generative AI model (OpenRouter) for dynamic content extraction with a regex-based parser as a reliable fallback.

The application converts unstructured PDF data into a clean, structured JSON format, making it easy to integrate with a front-end application or other services.

## ✨ Features

- **Hybrid AI & Regex Parsing**: Utilizes the OpenRouter API for intelligent, context-aware data extraction from complex documents. A robust regex-based parser serves as a reliable fallback.
- **Dynamic PDF Handling**: Extracts text from PDFs of varying layouts and structures using PyMuPDF.
- **Structured JSON Output**: Converts raw job notification text into a predictable JSON object containing fields like job title, salary, and eligibility.
- **Efficient & Secure**: The API key is managed via environment variables (.env file) for security, and the processing handles file uploads efficiently without saving them to disk.
- **FastAPI Backend**: Built on a modern, high-performance Python web framework.

## 🚀 API Endpoints

The API provides a single primary endpoint for parsing PDFs.

| Method | Endpoint            | Description                                             |
| ------ | ------------------- | ------------------------------------------------------- |
| POST   | `/api/v1/parse-pdf` | Upload a PDF file to extract and summarize job details. |

### Request Body

This endpoint expects a multipart/form-data request with a single field:

- `file`: The PDF file to be parsed.

### Example Response

A successful response will return a JSON object with the extracted job data:

```json
{
  "success": true,
  "data": {
    "job_title": "Technician Grade-I Signal and various categories of Technician Grade-III",
    "department": "Indian Railways",
    "vacancies": "6238",
    "eligibility": "Age: 18-33 for Gr-I Signal, 18-30 for Gr-III. Qualifications vary by trade.",
    "salary": "Level-5 (₹29,200) for Gr-I, Level-2 (₹19,900) for Gr-III",
    "application_deadline": "07-08-2025",
    "application_url": "https://www.rrbcdg.gov.in/",
    "raw_text": "CEN NO. 02/2025 (TECHNICIAN CATEGORIES)\n..."
  },
  "error": null,
  "extraction_summary": {
    "file_name": "job_notification.pdf",
    "file_size_bytes": 5964492,
    "text_length": 1000,
    "extracted_fields": {
      "job_title": true,
      "department": true,
      "vacancies": true,
      "eligibility": true,
      "salary": true,
      "application_deadline": true,
      "application_url": true
    },
    "parsing_timestamp": "2025-08-12T13:39:17.504028"
  }
}
```


## ⚙️ Setup and Installation

Follow these steps to get a local copy of the project up and running.

### Prerequisites

- Python 3.11 or later
- Poetry (for dependency management)

### Steps

1. Clone the repository:

   ```bash
   git clone https://github.com/LogeshBharathi/pdf_job_parser_backend
   cd pdf_job_parser_backend
   ```

2. Install dependencies using Poetry:

   ```bash
   poetry install
   ```

3. Configure environment variables:
   Create a `.env` file in the root directory of your project. This is where you'll store your API key.

   ```env
   # .env
   OPENROUTER_API_KEY="your_api_key_here"
   ```

   Note: Replace "your_api_key_here" with your actual key from the OpenRouter dashboard.

4. Run the FastAPI server:
   The server will run with automatic reloading for development.
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

Your API will be available at http://127.0.0.1:8000. You can access the interactive documentation at http://127.0.0.1:8000/docs.

## ☁️ Deployment on Render

This project is configured for easy deployment on Render using a `render.yaml` file.

### Deployment Instructions

1. Push your code (including `pyproject.toml`, `requirements.txt`, and the updated `app` directory) to a Git repository.
2. In the Render dashboard, create a new Web Service.
3. Connect it to your repository.
4. Render will automatically detect the `pyproject.toml` file and use Poetry for dependency management.
5. In the service settings, set the Start Command to:
   ```bash
   poetry run uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
6. Add `OPENROUTER_API_KEY` as a secret environment variable in your service settings.
