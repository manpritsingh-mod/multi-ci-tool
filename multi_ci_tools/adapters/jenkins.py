"""Adapter for Jenkins."""

from multi_ci_tools.adapters.base import CIAdapter
from multi_ci_tools.types import CIContext


class JenkinsAdapter(CIAdapter):
    """Adapter for Jenkins environments."""

    @classmethod
    def detect(cls, env: dict[str, str]) -> bool:
        """Return True if JENKINS_URL is present."""
        return "JENKINS_URL" in env

    def get_context(self) -> CIContext:
        """Extract Jenkins-specific context from environment variables."""
        # Clean branch name
        branch = self.env.get("GIT_BRANCH", "unknown")
        if branch.startswith("origin/"):
            branch = branch[7:]
        
        pr_number = self.env.get("CHANGE_ID")
        is_pr = bool(pr_number)

        return CIContext(
            ci_name="jenkins",
            commit_sha=self.env.get("GIT_COMMIT", "unknown"),
            branch=branch,
            build_number=self.env.get("BUILD_NUMBER", "0"),
            build_url=self.env.get("BUILD_URL", f"{self.env.get('JENKINS_URL', '')}job/{self.env.get('JOB_NAME', '')}/{self.env.get('BUILD_NUMBER', '')}/"),
            workspace=self.env.get("WORKSPACE", ""),
            job_name=self.env.get("JOB_NAME", "unknown"),
            is_ci=True,
            is_pull_request=is_pr,
            pr_number=pr_number,
            capabilities=frozenset(["docker", "junit"]),
        )
