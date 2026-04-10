# Testing

**Analysis Date:** 2026-04-10

## Current State

**Test Suite Status:** Phase 8 (Not Started)

**Existing Test Infrastructure:**
- `tests/conftest.py` - Minimal (only docstring, ~5 lines)
- No unit tests yet
- No integration tests yet
- No test fixtures defined yet

**Test Configuration (pyproject.toml):**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

**Coverage Requirement:** 80% minimum (enforced by CI)

## Testing Strategy (Planned for Phase 8)

### Test Pyramid

```
       E2E & Integration (5%)
            ↑
       Integration (20%)
            ↑
        Unit Tests (75%)
```

### Unit Tests (75% Coverage)

**Scope:** Individual functions/methods, no subprocess calls
**Tools:** pytest + unittest.mock
**Infrastructure:** Mock subprocess, file system, environment

#### Test Organization

```
tests/
├── conftest.py                      # Shared fixtures
├── unit/
│   ├── test_types.py                # Type contracts
│   ├── test_executor.py             # Command execution (mocked)
│   ├── test_orchestrator.py         # Stage sequencing logic
│   ├── test_exceptions.py           # Exception handling
│   ├── adapters/
│   │   ├── test_detect.py           # Detection logic
│   │   ├── test_jenkins.py          # Jenkins normalization
│   │   ├── test_github.py           # GitHub Actions normalization
│   │   └── test_local.py            # Local environment extraction
│   └── backends/
│       ├── test_maven_backend.py    # Maven command generation
│       └── test_base_backend.py     # Backend abstraction
├── integration/                     # Subprocess calls + real Maven
│   ├── test_full_pipeline.py        # End-to-end pipeline
│   ├── test_maven_build.py          # Real Maven execution
│   └── fixtures/
│       └── sample_pom.xml           # Test Maven project
└── resources/
    ├── jenkins_env.json             # Mock Jenkins env
    ├── github_env.json              # Mock GitHub Actions env
    └── mock_output.txt              # Captured command output
```

#### Test Examples

**Test: CommandExecutor Streaming** (`tests/unit/test_executor.py`)
```python
@patch("multi_ci_tools.executor.subprocess.Popen")
def test_should_stream_output_to_console(mock_popen):
    """Verify output streams real-time, not buffered."""
    mock_proc = MagicMock()
    mock_proc.stdout = iter([b"line1\n", b"line2\n"])
    mock_proc.stderr = iter([])
    mock_proc.returncode = 0
    mock_popen.return_value = mock_proc
    
    executor = CommandExecutor()
    result = executor.run(["echo", "test"])
    
    assert result.returncode == 0
    assert "line1" in result.stdout
    assert "line2" in result.stdout
```

**Test: Secret Redaction** (`tests/unit/test_executor.py`)
```python
def test_should_redact_api_tokens_from_output():
    """Verify sensitive data is stripped from logs."""
    output = "API_TOKEN=secret123-abc-xyz"
    redactor = Redactor()
    
    redacted = redactor.redact(output)
    
    assert "*TOKEN*" in redacted
    assert "secret123" not in redacted
```

**Test: Adapter Detection Priority** (`tests/unit/adapters/test_detect.py`)
```python
@patch.dict(os.environ, {
    "JENKINS_HOME": "/var/jenkins",
    "GITHUB_ACTIONS": "true"
})
def test_should_prefer_jenkins_over_github():
    """Verify Jenkins adapter wins in priority."""
    adapter = detect_adapter()
    
    assert isinstance(adapter, JenkinsAdapter)
```

**Test: Branch Normalization** (`tests/unit/adapters/test_jenkins.py`)
```python
@patch.dict(os.environ, {"GIT_BRANCH": "origin/main"})
def test_should_strip_origin_prefix_from_branch():
    """Verify Jenkins 'origin/main' normalized to 'main'."""
    adapter = JenkinsAdapter()
    context = adapter.get_context()
    
    assert context.branch == "main"
```

