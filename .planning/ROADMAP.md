# Roadmap: Multi-CI-Tools

## Overview

Build a CI-agnostic Python SDK for Maven pipelines across 8 phases. Start with package foundation and types, then build adapters and executor, wire into pipeline orchestrator, add reporting and notifications, create CI wrappers, and finish with full test coverage.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Package Foundation** - Python package skeleton, core types, exceptions, CLI entry point
- [x] **Phase 2: CI Adapters** - CIAdapter ABC, Jenkins/GitHub/Local adapters, auto-detection
- [ ] **Phase 3: Command Execution Engine** - subprocess wrapper with streaming, timeout, retry, redaction
- [ ] **Phase 4: Maven Backend** - BuildBackend ABC, Maven command generation, report path resolution
- [ ] **Phase 5: Pipeline Orchestrator** - Stage sequencing, result aggregation, PipelineResult output
- [ ] **Phase 6: Reporting & Notification** - JUnit parsing, summary generation, email/Slack/console notifiers
- [ ] **Phase 7: CI Wrappers** - Jenkinsfile with Docker support, GitHub Actions workflow, dry-run/inspect/doctor commands
- [ ] **Phase 8: Test Suite & Polish** - Full pytest coverage, contract tests, README, final validation

## Phase Details

### Phase 1: Package Foundation
**Goal**: Working Python package with CLI that can be invoked, types defined, and error handling in place
**Depends on**: Nothing (first phase)
**Requirements**: [CLI-01, CLI-07, CLI-08]
**Success Criteria** (what must be TRUE):
  1. `python -m multi_ci_tools --help` prints usage information
  2. `python -m multi_ci_tools inspect-env` runs without error
  3. All core types (CIContext, StageResult, PipelineResult, RunConfig) are importable
  4. Exception hierarchy is defined and importable
**Plans**: 2 plans

Plans:
- [x] 01-01: Package skeleton (pyproject.toml, __init__, __main__, cli.py)
- [x] 01-02: Core types and exceptions (types.py, exceptions.py, full CLI subcommands)

### Phase 2: CI Adapters
**Goal**: SDK correctly detects Jenkins, GitHub Actions, or local and normalizes environment
**Depends on**: Phase 1
**Requirements**: [ADAPT-01, ADAPT-02, ADAPT-03, ADAPT-04, ADAPT-05]
**Success Criteria** (what must be TRUE):
  1. Setting `JENKINS_URL` env var activates Jenkins adapter
  2. Setting `GITHUB_ACTIONS=true` activates GitHub adapter
  3. No CI env vars activates local adapter
  4. `inspect-env` prints normalized CI context from any adapter
**Plans**: 2 plans

Plans:
- [x] 02-01: CIAdapter ABC + detect.py + LocalAdapter
- [x] 02-02: JenkinsAdapter + GitHubAdapter with full env normalization

### Phase 3: Command Execution Engine
**Goal**: Production-grade command runner with streaming, timeouts, retries, and secret redaction
**Depends on**: Phase 1
**Requirements**: [EXEC-01, EXEC-02, EXEC-03, EXEC-04, EXEC-05, EXEC-06]
**Success Criteria** (what must be TRUE):
  1. Command output streams in real-time (not buffered until completion)
  2. Commands killed cleanly after timeout
  3. Retries work with exponential backoff for transient failures
  4. Secrets are redacted from output
**Plans**: 2 plans

Plans:
- [ ] 03-01: Core runner with streaming and timeout
- [ ] 03-02: Retry logic, secret redaction, edge cases (binary output, OOM protection)

### Phase 4: Maven Backend
**Goal**: Maven command generation and report path resolution working correctly
**Depends on**: Phase 1
**Requirements**: [MVN-01, MVN-02, MVN-03, MVN-04, MVN-05, MVN-06, MVN-07]
**Success Criteria** (what must be TRUE):
  1. Build command includes `-DskipTests` flag
  2. Smoke tests only activate when `MCT_ENABLE_SMOKE=true`
  3. All command strings match expected Maven CLI format
  4. Report paths resolve correctly for surefire and checkstyle
