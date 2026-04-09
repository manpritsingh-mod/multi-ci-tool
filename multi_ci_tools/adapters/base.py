"""Base class for CI Adapters."""

import abc
import os
from contextlib import contextmanager
from typing import Iterator

from multi_ci_tools.types import CIContext


class CIAdapter(abc.ABC):
    """Abstract base class for all CI platform adapters.
    
    Adapters have two responsibilities:
    1. Normalize the CI environment into a standard CIContext object.
    2. Provide UI hints for log grouping native to the platform.
    """

    def __init__(self, env: dict[str, str] | None = None) -> None:
        """Initialize the adapter with an optional environment dict."""
        self.env = env if env is not None else dict(os.environ)

    @classmethod
    @abc.abstractmethod
    def detect(cls, env: dict[str, str]) -> bool:
        """Return True if the environment matches this CI platform."""
        pass

    @abc.abstractmethod
    def get_context(self) -> CIContext:
        """Extract and normalize context from the CI environment."""
        pass

    @contextmanager
    def log_group(self, name: str) -> Iterator[None]:
        """A context manager that creates a collapsible log group.
        
        Subclasses should override this to use platform-specific ANSI 
        sequences or special commands (e.g., `::group::` in GHA).
        """
        print(f"--- {name} ---")
        yield
        print(f"--- End {name} ---")
