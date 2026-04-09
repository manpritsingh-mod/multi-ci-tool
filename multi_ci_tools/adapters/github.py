"""Adapter for GitHub Actions."""

import json
import os
from contextlib import contextmanager
from typing import Iterator

from multi_ci_tools.adapters.base import CIAdapter
from multi_ci_tools.types import CIContext


class GitHubAdapter(CIAdapter):
    """Adapter for GitHub Actions environments."""

    @classmethod
    def detect(cls, env: dict[str, str]) -> bool:
        """Return True if GITHUB_ACTIONS is present."""
        return env.get("GITHUB_ACTIONS") == "true"

    def get_context(self) -> CIContext:
        """Extract GitHub-specific context from environment variables."""
        # Clean branch name
        branch = self.env.get("GITHUB_REF_NAME", "unknown")
        
        # Check for PR event payload
        is_pr = self.env.get("GITHUB_EVENT_NAME") == "pull_request"
        pr_number = None

        if is_pr:
            event_path = self.env.get("GITHUB_EVENT_PATH")
            if event_path and os.path.isfile(event_path):
                try:
                    with open(event_path, "r", encoding="utf-8") as f:
                        event_data = json.load(f)
                        pr_number = str(event_data.get("pull_request", {}).get("number", ""))
                except Exception:
                    pass

        server_url = self.env.get("GITHUB_SERVER_URL", "https://github.com")
        repo = self.env.get("GITHUB_REPOSITORY", "")
        run_id = self.env.get("GITHUB_RUN_ID", "")
        
        build_url = ""
        if repo and run_id:
            build_url = f"{server_url}/{repo}/actions/runs/{run_id}"

        return CIContext(
            ci_name="github_actions",
            commit_sha=self.env.get("GITHUB_SHA", "unknown"),
            branch=branch,
            build_number=self.env.get("GITHUB_RUN_NUMBER", "0"),
            build_url=build_url,
            workspace=self.env.get("GITHUB_WORKSPACE", ""),
            job_name=self.env.get("GITHUB_WORKFLOW", "unknown"),
            is_ci=True,
            is_pull_request=is_pr,
            pr_number=pr_number if pr_number else None,
            capabilities=frozenset(["annotations", "step_summary"]),
        )

    @contextmanager
    def log_group(self, name: str) -> Iterator[None]:
        """Use GitHub Actions native log grouping sequences."""
        print(f"::group::{name}")
        try:
            yield
        finally:
            print("::endgroup::")
