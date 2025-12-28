"""
Gemini CLI adapter implementation.

This module provides a subprocess-based wrapper for the Gemini CLI tool.
It handles executing prompts, model selection, and capturing output.
"""

import subprocess
import shutil
from typing import Optional

from .base import CLIAdapter, ExecutionResult


class GeminiAdapter(CLIAdapter):
    """Adapter for Google's Gemini CLI tool."""

    # Available Gemini models
    MODELS = [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ]

    def __init__(self, default_model: str = "gemini-2.5-flash"):
        """
        Initialize the Gemini adapter.

        Args:
            default_model: Default model to use
        """
        super().__init__(default_model)
        self._cli_path = self._find_cli()

    def _find_cli(self) -> Optional[str]:
        """Find the Gemini CLI executable."""
        return shutil.which("gemini")

    def is_available(self) -> bool:
        """Check if Gemini CLI is installed."""
        if not self._cli_path:
            return False

        try:
            result = subprocess.run(
                [self._cli_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_available_models(self) -> list[str]:
        """Get list of available Gemini models."""
        return self.MODELS.copy()

    def execute(
        self,
        prompt: str,
        model: Optional[str] = None,
        sop_content: Optional[str] = None,
        timeout: int = 600
    ) -> ExecutionResult:
        """
        Execute a prompt using Gemini CLI.

        Args:
            prompt: The prompt to send
            model: Model to use (overrides default)
            sop_content: Optional SOP content to prepend
            timeout: Timeout in seconds

        Returns:
            ExecutionResult with output and status
        """
        if not self._cli_path:
            return ExecutionResult(
                output="",
                success=False,
                error="Gemini CLI not found. Please install it first.",
                exit_code=-1
            )

        # Build the full prompt with SOP if provided
        full_prompt = self.build_prompt_with_sop(prompt, sop_content)

        # Build command
        model_to_use = model or self.default_model
        cmd = [
            self._cli_path,
            "--model", model_to_use,
            "--prompt", full_prompt
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                return ExecutionResult(
                    output=result.stdout.strip(),
                    success=True,
                    exit_code=0
                )
            else:
                return ExecutionResult(
                    output=result.stdout.strip(),
                    success=False,
                    error=result.stderr.strip() or "Command failed",
                    exit_code=result.returncode
                )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                output="",
                success=False,
                error=f"Command timed out after {timeout} seconds",
                exit_code=-1
            )
        except Exception as e:
            return ExecutionResult(
                output="",
                success=False,
                error=str(e),
                exit_code=-1
            )

    def execute_with_web_search(
        self,
        prompt: str,
        model: Optional[str] = None,
        sop_content: Optional[str] = None,
        timeout: int = 600
    ) -> ExecutionResult:
        """
        Execute a prompt with web search capabilities enabled.

        This prepends the @web tool indicator to enable web search.

        Args:
            prompt: The prompt to send
            model: Model to use (overrides default)
            sop_content: Optional SOP content to prepend
            timeout: Timeout in seconds

        Returns:
            ExecutionResult with output and status
        """
        # Add web search indicator to prompt
        web_prompt = f"@web {prompt}"
        return self.execute(web_prompt, model, sop_content, timeout)