**Plans**: 1 plan

Plans:
- [ ] 04-01: BuildBackend ABC + MavenBackend implementation

### Phase 5: Pipeline Orchestrator
**Goal**: Full pipeline executes all stages in correct order with proper result aggregation
**Depends on**: Phase 2, Phase 3, Phase 4
**Requirements**: [PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-05, CLI-02, CLI-03, CLI-04, CLI-05, CLI-06]
**Success Criteria** (what must be TRUE):
  1. `python -m multi_ci_tools run` executes all stages sequentially
  2. `--stage` and `--skip-stage` flags work correctly
  3. `--strict` promotes warnings to failures
  4. Pipeline produces ci-result.json and summary.md
  5. Notify and publish stages always run
**Plans**: 2 plans

Plans:
- [ ] 05-01: Stage sequencing, skip logic, result aggregation
- [ ] 05-02: PipelineResult output (ci-result.json, summary.md)

### Phase 6: Reporting & Notification
**Goal**: JUnit XML parsing, build summaries, and multi-channel notifications
**Depends on**: Phase 5
**Requirements**: [RPT-01, RPT-02, RPT-03, RPT-04, RPT-05, NOTIF-01, NOTIF-02, NOTIF-03, NOTIF-04]
**Success Criteria** (what must be TRUE):
  1. JUnit parser extracts correct counts from surefire XML
  2. Malformed XML handled gracefully
  3. Console always prints build summary
  4. Slack/email failures never crash the pipeline
**Plans**: 2 plans

Plans:
- [ ] 06-01: JUnit parser + checkstyle parser + summary generation
- [ ] 06-02: Console + Slack + Email notifiers

### Phase 7: CI Wrappers
**Goal**: Thin Jenkinsfile and GitHub Actions workflow that run the SDK and translate results
**Depends on**: Phase 5, Phase 6
**Requirements**: [WRAP-01, WRAP-02, WRAP-03, WRAP-04, WRAP-05, CLI-09]
**Success Criteria** (what must be TRUE):
  1. Jenkinsfile reads ci-result.json and maps to Jenkins build states
  2. Jenkinsfile supports Docker container execution
  3. GitHub Actions workflow writes step summary and uploads artifacts
  4. `doctor` command validates workspace and tools
**Plans**: 2 plans

Plans:
- [ ] 07-01: Jenkins wrapper with Docker support + doctor command
- [ ] 07-02: GitHub Actions wrapper with step summary + artifact upload

### Phase 8: Test Suite & Polish
**Goal**: Complete test coverage, documentation, and final validation
**Depends on**: Phase 7
**Requirements**: [TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06, TEST-07]
**Success Criteria** (what must be TRUE):
  1. `pytest tests/ -v` passes with >80% coverage
  2. Contract tests verify ci-result.json schema stability
  3. README documents installation, usage, and configuration
  4. `python -m multi_ci_tools doctor` passes in a Maven project
**Plans**: 2 plans

Plans:
- [ ] 08-01: Full test suite (adapters, executor, pipeline, reporting, notifications)
- [ ] 08-02: README, documentation, final integration validation

## Progress

**Execution Order:**
Phases 1-4 can partially run in parallel (1 first, then 2/3/4 together). Phase 5 depends on 2+3+4. Phases 6-8 are sequential.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Package Foundation | 2/2 | Completed | 2026-04-10 |
| 2. CI Adapters | 2/2 | Completed | 2026-04-10 |
| 3. Command Execution Engine | 0/2 | Not started | - |
| 4. Maven Backend | 0/1 | Not started | - |
| 5. Pipeline Orchestrator | 0/2 | Not started | - |
| 6. Reporting & Notification | 0/2 | Not started | - |
| 7. CI Wrappers | 0/2 | Not started | - |
| 8. Test Suite & Polish | 0/2 | Not started | - |
