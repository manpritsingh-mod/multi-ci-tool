# Technology Stack

**Analysis Date:** 2026-04-10

## Languages

**Primary:**
- **Python 3.10+** - Main development language
  - Used in: `multi_ci_tools/` (entire SDK)
  - Minimum version: 3.10 (uses modern syntax like `dict[str, int]`)
  - Recommended: 3.11 or 3.12 (better performance, newer stdlib features)
  - Not compatible with: 3.8, 3.9 (older syntax and limited typing)

## Runtime

**Execution Environment:**
- **Python Runtime** - Standard CPython (system python or managed by Jenkins/GitHub)
- **Operating Systems:** Linux (CI standard), macOS (local development), Windows (WSL2 for CI tools)

## Build & Package Management

**Package Manager:**
- **pip** (standard Python package manager)
- **setuptools** - Package building and distribution
- **wheel** - Binary distribution format

**Installation:**
```bash
# Development install
pip install -e .

# With dev dependencies
pip install -e ".[dev]"

# Build distribution
python -m build
```

**Dependency Management:**
- **No lockfile** (`requirements.txt` not checked in)
- **Reason:** Core SDK has no external dependencies (uses only stdlib)
- **Dev dependencies** specified in `pyproject.toml` under `[project.optional-dependencies]`

**Version Specification (pyproject.toml):**
```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
requires-python = ">=3.10"
```

## Standard Library Dependencies

All production code uses only Python stdlib (no external packages):

- **subprocess** - Command execution (used in `executor.py`)
- **argparse** - CLI argument parsing (used in `cli.py`)
- **json** - JSON serialization (used for result output)
- **dataclasses** - Type-safe data structures (used in `types.py`)
- **enum** - Type-safe enumerations (used in `types.py`)
- **logging** - Structured logging (used throughout)
- **os** - Environment variable access (used in adapters)
- **threading** - Concurrent I/O for subprocess streaming (used in `executor.py`)
- **abc** - Abstract base classes (used in `adapters/base.py`, `backends.py`)
- **typing** - Type hints (used throughout for PEP 484 support)

## Development Dependencies

**Testing & Quality Tools** (`[project.optional-dependencies]` in pyproject.toml):

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",           # Test runner
    "pytest-cov>=4.0",       # Coverage reporting
    "mypy>=1.0",             # Static type checking (strict mode)
]
```

**Installation:**
```bash
pip install -e ".[dev]"
```

**Purpose:**
- **pytest** - Test framework and runner
- **pytest-cov** - Coverage measurement (target: 80% minimum)
- **mypy** - Static type checker in strict mode (enforces PEP 484 compliance)

## Build Tools

**No build pipeline beyond pip:**
- sdist and wheel built via `python -m build` (setuptools)
- No Gradle, Maven, or Makefile for Python packaging
- CI wrappers (Jenkinsfile, Actions) are separate from Python build

## CI/CD Integrations

### Jenkins
- **Jenkinsfile:** Thin wrapper (~15 lines)
- **Required Plugins:**
  - ShiningPanda plugin (for Python environment management)
  - Standard build/git plugins
- **Python Tool:** Configured in Jenkins Global Tool Configuration (tool name: "Python3")
- **Invocation:** `python -m multi_ci_tools run`

### GitHub Actions

**Workflow File:** `.github/workflows/ci.yml`

**Action Requirements:**
- `actions/checkout@v4` - Git checkout
- Python setup: Built-in `setup-python` action (or uses runner default)

**Invocation:** `python -m multi_ci_tools run`

### Local Development

**Entry Point:** `python -m multi_ci_tools` (uses `__main__.py`)

**Commands:**
- `python -m multi_ci_tools run` - Full pipeline
- `python -m multi_ci_tools inspect-env` - Detect CI platform
- `python -m multi_ci_tools dry-run` - Show what would run
- `python -m multi_ci_tools doctor` - Validate setup

## Build Backends (Application-Level)

**Current Implementation:**
- **Maven** (fully implemented in `backends.py`)
- Supports Maven 3.6.0+ (no specific version pinned; assumes available in PATH)

**Future Backends (Planned):**
- Gradle (Phase 2)
- npm/Yarn (Phase 3)
- .NET (Phase 4)

**Why No Version Pinning:**
- Assumes build tools installed separately in each environment
- Jenkins agents have Maven pre-installed
- GitHub Actions runners have Maven pre-installed
- Allows flexibility in tool versions without changing SDK code

## External Dependencies: NONE

**Philosophy:** Zero external dependencies in core SDK

**Benefits:**
- Minimal attack surface (no supply chain risks)
- Fast startup (no heavy imports)
- Easy to deploy (single Python install required)
- No version conflict nightmares

**Trade-offs:**
- Some features harder to implement (e.g., XML parsing uses only stdlib `xml.etree`)
- Some optimizations unavailable (e.g., no performance libraries)

## Configuration Files

### Project Metadata (`pyproject.toml`)
- Package name, version, description
- Python version requirement: 3.10+
- Optional dev dependencies
- pytest configuration:
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  python_files = ["test_*.py"]
  python_functions = ["test_*"]
  addopts = "-v --tb=short"
  ```
