"""Core type definitions for Multi-CI-Tools.

These types define the stable interfaces between SDK components.
CIContext is the adapter's output contract.
StageResult captures individual stage outcomes.
PipelineResult is the machine-readable contract consumed by CI wrappers.
RunConfig resolves CLI flags + env vars into validated runtime config.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Literal


class StageStatus(str, Enum):
    """Possible outcomes for a pipeline stage."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


class StageName(str, Enum):
    """Pipeline stage identifiers in execution order."""

    PREFLIGHT = "preflight"
    RESOLVE_DEPS = "resolve_deps"
    LINT = "lint"
    BUILD = "build"
    UNIT_TEST = "unit_test"
    SMOKE_TEST = "smoke_test"
    PUBLISH = "publish"
    NOTIFY = "notify"


class StageState(str, Enum):
    """Execution state of a pipeline stage."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class StageType(str, Enum):
    """Types of pipeline stages."""

    SETUP = "setup"
    BUILD = "build"
    TEST = "test"
    PUBLISH = "publish"
    NOTIFY = "notify"


@dataclass(frozen=True)
class TestSummary:
    """Summary of test execution results."""

    total: int
    passed: int
    failed: int
    skipped: int


@dataclass(frozen=True)
class LintSummary:
    """Summary of lint/code quality violations."""

    total_violations: int
    errors: int
    warnings: int
    infos: int


@dataclass(frozen=True)
class CIContext:
    """Normalized CI context — the adapter's output contract.

    Every adapter (Jenkins, GitHub Actions, Local) produces this
    identical structure. No downstream code ever checks which CI
    platform is running.
    """

    ci_name: str
    commit_sha: str
    branch: str
    build_number: str
    build_url: str
    workspace: str
    job_name: str
    is_ci: bool
    is_pull_request: bool
    pr_number: str | None = None
    capabilities: frozenset[str] = field(default_factory=frozenset)

    def to_dict(self) -> dict[str, object]:
        """Convert to JSON-serializable dictionary."""
        return {
            "ci_name": self.ci_name,
            "commit_sha": self.commit_sha,
            "branch": self.branch,
            "build_number": self.build_number,
            "build_url": self.build_url,
            "workspace": self.workspace,
            "job_name": self.job_name,
            "is_ci": self.is_ci,
            "is_pull_request": self.is_pull_request,
            "pr_number": self.pr_number,
            "capabilities": sorted(self.capabilities),
        }


@dataclass
class CommandResult:
    """Result of a single subprocess execution."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False

    @property
    def success(self) -> bool:
        """Check if command exited cleanly."""
        return self.exit_code == 0


@dataclass
class StageResult:
    """Outcome of a single pipeline stage."""

    name: str
    status: StageStatus
    duration_seconds: float
    error_message: str = ""
    command_results: list[CommandResult] = field(default_factory=list)
    evidence_paths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Convert to JSON-serializable dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "duration_seconds": round(self.duration_seconds, 2),
            "error_message": self.error_message,
            "evidence_paths": self.evidence_paths,
        }


