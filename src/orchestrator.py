"""
Orchestrator for coordinating the research workflow.

This module manages the overall research process:
1. Load configuration and SOPs
2. Run Manager agent to generate task list
3. Execute tasks via Worker Pool
4. Aggregate results
"""

import json
import logging
from pathlib import Path
from typing import Optional

import yaml
from rich.console import Console
from rich.panel import Panel

from .cli_adapters.base import CLIAdapter
from .cli_adapters.gemini_adapter import GeminiAdapter
from .worker_pool import WorkerPool, Task
from .aggregator import Aggregator


logger = logging.getLogger(__name__)
console = Console()


class Orchestrator:
    """
    Coordinates the market research workflow.

    Manages the Manager -> Worker -> Aggregator pipeline.
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        target_config: Optional[Path] = None
    ):
        """
        Initialize the orchestrator.

        Args:
            config_path: Path to settings.yaml
            target_config: Path to target industry config
        """
        self.config_path = config_path or Path("config/settings.yaml")
        self.target_config_path = target_config

        # Load configuration
        self.config = self._load_config()
        self.target = self._load_target_config() if target_config else {}

        # Initialize components
        self.adapter = self._create_adapter()
        self.worker_pool = self._create_worker_pool()
        self.aggregator = Aggregator(
            input_dir=Path(self.config.get("paths", {}).get("outputs", "data/outputs")),
            output_dir=Path(self.config.get("output", {}).get("directory", "data/aggregated"))
        )

        # Load SOPs
        self.sops = self._load_sops()

    def _load_config(self) -> dict:
        """Load main configuration file."""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}")
            return {}

        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def _load_target_config(self) -> dict:
        """Load target industry configuration."""
        if not self.target_config_path or not self.target_config_path.exists():
            return {}

        with open(self.target_config_path) as f:
            return yaml.safe_load(f)

    def _create_adapter(self) -> CLIAdapter:
        """Create the appropriate CLI adapter."""
        cli_type = self.config.get("cli", "gemini")
        models = self.config.get("models", {})

        if cli_type == "gemini":
            default_model = models.get("worker", "gemini-2.5-flash")
            return GeminiAdapter(default_model=default_model)
        else:
            # Default to Gemini
            return GeminiAdapter()

    def _create_worker_pool(self) -> WorkerPool:
        """Create the worker pool."""
        parallelism = self.config.get("parallelism", {})
        paths = self.config.get("paths", {})

        return WorkerPool(
            adapter=self.adapter,
            max_workers=parallelism.get("max_workers", 10),
            output_dir=Path(paths.get("outputs", "data/outputs")),
            spawn_delay=parallelism.get("spawn_delay", 0.5)
        )

    def _load_sops(self) -> dict:
        """Load SOP files."""
        sops_dir = Path(self.config.get("paths", {}).get("sops", "sops"))

        sops = {}

        # Manager SOP
        manager_sop = sops_dir / "manager" / "research_strategy.md"
        if manager_sop.exists():
            sops["manager"] = manager_sop.read_text()

        # Worker SOPs
        city_search_sop = sops_dir / "worker" / "city_search.md"
        if city_search_sop.exists():
            sops["city_search"] = city_search_sop.read_text()

        company_research_sop = sops_dir / "worker" / "company_research.md"
        if company_research_sop.exists():
            sops["company_research"] = company_research_sop.read_text()

        logger.info(f"Loaded {len(sops)} SOPs")
        return sops

    def run_manager(self, states: list[str]) -> list[dict]:
        """
        Run the Manager agent to generate research tasks.

        Args:
            states: List of state abbreviations to research

        Returns:
            List of task dictionaries
        """
        console.print(Panel(
            "[bold cyan]Running Manager Agent[/bold cyan]\n"
            f"Planning research for states: {', '.join(states)}",
            title="Phase 1: Planning"
        ))

        # Build manager prompt
        industry = self.target.get("industry", "businesses")
        search_terms = self.target.get("search_terms", [industry])
        data_fields = self.target.get("data_fields", [
            "company_name", "address", "phone", "website", "email"
        ])

        prompt = f"""
Generate research tasks for the following:

Industry: {industry}
States to research: {', '.join(states)}
Search terms to use: {', '.join(search_terms)}
Data fields to collect: {', '.join(data_fields)}

