# Requirements: Multi-CI-Tools v1.0

## v1 Requirements

### CI Adapter
- [ ] **ADAPT-01**: SDK auto-detects CI platform (Jenkins via `JENKINS_URL`, GitHub Actions via `GITHUB_ACTIONS`, local fallback)
- [ ] **ADAPT-02**: Adapter normalizes commit SHA, branch, build number, workspace, build URL, job name, PR status
- [ ] **ADAPT-03**: Adapter provides collapsible log groups (GHA `::group::`, Jenkins ANSI, local plain)
- [ ] **ADAPT-04**: Branch name normalization strips `origin/`, `refs/heads/` prefixes
- [ ] **ADAPT-05**: Detached HEAD falls back to commit SHA when branch unavailable

### CLI Interface
- [ ] **CLI-01**: `python -m multi_ci_tools run` executes full pipeline
- [ ] **CLI-02**: `python -m multi_ci_tools run --stage <name>` runs single stage
- [ ] **CLI-03**: `python -m multi_ci_tools run --skip-stage <name>` skips stage
- [ ] **CLI-04**: `python -m multi_ci_tools run --strict` promotes warnings to failures
- [ ] **CLI-05**: `python -m multi_ci_tools run --emit-json <path>` outputs structured result
- [ ] **CLI-06**: `python -m multi_ci_tools run --emit-summary <path>` outputs markdown summary
- [ ] **CLI-07**: `python -m multi_ci_tools dry-run` shows planned stages without executing
- [ ] **CLI-08**: `python -m multi_ci_tools inspect-env` prints detected CI context
- [ ] **CLI-09**: `python -m multi_ci_tools doctor` validates workspace, tools, config

### Pipeline Orchestrator
- [ ] **PIPE-01**: Executes stages in order: preflight → resolve_deps → lint → build → unit_test → smoke_test → publish → notify
- [ ] **PIPE-02**: Stage results classified as pass/warn/fail/skip
- [ ] **PIPE-03**: Overall pipeline result is worst stage result (fail > warn > pass)
- [ ] **PIPE-04**: Notify stage always runs regardless of earlier failures
- [ ] **PIPE-05**: Publish stage always runs regardless of earlier failures

### Maven Backend
- [ ] **MVN-01**: Build command: `mvn -B -ntp -DskipTests package`
- [ ] **MVN-02**: Unit test command: `mvn -B -ntp test`
- [ ] **MVN-03**: Lint command: `mvn -B -ntp checkstyle:check`
- [ ] **MVN-04**: Dependency resolve: `mvn -B -ntp dependency:resolve`
- [ ] **MVN-05**: Smoke test command configurable via `MCT_SMOKE_COMMAND` (default: `mvn -B -ntp test -Psmoke`)
- [ ] **MVN-06**: Smoke tests only run when `MCT_ENABLE_SMOKE=true`
- [ ] **MVN-07**: Report paths resolve correctly (surefire, checkstyle XML)

### Command Executor
- [ ] **EXEC-01**: Real-time stdout streaming to CI console (not buffered)
- [ ] **EXEC-02**: Configurable timeout with clean process kill (`MCT_TIMEOUT_SEC`, default 600)
- [ ] **EXEC-03**: Retry with exponential backoff for transient failures (`MCT_RETRY_RESOLVE_DEPS`, default 2)
- [ ] **EXEC-04**: Secret redaction from command output (env vars matching `*SECRET*`, `*PASSWORD*`, `*TOKEN*`)
- [ ] **EXEC-05**: Handles binary/non-UTF8 output gracefully
- [ ] **EXEC-06**: Caps stdout/stderr capture at 10MB to prevent OOM

### Reporting
- [ ] **RPT-01**: Parse JUnit XML from `target/surefire-reports/*.xml` → total, passed, failed, skipped
- [ ] **RPT-02**: Parse checkstyle XML from `target/checkstyle-result.xml` → violation count
- [ ] **RPT-03**: Handle malformed XML gracefully (log warning, return zeros)
- [ ] **RPT-04**: Generate `ci-result.json` with stages array, CI context, timing, overall result
- [ ] **RPT-05**: Generate `summary.md` with stage table, test counts, lint count, CI context

### Notification
- [ ] **NOTIF-01**: Console notification always outputs build summary to stdout
- [ ] **NOTIF-02**: Slack notification via `MCT_SLACK_WEBHOOK_URL` using urllib (no deps)
- [ ] **NOTIF-03**: Email notification via SMTP (`MCT_SMTP_HOST/PORT/USER/PASSWORD`, `MCT_EMAIL_TO`)
- [ ] **NOTIF-04**: Notification failures are logged, never crash the pipeline

