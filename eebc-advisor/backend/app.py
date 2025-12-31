import os
from flask import Flask, request, jsonify
from flask_cors import CORS

from rag.schemas import ChatRequest, ChatResponse, BuildingContext
from rag.ingest import extract_pages, split_into_chunks, save_chunks
from rag.index import VectorStore
from rag.agents import intake, applicability, build_answer

APP_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(APP_DIR, "data")
PDF_PATH = os.path.join(DATA_DIR, "EEBC 2021.pdf")
FAISS_PATH = os.path.join(DATA_DIR, "index.faiss")
CHUNKS_PATH = os.path.join(DATA_DIR, "chunks.json")

# Allow overriding paths and skipping expensive index build via environment variables
FAISS_PATH = os.getenv("FAISS_PATH", FAISS_PATH)
CHUNKS_PATH = os.getenv("CHUNKS_PATH", CHUNKS_PATH)
SKIP_INDEX_BUILD = os.getenv("SKIP_INDEX_BUILD", "false").lower() in ("1", "true", "yes")

app = Flask(__name__)
CORS(app)

store = VectorStore()
_index_loaded = False

def get_store():
    """Lazy-load index on first use instead of startup"""
    global _index_loaded
    if not _index_loaded:
        if os.path.exists(FAISS_PATH) and os.path.exists(CHUNKS_PATH):
            print("Loading FAISS index on first request...")
            store.load(FAISS_PATH, CHUNKS_PATH)
            print("FAISS index loaded successfully.")
        else:
            if not SKIP_INDEX_BUILD:
                print("Building index from PDF on first request...")
                pages = extract_pages(PDF_PATH)
                chunks = split_into_chunks(pages)
                store.build(chunks)
                store.save(FAISS_PATH, CHUNKS_PATH)
                print("Index built & saved.")
            else:
                print("Index files not found and SKIP_INDEX_BUILD=True — operating without index.")
        _index_loaded = True
    return store

def ensure_index():
    if os.path.exists(FAISS_PATH) and os.path.exists(CHUNKS_PATH):
        store.load(FAISS_PATH, CHUNKS_PATH)
        print("Loaded FAISS index.")
        return

    print("Building index from PDF (first run)...")
    pages = extract_pages(PDF_PATH)
    chunks = split_into_chunks(pages)
    store.build(chunks)
    store.save(FAISS_PATH, CHUNKS_PATH)
    print("Index built & saved.")

# Don't load index at startup - load on first request
# if SKIP_INDEX_BUILD:
#     if os.path.exists(FAISS_PATH) and os.path.exists(CHUNKS_PATH):
#         store.load(FAISS_PATH, CHUNKS_PATH)
#         print("Loaded FAISS index (SKIP_INDEX_BUILD).")
#     else:
#         print("SKIP_INDEX_BUILD=True and index files not found — starting without index.")
# else:
#     ensure_index()

from rag.agents import run_pipeline

@app.post("/api/chat")
def chat():
    data = request.get_json(force=True)
    req = ChatRequest(**data)

    current_store = get_store()
    answer, applies, reason, sources = run_pipeline(req.message, req.context, current_store)

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