Generate a JSON array of search tasks for each major city in these states.
"""

        # Execute manager with Pro model
        manager_model = self.config.get("models", {}).get("manager", "gemini-2.5-pro")

        result = self.adapter.execute(
            prompt=prompt,
            model=manager_model,
            sop_content=self.sops.get("manager", ""),
            timeout=600
        )

        if not result.success:
            console.print(f"[red]Manager failed: {result.error}[/red]")
            return []

        # Parse tasks from manager output
        tasks = self._parse_manager_output(result.output)
        console.print(f"[green]Manager generated {len(tasks)} tasks[/green]\n")

        return tasks

    def _parse_manager_output(self, output: str) -> list[dict]:
        """Parse task list from manager output."""
        # Try direct JSON parse
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON array from text
        output = output.strip()
        if '[' in output:
            start = output.find('[')
            end = output.rfind(']') + 1
            if end > start:
                try:
                    return json.loads(output[start:end])
                except json.JSONDecodeError:
                    pass

        logger.warning("Could not parse manager output as JSON")
        return []

    def create_worker_tasks(self, task_dicts: list[dict]) -> list[Task]:
        """
        Convert task dictionaries to Task objects.

        Args:
            task_dicts: List of task dictionaries from manager

        Returns:
            List of Task objects ready for worker pool
        """
        tasks = []

        for task_dict in task_dicts:
            task_type = task_dict.get("task_type", "city_search")
            task_id = task_dict.get("task_id", f"task_{len(tasks)}")

            # Get appropriate SOP
            sop = self.sops.get(task_type, self.sops.get("city_search", ""))

            # Build prompt based on task type
            if task_type == "city_search":
                prompt = self._build_city_search_prompt(task_dict)
            elif task_type == "company_research":
                prompt = self._build_company_research_prompt(task_dict)
            else:
                prompt = json.dumps(task_dict)

            tasks.append(Task(
                task_id=task_id,
                task_type=task_type,
                prompt=prompt,
                sop_content=sop,
                metadata=task_dict
            ))

        return tasks

    def _build_city_search_prompt(self, task: dict) -> str:
        """Build prompt for city search task."""
        return f"""
Search for businesses in:
City: {task.get('city', '')}
State: {task.get('state', '')}
Industry: {task.get('industry', '')}

Search terms to use: {', '.join(task.get('search_terms', []))}
Data fields to collect: {', '.join(task.get('data_fields', []))}

Task ID: {task.get('task_id', '')}

Find and return information about relevant businesses in this city.
Output your findings as a JSON object following the format in your instructions.
"""

    def _build_company_research_prompt(self, task: dict) -> str:
        """Build prompt for company research task."""
        return f"""
Research this company:
Company Name: {task.get('company_name', '')}
Location: {task.get('city', '')}, {task.get('state', '')}
Industry: {task.get('industry', '')}

Task ID: {task.get('task_id', '')}

Gather detailed information about this company.
Output your findings as a JSON object following the format in your instructions.
"""

    def run_workers(self, tasks: list[Task]) -> list:
        """
        Run worker agents on the task list.

        Args:
            tasks: List of Task objects

        Returns:
            List of TaskResult objects
        """
        console.print(Panel(
            f"[bold cyan]Running Worker Agents[/bold cyan]\n"
            f"Executing {len(tasks)} tasks with {self.worker_pool.max_workers} parallel workers",
            title="Phase 2: Execution"
        ))

        # Get worker model
        worker_model = self.config.get("models", {}).get("worker", "gemini-2.5-flash")

        # Execute tasks
        results = self.worker_pool.execute_tasks(tasks, model=worker_model)

        # Print stats
        stats = self.worker_pool.get_stats(results)
        console.print(f"\n[green]Completed: {stats['successful']}/{stats['total_tasks']} tasks[/green]")
        if stats['failed'] > 0:
            console.print(f"[red]Failed: {stats['failed']} tasks[/red]")

        return results

    def run_aggregation(self) -> dict:
        """
        Run data aggregation.

        Returns:
            Aggregation summary
        """
        console.print(Panel(
            "[bold cyan]Aggregating Results[/bold cyan]",
            title="Phase 3: Aggregation"
        ))

        formats = self.config.get("output", {}).get("formats", ["json", "csv"])
        return self.aggregator.aggregate(export_formats=formats)

    def run(self, states: list[str], skip_aggregation: bool = False) -> dict:
        """
        Run the complete research workflow.

        Args:
            states: List of state abbreviations to research
            skip_aggregation: If True, skip the aggregation step

        Returns:
            Summary of the research run
        """
        console.print(Panel(
            f"[bold green]Market Research Agent[/bold green]\n"
            f"Target: {self.target.get('industry', 'General')}\n"
            f"States: {', '.join(states)}",
            title="Starting Research"
        ))

        # Check if CLI is available
        if not self.adapter.is_available():
            console.print("[red]Error: Gemini CLI is not available. Please install it first.[/red]")
            return {"error": "CLI not available"}

        # Phase 1: Manager planning
        task_dicts = self.run_manager(states)
        if not task_dicts:
            console.print("[yellow]No tasks generated by manager.[/yellow]")
            return {"error": "No tasks generated"}

        # Convert to Task objects
        tasks = self.create_worker_tasks(task_dicts)

        # Phase 2: Worker execution
        results = self.run_workers(tasks)
        worker_stats = self.worker_pool.get_stats(results)

        # Phase 3: Aggregation
        aggregation_summary = {}
        if not skip_aggregation:
            aggregation_summary = self.run_aggregation()

        # Final summary
        summary = {
            "states_researched": states,
            "tasks_generated": len(task_dicts),
            "tasks_executed": worker_stats["total_tasks"],
            "tasks_successful": worker_stats["successful"],
            "tasks_failed": worker_stats["failed"],
            "execution_time": worker_stats["total_time"],
            "aggregation": aggregation_summary
        }

        console.print(Panel(
            f"[bold green]Research Complete[/bold green]\n"
            f"Tasks: {worker_stats['successful']}/{worker_stats['total_tasks']} successful\n"
            f"Time: {worker_stats['total_time']:.1f}s\n"
            f"Records: {aggregation_summary.get('unique_records', 'N/A')}",
            title="Summary"
        ))

        return summary
