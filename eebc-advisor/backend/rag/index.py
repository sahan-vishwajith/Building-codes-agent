import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

def _normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=1, keepdims=True) + 1e-12
    return v / n

class VectorStore:
    def __init__(self, embed_model="sentence-transformers/all-MiniLM-L6-v2"):
        self.embedder = SentenceTransformer(embed_model)
        self.index = None
        self.chunks = []
        self.embs = None

    def build(self, chunks, batch_size=64):
        self.chunks = chunks
        texts = [c["text"] for c in chunks]
        embs = []
        for i in range(0, len(texts), batch_size):
            embs.append(self.embedder.encode(texts[i:i+batch_size], show_progress_bar=False))
        embs = np.vstack(embs).astype("float32")
        embs = _normalize(embs)

        dim = embs.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embs)
        self.embs = embs

    def save(self, faiss_path: str, chunks_path: str):
        faiss.write_index(self.index, faiss_path)
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=False)

    def load(self, faiss_path: str, chunks_path: str):
        self.index = faiss.read_index(faiss_path)
        with open(chunks_path, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)

    def search(self, query: str, top_k=8):
        q = self.embedder.encode([query]).astype("float32")
        q = _normalize(q)
        scores, ids = self.index.search(q, top_k)

        out = []
        for s, idx in zip(scores[0], ids[0]):
            if idx == -1:
                continue
            c = dict(self.chunks[idx])
            c["score"] = float(s)
            out.append(c)
        return out
