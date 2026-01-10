"""Embed proxy client for fetching embeddings."""

import httpx
import numpy as np
from typing import List


class EmbedClient:
    """Client for the embed-proxy API."""

    MODELS = ["bge-small", "bge-base", "bge-large", "bge-m3"]

    def __init__(self, base_url: str = "https://embed-proxy.fly.dev", timeout: float = 300.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def embed(self, texts: List[str], model: str) -> np.ndarray:
        """Get embeddings for a list of texts using a specific model.

        Args:
            texts: List of texts to embed
            model: Model name (e.g., 'bge-small', 'bge-m3')

        Returns:
            numpy array of shape (len(texts), embedding_dim)
        """
        response = self._client.post(
            f"{self.base_url}/embed",
            json={"inputs": texts},
            headers={"X-Embed-Model": model, "Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        return np.array(data)

    def embed_single(self, text: str, model: str) -> np.ndarray:
        """Get embedding for a single text.

        Args:
            text: Text to embed
            model: Model name

        Returns:
            numpy array of shape (embedding_dim,)
        """
        embeddings = self.embed([text], model)
        return embeddings[0]

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
