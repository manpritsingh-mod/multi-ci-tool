"""CLI entry point for Multi-CI-Tools.

Usage:
    python -m multi_ci_tools run [--stage ...] [--skip-stage ...] [--strict]
    python -m multi_ci_tools dry-run
    python -m multi_ci_tools inspect-env
    python -m multi_ci_tools doctor
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Sequence

from multi_ci_tools import __version__
from multi_ci_tools.types import RunConfig, StageName


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="multi_ci_tools",
        description="CI-agnostic pipeline execution SDK for Maven projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m multi_ci_tools run                    Run full pipeline\n"
            "  python -m multi_ci_tools run --stage build      Run build stage only\n"
            "  python -m multi_ci_tools run --skip-stage lint  Skip lint stage\n"
            "  python -m multi_ci_tools run --strict           Treat warnings as failures\n"
            "  python -m multi_ci_tools dry-run                Show what would run\n"
            "  python -m multi_ci_tools inspect-env            Show detected CI environment\n"
            "  python -m multi_ci_tools doctor                 Validate workspace & tools\n"
        ),
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- run ---
    run_parser = subparsers.add_parser(
        "run",
        help="Run the pipeline (all stages by default)",
    )
    run_parser.add_argument(
        "--stage",
        action="append",
        dest="stages",
        metavar="STAGE",
        help="Run only specific stage(s). Can be repeated.",
    )
    run_parser.add_argument(
        "--skip-stage",
        action="append",
        dest="skip_stages",
        metavar="STAGE",
        help="Skip specific stage(s). Can be repeated.",
    )
    run_parser.add_argument(
        "--strict",
        action="store_true",
        default=False,
        help="Promote warnings to failures",
    )
    run_parser.add_argument(
        "--emit-json",
        metavar="PATH",
        help="Write ci-result.json to this path",
    )
    run_parser.add_argument(
        "--emit-summary",
        metavar="PATH",
        help="Write summary.md to this path",
    )

    # --- dry-run ---
    subparsers.add_parser(
        "dry-run",
        help="Show what would run without executing",
    )

    # --- inspect-env ---
    subparsers.add_parser(
        "inspect-env",
        help="Print detected CI environment",
    )

    # --- doctor ---
    subparsers.add_parser(
        "doctor",
        help="Validate workspace, tools, and configuration",
    )

    return parser


def _resolve_stage_name(name: str) -> StageName:
    """Resolve a stage name string to StageName enum.

    Raises SystemExit with helpful message if invalid.
    """
    try:
        return StageName(name)
    except ValueError:
        valid = ", ".join(s.value for s in StageName)
        print(f"Error: Unknown stage '{name}'. Valid stages: {valid}", file=sys.stderr)
        sys.exit(1)


def _resolve_config_from_env(args: argparse.Namespace) -> RunConfig:
    """Build RunConfig from parsed CLI args + environment variables.

    Priority: CLI flags > env vars > defaults.
    """
    config = RunConfig()

    # CLI: --stage
    if getattr(args, "stages", None):
        config.stages_to_run = [_resolve_stage_name(s) for s in args.stages]

    # CLI: --skip-stage
    if getattr(args, "skip_stages", None):
        config.stages_to_skip = [_resolve_stage_name(s) for s in args.skip_stages]

    # CLI: --strict
    config.strict = getattr(args, "strict", False)

    # CLI: --emit-json / --emit-summary
    config.emit_json = getattr(args, "emit_json", None)
    config.emit_summary = getattr(args, "emit_summary", None)

    # Env vars (override defaults, CLI overrides these if specified)
    env = os.environ

    config.enable_lint = env.get("MCT_ENABLE_LINT", "true").lower() == "true"
    config.enable_smoke = env.get("MCT_ENABLE_SMOKE", "false").lower() == "true"
    config.lint_mode = "fail" if env.get("MCT_LINT_MODE", "warn") == "fail" else "warn"
    config.test_failure_mode = (
        "warn" if env.get("MCT_TEST_FAILURE_MODE", "fail") == "warn" else "fail"
    )
    config.smoke_command = env.get("MCT_SMOKE_COMMAND", config.smoke_command)

    timeout_str = env.get("MCT_TIMEOUT_SEC")
    if timeout_str and timeout_str.isdigit():
        config.timeout_seconds = int(timeout_str)

    retry_str = env.get("MCT_RETRY_RESOLVE_DEPS")
    if retry_str and retry_str.isdigit():
        config.retry_resolve_deps = int(retry_str)

    # Notification env vars
    config.slack_webhook_url = env.get("MCT_SLACK_WEBHOOK_URL", "")
    config.smtp_host = env.get("MCT_SMTP_HOST", "")

    smtp_port = env.get("MCT_SMTP_PORT", "587")
    config.smtp_port = int(smtp_port) if smtp_port.isdigit() else 587

    config.smtp_user = env.get("MCT_SMTP_USER", "")
    config.smtp_password = env.get("MCT_SMTP_PASSWORD", "")
    config.email_to = env.get("MCT_EMAIL_TO", "")

    return config


def _cmd_run(args: argparse.Namespace) -> int:
    """Execute the pipeline."""
    config = _resolve_config_from_env(args)
    print(f"multi-ci-tools v{__version__}")
    print(f"Config: strict={config.strict}, lint={config.enable_lint}, smoke={config.enable_smoke}")
    print()

    # Count stages that will run
    stages_planned = [s for s in StageName if config.should_run_stage(s)]
    print(f"Stages planned: {', '.join(s.value for s in stages_planned)}")
    print()

    # TODO: Phase 5 will implement PipelineOrchestrator here
    print("Pipeline orchestrator not yet implemented.")
    print("Run /gsd-plan-phase 5 to build it.")
    return 0


def _cmd_dry_run(_args: argparse.Namespace) -> int:
    """Show planned stages without executing."""
    config = _resolve_config_from_env(_args)

    print(f"multi-ci-tools v{__version__} — dry run")
    print(f"{'='*50}")
    print()

    for stage in StageName:
        will_run = config.should_run_stage(stage)
        marker = "▶" if will_run else "⏭"
        reason = ""
        if stage in config.stages_to_skip:
            reason = " (skipped via --skip-stage)"
        elif stage == StageName.SMOKE_TEST and not config.enable_smoke:
            reason = " (MCT_ENABLE_SMOKE not set)"
        elif stage == StageName.LINT and not config.enable_lint:
            reason = " (MCT_ENABLE_LINT=false)"
        print(f"  {marker} {stage.value}{reason}")

    print()
    print("No commands will be executed in dry-run mode.")
    return 0


def _cmd_inspect_env(_args: argparse.Namespace) -> int:
    """Print detected CI environment."""
    print(f"multi-ci-tools v{__version__} — environment inspection")
    print(f"{'='*50}")
    print()

    # TODO: Phase 2 will implement adapter detection here
    # For now, show raw env var detection
    env = os.environ

    if env.get("JENKINS_URL"):
        print("Detected CI: Jenkins")
        print(f"  JENKINS_URL:  {env.get('JENKINS_URL', 'not set')}")
        print(f"  BUILD_NUMBER: {env.get('BUILD_NUMBER', 'not set')}")
        print(f"  GIT_COMMIT:   {env.get('GIT_COMMIT', 'not set')}")
        print(f"  GIT_BRANCH:   {env.get('GIT_BRANCH', 'not set')}")
        print(f"  WORKSPACE:    {env.get('WORKSPACE', 'not set')}")
    elif env.get("GITHUB_ACTIONS") == "true":
        print("Detected CI: GitHub Actions")
        print(f"  GITHUB_SHA:        {env.get('GITHUB_SHA', 'not set')}")
        print(f"  GITHUB_REF_NAME:   {env.get('GITHUB_REF_NAME', 'not set')}")
        print(f"  GITHUB_RUN_NUMBER: {env.get('GITHUB_RUN_NUMBER', 'not set')}")
        print(f"  GITHUB_WORKSPACE:  {env.get('GITHUB_WORKSPACE', 'not set')}")
    else:
        print("Detected CI: Local (no CI environment detected)")
        print(f"  Working directory: {os.getcwd()}")

    print()
    return 0


def _cmd_doctor(_args: argparse.Namespace) -> int:
    """Validate workspace, tools, and configuration."""
    import shutil
    import subprocess

    print(f"multi-ci-tools v{__version__} — doctor")
    print(f"{'='*50}")
    print()

    checks_passed = 0
    checks_failed = 0

    def check(name: str, passed: bool, detail: str = "") -> None:
        nonlocal checks_passed, checks_failed
        marker = "✅" if passed else "❌"
        suffix = f" — {detail}" if detail else ""
        print(f"  {marker} {name}{suffix}")
        if passed:
            checks_passed += 1
        else:
            checks_failed += 1

    # Python version
    py_ver = sys.version_info
    check(
        "Python >= 3.10",
        py_ver >= (3, 10),
        f"Found {py_ver.major}.{py_ver.minor}.{py_ver.micro}",
    )

    # Java available
    java_path = shutil.which("java")
    if java_path:
        try:
            result = subprocess.run(
                ["java", "-version"],
                capture_output=True, text=True, timeout=10,
            )
            version_line = (result.stderr or result.stdout).split("\n")[0]
            check("Java available", True, version_line.strip())
        except Exception:
            check("Java available", False, "java found but version check failed")
    else:
        check("Java available", False, "java not found in PATH")

    # Maven available
    mvn_path = shutil.which("mvn") or shutil.which("mvn.cmd")
    if mvn_path:
        try:
            result = subprocess.run(
                ["mvn", "--version"],
                capture_output=True, text=True, timeout=10,
            )
            version_line = result.stdout.split("\n")[0]
            check("Maven available", True, version_line.strip())
        except Exception:
            check("Maven available", False, "mvn found but version check failed")
    else:
        check("Maven available", False, "mvn not found in PATH")

    # pom.xml exists
    pom_exists = os.path.isfile("pom.xml")
    check("pom.xml exists", pom_exists, os.getcwd())

    # Git available
    git_path = shutil.which("git")
    check("Git available", git_path is not None)

    print()
    print(f"Results: {checks_passed} passed, {checks_failed} failed")
    return 0 if checks_failed == 0 else 1


def main(argv: Sequence[str] | None = None) -> None:
    """Main entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "run": _cmd_run,
        "dry-run": _cmd_dry_run,
        "inspect-env": _cmd_inspect_env,
        "doctor": _cmd_doctor,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    exit_code = handler(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
