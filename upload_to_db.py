"""
Utility script to directly insert PDF / DOCX / TXT files into the SQLite database.

Usage:
    python upload_to_db.py "path/to/your_document.pdf"
    python upload_to_db.py "path/to/your_document.pdf" "Custom Document Title"
"""

import sys
import os
import uuid
from datetime import datetime

from database.database import init_db, insert_document, insert_chunks, get_all_documents
from services.document_processor import extract_text_from_file, chunk_document


def upload_file_to_database(file_path: str, custom_title: str = None):
    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}")
        return False

    filename = os.path.basename(file_path)
    title = custom_title or os.path.splitext(filename)[0].replace("_", " ").title()
    ext = filename.rsplit(".", 1)[-1].upper() if "." in filename else "FILE"

    print(f"Reading file: {filename}...")
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    print("Extracting pages and text...")
    pages = extract_text_from_file(file_path)
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"

    print(f"Extracted {len(pages)} page(s). Chunking text...")
    chunks = chunk_document(doc_id, title, pages)

    doc_meta = {
        "id": doc_id,
        "title": title,
        "type": ext,
        "filename": filename,
        "page_count": len(pages),
        "chunks_count": len(chunks),
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "academic_year": "2026-27"
    }

    # Make sure DB schema exists
    init_db()

    # Insert raw file binary and metadata into SQLite
    print("Saving file binary and metadata into SQLite 'documents' table...")
    insert_document(doc_meta, file_bytes=file_bytes)

    # Insert chunks into SQLite
    print(f"Saving {len(chunks)} search chunks into SQLite 'document_chunks' table...")
    insert_chunks(chunks)

    print("\n[SUCCESS] Document stored in SQLite database!")
    print(f" - Document ID: {doc_id}")
    print(f" - Title:       {title}")
    print(f" - Format:      {ext}")
    print(f" - Pages:       {len(pages)}")
    print(f" - Chunks:      {len(chunks)}")
    print(f" - DB Location: database/campus_vault.db")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_to_db.py <path_to_file> [optional_title]")
        print("Example: python upload_to_db.py Examination_Rules.pdf \"Exam Rules 2026\"")
        sys.exit(1)

    path = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else None
    upload_file_to_database(path, title)