**Test: Stage Execution Order** (`tests/unit/test_orchestrator.py`)
```python
def test_should_execute_stages_in_correct_sequence(mock_executor):
    """Verify stage execution order: PREFLIGHT → BUILD → TEST → PUBLISH."""
    orchestrator = Orchestrator(backend=MockBackend())
    result = orchestrator.execute(RunConfig())
    
    stages_executed = [r.stage for r in result.stages]
    expected_order = [
        StageName.PREFLIGHT,
        StageName.RESOLVE_DEPS,
        StageName.LINT,
        StageName.BUILD,
        StageName.UNIT_TEST,
        StageName.SMOKE_TEST,
        StageName.PUBLISH,
        StageName.NOTIFY,
    ]
    assert stages_executed == expected_order
```

**Test: Overall Status Classification** (`tests/unit/test_orchestrator.py`)
```python
def test_should_classify_result_as_fail_if_any_stage_fails():
    """Verify worst stage determines overall status."""
    stages = [
        StageResult(StageName.BUILD, StageStatus.PASS, 10.0, "ok", None),
        StageResult(StageName.LINT, StageStatus.FAIL, 5.0, "fail", None),
        StageResult(StageName.PUBLISH, StageStatus.PASS, 2.0, "ok", None),
    ]
    orchestrator = Orchestrator(backend=MockBackend())
    
    overall = orchestrator._classify_overall_status(stages)
    
    assert overall == StageStatus.FAIL
```

### Integration Tests (20% Coverage)

**Scope:** Real subprocess calls, real Maven (if available), real file I/O
**Infrastructure:** Docker container with Maven, Git repo, JUnit XML samples

#### Integration Examples

**Test: Full Pipeline End-to-End** (`tests/integration/test_full_pipeline.py`)
```python
@pytest.mark.integration
@pytest.mark.requires_maven
def test_should_run_full_pipeline_with_sample_maven_project():
    """Full pipeline on real Maven project bundled in tests."""
    config = RunConfig(strict_mode=False, enable_smoke_tests=False)
    adapter = LocalAdapter()  # Real local env
    backend = MavenBackend(executor=CommandExecutor())
    orchestrator = Orchestrator(adapter, backend)
    
    result = orchestrator.execute(config)
    
    assert result.overall_status == StageStatus.PASS
    assert len(result.stages) == 8
    assert all(s.duration_sec > 0 for s in result.stages)
```

**Test: Jenkins Environment Detection** (`tests/integration/test_adapters.py`)
```python
@pytest.mark.integration
@pytest.mark.slow
def test_should_detect_jenkins_adapter_when_in_jenkins():
    """Real detection on actual Jenkins runner (CI only)."""
    if not os.getenv("JENKINS_HOME"):
        pytest.skip("Not running in Jenkins")
    
    adapter = detect_adapter()
    context = adapter.get_context()
    
    assert isinstance(adapter, JenkinsAdapter)
    assert context.commit  # Should have real commit
    assert context.branch  # Should have real branch
```

### Test Fixtures (conftest.py)

```python
# tests/conftest.py

import os
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_executor():
    """Mock CommandExecutor for unit tests."""
    executor = MagicMock()
    executor.run.return_value = CommandResult(
        returncode=0,
        stdout="output",
        stderr="",
        duration_sec=1.0
    )
    return executor

@pytest.fixture
def mock_backend():
    """Mock BuildBackend for orchestrator tests."""
    backend = MagicMock()
    backend.resolve_deps.return_value = CommandResult(0, "deps resolved", "", 1.0)
    backend.lint.return_value = CommandResult(0, "lint passed", "", 2.0)
    backend.build.return_value = CommandResult(0, "build succeeded", "", 10.0)
    backend.test.return_value = CommandResult(0, "tests passed", "", 15.0)
    backend.publish.return_value = CommandResult(0, "published", "", 2.0)
    return backend

@pytest.fixture
def mock_jenkins_env():
    """Jenkins environment variables."""
    return {
        "JENKINS_HOME": "/var/jenkins",
        "GIT_COMMIT": "abc123def456",
        "GIT_BRANCH": "origin/main",
        "BUILD_NUMBER": "42",
        "BUILD_URL": "http://jenkins:8080/job/test/42/",
        "WORKSPACE": "/var/jenkins/jobs/test/workspace",
    }

@pytest.fixture
def mock_github_env():
    """GitHub Actions environment variables."""
    return {
        "GITHUB_ACTIONS": "true",
        "GITHUB_SHA": "abc123def456",
        "GITHUB_REF_NAME": "main",
        "GITHUB_RUN_NUMBER": "42",
        "GITHUB_WORKSPACE": "/home/runner/work/multi-ci-tools/multi-ci-tools",
        "GITHUB_EVENT_NAME": "push",
    }

@pytest.fixture(autouse=True)
def clear_env():
    """Clear CI-specific env vars between tests."""
    original_env = dict(os.environ)
    keys_to_remove = [
        "JENKINS_HOME", "GIT_COMMIT", "GIT_BRANCH",
        "GITHUB_ACTIONS", "GITHUB_SHA", "GITHUB_REF_NAME",
    ]
    for key in keys_to_remove:
        os.environ.pop(key, None)
    
    yield
    
    os.environ.clear()
    os.environ.update(original_env)
```

