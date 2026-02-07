import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

APP_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(APP_DIR, "data")
PDF_PATH = os.path.join(DATA_DIR, "EEBC 2021.pdf")
FAISS_PATH = os.path.join(DATA_DIR, "index.faiss")
CHUNKS_PATH = os.path.join(DATA_DIR, "chunks.json")
XLSX_PATH = os.path.join(DATA_DIR, "application-and-compliance-forms-for-energy-efficiency-building-code.xlsx")

# Allow overriding paths via environment variables
FAISS_PATH = os.getenv("FAISS_PATH", FAISS_PATH)
CHUNKS_PATH = os.getenv("CHUNKS_PATH", CHUNKS_PATH)
SKIP_INDEX_BUILD = os.getenv("SKIP_INDEX_BUILD", "false").lower() in ("1", "true", "yes")

_store = None
_pipeline = None

_store = None

def get_store():
    """Lazy-load vector store and FAISS index on first use"""
    global _store
    if _store is not None:
        return _store

    print(">>> Initializing vector store...")
    from rag.index import VectorStore
    _store = VectorStore()

    # Load existing FAISS index and chunks if available
    if os.path.exists(FAISS_PATH) and os.path.exists(CHUNKS_PATH):
        print(">>> Loading FAISS index from disk...")
        _store.load(FAISS_PATH, CHUNKS_PATH)
        print(">>> FAISS index loaded successfully.")
    else:
        if not SKIP_INDEX_BUILD:
            print(">>> Building FAISS index from PDF (this may take a minute)...")
            from rag.ingest import extract_pages, split_into_chunks
            pages = extract_pages(PDF_PATH)
            chunks = split_into_chunks(pages)
            _store.build(chunks)
            _store.save(FAISS_PATH, CHUNKS_PATH)
            print(">>> FAISS index built & saved.")
        else:
            print(">>> WARNING: Index files not found and SKIP_INDEX_BUILD=True — operating without index.")

    # -----------------------------
    # OPTIONAL: append Excel file if env flag is set
    # -----------------------------
    if os.getenv("APPEND_EXCEL", "true").lower() in ("1", "true", "yes"):
        from app import append_excel_if_needed
        append_excel_if_needed()
    # -----------------------------

    return _store

def append_excel_if_needed():
    store = get_store()

    from rag.ingest import extract_excel, split_into_chunks

    pages = extract_excel(XLSX_PATH)
    new_chunks = split_into_chunks(pages)

    # tag source (important)
    for c in new_chunks:
        c["source"] = "excel_forms"

    store.append(new_chunks)
    store.save(FAISS_PATH, CHUNKS_PATH)

def get_pipeline():
    """Lazy-load RAG pipeline on first use"""
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    print(">>> Loading RAG pipeline...")
    from rag.agents import run_pipeline
    _pipeline = run_pipeline
    return _pipeline

@app.post("/api/chat")
def chat():
    from rag.schemas import ChatRequest, ChatResponse

    data = request.get_json(force=True)
    req = ChatRequest(**data)

    store = get_store()
    pipeline = get_pipeline()
    answer, applies, reason, sources = pipeline(req.message, req.context, store)

    resp = ChatResponse(
        answer=answer,
        applies=applies,
        reason=reason,
        sources=sources
    )
    return jsonify(resp.model_dump())

@app.get("/health")
def health():
    return {"ok": True}

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") in ("1", "true", "yes")
    app.run(host=host, port=port, debug=debug)

