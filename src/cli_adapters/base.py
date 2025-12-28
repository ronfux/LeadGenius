"""
Abstract base class for CLI adapters.

This module defines the interface that all CLI adapters must implement.
Adapters wrap different AI CLI tools (Gemini, Claude, etc.) with a common interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionResult:
    """Result from executing a CLI command."""
    output: str
    success: bool
    error: Optional[str] = None
    exit_code: int = 0


class CLIAdapter(ABC):
    """Abstract base class for AI CLI adapters."""

    def __init__(self, default_model: str):
        """
        Initialize the adapter.

        Args:
            default_model: The default model to use for execution
        """
        self.default_model = default_model

    @abstractmethod
    def execute(
        self,
        prompt: str,
        model: Optional[str] = None,
        sop_content: Optional[str] = None,
        timeout: int = 600
    ) -> ExecutionResult:
        """
        Execute a prompt using the CLI tool.

        Args:
            prompt: The prompt to send to the AI
            model: Model to use (overrides default)
            sop_content: Optional SOP content to prepend to the prompt
            timeout: Timeout in seconds for the execution

        Returns:
            ExecutionResult containing the output and status
        """
        pass

    @abstractmethod
    def get_available_models(self) -> list[str]:
        """
        Get list of available models for this CLI.

        Returns:
            List of model identifiers
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the CLI tool is installed and accessible.

        Returns:
            True if the CLI is available, False otherwise
        """
        pass

    def build_prompt_with_sop(self, prompt: str, sop_content: Optional[str]) -> str:
        """
        Combine SOP content with the prompt.

        Args:
            prompt: The main prompt
            sop_content: Optional SOP instructions

        Returns:
            Combined prompt string
        """
        if sop_content:
            return f"{sop_content}\n\n---\n\n{prompt}"
        return prompt
