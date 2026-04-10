# Structure

**Analysis Date:** 2026-04-10

## Directory Organization

```
multi-ci-tools/
├── .agent/                          # VS Code agent customizations (GSD framework)
│   ├── agents/                      # Custom agent definitions
│   │   ├── gsd-codebase-mapper.md
│   │   ├── gsd-code-fixer.md
│   │   └── ... (24 agents total)
│   ├── get-shit-done/               # GSD framework core
│   │   ├── bin/                     # Executable tools
│   │   ├── contexts/                # Operation contexts
│   │   ├── references/              # Extended documentation
│   │   ├── templates/               # Code templates
│   │   └── workflows/               # GSD workflows
│   ├── hooks/                       # Git/VS Code hooks
│   ├── skills/                      # Reusable skills
│   ├── settings.json                # VS Code settings
│   ├── package.json                 # GSD dependencies
│   └── gsd-file-manifest.json       # File checksums
│
├── .github/
│   ├── workflows/
│   │   └── ci.yml                   # GitHub Actions CI workflow
│   └── (copilot-instructions.md will go here if created)
│
├── .planning/                       # Project planning & state tracking
│   ├── codebase/                    # Codebase analysis docs (THIS DIRECTORY)
│   │   ├── ARCHITECTURE.md
│   │   ├── STRUCTURE.md
│   │   ├── CONVENTIONS.md
│   │   ├── TESTING.md
│   │   ├── STACK.md
│   │   └── CONCERNS.md
│   ├── phases/                      # Phase-specific planning docs
│   ├── research/                    # Research notes
│   ├── PROJECT.md                   # Investment decisions & rationale
│   ├── ROADMAP.md                   # 8-phase development roadmap
│   ├── REQUIREMENTS.md              # 60+ requirement traces (ADAPT-01, etc.)
│   ├── STATE.md                     # Current progress & phase status
│   └── config.json                  # Planning configuration
│
├── .git/                            # Git repository
├── .gitignore                       # Ignore file patterns
│
├── multi_ci_tools/                  # Main Python package
│   ├── __init__.py                  # Package initialization
│   ├── __main__.py                  # Entry point for python -m multi_ci_tools
│   ├── cli.py                       # Command-line interface (argparse)
│   ├── types.py                     # Frozen dataclasses & type contracts
│   ├── exceptions.py                # Exception hierarchy
│   ├── executor.py                  # Command execution with streaming & redaction
│   ├── backends.py                  # Build backend abstraction + Maven impl
│   ├── orchestrator.py              # Pipeline stage orchestration
│   │
│   └── adapters/                    # CI platform abstraction
│       ├── __init__.py
│       ├── base.py                  # CIAdapter abstract base
│       ├── detect.py                # Auto-detection logic
│       ├── jenkins.py               # Jenkins adapter
│       ├── github.py                # GitHub Actions adapter
│       └── local.py                 # Local development adapter
│
├── tests/                           # Test suite (under-developed)
│   └── conftest.py                  # pytest fixtures (minimal: ~5 lines)
│
├── Jenkinsfile                      # Jenkins pipeline wrapper (~15 lines)
├── pyproject.toml                   # Python project config & dependencies
├── README.md                        # (if exists) Project overview
├── CONTRIBUTING.md                  # (if exists) Contributing guidelines
└── implementation_plan.md           # Detailed implementation analysis (150+ lines)
```

## Where to Add New Code

### Adding a New Adapter (New CI Platform)

**Location:** `multi_ci_tools/adapters/{platform}.py`

**Pattern:**
1. Create new file named after platform (e.g., `gitlab.py`)
2. Implement class `{Platform}Adapter(CIAdapter)`
3. Implement required methods:
   - `detect() -> bool` - Check for platform-specific env vars
   - `get_context() -> CIContext` - Extract and normalize environment
4. Update `adapters/detect.py` to include in detection priority order

**Example Structure:**
```python
# multi_ci_tools/adapters/gitlab.py
from adapters.base import CIAdapter
from types import CIContext

class GitLabAdapter(CIAdapter):
    @staticmethod
    def detect() -> bool:
        return "GITLAB_CI" in os.environ
    
    def get_context(self) -> CIContext:
        # Return normalized CIContext from GitLab env vars
        pass
```

### Adding a New Build Backend (Build System)

**Location:** Add class to `multi_ci_tools/backends.py`

**Pattern:**
1. Create class `{Tool}Backend(BuildBackend)`
2. Implement abstract methods:
   - `resolve_deps()`
   - `lint()`
   - `build()`
   - `test()`
   - `publish()`
3. Each method returns `CommandResult` from executing the tool's CLI

**Example Structure:**
```python
# In backends.py
class GradleBackend(BuildBackend):
    def build(self) -> CommandResult:
        return self.executor.run(["gradle", "build"])
    
    def test(self) -> CommandResult:
        return self.executor.run(["gradle", "test"])
```

### Adding a New Stage to Orchestrator

