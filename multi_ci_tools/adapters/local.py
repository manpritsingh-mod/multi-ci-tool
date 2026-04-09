"""Adapter for Local execution (fallback)."""

import os
from contextlib import contextmanager
from typing import Iterator

from multi_ci_tools.adapters.base import CIAdapter
from multi_ci_tools.types import CIContext


class LocalAdapter(CIAdapter):
    """Fallback adapter for local developer environments.
    
    Extracts minimal context since no CI is running.
    """

    @classmethod
    def detect(cls, env: dict[str, str]) -> bool:
        """Local is the fallback, so it's always True when asked."""
        return True

    def get_context(self) -> CIContext:
        """Get minimal local context."""
        return CIContext(
            ci_name="local",
            commit_sha="local",
            branch="local",
            build_number="0",
            build_url="",
            workspace=os.getcwd(),
            job_name="local-run",
            is_ci=False,
            is_pull_request=False,
            capabilities=frozenset(),
        )

    @contextmanager
    def log_group(self, name: str) -> Iterator[None]:
        """Local console doesn't support collapsing, so just use simple dividers."""
        print(f"\n[{name}]")
        print("=" * 60)
        try:
            yield
        finally:
            print("-" * 60)
