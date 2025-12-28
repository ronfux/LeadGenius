#!/usr/bin/env python3
"""
Market Research AI Employee - CLI Entry Point

A scalable, agentic workflow for automated market research.
Uses a Manager/Worker model with parallel execution via Gemini CLI.

Usage:
    python main.py research --target ems --states TX,CA
    python main.py aggregate
    python main.py check
"""

import sys
import logging
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler

from src.orchestrator import Orchestrator
from src.aggregator import Aggregator
from src.cli_adapters.gemini_adapter import GeminiAdapter


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(show_time=False, show_path=False)]
)
logger = logging.getLogger(__name__)
console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Market Research AI Employee - Automated business research at scale."""
    pass


@cli.command()
@click.option(
    "--target", "-t",
    type=click.Path(exists=True),
    help="Path to target industry config (e.g., config/targets/ems.yaml)"
)
@click.option(
    "--states", "-s",
    required=True,
    help="Comma-separated list of state abbreviations (e.g., TX,CA,FL)"
)
@click.option(
    "--workers", "-w",
    type=int,
    default=10,
    help="Maximum number of parallel workers (default: 10)"
)
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    default="config/settings.yaml",
    help="Path to settings.yaml"
)
@click.option(
    "--skip-aggregate",
    is_flag=True,
    help="Skip aggregation after research completes"
)
def research(target, states, workers, config, skip_aggregate):
    """
    Run market research for specified states.

    Examples:
        python main.py research --target config/targets/ems.yaml --states TX
        python main.py research --states TX,CA,FL --workers 20
    """
    # Parse states
    state_list = [s.strip().upper() for s in states.split(",")]

    # Validate states
    valid_states = {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"
    }

    invalid_states = [s for s in state_list if s not in valid_states]
    if invalid_states:
        console.print(f"[red]Invalid state codes: {', '.join(invalid_states)}[/red]")
        sys.exit(1)

    # Create orchestrator
    config_path = Path(config) if config else None
    target_path = Path(target) if target else None

    orchestrator = Orchestrator(
        config_path=config_path,
        target_config=target_path
    )

    # Override workers if specified
    if workers:
        orchestrator.worker_pool.max_workers = workers

    # Run research
    try:
        summary = orchestrator.run(state_list, skip_aggregation=skip_aggregate)

        if "error" in summary:
            console.print(f"[red]Research failed: {summary['error']}[/red]")
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Research interrupted by user.[/yellow]")
        sys.exit(130)
    except Exception as e:
        logger.exception("Research failed with error")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option(
    "--input", "-i",
    type=click.Path(exists=True),
    default="data/outputs",
    help="Directory containing worker output files"
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    default="data/aggregated",
    help="Directory for aggregated results"
)
@click.option(
    "--format", "-f",
    type=click.Choice(["json", "csv", "both"]),
    default="both",
    help="Output format (default: both)"
)
def aggregate(input, output, format):
    """
    Aggregate results from completed research.

    Examples:
        python main.py aggregate
        python main.py aggregate --input data/outputs --format csv
    """
    # Determine formats
    if format == "both":
        formats = ["json", "csv"]
    else:
        formats = [format]

    # Run aggregation
    aggregator = Aggregator(
        input_dir=Path(input),
        output_dir=Path(output)
    )

    try:
        summary = aggregator.aggregate(export_formats=formats)

        console.print(f"\n[green]Aggregation complete![/green]")
        console.print(f"  Input files: {summary['input_files']}")
        console.print(f"  Total records: {summary['total_records_found']}")
        console.print(f"  Unique records: {summary['unique_records']}")
        console.print(f"  Duplicates removed: {summary['duplicates_removed']}")

    except Exception as e:
        logger.exception("Aggregation failed")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
def check():
    """
    Check if Gemini CLI is installed and configured.

    This verifies that the CLI tool is available and can be used.
    """
    console.print("[cyan]Checking Gemini CLI...[/cyan]\n")

    adapter = GeminiAdapter()

    if adapter.is_available():
        console.print("[green]✓ Gemini CLI is installed and available[/green]")
        console.print(f"  Path: {adapter._cli_path}")
        console.print(f"  Available models: {', '.join(adapter.get_available_models())}")
    else:
        console.print("[red]✗ Gemini CLI is not available[/red]")
        console.print("\nTo install Gemini CLI:")
        console.print("  npm install -g @anthropic-ai/gemini-cli")
        console.print("  # or")
        console.print("  pip install gemini-cli")
        console.print("\nThen configure your API key:")
        console.print("  gemini auth login")
        sys.exit(1)


@cli.command()
@click.option(
    "--target", "-t",
    type=click.Path(),
    default="config/targets/example.yaml",
    help="Path for the new target config"
)
@click.option(
    "--industry", "-i",
    required=True,
    help="Industry name (e.g., 'EMS', 'Plumbing')"
)
def init_target(target, industry):
    """
    Create a new target industry configuration.

    Examples:
        python main.py init-target --industry "Plumbing" --target config/targets/plumbing.yaml
    """
    import yaml

    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate search terms based on industry
    search_terms = [
        industry.lower(),
        f"{industry.lower()} company",
        f"{industry.lower()} services",
        f"{industry.lower()} provider"
    ]

    config = {
        "industry": industry,
        "search_terms": search_terms,
        "data_fields": [
            "company_name",
            "address",
            "phone",
            "website",
            "email"
        ]
    }

    with open(target_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    console.print(f"[green]Created target config: {target_path}[/green]")
    console.print(f"\nYou can now run:")
    console.print(f"  python main.py research --target {target_path} --states TX,CA")


if __name__ == "__main__":
    cli()
