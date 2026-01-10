"""Retrieval evaluation - test if queries retrieve the correct documents."""

import numpy as np
from dataclasses import dataclass
from typing import List

from ..client import EmbedClient


@dataclass
class Document:
    id: str
    text: str


@dataclass
class RetrievalTestCase:
    query: str
    relevant: List[str]  # list of doc IDs that are relevant
    k: int  # check top-k results


@dataclass
class RetrievalResult:
    query: str
    model: str
    retrieved: List[str]  # doc IDs in order of similarity
    relevant: List[str]
    k: int
    recall_at_k: float  # fraction of relevant docs in top-k
    passed: bool


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def evaluate_retrieval(
    client: EmbedClient,
    corpus: List[Document],
    test: RetrievalTestCase,
    model: str,
) -> RetrievalResult:
    """Run a retrieval test for a specific model.

    Args:
        client: Embed client
        corpus: List of documents to search
        test: Test case with query and expected relevant docs
        model: Model name to test

    Returns:
        RetrievalResult with retrieved docs and metrics
    """
    query_embedding = client.embed_single(test.query, model)
    corpus_texts = [doc.text for doc in corpus]
    corpus_embeddings = client.embed(corpus_texts, model)

    similarities = []
    for i, doc in enumerate(corpus):
        sim = cosine_similarity(query_embedding, corpus_embeddings[i])
        similarities.append((doc.id, sim))

    similarities.sort(key=lambda x: x[1], reverse=True)
    retrieved = [doc_id for doc_id, _ in similarities]

    top_k = set(retrieved[: test.k])
    relevant_set = set(test.relevant)
    hits = len(top_k & relevant_set)
    recall_at_k = hits / len(relevant_set) if relevant_set else 0.0

    passed = relevant_set <= top_k

    return RetrievalResult(
        query=test.query,
        model=model,
        retrieved=retrieved,
        relevant=test.relevant,
        k=test.k,
        recall_at_k=recall_at_k,
        passed=passed,
    )


def parse_retrieval_suite(data: dict) -> tuple[List[Document], List[RetrievalTestCase]]:
    """Parse a retrieval test suite from YAML data."""
    corpus = [
        Document(id=doc["id"], text=doc["text"])
        for doc in data.get("corpus", [])
    ]
    tests = [
        RetrievalTestCase(
            query=test["query"],
            relevant=test["relevant"],
            k=test.get("k", 1),
        )
        for test in data.get("tests", [])
    ]
    return corpus, tests