### CI Wrappers
- [ ] **WRAP-01**: Jenkinsfile reads `ci-result.json`, maps `warn` → `unstable()`, `fail` → build failure
- [ ] **WRAP-02**: Jenkinsfile supports Docker container execution (`docker.withRegistry` + `image.inside`)
- [ ] **WRAP-03**: Jenkinsfile archives artifacts and publishes JUnit results
- [ ] **WRAP-04**: GitHub Actions workflow uses `setup-java`, `setup-python`, writes GITHUB_STEP_SUMMARY
- [ ] **WRAP-05**: GitHub Actions workflow uploads artifacts on all outcomes

### Testing
- [ ] **TEST-01**: Unit tests for adapter detection, normalization, and PR metadata
- [ ] **TEST-02**: Unit tests for Maven backend commands and report paths
- [ ] **TEST-03**: Unit tests for executor (streaming, timeout, retry, redaction)
- [ ] **TEST-04**: Unit tests for pipeline stage sequencing and result classification
- [ ] **TEST-05**: Unit tests for JUnit XML parsing edge cases
- [ ] **TEST-06**: Contract tests for `ci-result.json` schema
- [ ] **TEST-07**: Unit tests for notification (best-effort behavior)

## v2 Requirements (Deferred)

- [ ] Multi-language backends (Python/pip, Gradle, React/npm, Node.js)
- [ ] `ci-config.yaml` file support (3-tier config)
- [ ] GitLab CI adapter
- [ ] Parallel test execution within SDK
- [ ] Allure report generation
- [ ] Pydantic config validation

## Out of Scope

- Mobile builds (React Native, iOS) — different problem domain
- Docker orchestration within SDK — CI wrappers own container lifecycle
- Plugin system for custom stages — over-engineering for v1
- Web dashboard for build results — CI platforms already provide this
- Multi-repo / monorepo support — single project per pipeline

## Traceability

| Requirement | Phase | Plan | Status |
|-------------|-------|------|--------|
| ADAPT-01 | - | - | Not started |
| ADAPT-02 | - | - | Not started |
| ADAPT-03 | - | - | Not started |
| ADAPT-04 | - | - | Not started |
| ADAPT-05 | - | - | Not started |
| CLI-01 | - | - | Not started |
| CLI-02 | - | - | Not started |
| CLI-03 | - | - | Not started |
| CLI-04 | - | - | Not started |
| CLI-05 | - | - | Not started |
| CLI-06 | - | - | Not started |
| CLI-07 | - | - | Not started |
| CLI-08 | - | - | Not started |
| CLI-09 | - | - | Not started |
| PIPE-01 | - | - | Not started |
| PIPE-02 | - | - | Not started |
| PIPE-03 | - | - | Not started |
| PIPE-04 | - | - | Not started |
| PIPE-05 | - | - | Not started |
| MVN-01 | - | - | Not started |
| MVN-02 | - | - | Not started |
| MVN-03 | - | - | Not started |
| MVN-04 | - | - | Not started |
| MVN-05 | - | - | Not started |
| MVN-06 | - | - | Not started |
| MVN-07 | - | - | Not started |
| EXEC-01 | - | - | Not started |
| EXEC-02 | - | - | Not started |
| EXEC-03 | - | - | Not started |
| EXEC-04 | - | - | Not started |
| EXEC-05 | - | - | Not started |
| EXEC-06 | - | - | Not started |
| RPT-01 | - | - | Not started |
| RPT-02 | - | - | Not started |
| RPT-03 | - | - | Not started |
| RPT-04 | - | - | Not started |
| RPT-05 | - | - | Not started |
| NOTIF-01 | - | - | Not started |
| NOTIF-02 | - | - | Not started |
| NOTIF-03 | - | - | Not started |
| NOTIF-04 | - | - | Not started |
| WRAP-01 | - | - | Not started |
| WRAP-02 | - | - | Not started |
| WRAP-03 | - | - | Not started |
| WRAP-04 | - | - | Not started |
| WRAP-05 | - | - | Not started |
| TEST-01 | - | - | Not started |
| TEST-02 | - | - | Not started |
| TEST-03 | - | - | Not started |
| TEST-04 | - | - | Not started |
| TEST-05 | - | - | Not started |
| TEST-06 | - | - | Not started |
| TEST-07 | - | - | Not started |
