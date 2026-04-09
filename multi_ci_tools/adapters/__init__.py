"""CI Platform Adapters.

Adapters normalize the environment into a standard CIContext object
and provide CI-specific logging groups.
"""

from multi_ci_tools.adapters.base import CIAdapter
from multi_ci_tools.adapters.detect import detect_ci_adapter
from multi_ci_tools.adapters.github import GitHubAdapter
from multi_ci_tools.adapters.jenkins import JenkinsAdapter
from multi_ci_tools.adapters.local import LocalAdapter

__all__ = [
    "CIAdapter",
    "LocalAdapter",
    "JenkinsAdapter",
    "GitHubAdapter",
    "detect_ci_adapter",
]
