# Campus Knowledge Copilot — Backend

Python + Flask institutional knowledge RAG backend with SQLite persistence and document processing.

## Features

- **REST API:** Flask with CORS configured for cross-origin frontend communication.
- **Persistent Database:** SQLite (`campus_vault.db`) storing document metadata, raw file binary (`BLOB`), and extracted text chunks.
- **Document Processing:** Page-by-page text extraction for PDF (PyMuPDF) and DOCX (`python-docx`).
- **Grounded Retrieval & QA:** Keyword and token overlap chunk ranking with exact citations (page, section, snippet) and anti-hallucination fallback.
- **REST Endpoints:**
  - `GET  /api/health` — Service health probe
  - `POST /api/chat` & `POST /api/ask` — Question answering with sources & evidence
  - `POST /api/documents/upload` — Upload and index documents
  - `GET  /api/documents` — List indexed documents
  - `DELETE /api/documents/<id>` — Remove document and chunks
  - `GET  /api/source/<id>` — Download original file

## Setup & Running

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server:**
   ```bash
   python app.py
   ```
   Server starts at `http://localhost:5000`.

3. **Upload documents via CLI (optional):**
   ```bash
   python upload_to_db.py "path/to/document.pdf" "Optional Title"
   ```
