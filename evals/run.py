#!/usr/bin/env python3
"""CLI entry point for running embedding evaluations."""

import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.client import MultiClient
from src.runner import run_suite, discover_suites
from src.report import print_console_report, save_json_report, save_markdown_report

app = typer.Typer(help="Embedding model evaluation harness")
console = Console()


@app.command()
def main(
    suite: Optional[Path] = typer.Option(
        None,
        "--suite", "-s",
        help="Run a specific suite file (relative to suites/)",
    ),
    models: Optional[str] = typer.Option(
        None,
        "--models", "-m",
        help="Comma-separated list of models to test (default: all available)",
    ),
    output: Path = typer.Option(
        Path("results"),
        "--output", "-o",
        help="Output directory for reports",
    ),
    base_url: str = typer.Option(
        "https://embed-proxy.fly.dev",
        "--base-url", "-u",
        help="Base URL for embed proxy",
    ),
    timeout: float = typer.Option(
        300.0,
        "--timeout", "-t",
        help="Request timeout in seconds",
    ),
    no_openai: bool = typer.Option(
        False,
        "--no-openai",
        help="Disable OpenAI models even if OPENAI_API_KEY is set",
    ),
):
    """Run embedding model evaluations."""
    include_openai = not no_openai and bool(os.environ.get("OPENAI_API_KEY"))

    if include_openai:
        console.print("[dim]OPENAI_API_KEY detected, including OpenAI models[/dim]")

    with MultiClient(
        proxy_url=base_url,
        timeout=timeout,
        include_openai=include_openai,
    ) as client:
        available_models = client.models()

        if models:
            model_list = [m.strip() for m in models.split(",")]
            for m in model_list:
                if m not in available_models:
                    console.print(f"[red]Unknown model: {m}[/red]")
                    console.print(f"[dim]Available: {', '.join(available_models)}[/dim]")
                    raise typer.Exit(1)
        else:
            model_list = available_models

        console.print(f"[bold]Models:[/bold] {', '.join(model_list)}")
        console.print(f"[bold]Base URL:[/bold] {base_url}")
        console.print()

        suites_dir = Path(__file__).parent / "suites"
        if suite:
            suite_paths = [suites_dir / suite]
            if not suite_paths[0].exists():
                console.print(f"[red]Suite not found: {suite}[/red]")
                raise typer.Exit(1)
        else:
            suite_paths = discover_suites(suites_dir)
            if not suite_paths:
                console.print(f"[yellow]No suites found in {suites_dir}[/yellow]")
                raise typer.Exit(0)

        console.print(f"[bold]Suites:[/bold] {len(suite_paths)} found")
        for p in suite_paths:
            console.print(f"  - {p.relative_to(suites_dir)}")
        console.print()

        results = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running evaluations...", total=None)

            for suite_path in suite_paths:
                progress.update(task, description=f"Running {suite_path.stem}...")
                result = run_suite(
                    client,
                    suite_path,
                    model_list,
                    on_progress=lambda msg: progress.update(task, description=msg),
                )
                results.append(result)

    console.print()
    print_console_report(results, console)

    output.mkdir(parents=True, exist_ok=True)
    save_json_report(results, output / "results.json")
    save_markdown_report(results, output / "report.md")

    console.print(f"\n[green]Reports saved to {output}/[/green]")
    console.print(f"  - results.json")
    console.print(f"  - report.md")


if __name__ == "__main__":
    app()
