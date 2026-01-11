"""Embed clients for fetching embeddings from various providers."""

import os
import httpx
import numpy as np
from typing import List, Protocol, runtime_checkable


@runtime_checkable
class EmbedProvider(Protocol):
    """Protocol for embedding providers."""

    def embed(self, texts: List[str], model: str) -> np.ndarray:
        """Get embeddings for a list of texts."""
        ...

    def models(self) -> List[str]:
        """Return list of available models."""
        ...


class ProxyClient:
    """Client for the embed-proxy API (BGE models via TEI)."""

    MODELS = ["bge-small", "bge-base", "bge-large", "bge-m3"]

    def __init__(self, base_url: str = "https://embed-proxy.fly.dev", timeout: float = 300.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def embed(self, texts: List[str], model: str) -> np.ndarray:
        """Get embeddings for a list of texts using a specific model."""
        response = self._client.post(
            f"{self.base_url}/embed",
            json={"inputs": texts},
            headers={"X-Embed-Model": model, "Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        return np.array(data)

    def models(self) -> List[str]:
        return self.MODELS

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class OpenAIClient:
    """Client for OpenAI embeddings API."""

    MODELS = ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"]

    def __init__(self, api_key: str | None = None, timeout: float = 300.0):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not provided")
        self.timeout = timeout
        self._client = httpx.Client(
            timeout=timeout,
            base_url="https://api.openai.com/v1",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    def embed(self, texts: List[str], model: str) -> np.ndarray:
        """Get embeddings for a list of texts using OpenAI API."""
        response = self._client.post(
            "/embeddings",
            json={"input": texts, "model": model},
        )
        response.raise_for_status()
        data = response.json()
        # OpenAI returns embeddings in data[i].embedding format
        embeddings = [item["embedding"] for item in data["data"]]
        return np.array(embeddings)

    def models(self) -> List[str]:
        return self.MODELS

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class MultiClient:
    """Composite client that routes to the appropriate provider based on model."""

    def __init__(
        self,
        proxy_url: str = "https://embed-proxy.fly.dev",
        timeout: float = 300.0,
        include_openai: bool = False,
    ):
        self._proxy = ProxyClient(base_url=proxy_url, timeout=timeout)
        self._openai: OpenAIClient | None = None
        self._model_to_provider: dict[str, EmbedProvider] = {}

        for model in self._proxy.models():
            self._model_to_provider[model] = self._proxy

        if include_openai:
            try:
                self._openai = OpenAIClient(timeout=timeout)
                for model in self._openai.models():
                    self._model_to_provider[model] = self._openai
            except ValueError:
                # Gracefully degrade if key is missing despite include_openai=True
                pass

    def embed(self, texts: List[str], model: str) -> np.ndarray:
        """Get embeddings, routing to the appropriate provider."""
        provider = self._model_to_provider.get(model)
        if provider is None:
            raise ValueError(f"Unknown model: {model}. Available: {list(self._model_to_provider.keys())}")
        return provider.embed(texts, model)

    def models(self) -> List[str]:
        """Return all available models across all providers."""
        return list(self._model_to_provider.keys())

    def embed_single(self, text: str, model: str) -> np.ndarray:
        """Get embedding for a single text."""
        embeddings = self.embed([text], model)
        return embeddings[0]

    def close(self):
        self._proxy.close()
        if self._openai:
            self._openai.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Backwards compatibility alias
EmbedClient = ProxyClient
