import json
import os
import numpy as np
import faiss
import voyageai
from .embedder import VoyageEmbedder

def _normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=1, keepdims=True) + 1e-12
    return v / n

class VectorStore:
    def __init__(self, model: str = "voyage-3"):
        self.model = model
        self._embedder = None
        self.index = None
        self.chunks = []
        self.embs = None

        # Initialize Voyage client once
        api_key = os.getenv("VOYAGE_API_KEY")
        if not api_key:
            raise ValueError(
                "VOYAGE_API_KEY environment variable not set. "
                "Please set it before initializing VectorStore."
            )
        self.client = voyageai.Client(api_key=api_key)
        print(f"Initialized Voyage client with model: {self.model}")

    @property
    def embedder(self):
        """Lazy-load Voyage embedder on first access"""
        if self._embedder is None:
            print(f"Loading Voyage embedder: {self.model}")
            self._embedder = VoyageEmbedder(client=self.client, model=self.model)
        return self._embedder

    def build(self, chunks, batch_size=64):
        self.chunks = chunks
        texts = [c["text"] for c in chunks]
        print(f"Building embeddings for {len(texts)} chunks...")

        # Voyage API handles large batches efficiently, but we can chunk if needed
        embs = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            print(f"  Encoding batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}...")
            batch_embs = self.embedder.encode(batch)
            embs.append(batch_embs)

        embs = np.vstack(embs).astype("float32")
        # Already normalized by VoyageEmbedder, but normalize again to be safe
        embs = _normalize(embs)

        dim = embs.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embs)
        self.embs = embs
        print(f"Built FAISS index with {len(embs)} embeddings of dimension {dim}")

    def save(self, faiss_path: str, chunks_path: str):
        faiss.write_index(self.index, faiss_path)
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=False)
        print(f"Saved FAISS index to {faiss_path} and chunks to {chunks_path}")

    def load(self, faiss_path: str, chunks_path: str):
        self.index = faiss.read_index(faiss_path)
        with open(chunks_path, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)
        print(f"Loaded FAISS index from {faiss_path} and {len(self.chunks)} chunks")

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


