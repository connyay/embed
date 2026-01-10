"""Similarity evaluation - test if similar texts have similar embeddings."""

import numpy as np
from dataclasses import dataclass
from typing import List, Literal

from ..client import EmbedClient


@dataclass
class SimilarityTestCase:
    name: str
    pairs: List[tuple[str, str]]
    expect: Literal["high", "low", "medium"]


@dataclass
class SimilarityResult:
    test_name: str
    model: str
    scores: List[float]  # cosine similarity for each pair
    mean_score: float
    passed: bool
    expected: str


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def evaluate_similarity(
    client: EmbedClient,
    test: SimilarityTestCase,
    model: str,
) -> SimilarityResult:
    """Run a similarity test for a specific model.

    Args:
        client: Embed client
        test: Test case with pairs and expectations
        model: Model name to test

    Returns:
        SimilarityResult with scores and pass/fail
    """
    # Batch all texts into a single embed call for efficiency
    all_texts = []
    for a, b in test.pairs:
        all_texts.extend([a, b])

    embeddings = client.embed(all_texts, model)

    scores = []
    for i in range(0, len(all_texts), 2):
        sim = cosine_similarity(embeddings[i], embeddings[i + 1])
        scores.append(sim)

    mean_score = float(np.mean(scores))

    thresholds = {
        "high": (0.7, 1.0),    # expect cosine > 0.7
        "medium": (0.4, 0.7),  # expect 0.4 < cosine < 0.7
        "low": (0.0, 0.4),     # expect cosine < 0.4
    }
    low, high = thresholds[test.expect]
    passed = low <= mean_score <= high

    return SimilarityResult(
        test_name=test.name,
        model=model,
        scores=scores,
        mean_score=mean_score,
        passed=passed,
        expected=test.expect,
    )


def parse_similarity_suite(data: dict) -> List[SimilarityTestCase]:
    """Parse a similarity test suite from YAML data."""
    tests = []
    for test_data in data.get("tests", []):
        tests.append(SimilarityTestCase(
            name=test_data["name"],
            pairs=[tuple(p) for p in test_data["pairs"]],
            expect=test_data["expect"],
        ))
    return tests