@dataclass
class PipelineResult:
    """Machine-readable pipeline outcome consumed by CI wrappers.

    This is the primary contract between the SDK and CI wrappers.
    Wrappers read ci-result.json and translate to CI-native states:
    - Jenkins: warn -> unstable(), fail -> build failure
    - GHA: warn -> annotations, fail -> exit 1
    """

    overall: StageStatus
    stages: list[StageResult]
    ci_context: CIContext
    duration_seconds: float
    test_summary: TestSummary | None = None
    lint_summary: LintSummary | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_dict(self) -> dict[str, object]:
        """
        Build a JSON-serializable mapping representing this PipelineResult.
        
        Returns:
            dict[str, object]: A dictionary containing:
                - "overall": stage status as a string value,
                - "stages": list of stage dictionaries (each from StageResult.to_dict()),
                - "ci_context": CI context as a dictionary,
                - "duration_seconds": total duration rounded to 2 decimals,
                - "timestamp": ISO 8601 timestamp string,
                - "test_summary" (optional): object with keys "total", "passed", "failed", "skipped" when test_summary is present,
                - "lint_summary" (optional): object with keys "total_violations", "errors", "warnings", "infos" when lint_summary is present.
        """
        result_dict = {
            "overall": self.overall.value,
            "stages": [s.to_dict() for s in self.stages],
            "ci_context": self.ci_context.to_dict(),
            "duration_seconds": round(self.duration_seconds, 2),
            "timestamp": self.timestamp,
        }

        # Include test and lint summaries if available
        if self.test_summary is not None:
            result_dict["test_summary"] = {
                "total": self.test_summary.total,
                "passed": self.test_summary.passed,
                "failed": self.test_summary.failed,
                "skipped": self.test_summary.skipped,
            }

        if self.lint_summary is not None:
            result_dict["lint_summary"] = {
                "total_violations": self.lint_summary.total_violations,
                "errors": self.lint_summary.errors,
                "warnings": self.lint_summary.warnings,
                "infos": self.lint_summary.infos,
            }

        return result_dict

    def to_summary_md(self) -> str:
        """
        Generate a markdown-formatted build summary for the pipeline result.
        
        Returns:
            md (str): A markdown string containing:
                - A header with the CI job name and an overall status badge.
                - A "CI Context" section with platform, branch, short commit SHA, and build number.
                - A "Stage Results" table listing each stage's name, emoji status, duration, and details.
                - An optional "Test & Lint Summary" section (included when test or lint summaries are present) showing test counts and passed percentage and lint violation counts.
                - Total duration and timestamp.
        """
        lines: list[str] = []
        lines.append(f"# Build Summary — {self.ci_context.job_name}")
        lines.append("")

        # Status badge
        status_emoji = {"pass": "✅", "warn": "⚠️", "fail": "❌", "skip": "⏭️"}
        overall_emoji = status_emoji.get(self.overall.value, "❓")
        lines.append(f"**Overall: {overall_emoji} {self.overall.value.upper()}**")
        lines.append("")

        # CI context
        lines.append("## CI Context")
        lines.append(f"- **Platform:** {self.ci_context.ci_name}")
        lines.append(f"- **Branch:** {self.ci_context.branch}")
        lines.append(f"- **Commit:** `{self.ci_context.commit_sha[:8]}`")
        lines.append(f"- **Build:** {self.ci_context.build_number}")
        lines.append("")

        # Stage results table
        lines.append("## Stage Results")
        lines.append("")
        lines.append("| Stage | Status | Duration | Details |")
        lines.append("|-------|--------|----------|---------|")
        for stage in self.stages:
            emoji = status_emoji.get(stage.status.value, "❓")
            dur = f"{stage.duration_seconds:.1f}s"
            detail = stage.error_message or "—"
            lines.append(f"| {stage.name} | {emoji} {stage.status.value} | {dur} | {detail} |")
        lines.append("")

        # Test & Lint Summary
        if self.test_summary is not None or self.lint_summary is not None:
            lines.append("## Test & Lint Summary")
            lines.append("")

            if self.test_summary is not None:
                passed_pct = (
                    (self.test_summary.passed / self.test_summary.total * 100)
                    if self.test_summary.total > 0
                    else 0
                )
                lines.append(
                    f"- **Tests:** {self.test_summary.passed}/{self.test_summary.total} passed "
                    f"({passed_pct:.0f}%)"
                )
                lines.append(f"  - ✅ Passed: {self.test_summary.passed}")
                lines.append(f"  - ❌ Failed: {self.test_summary.failed}")
                lines.append(f"  - ⏭️ Skipped: {self.test_summary.skipped}")
                lines.append("")

            if self.lint_summary is not None:
                lines.append(f"- **Lint Violations:** {self.lint_summary.total_violations}")
                lines.append(f"  - 🛑 Errors: {self.lint_summary.errors}")
                lines.append(f"  - ⚠️ Warnings: {self.lint_summary.warnings}")
                lines.append(f"  - ℹ️ Infos: {self.lint_summary.infos}")
                lines.append("")

        # Timing
        lines.append(f"**Total Duration:** {self.duration_seconds:.1f}s")
        lines.append(f"**Timestamp:** {self.timestamp}")
        lines.append("")

        return "\n".join(lines)


@dataclass
class RunConfig:
    """Resolved runtime configuration from CLI flags + env vars.

    Priority: CLI flags > env vars > defaults.
    """

    # Stage control
    stages_to_run: list[StageName] = field(
        default_factory=lambda: list(StageName)
    )
    stages_to_skip: list[StageName] = field(default_factory=list)
    strict: bool = False

    # Maven settings
    enable_lint: bool = True
    enable_smoke: bool = False
    lint_mode: Literal["warn", "fail"] = "warn"
    test_failure_mode: Literal["warn", "fail"] = "fail"
    smoke_command: str = "mvn -B -ntp test -Psmoke"

    # Execution settings
    timeout_seconds: int = 600
    retry_resolve_deps: int = 2

    # Output paths
    emit_json: str | None = None
    emit_summary: str | None = None

    # Notification
    slack_webhook_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_to: str = ""

    def should_run_stage(self, stage: StageName) -> bool:
        """Determine if a specific stage should execute."""
        if stage in self.stages_to_skip:
            return False

        # If specific stages requested, only run those + always-run stages
        always_run = {StageName.PUBLISH, StageName.NOTIFY}
        if self.stages_to_run != list(StageName):
            return stage in self.stages_to_run or stage in always_run

        # Smoke tests need explicit opt-in
        if stage == StageName.SMOKE_TEST and not self.enable_smoke:
            return False

        # Lint can be disabled
        if stage == StageName.LINT and not self.enable_lint:
            return False

        return True
