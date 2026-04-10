# Conventions

**Analysis Date:** 2026-04-10

## Code Style & Language

### Python Version & Targets
- **Minimum:** Python 3.10+
- **Recommended:** 3.11 or 3.12
- **Target Environments:** Local development, Jenkins agents, GitHub Actions runners

### Type Hints
- **Required:** All function signatures must include type hints (PEP 484)
- **Style:** Use modern syntax: `dict[str, int]` instead of `Dict[str, int]` (requires Python 3.9+)
- **Checked:** mypy in strict mode (enforced in pyproject.toml)

**Example:**
```python
def execute_stage(stage: StageName, timeout_sec: int = 300) -> StageResult:
    """Execute a single pipeline stage with timeout."""
    pass
```

### Naming Conventions

| Entity | Convention | Example |
|--------|-----------|---------|
| Constants | UPPER_SNAKE_CASE | `DEFAULT_TIMEOUT = 300`, `MCT_LINT_MODE` |
| Functions | snake_case | `def get_context()`, `def execute_stage()` |
| Classes | PascalCase | `CIAdapter`, `StageResult`, `MavenBackend` |
| Private methods | _leading_underscore | `def _execute_stage()`, `def _parse_output()` |
| Variables | snake_case | `commit_hash`, `is_pr_build` |
| Booleans | is/has prefix | `is_pr`, `has_errors` |
| Enum members | UPPER_SNAKE_CASE | `StageName.RESOLVE_DEPS`, `StageStatus.PASS` |

### Docstrings

**Style:** Google-style docstrings (not Sphinx or NumPy)

**Template:**
```python
def run_command(cmd: list[str], timeout_sec: int = 300) -> CommandResult:
    """Execute a shell command with timeout and secret redaction.
    
    This method runs a command in a subprocess, streams output to the console,
    and redacts sensitive information (passwords, API tokens) from logs.
    
    Args:
        cmd: List of command arguments (e.g., ["mvn", "test"])
        timeout_sec: Timeout in seconds. Defaults to 300 (5 minutes).
    
    Returns:
        CommandResult: Execution result with return code, stdout, stderr.
    
    Raises:
        CommandError: If timeout exceeded or subprocess crashed.
        ConfigError: If command list is empty.
    
    Example:
        >>> executor = CommandExecutor()
        >>> result = executor.run(["python", "--version"])
        >>> print(result.returncode)
        0
    """
    pass
```

**Required Sections:**
- One-line summary (first line)
- Detailed description (if needed)
- Args (for all parameters)
- Returns (for all return values)
- Raises (for all exceptions)
- Example (for public APIs)

### Immutability Pattern

**Frozen Dataclasses:** Use for all data contracts

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class CIContext:
    """Immutable CI environment context."""
    commit: str
    branch: str
    build_number: str
    workspace: str
```

**Why Frozen?**
- Prevents accidental mutation during pipeline execution
- Enables caching and result replication
- Signals immutability in code (self-documenting)

**When to Use:**
- All input/output data structures
- Configuration objects
- Result containers

### Enums for Type Safety

**Use Enums instead of magic strings:**

```python
from enum import Enum

class StageName(Enum):
    PREFLIGHT = "preflight"
    RESOLVE_DEPS = "resolve_deps"
    LINT = "lint"
    BUILD = "build"
    UNIT_TEST = "unit_test"
    SMOKE_TEST = "smoke_test"
    PUBLISH = "publish"
    NOTIFY = "notify"

