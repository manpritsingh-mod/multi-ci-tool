---
phase: 7
name: "CI Wrappers"
gathered: 2026-04-10
status: "Ready for planning"
dependencies: ["Phase 5: Pipeline Orchestrator", "Phase 6: Reporting & Notification"]
---

# Phase 7: CI Wrappers

## Phase Boundary

Build thin CI platform adapters (Jenkinsfile for Jenkins, GitHub Actions workflow for GitHub Actions) that invoke the Python SDK and translate structured results (`ci-result.json`) back to native CI platform states. Also implement CLI commands (`doctor` and `dry-run`) for workspace validation and pipeline inspection.

This phase completes the **closed-loop integration**: CI platforms now speak only to the SDK via a single Python command, and the SDK reports results in machine-readable format that CI platforms consume to set final build status.

**What gets delivered:**
1. **Jenkinsfile wrapper** — Thin Docker-based pipeline that runs SDK and maps results to Jenkins build states
2. **GitHub Actions workflow** — Modern workflow using matrix strategy for multi-version testing, artifact upload, step summaries
3. **doctor CLI command** — Validates workspace and prerequisite tools (Java, Maven, Python)
4. **dry-run CLI command** — Shows what stages would execute without running them

## Success Criteria (What Must Be TRUE)

1. ✓ Jenkinsfile runs `python -m multi_ci_tools run` inside Docker container
2. ✓ Jenkinsfile reads `ci-result.json` and maps: `warn` → `unstable()`, `fail` → build failure
3. ✓ Jenkinsfile archives test/lint artifacts and JUnit results
4. ✓ GitHub Actions workflow uses `setup-java`, `setup-python`, writes GITHUB_STEP_SUMMARY
5. ✓ GitHub Actions uploads `ci-result.json` and `summary.md` as workflow artifacts
6. ✓ `python -m multi_ci_tools doctor` validates: Java version, Maven installed, Python 3.10+, workspace structure
7. ✓ `python -m multi_ci_tools dry-run` prints planned stages without executing commands

## Design Decisions

### Jenkinsfile Strategy
- **Decision:** Use Docker container to ensure consistent environment (no dependency on Jenkins node setup)
- **Rationale:** Maven + Java versioning becomes a non-issue; all tooling packaged in image
- **Implementation:** Single Docker agent with `image.inside()` context
- **Result mapping:** Parse `ci-result.json` at end; use `unstable()` for warnings, `currentBuild.result = 'FAILURE'` for fails

### GitHub Actions Strategy
- **Decision:** Use matrix strategy for Java/Python version combinations (optional multi-version testing)
- **Rationale:** Parallelize testing, catch version-specific issues early
- **Output:** Step summary via `GITHUB_STEP_SUMMARY`, not Slack (Slack is SDK responsibility)
- **Artifacts:** Upload both `ci-result.json` and `summary.md` on all outcomes (success, failure, cancelled)

### Doctor Command Design
- **Decision:** Python CLI command that checks prerequisites without running full pipeline
- **Rationale:** Fast feedback loop; users know instantly if workspace is valid before investing time
- **Checks:** Java version (11+), Maven (3.6+), Python (3.10+), workspace structure (src/, pom.xml)
- **Exit code:** 0 = healthy, 1 = issues found (CI script can gate on this)

### Dry-run Command Design
- **Decision:** Prints planned stages without side effects (no network calls, no file writes except to stderr)
- **Rationale:** Users can preview pipeline before committing to run
- **Output:** List stages in order with config applied (--skip-stage honored)
- **Exit code:** Always 0 (dry-run never fails; information layer only)

### ci-result.json Schema Stability
- **Decision:** Schema defined in Phase 6; Phase 7 wrappers consume as-is (no schema changes)
- **Rationale:** Contract between SDK and CI platforms is fixed; wrappers are thin adapters, not logic owners
- **Parsing:** Simple JSON deserialization; no validation (trust SDK output)

## Architectural Context

### From Phase 6: Orchestrator Output

The orchestrator produces two artifacts:

1. **ci-result.json** — Machine-readable pipeline result:
   ```json
   {
     "overall": "warn",
     "stages": [...],
     "ci_context": {...},
     "duration_seconds": 45.2,
     "test_summary": {...},
     "lint_summary": {...},
     "timestamp": "2026-04-10T12:34:56Z"
   }
   ```

2. **summary.md** — Human-readable markdown summary with stage table, test counts, lint violations

### CLI Layer Integration

New commands added to `multi_ci_tools/cli.py`:

- `doctor` — Validates prerequisites
- `dry-run` — Shows planned stages

Existing commands:
- `run` — Already outputs `ci-result.json` and `summary.md`

### File Additions

**New files:**
- `Jenkinsfile` — Thin Jenkins pipeline wrapper
- `.github/workflows/ci.yml` — GitHub Actions workflow
- CLI commands for `doctor` and `dry-run` (in `multi_ci_tools/__main__.py` or `cli.py`)

