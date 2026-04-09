# Multi-CI-Tools v1 Implementation Plan

## Summary
- Build a Python `3.10+` package and CLI under `multi_ci_tools` for Maven pipelines that run the same core logic on local machines, Jenkins, and GitHub Actions.
- This is a replacement plan for `implementation_plan.md`: it keeps the strong adapter idea, but narrows v1 so it is easier to implement, safer to operate, and less likely to drift across CI systems.
- Keep the SDK CI-agnostic and container-agnostic. CI wrappers own checkout, tool provisioning, artifact upload, and CI-native status presentation.

## Key Changes From Your Draft
- Remove `checkout` from the SDK pipeline. Checkout stays in Jenkins/GitHub Actions; the SDK starts at `preflight`.
- Drop repo YAML for v1. Configuration comes only from CLI flags and environment variables.
- Do not use `exit code 2 = UNSTABLE` as the process contract. The SDK emits a structured `PipelineResult`; wrappers translate that into Jenkins `UNSTABLE` or GitHub summaries/annotations.
- Keep adapter scope narrow: normalize CI context and provide optional log-group support only. Exporting variables and mutating build state are wrapper concerns, not core adapter requirements.
- Do not run unit and smoke tests in parallel inside one Maven workspace. Default to sequential execution; add CI-level fan-out later if parallelism is needed.
- Split build from test correctly. Default build command is `mvn -B -ntp -DskipTests package`, so tests are not run twice.
- Make smoke tests opt-in by default. Many Maven projects will not have a smoke profile on day one.
- Treat test failures as `fail` by default and lint violations as `warn` by default. Keep both policies configurable.
- Start with a smaller module surface instead of a ~50-file layout. The stable seams for v1 are `CIAdapter`, `BuildBackend`, `PipelineResult`, and `Notifier`.

## Implementation Changes
- Public CLI:
  - `python -m multi_ci_tools run [--stage ...] [--skip-stage ...] [--strict] [--emit-json path] [--emit-summary path]`
  - `python -m multi_ci_tools dry-run`
  - `python -m multi_ci_tools inspect-env`
  - `python -m multi_ci_tools doctor`
- Public config contract:
  - Core env vars: `MCT_ENABLE_LINT`, `MCT_ENABLE_SMOKE`, `MCT_LINT_MODE`, `MCT_TEST_FAILURE_MODE`, `MCT_TIMEOUT_SEC`, `MCT_RETRY_RESOLVE_DEPS`, `MCT_SMOKE_COMMAND`
  - Notification env vars: `MCT_SLACK_WEBHOOK_URL`, `MCT_SMTP_HOST`, `MCT_SMTP_PORT`, `MCT_SMTP_USER`, `MCT_SMTP_PASSWORD`, `MCT_EMAIL_TO`
- Core types/interfaces:
  - `CIContext` normalizes branch, SHA, build URL, workspace, job name, PR metadata, and CI capabilities.
  - `RunConfig` resolves CLI plus env defaults into one validated runtime config.
  - `BuildBackend` owns Maven commands, report paths, and backend-specific capability checks.
  - `StageResult` records `pass|warn|fail|skip`, duration, command metadata, and evidence paths.
  - `PipelineResult` is the machine-readable contract consumed by wrappers, summaries, and notifiers.
- Pipeline behavior:
  - `preflight` validates workspace, `pom.xml`, Java, Maven, and resolved config.
  - `resolve_deps` is an optional cache warm-up stage, retried only for retryable network failures.
  - `lint`, `build`, `unit_test`, `smoke_test`, `publish_summary`, and `notify` run in order, with `notify` always best-effort.
  - Command execution uses streaming subprocess handling, timeout enforcement, bounded capture, and secret redaction.
  - Every run writes `target/multi-ci/ci-result.json` and `target/multi-ci/summary.md` unless overridden.
- CI wrappers/examples:
  - Jenkins example runs the SDK, reads `ci-result.json`, archives reports, maps `warn` to `unstable()`, and maps `fail` to build failure.
  - GitHub Actions example uses `setup-java` and `setup-python`, writes annotations and `GITHUB_STEP_SUMMARY`, uploads artifacts, and fails only on hard failures or when `--strict` promotes warnings.
  - Jenkins container use stays optional at the wrapper layer. The SDK only assumes Java, Maven, and Python exist in the active environment.

## Test Plan
- Unit-test config parsing, adapter detection, branch normalization, PR metadata extraction, and severity-policy resolution.
- Unit-test the Maven backend so build commands skip tests, smoke stays opt-in, and report discovery works for both passing and failing suites.
- Unit-test the executor for streaming, timeout, large output truncation, retry policy, and secret redaction.
- Unit-test pipeline classification for missing `pom.xml`, missing tools, lint violations, failing tests, missing reports, notification failures, and `--strict` promotion.
- Add contract tests for `ci-result.json` and summary output so wrappers and notifications do not drift.
- Add wrapper tests or fixture-driven examples for Jenkins and GitHub Actions result translation.
- Add one integration fixture Maven project covering clean pass, lint warning, unit-test failure, smoke disabled, smoke enabled, and hard tool failure.

## Assumptions And Defaults
- Python minimum is `3.10+` so v1 avoids EOL runtimes while staying easy to provision on Jenkins and GitHub-hosted runners.
- V1 optimizes for a clean re-platform, not a literal Groovy port, because the original Groovy implementation is not present in this repo.
- Tests are part of the initial implementation, not a follow-up, because result classification and CI portability are the highest-risk areas.
- Per-stage timings and statuses are included in JSON, Markdown summary output, Slack, and email.
- Slack and email are included in v1, but both are best-effort and never change the pipeline result.
- CI status mapping intentionally does not rely on `exit 2 = unstable`; GitHub Actions treats any nonzero exit as failure and Jenkins needs explicit unstable handling. References: GitHub exit codes, GitHub workflow commands, Jenkins `sh` step, Jenkins `unstable` step.