### Running Tests

**Commands:**
```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage report
pytest tests/ --cov=multi_ci_tools --cov-report=html

# Run specific test
pytest tests/unit/test_executor.py::test_should_stream_output_to_console -v

# Run integration tests only (slow)
pytest tests/integration/ -v -m integration

# Run all except integration tests
pytest tests/ -v -m "not integration"

# Run with detailed output on failures
pytest tests/ -vv --tb=long
```

## Continuous Integration Testing

**GitHub Actions Workflow** (`.github/workflows/ci.yml`)

Currently tests adapter detection. Phase 8 will expand to full coverage:

```yaml
- name: Run unit tests
  run: pytest tests/unit/ --cov=multi_ci_tools --cov-report=xml

- name: Check coverage threshold (80%)
  uses: codecov/codecov-action@v3
  with:
    fail_ci_if_error: true
    minimum_coverage: 80

- name: Run integration tests (if Maven available)
  run: pytest tests/integration/ -m integration
  continue-on-error: true
```

## Known Test Gaps (Phase 8 Blockers)

| Area | Gap | Impact | Priority |
|------|-----|--------|----------|
| Executor | No timeout testing | Critical (timeouts prevent hung builds) | High |
| Orchestrator | No result aggregation tests | Critical (classification logic untested) | High |
| Backends | No Maven command generation tests | High (commands are core logic) | High |
| Adapters | No environment variable tests | High (normalization is critical) | High |
| CLI | No argument parsing tests | Medium (flags may have bugs) | Medium |
| Reporting | No JUnit parser tests | Medium (Phase 6 feature) | Blocked by Phase 6 |
| Exceptions | No error recovery tests | Medium (error cases not validated) | Medium |

## Test Data & Fixtures

**Location:** `tests/resources/`

**Sample Data:**
- `jenkins_env.json` - Mocked Jenkins env vars
- `github_env.json` - Mocked GitHub Actions env vars
- `mock_output.txt` - Captured Maven output for testing parsing
- `sample-pom.xml` - Minimal Maven project for integration tests
- `sample_junit.xml` - Maven surefire report for parser testing (Phase 6)

## Code Coverage Goals

**Target:** 80% (enforced by CI)

**By Module:**
- `types.py` - 100% (dataclasses are deterministic)
- `executor.py` - 90% (error paths and edge cases)
- `orchestrator.py` - 95% (core logic must be covered)
- `backends.py` - 85% (command generation)
- `adapters/*.py` - 90% (environment extraction)
- `cli.py` - 75% (argument parsing difficult to test fully)
- `exceptions.py` - 100% (simple classes)

## Testing Best Practices (For Future Phases)

1. **Test One Thing Per Test** - Each test verifies one behavior
2. **Mock External Systems** - Subprocess, file I/O, environment
3. **Use Descriptive Names** - `test_should_X_when_Y` makes intent clear
4. **Group Related Tests** - Use test classes for organization
5. **Isolate Test State** - Fixtures reset environment between tests
6. **No Test Interdependence** - Tests run in any order
7. **Keep Tests Fast** - Unit tests should run in milliseconds
8. **Use Markers** - `@pytest.mark.integration`, `@pytest.mark.slow` for filtering