**Modified files:**
- `multi_ci_tools/cli.py` — Add `doctor` and `dry-run` subcommands

### No SDK Changes Required

Phase 7 does NOT modify orchestrator, executor, adapters, or backend logic. The SDK is complete and stable from Phase 6. Phase 7 only adds **thin wrappers** and **CLI inspection tools**.

## Requirements Coverage

**Phase 7 Requirements:**

| ID | Requirement | Plan | Notes |
|----|-------------|------|-------|
| WRAP-01 | Jenkinsfile reads `ci-result.json`, maps `warn` → `unstable()`, `fail` → failure | 07-01 | Docker-based |
| WRAP-02 | Jenkinsfile supports Docker container execution | 07-01 | `image.inside()` context |
| WRAP-03 | Jenkinsfile archives artifacts + publishes JUnit results | 07-01 | `archiveArtifacts`, `junit` step |
| WRAP-04 | GitHub Actions uses `setup-java`, `setup-python`, writes GITHUB_STEP_SUMMARY | 07-02 | Matrix optional |
| WRAP-05 | GitHub Actions uploads artifacts on all outcomes | 07-02 | `actions/upload-artifact` |
| CLI-09 | `python -m multi_ci_tools doctor` validates workspace, tools, config | 07-01 | New CLI command |
| CLI-07 | `python -m multi_ci_tools dry-run` shows planned stages | 07-02 | New CLI command |

**Related Requirements from Other Phases:**

- PIPE-04, PIPE-05 — Notify/Publish always run (already in Phase 5)
- RPT-04, RPT-05 — ci-result.json and summary.md generation (already in Phase 6)

## Assumptions from Prior Phases

- ✓ SDK always produces `ci-result.json` in workspace root (or specified path)
- ✓ SDK always produces `summary.md` next to `ci-result.json`
- ✓ Both outputs exist even if stages fail
- ✓ `ci-result.json` is valid JSON (no malformed output from SDK)
- ✓ Adapters correctly detect Jenkins vs GitHub vs Local
- ✓ No external dependencies in SDK (stdlib only)
- ✓ CLI entry point `python -m multi_ci_tools` works reliably

## Design Discretion Areas (Not Locked by Requirements)

These implementation details are explicitly NOT specified and are left to planner discretion:

1. **Docker image choice** — Which Java/Maven image to use? (e.g., `maven:3.9-eclipse-temurin-21`)
2. **GitHub Actions matrix scope** — Test Java 11, 17, 21? Python 3.10, 3.11, 3.12? Or single version?
3. **Artifact retention** — How long should GitHub Actions retain artifacts? (default 90 days, make configurable?)
4. **Step summary format** — Should step summary include emoji? Collapsible sections? Or plain markdown?
5. **Build status mapping** — Should `warn` set `unstable()` in Jenkins? Or treat as failure? (decision: `unstable()`)
6. **Error recovery** — If `ci-result.json` is missing, should Jenkinsfile fail hard or default to failure status?
7. **Logging verbosity** — Should Jenkinsfile/workflow log all steps or minimal output?

## Canonical References

**Roadmap:** [ROADMAP.md](../../ROADMAP.md) — Phase 7 section  
**Requirements:** [REQUIREMENTS.md](../../REQUIREMENTS.md) — WRAP-01 to WRAP-05, CLI-07, CLI-09  
**Architecture:** [.planning/codebase/ARCHITECTURE.md](../../codebase/ARCHITECTURE.md) — CLI layer, orchestrator  
**Phase 6 Output:** [06-ci-wrappers/CONTEXT.md](../06-reporting-notification/CONTEXT.md) — ci-result.json schema

## Open Questions for Planning

1. **Docker image selection:** Should we hardcode Maven 3.9 + JDK 21, or make it configurable?
2. **Jenkinsfile extensibility:** Should the Jenkinsfile support additional stages beyond the SDK pipeline?
3. **GitHub matrix performance:** Testing on 9 combinations (3 Java × 3 Python) adds overhead; worth it for v1?
4. **ci-result.json location:** Can we assume it's in workspace root, or should Jenkinsfile accept `--emit-json` path?
5. **Error messages in doctor:** How detailed should validation failures be? (e.g., "Java 8.0.392 detected, but 11+ required")
6. **Dry-run stage filtering:** If user passes `--stage lint`, should dry-run show only `lint` stage, or all stages with `lint` highlighted?
7. **Live testing environment:** Will we test against public Maven project (https://github.com/manpritsingh-mod/Java-Maven-Testing.git) or local mock?

## Ready to Plan

All context gathered. Phase 7 can proceed to detailed planning:

**Next:** Two parallel work streams can be planned independently:
- [07-01-PLAN.md](07-01-PLAN.md) — Jenkinsfile + doctor command (Jenkins-focused)
- [07-02-PLAN.md](07-02-PLAN.md) — GitHub Actions + dry-run command (GitHub Actions-focused)

Phase 7 implementation can proceed with both plans in parallel after planning.
