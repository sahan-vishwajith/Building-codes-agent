import os
import numpy as np
import voyageai

class VoyageEmbedder:
    """Wrapper for Voyage AI embeddings API"""

    def __init__(self, model: str = "voyage-3", api_key: str = None):
        """
        Initialize Voyage AI embedder

        Args:
            model: Voyage model name (default: voyage-3)
            api_key: Voyage API key (defaults to VOYAGE_API_KEY env var)
        """
        self.model = model
        self.api_key = api_key or os.getenv("VOYAGE_API_KEY")

        if not self.api_key:
            raise ValueError(
                "VOYAGE_API_KEY environment variable not set. "
                "Please set it before initializing the embedder."
            )

        self.client = voyageai.Client(api_key=self.api_key)
        print(f"Initialized Voyage embedder with model: {self.model}")

    def encode(self, texts, batch_size: int = 128, show_progress_bar: bool = False):
        """
        Encode texts to embeddings using Voyage API

        Args:
            texts: List of text strings to embed
            batch_size: Batch size for API requests (Voyage handles batching)
            show_progress_bar: Whether to show progress (ignored for API calls)

        Returns:
            numpy array of embeddings with shape (len(texts), embedding_dim)
        """
        if isinstance(texts, str):
            texts = [texts]

        print(f"Encoding {len(texts)} texts with Voyage API (model: {self.model})...")

        try:
            # Voyage API handles batching internally
            result = self.client.embed(texts, model=self.model, input_type="document")

            # Extract embeddings from result
            embeddings = np.array([item.embedding for item in result.embeddings])
            print(f"Successfully encoded {len(embeddings)} texts")

            return embeddings

        except Exception as e:
            print(f"Error encoding texts: {e}")
            raise