- mypy configuration: (stub only in current file, strict mode planned)

### Runtime Configuration
- **Environment Variables, not files**
- Prefix: `MCT_` (Multi-CI-Tools)
- Examples:
  - `MCT_LINT_MODE` - "pass" or "fail"
  - `MCT_ENABLE_SMOKE` - "true" or "false"
  - `MCT_BUILD_TIMEOUT` - seconds (default 300)

**Rationale:** CI systems easily support env vars; YAML/JSON config more complex in CI context

### No Configuration Files (Phase 2)
- **Planned:** `.multi-ci-tools.yaml` or `ci-config.json`
- **Status:** Deferred to Phase 2
- **Reason:** Env vars sufficient for MVP

## Development Tools

### VS Code Extensions (`.agent/`)

**GSD Framework:** Get Shit Done - sophisticated agent customization system
- 24 custom agents for different tasks
- Framework at `.agent/get-shit-done/`
- Enables:
  - Codebase mapping (gsd-codebase-mapper.md)
  - Code fixing (gsd-code-fixer.md)
  - Code review (gsd-code-reviewer.md)
  - Planning (gsd-planner.md)
  - And more...

### Version Control
- **Git** (obviously)
- `.gitignore` configured for Python (stdlib)

### Project State Tracking
- `.planning/` directory (project management metadata)
- Not part of runtime; informational only

## Known Limitations & Constraints

| Limitation | Impact | Workaround |
|-----------|--------|-----------|
| Only Maven backend implemented | Gradle projects can't use SDK yet | Phase 2 will add Gradle |
| No YAML/JSON config files | CI env vars only; no structured config | Use env vars; Phase 2 planned |
| No external code analysis tools | Linting relies on Maven plugins only | Phase 6 will add custom analysis |
| No email/Slack notifiers yet | Can only output JSON results | Phase 6 will add notifiers |
| Python 3.10+ required | Won't run on older systems | Update Python on CI runners |
| Single-threaded stage execution | Stages run sequentially, not parallel | Improves debugging; parallel planned for Phase 7 |

## Performance Characteristics

- **Startup time:** ~100-200ms (small imports, no external deps)
- **Typical pipeline time:** 5-30 minutes (dominated by Maven build/test, not Python)
- **Memory footprint:** ~50MB (lightweight SDK, streaming output to CI console)

## Upgrading Dependencies

**Development Dependencies:**
```bash
# Check for updates
pip list --outdated

# Upgrade all dev dependencies
pip install --upgrade pytest pytest-cov mypy
```

**Note:** Core SDK has no dependencies to upgrade.

## Deployment Packaging

**Distribution Methods:**
1. **Development Install** (clone repo, `pip install -e .`)
2. **pip Install from PyPI** (when published)
3. **Docker Image** (future; not currently available)

**What Gets Packaged:**
- `multi_ci_tools/` package (pure Python)
- `pyproject.toml` (metadata)
- `README.md` (documentation)

**What Does NOT Get Packaged:**
- `.agent/` (customization framework; VS Code only)
- `.planning/` (project management; informational)
- `tests/` (separate distribution or omitted from package)
- `Jenkinsfile` (platform-specific wrapper)

## Security Considerations

**No External Dependencies:**
- Eliminates pip supply chain attacks
- No CVE monitoring needed for SDK core
- Dev tools (pytest, mypy) are isolated to development

**Secrets Handling:**
- Secret redaction in executor (patterns: `*SECRET*`, `*PASSWORD*`, `*TOKEN*`)
- Never logs API keys or credentials
- CI env vars handled safely (no persistence to disk)
