# Architecture

**Analysis Date:** 2026-04-10

## Core Design Pattern

The Multi-CI-Tools project uses a **layered adapter pattern** where CI platforms (Jenkins, GitHub Actions, Local) are abstracted into a common interface. A single Python SDK runs the pipeline logic, and CI platforms are thin wrappers that invoke `python -m multi_ci_tools run`.

**Design Philosophy:** The Python SDK is the source of truth. Every CI platform normalizes to identical CIContext objects.

```
┌─ CI Platform Layer (Jenkins/GitHub/Local) ───────────────────┐
│  Jenkinsfile (~15 lines) │ Actions YAML (~20 lines) │ Local  │
└─────────────────────┬──────────────────────────────────────┘
                      │ python -m multi_ci_tools run
┌─────────────────────▼──────────────────────────────────────┐
│  CLI Entry Point (`multi_ci_tools/cli.py`)                 │
│  - argparse with subcommands (run, dry-run, inspect-env)  │
└─────────────────────┬──────────────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────────┐
│  CI Adapter Layer (`multi_ci_tools/adapters/`)             │
│  - JenkinsAdapter    - GitHubAdapter    - LocalAdapter    │
│  - Auto-detects environment, normalizes to CIContext       │
└─────────────────────┬──────────────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────────┐
│  Pipeline Orchestrator (`multi_ci_tools/orchestrator.py`)  │
│  - Stage sequencing & result aggregation                   │
└─────────────────────┬──────────────────────────────────────┘
           ┌──────────┬──────────┬──────────┬────────────┐
           ▼          ▼          ▼          ▼            ▼
    ┌──────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
    │Executor  │ │Backend │ │Notifier│ │Reporting│ │Results   │
    │(subprocess)│(Maven) │ │(Stub)   │ │(Stub)   │ │(JSON)    │
    └──────────┘ └────────┘ └────────┘ └────────┘ └──────────┘
```

## Component Details

### CLI Layer (`multi_ci_tools/cli.py`, Lines 1-150)

**Purpose:** Argument parsing and subcommand routing.

**Key Functions:**
- `def create_parser()` - Configures argparse with subcommands
- `def main()` - Parses args, instantiates adapters, calls orchestrator
- Supports: `run`, `dry-run`, `inspect-env`, `doctor`, `--version`

**Config Priority (highest to lowest):**
1. CLI flags (e.g., `--stage build`)
2. Environment variables (e.g., `MCT_LINT_MODE`)
3. Defaults (from RunConfig in types.py)

### Adapter Layer (`multi_ci_tools/adapters/`)

**Abstract Base:** `adapters/base.py`
- `CIAdapter` - Abstract base class with `detect()` and `get_context()` methods
- Provides `log_group()` abstraction for platform-specific grouping (GHA uses `::group::`, Jenkins uses ANSI)

**Auto-Detection:** `adapters/detect.py`
- Priority order: Jenkins > GitHub > Local (not reversed)
- If Jenkins env vars are present AND `GITHUB_ACTIONS=true`, Jenkins wins
- Fallback to LocalAdapter if no CI platform detected

**Concrete Adapters:**
- `adapters/jenkins.py` - Reads `GIT_COMMIT`, `GIT_BRANCH`, `BUILD_NUMBER`, `WORKSPACE` from Jenkins environment
- `adapters/github.py` - Reads `GITHUB_SHA`, `GITHUB_REF_NAME`, `GITHUB_RUN_NUMBER`, `GITHUB_WORKSPACE` from GHA environment
- `adapters/local.py` - Uses `git` commands and filesystem inspection

**Normalization Table:**

| Concept | Jenkins | GitHub Actions | Local |
|---------|---------|----------------|-------|
| Commit | `GIT_COMMIT` | `GITHUB_SHA` | `git rev-parse HEAD` |
| Branch | `GIT_BRANCH` | `GITHUB_REF_NAME` | `git branch --show-current` |
| Build # | `BUILD_NUMBER` | `GITHUB_RUN_NUMBER` | `local-{timestamp}` |
| Workspace | `WORKSPACE` | `GITHUB_WORKSPACE` | `os.getcwd()` |
| Build URL | `BUILD_URL` | `$GITHUB_SERVER_URL/...` | `file://{cwd}` |
| Is PR? | `CHANGE_ID` set | `GITHUB_EVENT_NAME=pull_request` | False |