class StageStatus(Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"
```

**Benefits:**
- IDE autocomplete
- Typo detection
- Exhaustiveness checking in type checkers

**Usage:**
```python
# ✓ GOOD: Typed enum access
if stage.status == StageStatus.PASS:
    print("Stage passed")

# ✗ BAD: Magic string comparison
if stage.status == "pass":  # Will fail mypy check
    print("Stage passed")
```

### Abstract Base Classes for Extension

**Pattern:** Use ABC for adapter and backend interfaces

```python
from abc import ABC, abstractmethod

class CIAdapter(ABC):
    """Abstract base for CI platform adapters."""
    
    @staticmethod
    @abstractmethod
    def detect() -> bool:
        """Return True if this adapter matches the current CI environment."""
        pass
    
    @abstractmethod
    def get_context(self) -> CIContext:
        """Extract and return normalized CI context."""
        pass
```

**Benefits:**
- Clear interface contracts
- Prevents accidental subclass incompleteness
- Easy to add new platforms (Jenkins → GitHub → GitLab)

### Logging & Output

**Logging Style:**
- Use Python's `logging` module (from stdlib)
- Log at INFO level for normal operations
- Log at WARNING for non-critical issues
- Log at ERROR for failures
- No print() statements in library code (use logging)

**Example:**
```python
import logging

logger = logging.getLogger(__name__)

def execute_stage(stage: StageName) -> StageResult:
    logger.info(f"Starting stage: {stage.value}")
    try:
        result = ...
        logger.info(f"Stage {stage.value} completed with status {result.status.value}")
        return result
    except Exception as e:
        logger.error(f"Stage {stage.value} failed: {e}")
        raise
```

**Secret Redaction:**
- Redactor class in `executor.py` handles this
- Never log passwords, API keys, or tokens
- Redactor strips `*SECRET*`, `*PASSWORD*`, `*TOKEN*` patterns

### Error Handling

**Custom Exception Hierarchy:**
```python
from multi_ci_tools.exceptions import (
    MCTException,           # Base exception
    ConfigError,            # Config validation failed
    AdapterError,           # Adapter detection/extraction failed
    CommandError,           # Command execution failed
    StageError              # Stage execution failed
)
```

**Pattern:**
```python
try:
    result = executor.run(cmd)
    if result.returncode != 0:
        raise StageError(f"Command failed: {cmd}", returncode=result.returncode)
except CommandError as e:
    logger.error(f"Command execution error: {e}")
    raise StageError(f"Stage {stage.value} failed") from e
```

**When to Raise:**
- ConfigError: Invalid configuration (missing required env var, bad flag)
- AdapterError: Can't detect CI platform or extract context
- CommandError: Subprocess execution failed (timeout, crash)
- StageError: Pipeline stage failed (non-zero exit code)

### Subprocess Execution Patterns

**Always Use This Pattern:**
```python
from multi_ci_tools.executor import CommandExecutor

executor = CommandExecutor()
result = executor.run(
    cmd=["mvn", "test"],
    timeout_sec=600,
    env={"MAVEN_OPTS": "-Xmx512m"}
)

if result.returncode != 0:
    raise CommandError(f"Maven failed: {result.stderr}")
```

**Pattern Benefits:**
- Streaming output (real-time to CI console)
- Timeout protection (not hung processes)
- Secret redaction (automatic)
- Thread-safe output handling

**Never Use Direct subprocess:**
```python
# ✗ BAD: Direct subprocess call (single-threaded, buffered output)
proc = subprocess.run(["mvn", "test"], capture_output=True)

# ✗ BAD: Popen without proper thread handling
proc = subprocess.Popen(["mvn", "test"])
proc.wait()
```

### Configuration Pattern

**Priority Order (highest to lowest):**
1. CLI Flags (e.g., `--stage build`)
2. Environment Variables (e.g., `MCT_LINT_MODE`)
3. Defaults (from RunConfig in types.py)

**Environment Variable Naming:**
- Start with `MCT_` prefix (Multi-CI-Tools)
- Use UPPER_SNAKE_CASE
- Examples: `MCT_LINT_MODE`, `MCT_ENABLE_SMOKE`, `MCT_BUILD_TIMEOUT`

**Example:**
```python
# In types.py
@dataclass(frozen=True)
class RunConfig:
    """Configuration with priority: env vars > CLI > defaults."""
    
    strict_mode: bool = False
    enable_smoke_tests: bool = False
    lint_mode: str = "fail"  # "fail" or "warn"
    
    @classmethod
    def from_env_and_cli(cls, cli_args):
        """Build config from environment variables and CLI flags."""
        strict = os.getenv("MCT_STRICT", "false").lower() == "true"
        if cli_args.strict:  # CLI overrides env
            strict = True
        return cls(strict_mode=strict, ...)
```

### Comment guidelines

**When to Comment:**
- Complex algorithms or non-obvious logic
- Workarounds for known issues
- Why something is done a certain way (not what it does)

**When NOT to Comment:**
- Self-documenting code (clear function/variable names)
- Obvious operations (e.g., `count += 1`)
- Every single line (noise)

**Example:**
```python
# ✓ GOOD: Explains why
# Jenkins uses 'origin/main' but GitHub uses 'main'. Strip
# 'origin/' prefix to normalize across platforms.
if branch.startswith("origin/"):
    branch = branch[7:]

# ✗ BAD: Says what the code does, not why
# Strip 'origin/' from branch
branch = branch[7:]
```

### Import Organization

**Order:**
1. Standard library (`import os`, `import sys`)
2. Third-party packages (if any)
3. Local modules (from `multi_ci_tools`)
4. Blank line between groups

**Example:**
```python
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from multi_ci_tools.types import CIContext, StageResult
from multi_ci_tools.executor import CommandExecutor
```

**Keep imports specific:**
```python
# ✓ GOOD: Clear what's used
from multi_ci_tools.types import CIContext, StageResult

# ✗ BAD: Unclear dependencies
from multi_ci_tools import *
```

## Git Conventions

### Commit Messages
- First line: ≤50 characters, imperative tense (e.g., "Add JUnit parser")
- Body: Explain what and why (not how)
- Reference issues/phases when applicable

**Example:**
```
Add JUnit parser for test result extraction

Extract test results from Maven surefire reports. This enables
detailed reporting of individual test failures vs. stage-level pass/fail.

Related to Phase 6 requirements: PIPE-12, PIPE-13
```

### Branch Naming
- Feature: `feature/short-description` (e.g., `feature/gitlab-adapter`)
- Bugfix: `bugfix/issue-name` (e.g., `bugfix/jenkins-envvar-normalization`)
- Phase work: `phase/{N}/short-description` (e.g., `phase/6/junit-parsing`)

## Testing Conventions (Phase 8)

### Test File Organization
- One test module per source module (e.g., `test_executor.py` for `executor.py`)
- Group related tests in test classes (e.g., `TestCommandExecutor`)
- Use descriptive test names: `test_should_...` or `test_does_...`

### Test Naming
```python
# ✓ GOOD: Clear intent
def test_should_timeout_after_max_duration():
    pass

def test_should_redact_password_from_logs():
    pass

# ✗ BAD: Unclear what's being tested
def test_timeout():
    pass

def test_logging():
    pass
```

### Mocking Pattern
- Mock subprocess calls (never execute real commands in tests)
- Mock file system access for unit tests
- Use fixtures in conftest.py for shared mock data

**Example:**
```python
import pytest
from unittest.mock import patch, MagicMock

@patch("multi_ci_tools.executor.subprocess.run")
def test_should_capture_command_output(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout=b"output")
    executor = CommandExecutor()
    result = executor.run(["echo", "test"])
    assert result.returncode == 0
```
