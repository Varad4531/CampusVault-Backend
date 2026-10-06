import os
import uuid
import io
from datetime import datetime
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

from database.database import (
    init_db,
    insert_document,
    insert_chunks,
    get_all_documents,
    get_document_by_id,
    get_all_chunks,
    delete_document as db_delete_document
)
from services.document_processor import extract_text_from_file, chunk_document
from services.retriever import search_chunks

# Load environment variables
load_dotenv()

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def seed_default_knowledge():
    """Seeds baseline institutional knowledge into SQLite if empty."""
    existing = get_all_documents()
    if existing:
        return

    seed_docs = [
        {
            "meta": {
                "id": "doc_exam_rules",
                "title": "Examination Rules & Regulations",
                "type": "PDF",
                "filename": "Examination_Rules.pdf",
                "page_count": 12,
                "chunks_count": 1,
                "uploaded_at": "2026-10-06 09:00",
                "academic_year": "2026-27"
            },
            "chunks": [
                {
                    "chunk_id": "doc_exam_rules_c1",
                    "doc_id": "doc_exam_rules",
                    "doc_title": "Examination Rules & Regulations",
                    "page": 12,
                    "section": "Attendance Requirements",
                    "text": "Students must maintain a minimum attendance of 75% in each course to be eligible to appear for the end-semester examination. In exceptional medical circumstances, condonation up to 10% may be granted by the Dean of Academic Affairs upon submission of verified medical certificates.",
                    "created_at": "2026-10-06"
                }
            ]
        },
        {
            "meta": {
                "id": "doc_acad_calendar",
                "title": "Academic Calendar 2026–27",
                "type": "PDF",
                "filename": "Academic_Calendar_2026_27.pdf",
                "page_count": 4,
                "chunks_count": 1,
                "uploaded_at": "2026-10-06 09:00",
                "academic_year": "2026-27"
            },
            "chunks": [
                {
                    "chunk_id": "doc_acad_calendar_c1",
                    "doc_id": "doc_acad_calendar",
                    "doc_title": "Academic Calendar 2026–27",
                    "page": 3,
                    "section": "Key Examination Dates",
                    "text": "Mid-semester examinations: October 12–18, 2026. End-semester examinations: December 1–15, 2026. Winter vacation commences on December 18, 2026.",
                    "created_at": "2026-10-06"
                }
            ]
        },
        {
            "meta": {
                "id": "doc_hostel_policy",
                "title": "Hostel Code of Conduct",
                "type": "PDF",
                "filename": "Hostel_Policy.pdf",
                "page_count": 8,
                "chunks_count": 1,
                "uploaded_at": "2026-10-06 09:00",
                "academic_year": "2026-27"
            },
            "chunks": [
                {
                    "chunk_id": "doc_hostel_policy_c1",
                    "doc_id": "doc_hostel_policy",
                    "doc_title": "Hostel Code of Conduct",
                    "page": 4,
                    "section": "Curfew and Security Timings",
                    "text": "Hostel gates close strictly at 10:00 PM on weekdays and 10:30 PM on weekends. Late entry requires prior warden approval via the Campus Portal.",
                    "created_at": "2026-10-06"
                }
            ]
        }
    ]

    for item in seed_docs:
        insert_document(item["meta"], file_bytes=None)
        insert_chunks(item["chunks"])