### Executor (`multi_ci_tools/executor.py`, Lines 1-200)

**Responsibilities:**
- Execute shell commands with timeouts, retries, and real-time output streaming
- Redact secrets from logs (patterns: `*SECRET*`, `*PASSWORD*`, `*TOKEN*`)
- Capture return codes and output

**Key Classes:**
- `CommandExecutor` - Main executor with streaming subprocess handling
- `Redactor` - Redacts sensitive output before logging

**Pattern: StreamReader Thread**
- Real-time output to CI console (not buffered until completion)
- Each stream (stdout, stderr) handled in a separate thread
- Aggregates output while respecting timeouts

### Backends (`multi_ci_tools/backends.py`, Lines 1-150)

**Abstract Base:** `BuildBackend`
- Methods: `resolve_deps()`, `lint()`, `build()`, `test()`, `publish()`
- Each returns a `CommandResult` with status, output, and diagnostics

**Concrete Implementation:** `MavenBackend`
- Hard-coded Maven commands:
  - Build: `mvn clean install -DskipTests`
  - Test: `mvn test`
  - Lint: `mvn checkstyle:check`
  - Smoke tests: `mvn test -Psmoke` (only if `MCT_ENABLE_SMOKE=true`)
  - Resolve deps: `mvn dependency:resolve`

**Pattern: Command Standardization**
All Maven commands use consistent flags for reproducibility.

### Orchestrator (`multi_ci_tools/orchestrator.py`, Lines 1-250)

**Responsibilities:**
- Execute stages in sequence
- Aggregate results
- Classify overall success/failure

**Stage Execution Order:**
```
PREFLIGHT → RESOLVE_DEPS → LINT → BUILD → UNIT_TEST → SMOKE_TEST → PUBLISH → NOTIFY
```

**Result Classification:**
- Status values: `pass`, `warn`, `fail`, `skip`
- Overall result = worst stage (fail > warn > pass)
- Publish & Notify always execute regardless of prior failures (must be idempotent)

**Stage Result Aggregation:**
Each stage produces a `StageResult`:
```python
@dataclass(frozen=True)
class StageResult:
    stage: StageName
    status: StageStatus
    duration_sec: float
    output: str
    diagnostics: Optional[Dict[str, Any]]
```

Final result is `PipelineResult`:
```python
@dataclass(frozen=True)
class PipelineResult:
    overall_status: StageStatus
    stages: List[StageResult]
    start_time: float
    end_time: float
    ci_context: CIContext
```

### Type System (`multi_ci_tools/types.py`)

**Core Immutable Contracts:**
All major types are frozen dataclasses to prevent accidental mutation during pipeline execution.

- `CIContext` - Normalized environment from adapter (commit, branch, workspace, build URL, etc.)
- `CommandResult` - Subprocess execution result (return code, stdout, stderr)
- `StageResult` - Individual stage execution result with duration and diagnostics
- `PipelineResult` - Complete pipeline execution summary
- `RunConfig` - Configuration with priority: env vars > CLI > defaults
- `StageName`, `StageStatus` - Enums for type-safe stage references

**Type Safety Pattern:**
- No magic strings for stage names (use `StageName.BUILD`, not `"build"`)
- No magic strings for result statuses (use `StageStatus.PASS`, not `"pass"`)
- Frozen prevents mutation after construction

### Exception Hierarchy (`multi_ci_tools/exceptions.py`)

**Base:** `MCTException` - All exceptions inherit from this

**Concrete Types:**
- `ConfigError` - Configuration validation failed
- `AdapterError` - CI environment detection or context retrieval failed
- `StageError` - A pipeline stage failed (wraps exit code)
- `CommandError` - Command execution failed (timeout, subprocess error)

Each exception includes context about what failed and why.

## Extension Points

### Add a New CI Platform

