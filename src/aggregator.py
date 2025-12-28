"""
Data Aggregator for combining and exporting research results.

This module handles reading worker outputs, deduplicating data,
and exporting to JSON and CSV formats.
"""

import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from rich.console import Console
from rich.table import Table


logger = logging.getLogger(__name__)
console = Console()


@dataclass
class Business:
    """Represents a business found during research."""
    company_name: str
    city: str
    state: str
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    industry: Optional[str] = None
    source_task: Optional[str] = None
    extra_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "company_name": self.company_name,
            "city": self.city,
            "state": self.state,
            "address": self.address,
            "phone": self.phone,
            "website": self.website,
            "email": self.email,
            "industry": self.industry,
            "source_task": self.source_task,
            **self.extra_data
        }

    @property
    def dedup_key(self) -> str:
        """Generate a key for deduplication."""
        # Normalize company name for comparison
        name = self.company_name.lower().strip()
        # Remove common suffixes
        for suffix in [" llc", " inc", " corp", " company", " co"]:
            name = name.replace(suffix, "")
        return f"{name}|{self.city.lower()}|{self.state.upper()}"


class Aggregator:
    """
    Aggregates and exports research results.

    Reads JSON output files from workers, combines them,
    removes duplicates, and exports to various formats.
    """

    def __init__(
        self,
        input_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None
    ):
        """
        Initialize the aggregator.

        Args:
            input_dir: Directory containing worker output files
            output_dir: Directory for aggregated output
        """
        self.input_dir = input_dir or Path("data/outputs")
        self.output_dir = output_dir or Path("data/aggregated")

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_results(self) -> list[dict]:
        """
        Load all JSON result files from input directory.

        Returns:
            List of parsed JSON data from each file
        """
        results = []

        json_files = list(self.input_dir.glob("*.json"))
        logger.info(f"Found {len(json_files)} JSON files in {self.input_dir}")

        for file_path in json_files:
            # Skip files ending with _raw.json
            if file_path.stem.endswith("_raw"):
                continue

            try:
                with open(file_path) as f:
                    data = json.load(f)
                    results.append({
                        "file": file_path.name,
                        "data": data
                    })
                    logger.debug(f"Loaded {file_path.name}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse {file_path.name}: {e}")
            except Exception as e:
                logger.error(f"Error reading {file_path.name}: {e}")

        return results

    def extract_businesses(self, results: list[dict]) -> list[Business]:
        """
        Extract business records from loaded results.

        Args:
            results: List of loaded result data

        Returns:
            List of Business objects
        """
        businesses = []

        for result in results:
            data = result["data"]
            source = result["file"]

            # Handle city_search results (array of businesses)
            if isinstance(data, dict) and "businesses" in data:
                city = data.get("city", "")
                state = data.get("state", "")
                industry = data.get("industry", "")
                task_id = data.get("task_id", source)

                for biz in data.get("businesses", []):
                    if not biz.get("company_name"):
                        continue

                    businesses.append(Business(
                        company_name=biz.get("company_name", ""),
                        city=biz.get("city", city),
                        state=biz.get("state", state),
                        address=biz.get("address"),
                        phone=biz.get("phone"),
                        website=biz.get("website"),
                        email=biz.get("email"),
                        industry=industry,
                        source_task=task_id
                    ))

            # Handle company_research results (single company)
            elif isinstance(data, dict) and "company_name" in data:
                location = data.get("location", {})
                contact = data.get("contact", {})

                businesses.append(Business(
                    company_name=data.get("company_name", ""),
                    city=location.get("city", ""),
                    state=location.get("state", ""),
                    address=location.get("address"),
                    phone=contact.get("phone"),
                    website=contact.get("website"),
                    email=contact.get("email"),
                    source_task=data.get("task_id", source),
                    extra_data={
                        "business_details": data.get("business_details"),
                        "key_contacts": data.get("key_contacts"),
                        "online_presence": data.get("online_presence")
                    }
                ))

            # Handle direct array of businesses
            elif isinstance(data, list):
                for biz in data:
                    if isinstance(biz, dict) and biz.get("company_name"):
                        businesses.append(Business(
                            company_name=biz.get("company_name", ""),
                            city=biz.get("city", ""),
                            state=biz.get("state", ""),
                            address=biz.get("address"),
                            phone=biz.get("phone"),
                            website=biz.get("website"),
                            email=biz.get("email"),
                            source_task=source
                        ))

        logger.info(f"Extracted {len(businesses)} business records")
        return businesses

    def deduplicate(self, businesses: list[Business]) -> list[Business]:
        """
        Remove duplicate businesses.

        Uses company name + city + state as the deduplication key.
        Keeps the record with the most complete data.

        Args:
            businesses: List of Business objects

        Returns:
            Deduplicated list of Business objects
        """
        seen = {}

        for biz in businesses:
            key = biz.dedup_key

            if key not in seen:
                seen[key] = biz
            else:
                # Keep the one with more data
                existing = seen[key]
                existing_fields = sum(1 for v in existing.to_dict().values() if v)
                new_fields = sum(1 for v in biz.to_dict().values() if v)

                if new_fields > existing_fields:
                    seen[key] = biz

        deduplicated = list(seen.values())
        removed = len(businesses) - len(deduplicated)

        logger.info(f"Removed {removed} duplicates, {len(deduplicated)} unique records")
        return deduplicated

    def export_json(self, businesses: list[Business], filename: str = "results.json") -> Path:
        """
        Export businesses to JSON file.

        Args:
            businesses: List of Business objects
            filename: Output filename

        Returns:
            Path to the output file
        """
        output_path = self.output_dir / filename

        data = {
            "generated_at": datetime.now().isoformat(),
            "total_records": len(businesses),
            "businesses": [biz.to_dict() for biz in businesses]
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported JSON to {output_path}")
        return output_path

    def export_csv(self, businesses: list[Business], filename: str = "results.csv") -> Path:
        """
        Export businesses to CSV file.

        Args:
            businesses: List of Business objects
            filename: Output filename

        Returns:
            Path to the output file
        """
        output_path = self.output_dir / filename

        # Define CSV columns
        fieldnames = [
            "company_name", "city", "state", "address",
            "phone", "website", "email", "industry", "source_task"
        ]

        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for biz in businesses:
                writer.writerow(biz.to_dict())

        logger.info(f"Exported CSV to {output_path}")
        return output_path

    def aggregate(self, export_formats: list[str] = None) -> dict:
        """
        Run the full aggregation pipeline.

        Args:
            export_formats: List of formats to export ("json", "csv")

        Returns:
            Summary statistics
        """
        if export_formats is None:
            export_formats = ["json", "csv"]

        console.print("\n[bold cyan]Starting data aggregation...[/bold cyan]\n")

        # Load results
        results = self.load_results()
        console.print(f"  Loaded [green]{len(results)}[/green] result files")

        # Extract businesses
        businesses = self.extract_businesses(results)
        console.print(f"  Extracted [green]{len(businesses)}[/green] business records")

        # Deduplicate
        unique_businesses = self.deduplicate(businesses)
        console.print(f"  After deduplication: [green]{len(unique_businesses)}[/green] unique records")

        # Export
        output_files = []
        if "json" in export_formats:
            json_path = self.export_json(unique_businesses)
            output_files.append(str(json_path))
            console.print(f"  Exported JSON: [blue]{json_path}[/blue]")

        if "csv" in export_formats:
            csv_path = self.export_csv(unique_businesses)
            output_files.append(str(csv_path))
            console.print(f"  Exported CSV: [blue]{csv_path}[/blue]")

        # Generate summary
        summary = {
            "input_files": len(results),
            "total_records_found": len(businesses),
            "unique_records": len(unique_businesses),
            "duplicates_removed": len(businesses) - len(unique_businesses),
            "output_files": output_files
        }

        # Print summary table
        self._print_summary(unique_businesses)

        return summary

    def _print_summary(self, businesses: list[Business]) -> None:
        """Print a summary table of results by state/city."""
        if not businesses:
            console.print("\n[yellow]No businesses found.[/yellow]")
            return

        # Group by state
        by_state = {}
        for biz in businesses:
            state = biz.state or "Unknown"
            if state not in by_state:
                by_state[state] = []
            by_state[state].append(biz)

        # Create summary table
        table = Table(title="\nResults Summary")
        table.add_column("State", style="cyan")
        table.add_column("Cities", style="green")
        table.add_column("Businesses", style="yellow", justify="right")

        for state in sorted(by_state.keys()):
            biz_list = by_state[state]
            cities = set(b.city for b in biz_list if b.city)
            table.add_row(
                state,
                str(len(cities)),
                str(len(biz_list))
            )

        console.print(table)
