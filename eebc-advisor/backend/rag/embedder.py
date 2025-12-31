import numpy as np


class VoyageEmbedder:
    """Wrapper for Voyage AI embeddings API"""

    def __init__(self, client, model="voyage-3"):
        """
        Initialize Voyage AI embedder with a pre-initialized client

        Args:
            client: voyageai.Client instance
            model: Voyage model name (default: voyage-3)
        """
        self.client = client
        self.model = model

    def encode(self, texts):
        """
        Encode texts to embeddings using Voyage API

        Args:
            texts: List of text strings to embed

        Returns:
            numpy array of normalized embeddings with shape (len(texts), embedding_dim)
        """
        # texts is a list[str]
        result = self.client.embed(texts, model=self.model)

        # voyageai SDK typically returns embeddings as list[list[float]]
        vecs = getattr(result, "embeddings", result)

        embeddings = np.array(vecs, dtype=np.float32)

        # normalize for cosine similarity with IndexFlatIP
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-12
        embeddings = embeddings / norms

        return embeddings


