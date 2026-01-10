"""Report generation - console, JSON, and Markdown output."""

import json
from pathlib import Path
from dataclasses import asdict
from typing import List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .runner import SuiteResult
from .evals.similarity import SimilarityResult
from .evals.retrieval import RetrievalResult
from .evals.clustering import ClusteringResult


def print_console_report(results: List[SuiteResult], console: Console = None):
    """Print a formatted report to the console."""
    if console is None:
        console = Console()

    console.print(Panel.fit(
        "[bold]Embedding Model Evaluation[/bold]",
        border_style="blue",
    ))
    console.print()

    for suite in results:
        console.print(f"[bold cyan]Suite: {suite.name}[/bold cyan]")
        console.print(f"[dim]{suite.description}[/dim]")
        console.print()

        if suite.suite_type == "similarity":
            _print_similarity_table(suite.results, console)
        elif suite.suite_type == "retrieval":
            _print_retrieval_table(suite.results, console)
        elif suite.suite_type == "clustering":
            _print_clustering_table(suite.results, console)

        console.print()


def _print_similarity_table(results: List[SimilarityResult], console: Console):
    """Print similarity results as a table."""
    # Group by test name
    tests = {}
    models = set()
    for r in results:
        if r.test_name not in tests:
            tests[r.test_name] = {}
        tests[r.test_name][r.model] = r
        models.add(r.model)

    models = sorted(models)
    table = Table()
    table.add_column("Test", style="bold")
    for model in models:
        table.add_column(model)

    for test_name, model_results in tests.items():
        row = [test_name]
        for model in models:
            r = model_results.get(model)
            if r:
                status = "[green]✓[/green]" if r.passed else "[red]✗[/red]"
                row.append(f"{status} {r.mean_score:.2f}")
            else:
                row.append("-")
        table.add_row(*row)

    console.print(table)


def _print_retrieval_table(results: List[RetrievalResult], console: Console):
    """Print retrieval results as a table."""
    # Group by query
    queries = {}
    models = set()
    for r in results:
        key = r.query[:40] + "..." if len(r.query) > 40 else r.query
        if key not in queries:
            queries[key] = {}
        queries[key][r.model] = r
        models.add(r.model)

    models = sorted(models)
    table = Table()
    table.add_column("Query", style="bold")
    for model in models:
        table.add_column(model)

    for query, model_results in queries.items():
        row = [query]
        for model in models:
            r = model_results.get(model)
            if r:
                status = "[green]✓[/green]" if r.passed else "[red]✗[/red]"
                row.append(f"{status} R@{r.k}={r.recall_at_k:.2f}")
            else:
                row.append("-")
        table.add_row(*row)

    console.print(table)


def _print_clustering_table(results: List[ClusteringResult], console: Console):
    """Print clustering results as a table."""
    table = Table()
    table.add_column("Metric", style="bold")
    for r in sorted(results, key=lambda x: x.model):
        table.add_column(r.model)

    silhouettes = ["silhouette_score"]
    for r in sorted(results, key=lambda x: x.model):
        silhouettes.append(f"{r.silhouette:.3f}")
    table.add_row(*silhouettes)

    console.print(table)


def save_json_report(results: List[SuiteResult], path: Path):
    """Save detailed results as JSON."""
    data = []
    for suite in results:
        suite_data = {
            "name": suite.name,
            "description": suite.description,
            "type": suite.suite_type,
            "results": [_result_to_dict(r) for r in suite.results],
        }
        data.append(suite_data)

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _result_to_dict(result) -> dict:
    """Convert a result dataclass to a dict."""
    if hasattr(result, "__dataclass_fields__"):
        return asdict(result)
    return result


def save_markdown_report(results: List[SuiteResult], path: Path):
    """Save a markdown summary report."""
    lines = ["# Embedding Model Evaluation Report\n"]

    for suite in results:
        lines.append(f"## {suite.name}\n")
        lines.append(f"{suite.description}\n")

        if suite.suite_type == "similarity":
            lines.extend(_similarity_markdown(suite.results))
        elif suite.suite_type == "retrieval":
            lines.extend(_retrieval_markdown(suite.results))
        elif suite.suite_type == "clustering":
            lines.extend(_clustering_markdown(suite.results))

        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(lines))


def _similarity_markdown(results: List[SimilarityResult]) -> List[str]:
    """Generate markdown table for similarity results."""
    tests = {}
    models = set()
    for r in results:
        if r.test_name not in tests:
            tests[r.test_name] = {}
        tests[r.test_name][r.model] = r
        models.add(r.model)

    models = sorted(models)
    lines = [
        "| Test | " + " | ".join(models) + " |",
        "| --- | " + " | ".join(["---"] * len(models)) + " |",
    ]

    for test_name, model_results in tests.items():
        row = [test_name]
        for model in models:
            r = model_results.get(model)
            if r:
                status = "✓" if r.passed else "✗"
                row.append(f"{status} {r.mean_score:.2f}")
            else:
                row.append("-")
        lines.append("| " + " | ".join(row) + " |")

    return lines


def _retrieval_markdown(results: List[RetrievalResult]) -> List[str]:
    """Generate markdown table for retrieval results."""
    queries = {}
    models = set()
    for r in results:
        key = r.query[:40] + "..." if len(r.query) > 40 else r.query
        if key not in queries:
            queries[key] = {}
        queries[key][r.model] = r
        models.add(r.model)

    models = sorted(models)
    lines = [
        "| Query | " + " | ".join(models) + " |",
        "| --- | " + " | ".join(["---"] * len(models)) + " |",
    ]

    for query, model_results in queries.items():
        row = [query]
        for model in models:
            r = model_results.get(model)
            if r:
                status = "✓" if r.passed else "✗"
                row.append(f"{status} R@{r.k}={r.recall_at_k:.2f}")
            else:
                row.append("-")
        lines.append("| " + " | ".join(row) + " |")

    return lines


def _clustering_markdown(results: List[ClusteringResult]) -> List[str]:
    """Generate markdown table for clustering results."""
    models = sorted(results, key=lambda x: x.model)
    lines = [
        "| Metric | " + " | ".join(r.model for r in models) + " |",
        "| --- | " + " | ".join(["---"] * len(models)) + " |",
        "| silhouette_score | " + " | ".join(f"{r.silhouette:.3f}" for r in models) + " |",
    ]
    return lines
