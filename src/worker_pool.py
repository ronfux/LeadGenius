"""
Worker Pool for parallel task execution.

This module manages a pool of worker subprocesses that execute research tasks
in parallel using the Gemini CLI.
"""

import json
import time
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.console import Console

from .cli_adapters.base import CLIAdapter, ExecutionResult


logger = logging.getLogger(__name__)
console = Console()


@dataclass
class Task:
    """A research task to be executed by a worker."""
    task_id: str
    task_type: str  # "city_search" or "company_research"
    prompt: str
    sop_content: str
    metadata: dict = field(default_factory=dict)


@dataclass
class TaskResult:
    """Result from executing a task."""
    task_id: str
    success: bool
    output: Optional[str] = None
    parsed_data: Optional[dict] = None
    error: Optional[str] = None
    execution_time: float = 0.0


class WorkerPool:
    """
    Manages parallel execution of research tasks.

    Uses ThreadPoolExecutor to run multiple CLI subprocesses concurrently.
    Each worker is a separate thread that spawns a subprocess to call the CLI.
    """

    def __init__(
        self,
        adapter: CLIAdapter,
        max_workers: int = 10,
        output_dir: Optional[Path] = None,
        spawn_delay: float = 0.5
    ):
        """
        Initialize the worker pool.

        Args:
            adapter: CLI adapter to use for execution
            max_workers: Maximum concurrent workers
            output_dir: Directory to save individual task outputs
            spawn_delay: Delay between spawning workers (rate limiting)
        """
        self.adapter = adapter
        self.max_workers = max_workers
        self.output_dir = output_dir or Path("data/outputs")
        self.spawn_delay = spawn_delay

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def execute_task(self, task: Task, model: Optional[str] = None) -> TaskResult:
        """
        Execute a single task.

        Args:
            task: The task to execute
            model: Model to use (optional override)

        Returns:
            TaskResult with execution results
        """
        start_time = time.time()

        try:
            # Execute via CLI adapter
            result = self.adapter.execute_with_web_search(
                prompt=task.prompt,
                model=model,
                sop_content=task.sop_content,
                timeout=600
            )

            execution_time = time.time() - start_time

            if not result.success:
                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    error=result.error,
                    execution_time=execution_time
                )

            # Try to parse output as JSON
            parsed_data = None
            try:
                parsed_data = json.loads(result.output)
            except json.JSONDecodeError:
                # Output might not be pure JSON, try to extract JSON
                parsed_data = self._extract_json(result.output)

            # Save result to file
            self._save_result(task.task_id, result.output, parsed_data)

            return TaskResult(
                task_id=task.task_id,
                success=True,
                output=result.output,
                parsed_data=parsed_data,
                execution_time=execution_time
            )

        except Exception as e:
            logger.exception(f"Error executing task {task.task_id}")
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )

    def _extract_json(self, text: str) -> Optional[dict]:
        """
        Try to extract JSON from text that might have other content.

        Args:
            text: Text that might contain JSON

        Returns:
            Parsed JSON dict or None
        """
        # Try to find JSON array or object in the text
        text = text.strip()

        # Look for JSON array
        if '[' in text:
            start = text.find('[')
            end = text.rfind(']') + 1
            if end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass

        # Look for JSON object
        if '{' in text:
            start = text.find('{')
            end = text.rfind('}') + 1
            if end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass

        return None

    def _save_result(
        self,
        task_id: str,
        raw_output: str,
        parsed_data: Optional[dict]
    ) -> None:
        """
        Save task result to file.

        Args:
            task_id: Task identifier
            raw_output: Raw CLI output
            parsed_data: Parsed JSON data (if available)
        """
        # Save raw output
        raw_file = self.output_dir / f"{task_id}_raw.txt"
        raw_file.write_text(raw_output)

        # Save parsed JSON if available
        if parsed_data:
            json_file = self.output_dir / f"{task_id}.json"
            json_file.write_text(json.dumps(parsed_data, indent=2))

    def execute_tasks(
        self,
        tasks: list[Task],
        model: Optional[str] = None,
        on_complete: Optional[Callable[[TaskResult], None]] = None
    ) -> list[TaskResult]:
        """
        Execute multiple tasks in parallel.

        Args:
            tasks: List of tasks to execute
            model: Model to use for all tasks
            on_complete: Callback function called when each task completes

        Returns:
            List of TaskResults
        """
        results = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:

            task_id = progress.add_task(
                f"[cyan]Executing {len(tasks)} tasks...",
                total=len(tasks)
            )

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_task = {}
                for i, task in enumerate(tasks):
                    if i > 0:
                        time.sleep(self.spawn_delay)  # Rate limiting

                    future = executor.submit(self.execute_task, task, model)
                    future_to_task[future] = task

                # Collect results as they complete
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        result = future.result()
                        results.append(result)

                        # Update progress
                        status = "[green]✓" if result.success else "[red]✗"
                        progress.update(
                            task_id,
                            advance=1,
                            description=f"{status} {task.task_id}"
                        )

                        # Call completion callback
                        if on_complete:
                            on_complete(result)

                        if result.success:
                            logger.info(
                                f"Task {task.task_id} completed in {result.execution_time:.1f}s"
                            )
                        else:
                            logger.warning(
                                f"Task {task.task_id} failed: {result.error}"
                            )

                    except Exception as e:
                        logger.exception(f"Error collecting result for {task.task_id}")
                        results.append(TaskResult(
                            task_id=task.task_id,
                            success=False,
                            error=str(e)
                        ))
                        progress.update(task_id, advance=1)

        return results

    def get_stats(self, results: list[TaskResult]) -> dict:
        """
        Calculate statistics from task results.

        Args:
            results: List of TaskResults

        Returns:
            Dictionary of statistics
        """
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        total_time = sum(r.execution_time for r in results)
        avg_time = total_time / len(results) if results else 0

        return {
            "total_tasks": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(results) * 100 if results else 0,
            "total_time": total_time,
            "average_time": avg_time,
            "failed_task_ids": [r.task_id for r in failed]
        }