1. Create `multi_ci_tools/adapters/newplatform.py`
2. Implement `NewPlatformAdapter(CIAdapter)` with `detect()` and `get_context()` methods
3. Update `adapters/detect.py` to add to priority detection order

**Example:** To add GitLab:
```python
# adapters/gitlab.py
class GitLabAdapter(CIAdapter):
    def detect(self) -> bool:
        return "GITLAB_CI" in os.environ
    
    def get_context(self) -> CIContext:
        return CIContext(
            commit=os.environ["CI_COMMIT_SHA"],
            branch=os.environ["CI_COMMIT_REF_NAME"],
            ...
        )
```

### Add a New Build Backend

1. Create `NewBackend(BuildBackend)` in `backends.py`
2. Implement abstract methods: `resolve_deps()`, `lint()`, `build()`, `test()`, `publish()`
3. Update CLI to allow selection (planned in Phase 2)

**Example:** To add Gradle:
```python
class GradleBackend(BuildBackend):
    def build(self) -> CommandResult:
        return self.executor.run(["gradle", "build"])
```

### Add a New Stage

1. Add stage name to `StageName` enum in `types.py`
2. Add logic to `Orchestrator.execute()` in `orchestrator.py`
3. Add implementation to `BuildBackend` (or skip if custom logic)

## Phase Maturity

| Component | Status | Phase |
|-----------|--------|-------|
| Adapter layer | ✅ Complete | 1-2 |
| Executor & timeouts | ✅ Complete | 3 |
| Maven backend | ✅ Complete | 4 |
| Orchestrator | ✅ Complete | 5 |
| Reporting (JUnit, summary) | ⏳ Draft design | 6 |
| CI wrappers (Jenkinsfile, Actions) | ⏳ Minimal examples | 7 |
| Test suite | ⚪ Not started | 8 |

## Architectural Decisions (Why This Pattern?)

**Why Adapters?**
- No other CI platform coupling in pipeline code
- Easy to test in local environment
- Reduces context switching between Jenkins, GitHub, local workflows

**Why Frozen Dataclasses?**
- Type contracts prevent mutations during pipeline (safer than mutable dicts)
- Immutability enables caching and result replication
- Self-documenting (fields are explicit in code)

**Why CLI Entry Point?**
- CI platforms invoke via `python -m multi_ci_tools run`
- Same behavior locally, in Jenkins, in GitHub
- Easy to debug locally before pushing to CI

**Why No YAML Config?**
- Flat env var config is simpler for CI systems to set
- Phase 2 deferred to keep core simple
- Reduces external dependencies (no PyYAML required)

## Data Flow Example: Full Pipeline Run

1. **Detection Phase** (`adapters/detect.py`)
   - Checks `JENKINS_HOME` env var → JenkinsAdapter
   - Or `GITHUB_ACTIONS=true` → GitHubAdapter
   - Or fallback → LocalAdapter

2. **Context Extraction** (`adapters/jenkins.py` or similar)
   - Normalizes platform-specific env vars into `CIContext`
   - Example: Jenkins's `GIT_BRANCH=origin/main` → `branch="main"`

3. **CLI Parsing** (`cli.py`)
   - Parses flags like `--stage build --skip-stage lint`
   - Builds `RunConfig` with user preferences

4. **Orchestration** (`orchestrator.py`)
   - Reads `RunConfig` and `CIContext`
   - Iterates stages in order: PREFLIGHT → RESOLVE_DEPS → ... → NOTIFY
   - For each stage, calls appropriate `BuildBackend` method

5. **Execution** (`executor.py`)
   - `MavenBackend.build()` returns command string
   - `CommandExecutor.run()` executes via subprocess, streams output, redacts secrets

6. **Result Aggregation** (`orchestrator.py`)
   - Collects all `StageResult` objects
   - Computes overall status (worst stage)
   - Returns `PipelineResult` JSON

7. **Output** (`cli.py`)
   - Serializes `PipelineResult` to JSON (if `--emit-json` flag)
   - Writes summary (if `--emit-summary` flag)
   - Sets exit code based on overall status
