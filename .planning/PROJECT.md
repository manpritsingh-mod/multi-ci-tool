# Multi-CI-Tools

## What This Is

A production-grade Python SDK that provides a single, unified business logic layer for CI/CD pipelines. It runs identically on Jenkins, GitHub Actions, and local developer machines from a single codebase. The initial implementation focuses on Maven (Java) projects as the reference build backend.

## Core Value

The Python SDK is the single source of truth for pipeline logic — every CI system is a thin wrapper that triggers `python -m multi_ci_tools run` and reads the structured result.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] REQ-ADAPT-01: SDK auto-detects CI platform (Jenkins, GitHub Actions, local) and normalizes environment
- [ ] REQ-ADAPT-02: Adapter provides collapsible log groups native to each CI platform
- [ ] REQ-CLI-01: CLI supports `run`, `dry-run`, `inspect-env`, and `doctor` subcommands
- [ ] REQ-CLI-02: CLI accepts `--stage`, `--skip-stage`, `--strict`, `--emit-json`, `--emit-summary` flags
- [ ] REQ-PIPE-01: Pipeline executes stages in order: preflight → resolve_deps → lint → build → unit_test → smoke_test → publish → notify
- [ ] REQ-PIPE-02: Stage results are classified as pass/warn/fail/skip
- [ ] REQ-PIPE-03: Pipeline produces machine-readable `ci-result.json` and human-readable `summary.md`
- [ ] REQ-MVN-01: Maven backend generates correct CLI commands for build, test, lint, and smoke
- [ ] REQ-MVN-02: Build command uses `-DskipTests` to prevent double test execution
- [ ] REQ-MVN-03: Smoke tests are opt-in via `MCT_ENABLE_SMOKE=true`
- [ ] REQ-EXEC-01: Command executor streams stdout in real-time to CI console
- [ ] REQ-EXEC-02: Commands enforce configurable timeout with clean process kill
- [ ] REQ-EXEC-03: Dependency resolution retries on transient network failures
- [ ] REQ-EXEC-04: Executor redacts secrets from command output
- [ ] REQ-REPORT-01: JUnit XML parser extracts test counts from surefire reports
- [ ] REQ-REPORT-02: Lint violation count extracted from checkstyle XML
- [ ] REQ-NOTIFY-01: Console notification always runs (build summary to stdout)
- [ ] REQ-NOTIFY-02: Slack notification via webhook URL (best-effort, never crashes pipeline)
- [ ] REQ-NOTIFY-03: Email notification via SMTP (best-effort, never crashes pipeline)
- [ ] REQ-WRAP-01: Jenkins wrapper reads ci-result.json, maps warn→unstable(), fail→build failure
- [ ] REQ-WRAP-02: GitHub Actions wrapper writes GITHUB_STEP_SUMMARY and uploads artifacts
- [ ] REQ-WRAP-03: Jenkins wrapper supports Docker container execution for Maven builds
- [ ] REQ-TEST-01: Full pytest test suite covering adapters, executor, pipeline, reporting, and notifications
- [ ] REQ-TEST-02: Contract tests for ci-result.json schema stability

### Out of Scope

- Multi-language support (Python, React, Node.js, Gradle) — v2 feature, design for extensibility but don't implement
- Mobile builds (React Native, iOS, IPA/APK) — different problem domain
- Docker orchestration within SDK — CI wrappers own container lifecycle
- `ci-config.yaml` file — v1 uses CLI flags + env vars only; YAML config added later if needed
- Parallel test execution within SDK — sequential by default; CI-level fan-out later
- Allure report generation — replaced by structured ci-result.json + summary.md

## Context

- **Origin**: Port of `My_UnifiedCI` Jenkins shared library (Groovy) to CI-agnostic Python SDK
- **Existing codebase**: `src/*.groovy` command generators (MavenScript, GradleScript, etc.) + `vars/*.groovy` pipeline templates
- **Key insight**: ~75% of Groovy logic is pure string generation, directly portable to Python
- **Non-portable**: Jenkins DSL (`sh`, `stage`, `parallel`, `docker.withRegistry()`) — replaced by Python `subprocess` + adapter pattern
- **User's environment**: Windows dev machine, Jenkins agents, GitHub Actions runners
- **Team familiarity**: DevOps background with Groovy/Jenkins, moving to Python

## Constraints

- **Python version**: 3.10+ required (match/case syntax, modern type hints)
- **Zero required deps**: Core SDK uses only Python stdlib. Optional: pydantic, tenacity
- **CI runner compatibility**: Must work on Ubuntu (GHA), various Jenkins agents, Windows (local dev)
- **Backward compatible config**: MCT_* env vars for all configuration, matching existing ci-config.yaml concepts
- **Exit code contract**: SDK always exits 0. Success/warn/fail communicated via `ci-result.json` — wrappers translate to CI-native states

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python 3.10+ minimum | match/case syntax, modern type hints, all CI runners support it | — Pending |
| Package name: `multi_ci_tools` | Matches repository name | — Pending |
| Narrow adapter scope | Adapter only normalizes env + log groups. Build status, artifacts, annotations stay in CI wrappers | — Pending |
| No exit code 2 for UNSTABLE | GHA treats any nonzero as failure. Use structured PipelineResult JSON instead | — Pending |
| Sequential test execution | Parallel in single Maven workspace causes classpath conflicts. CI-level fan-out later | — Pending |
| Build with -DskipTests | Prevents running tests twice (build + test stages) | — Pending |
| Smoke tests opt-in | Most Maven projects don't have a smoke profile on day one | — Pending |
| Lint violations → warn (default) | Less disruptive; configurable via MCT_LINT_MODE=fail | — Pending |
| Test failures → fail (default) | Safer; configurable via MCT_TEST_FAILURE_MODE=warn for UNSTABLE behavior | — Pending |
| Docker in Jenkins wrapper | Jenkins wrapper handles docker.withRegistry() + image.inside() for Maven image | — Pending |
| GSD workflow for development | Atomic commits, code review, verification per phase | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-10 after initialization*