def create_app():
    """Application factory for the Campus Knowledge Copilot Flask backend."""
    app = Flask(__name__)

    # Enable CORS for frontend integration
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "campus-knowledge-vault-secret-key")
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB max upload size

    # Initialize SQLite database and baseline knowledge
    with app.app_context():
        init_db()
        seed_default_knowledge()

    # Health check
    @app.route("/", methods=["GET"])
    @app.route("/api/health", methods=["GET"])
    def health_check():
        docs = get_all_documents()
        chunks = get_all_chunks()
        return jsonify({
            "status": "healthy",
            "service": "Campus Knowledge Copilot API",
            "framework": "Flask",
            "database": "SQLite (database/campus_vault.db)",
            "indexed_documents": len(docs),
            "total_chunks": len(chunks)
        }), 200

    # 1. Document Upload endpoint: POST /api/documents/upload
    @app.route("/api/documents/upload", methods=["POST"])
    def upload_document():
        if "file" not in request.files:
            return jsonify({"error": "No file part in request. Provide a file with key 'file'."}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected."}), 400

        if not allowed_file(file.filename):
            return jsonify({
                "error": f"Invalid file type. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}"
            }), 400

        original_filename = file.filename
        file_bytes = file.read()
        file.seek(0)

        # Save to uploads directory
        safe_name = f"{uuid.uuid4().hex[:6]}_{secure_filename(original_filename)}"
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
        file.save(save_path)

        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        custom_title = request.form.get("title") or original_filename
        ext = original_filename.rsplit(".", 1)[-1].upper() if "." in original_name else "FILE"

        try:
            pages = extract_text_from_file(save_path)
            chunks = chunk_document(doc_id, custom_title, pages)

            doc_meta = {
                "id": doc_id,
                "title": custom_title,
                "type": ext,
                "filename": original_filename,
                "page_count": len(pages),
                "chunks_count": len(chunks),
                "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "academic_year": "2026-27"
            }

            # Persist document metadata and raw file BLOB to SQLite
            insert_document(doc_meta, file_bytes=file_bytes)

            # Persist text chunks to SQLite
            insert_chunks(chunks)

            return jsonify({
                "message": "File uploaded and stored in SQLite database successfully.",
                "document": doc_meta,
                "chunks_indexed": len(chunks)
            }), 201
        except Exception as e:
            return jsonify({"error": f"Failed to process and store document: {str(e)}"}), 500

    # 2. Document List endpoint: GET /api/documents
    @app.route("/api/documents", methods=["GET"])
    def list_documents():
        docs = get_all_documents()
        return jsonify(docs), 200

    # 3. Source / File download endpoint: GET /api/source/<id>
    @app.route("/api/source/<string:doc_id>", methods=["GET"])
    def get_source_file(doc_id):
        doc = get_document_by_id(doc_id)
        if not doc:
            return jsonify({"error": f"Document {doc_id} not found."}), 404

        if doc.get("file_data"):
            return send_file(
                io.BytesIO(doc["file_data"]),
                download_name=doc["filename"],
                as_attachment=True
            )

        return jsonify({
            "id": doc["id"],
            "title": doc["title"],
            "filename": doc["filename"],
            "page_count": doc["page_count"],
            "uploaded_at": doc["uploaded_at"]
        }), 200

    # 4. Delete Document endpoint: DELETE /api/documents/<id>
    @app.route("/api/documents/<string:doc_id>", methods=["DELETE"])
    def delete_document(doc_id):
        success = db_delete_document(doc_id)
        if not success:
            return jsonify({"error": f"Document {doc_id} not found."}), 404

        return jsonify({"message": f"Document {doc_id} deleted successfully from database."}), 200

    # 5. Query / Chat endpoint: POST /api/chat & POST /api/ask
    @app.route("/api/chat", methods=["POST"])
    @app.route("/api/ask", methods=["POST"])
    def chat_endpoint():
        payload = request.get_json(silent=True) or {}
        query = (
            payload.get("query")
            or payload.get("question")
            or payload.get("message")
            or ""
        ).strip()

        if not query:
            return jsonify({"error": "Query or question is required."}), 400

        # Retrieve chunks from SQLite
        all_chunks = get_all_chunks()
        top_chunks = search_chunks(query, all_chunks, top_k=3)

        if top_chunks:
            primary = top_chunks[0]
            answer = f"According to {primary['doc_title']} (Section: {primary['section']}, Page {primary['page']}): {primary['text'][:350]}"

            sources = [
                {
                    "document": c["doc_title"],
                    "document_id": c["doc_id"],
                    "title": c["doc_title"],
                    "page": c["page"],
                    "section": c["section"],
                    "snippet": c["text"]
                }
                for c in top_chunks
            ]

            return jsonify({
                "answer": answer,
                "has_evidence": True,
                "confidence": "high",
                "academic_year": "2026-27",
                "conflict_detected": False,
                "sources": sources,
                "evidence": [c["text"] for c in top_chunks]
            }), 200

        # Grounded fallback when no indexed evidence matches
        return jsonify({
            "answer": "This information is not available in the current institutional knowledge base.",
            "has_evidence": False,
            "confidence": "low",
            "sources": [],
            "evidence": [],
            "academic_year": None,
            "conflict_detected": False
        }), 200

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)
