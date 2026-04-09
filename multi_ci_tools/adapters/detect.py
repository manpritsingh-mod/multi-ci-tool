"""Detection logic for CI adapters."""

import os
from typing import Mapping

from multi_ci_tools.adapters.base import CIAdapter
from multi_ci_tools.adapters.github import GitHubAdapter
from multi_ci_tools.adapters.jenkins import JenkinsAdapter
from multi_ci_tools.adapters.local import LocalAdapter


def detect_ci_adapter(env: Mapping[str, str] | None = None) -> CIAdapter:
    """Detect and return the appropriate CI adapter for the environment.
    
    Checks environments in a specific priority order:
    1. Jenkins
    2. GitHub Actions
    3. Local (fallback)
    """
    env_dict = dict(env) if env is not None else dict(os.environ)

    # Check specific CI platforms
    if JenkinsAdapter.detect(env_dict):
        return JenkinsAdapter(env_dict)
    
    if GitHubAdapter.detect(env_dict):
        return GitHubAdapter(env_dict)

    # Fallback
    return LocalAdapter(env_dict)
