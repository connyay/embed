"""Test suite runner - loads YAML files and runs evaluations."""

import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Any

from .client import EmbedClient
from .evals.similarity import (
    parse_similarity_suite,
    evaluate_similarity,
    SimilarityResult,
)
from .evals.retrieval import (
    parse_retrieval_suite,
    evaluate_retrieval,
    RetrievalResult,
)
from .evals.clustering import (
    parse_clustering_suite,
    evaluate_clustering,
    ClusteringResult,
)


@dataclass
class SuiteResult:
    name: str
    description: str
    suite_type: str
    results: List[Any] = field(default_factory=list)


def load_suite(path: Path) -> dict:
    """Load a YAML test suite file."""
    with open(path) as f:
        return yaml.safe_load(f)


def run_suite(
    client: EmbedClient,
    suite_path: Path,
    models: List[str],
    on_progress: callable = None,
) -> SuiteResult:
    """Run a test suite against multiple models.

    Args:
        client: Embed client
        suite_path: Path to YAML suite file
        models: List of model names to test
        on_progress: Optional callback for progress updates

    Returns:
        SuiteResult with all results
    """
    data = load_suite(suite_path)
    suite_type = data.get("type", "unknown")
    suite_result = SuiteResult(
        name=data.get("name", suite_path.stem),
        description=data.get("description", ""),
        suite_type=suite_type,
    )

    if suite_type == "similarity":
        tests = parse_similarity_suite(data)
        for test in tests:
            for model in models:
                if on_progress:
                    on_progress(f"Running {test.name} on {model}...")
                result = evaluate_similarity(client, test, model)
                suite_result.results.append(result)

    elif suite_type == "retrieval":
        corpus, tests = parse_retrieval_suite(data)
        for test in tests:
            for model in models:
                if on_progress:
                    on_progress(f"Running retrieval '{test.query[:30]}...' on {model}...")
                result = evaluate_retrieval(client, corpus, test, model)
                suite_result.results.append(result)

    elif suite_type == "clustering":
        clusters = parse_clustering_suite(data)
        for model in models:
            if on_progress:
                on_progress(f"Running clustering on {model}...")
            result = evaluate_clustering(client, clusters, model)
            suite_result.results.append(result)

    return suite_result


def discover_suites(suites_dir: Path) -> List[Path]:
    """Find all YAML suite files in a directory."""
    return sorted(suites_dir.rglob("*.yaml"))