**Location:** Modify three files:

1. **`multi_ci_tools/types.py`** - Add to `StageName` enum
   ```python
   class StageName(Enum):
       PREFLIGHT = "preflight"
       RESOLVE_DEPS = "resolve_deps"
       # ... existing stages ...
       NEW_STAGE = "new_stage"  # ADD HERE
   ```

2. **`multi_ci_tools/orchestrator.py`** - Add execution logic
   ```python
   def execute(self, config: RunConfig) -> PipelineResult:
       # ... existing stages ...
       new_stage_result = self._execute_stage(
           StageName.NEW_STAGE,
           lambda: self.backend.new_stage_method()
       )
   ```

3. **`multi_ci_tools/backends.py`** - Add implementation
   ```python
   class BuildBackend(ABC):
       @abstractmethod
       def new_stage_method(self) -> CommandResult:
           pass
   ```

### Adding New Tests

**Location:** `tests/test_{module}.py`

**Pattern:**
- One test file per module (e.g., `test_executor.py` for `executor.py`)
- Use pytest fixtures from `conftest.py`
- Mock subprocess calls (don't execute real commands)
- Test both success and error paths

**Current Status:** No test files exist yet (Phase 8 - To Do). Conftest.py only has a docstring.

## File Responsibilities

| File | Lines | Purpose | When to Edit |
|------|-------|---------|--------------|
| `cli.py` | ~150 | Argument parsing, CLI routing | Adding new CLI subcommands or flags |
| `types.py` | ~200 | Type contracts, frozen dataclasses | Adding new stages, config options, or data structures |
| `executor.py` | ~200 | Subprocess execution, streaming, redaction | Changing how commands execute (timeouts, retries, output handling) |
| `backends.py` | ~150 | Build system abstraction | Adding new build backends or stages |
| `orchestrator.py` | ~250 | Stage sequencing, result aggregation | Changing stage order, result classification, or execution flow |
| `adapters/base.py` | ~50 | CI adapter abstraction | Adding required methods to CIAdapter interface |
| `adapters/detect.py` | ~30 | Auto-detection logic | Adjusting CI platform detection priority |
| `adapters/jenkins.py` | ~80 | Jenkins env var extraction | Supporting new Jenkins env vars or changing normalization |
| `adapters/github.py` | ~80 | GitHub Actions env var extraction | Supporting new GitHub Actions context or changing normalization |
| `adapters/local.py` | ~60 | Local filesystem inspection | Changing how local environment is detected |
| `exceptions.py` | ~40 | Exception hierarchy | Adding new error types |
| `__init__.py` | ~10 | Package exports | Exporting new public classes/functions |
| `__main__.py` | ~5 | Entry point for `python -m` | Rarely changes |

## Layer Boundaries

### Python SDK (Lower Layer)
- **Files:** Everything in `multi_ci_tools/`
- **Responsibility:** CI-platform-agnostic pipeline logic
- **Interface:** `python -m multi_ci_tools run [options]`
- **Output:** Structured JSON result, exit code
- **Rule:** No platform-specific code below adapter layer

### CI Platform Layer (Upper Layer)
- **Files:** `Jenkinsfile`, `.github/workflows/ci.yml`, shell scripts
- **Responsibility:** Invoke SDK with appropriate flags, parse results
- **Interface:** Call SDK via subprocess
- **Output:** Platform-specific status/notification (build badge, job result)
- **Rule:** Thin wrappers only (~10-20 lines each); no pipeline logic

### Planning & Customization (Side Layer)
- **Files:** `.planning/` and `.agent/`
- **Responsibility:** Document architecture, define workflows
- **Rule:** Does not affect runtime behavior; informational only

## Adding New Directories

**When to Create a New Directory:**
- More than 3 related modules at same level
- Clear logical grouping (e.g., `adapters/` groups CI platform code)
- Files have common dependencies

**When NOT to Create a New Directory:**
- Just 1-2 files with no clear grouping
- Code primarily used by one other module
- Current structure is already flat and clear

**Current Flat Modules (Intentional):**
- Top-level `multi_ci_tools/` keeps core modules visible
- Easy to grasp project structure at a glance
- `adapters/` subdirectory justified because CI platforms are a major concern

## Testing Directory Structure (Phase 8)

When Phase 8 (testing) begins, adopt this structure:

```
tests/
├── conftest.py                      # Global fixtures & test config
├── unit/                            # Unit tests (no subprocess calls)
│   ├── test_types.py
│   ├── test_executor.py
│   ├── test_orchestrator.py
│   └── adapters/
│       ├── test_jenkins.py
│       ├── test_github.py
│       └── test_local.py
├── integration/                     # Integration tests (with subprocess)
│   ├── test_full_pipeline.py
│   ├── test_maven_backend.py
│   └── fixtures/
│       └── sample_pom.xml           # Test Maven projects
└── resources/                       # Test data & mocks
    ├── jenkins_env.json
    ├── github_env.json
    └── sample_output.txt
```
