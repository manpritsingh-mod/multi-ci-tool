# Concerns

**Analysis Date:** 2026-04-10

## Technical Debt & Issues

### HIGH PRIORITY

#### 1. No Test Coverage (Phase 8 Blocker)

**Issue:** Zero unit/integration tests exist; conftest.py is only 5 lines with docstring.

**Impact:**
- Cannot detect regressions during refactor
- Undiscovered bugs in adapter detection, stage orchestration, command execution
- CI pipeline logic untested before production deployment

**Location:** `tests/conftest.py` (minimal), no test files

**Severity:** High - Core SDK untested

**Fix Approach (Phase 8):**
1. Create `tests/conftest.py` with shared fixtures (mocks, sample data)
2. Write unit tests for:
   - `types.py` (dataclass serialization, enum safety)
   - `executor.py` (streaming output, secret redaction, timeouts)
   - `orchestrator.py` (stage sequencing, result classification)
   - `adapters/` (environment detection priority, normalization)
   - `backends.py` (Maven command generation)
3. Write integration tests (real Maven, real Git)
4. Achieve 80% coverage (enforced by CI)

**Estimated Effort:** 4-6 weeks

---

#### 2. Reporting & Notifications Not Implemented (Phase 6)

**Issue:** JUnit parsing, summary generation, email/Slack notifiers are draft designs only.

**Impact:**
- `--emit-json ci-result.json` produces output but no schema validation
- `--emit-summary summary.md` not implemented
- No integration with Slack/email for notifications
- No parsing of Maven test failures → individual assertion failures invisible

**Locations:**
- `backends.py` (MavenBackend) - No JUnit parser
- `orchestrator.py` (Orchestrator) - No summary generation
- No notifier module exists

**Severity:** High - Currently no reporting beyond exit code

**Plan (Phase 6):**
1. Implement JUnit XML parser (`targets/surefire-reports/*.xml`)
2. Generate human-readable summary (`.md` format)
3. Implement Slack notifier (webhook URL from env var)
4. Implement email notifier (SMTP settings)
5. Enhance `ci-result.json` schema with test failure details

**Estimated Effort:** 3-4 weeks

---

#### 3. No YAML Configuration Support (Phase 2)

**Issue:** Configuration only via flat environment variables; no structured config file.

**Impact:**
- Complex pipelines require many env vars (hard to manage)
- No schema validation (easy to make typos)
- No config version control (env vars ephemeral)
- CI operators can't version control pipeline config

**Current State:**
- Config priority: CLI flags > env vars > defaults
- All config is flat (no nesting)
- Example: `MCT_LINT_MODE`, `MCT_ENABLE_SMOKE`, `MCT_BUILD_TIMEOUT`

**Severity:** Medium - Works, but limited scaling

**Plan (Phase 2):**
1. Support `.multi-ci-tools.yaml` or `ci-config.json` in repo root
2. Implement schema validation (Pydantic planned)
3. Merge file config with env var config (env vars override)
4. Document config schema in README

**Estimated Effort:** 1-2 weeks

---

### MEDIUM PRIORITY

#### 4. CI Wrapper Coupling & Brittleness

**Issue:** Jenkins & GitHub wrappers hardcoded assumptions that may break.

**Locations:**
- `Jenkinsfile` - Hardcodes "Python3" tool name (must match Jenkins Global Tool Configuration exactly)
- `.github/workflows/ci.yml` - Assumes `actions/checkout@v4` API stability

**Specific Problems:**
- Jenkinsfile line 20: `tool 'Python3'` - If admin renames tool, pipeline breaks silently
- GitHub Actions: Future API versions might deprecate action formats
- No error checking if Python not found in Jenkinsfile
- Jenkinsfile doesn't validate Maven is available

**Impact:** Pipeline mysteriously fails if CI config drifts

**Severity:** Medium - Rare issue, but hard to debug

**Fix Approach (Phase 7):**
1. Add error checking in Jenkinsfile
   ```groovy
   stage('Validate') {
       steps {
           sh 'python --version || (echo "Python not found"; exit 1)'
           sh 'mvn --version || (echo "Maven not found"; exit 1)'
       }
   }
   ```
2. Document required Jenkins Global Tool Configuration in README
3. Add comments linking to GitHub Actions action deprecation docs
4. CI health check command (`python -m multi_ci_tools doctor`)

**Estimated Effort:** 1 week

---

#### 5. Staging Example Not Production-Hardened

**Issue:** `MavenBackend` hardcodes Maven commands; no environment variable override for versions/options.

**Example Problem:**
- Command: `mvn clean install -DskipTests` assumes Maven binary in PATH
- No support for custom Maven options (e.g., `-X` debug, custom settings.xml location)
- No support for Java version specification
- No support for proxy settings

**Locations:**
- `backends.py` - Lines 40-50 (hardcoded commands)
- No env var like `MCT_MAVEN_OPTS` or `MCT_MAVEN_VERSION`

**Impact:** Advanced Maven configs can't be set without code change

**Severity:** Medium - Limits adoption for enterprises with custom Maven setups

**Fix Approach:**
1. Read `MCT_MAVEN_OPTS` env var, append to all Maven commands
2. Allow `JAVA_HOME` env var to override Java version
3. Allow `MAVEN_HOME` env var to override Maven location
4. Document in README

**Estimated Effort:** 1 week

---

#### 6. Command Timeout Handling Incomplete

**Issue:** `executor.py` implements timeouts, but no mechanism to handle graceful shutdown of hung processes.

**Current Behavior:**
- CommandExecutor times out after N seconds
- But subprocess may not be cleanly terminated
- No `SIGTERM` → `SIGKILL` escalation

**Location:** `executor.py` - CommandExecutor.run() method

**Impact:** Hung Maven builds might linger, consuming resources

**Severity:** Medium - Edge case, but serious for unreliable builds

**Fix Approach:**
1. On timeout, send `SIGTERM` to subprocess
2. Wait 10 seconds for graceful shutdown
3. If still running, send `SIGKILL`
4. Log which signal was used
5. Add integration test for timeout behavior

**Estimated Effort:** 1 week

---

#### 7. Secret Redaction Pattern Too Simplistic

**Issue:** `Redactor` class only patterns `*SECRET*`, `*PASSWORD*`, `*TOKEN*`; misses many secret types.

**Locations:**
- `executor.py` - Redactor class, patterns are hardcoded

**Examples of Unredacted Secrets:**
- API keys without "TOKEN" in name (e.g., `aws_access_key_id=...`)
- Bearer tokens in Authorization headers
- URLs with embedded credentials (e.g., `https://user:pass@github.com`)
- Docker registry credentials
- SSH keys
- Database connection strings

**Impact:** Secrets may appear in logs despite redaction intent

**Severity:** Medium - Security/compliance issue

**Fix Approach:**
1. Expand Redactor patterns to include common patterns
2. Add regex-based redaction for URLs with credentials
3. Read custom patterns from `MCT_REDACTION_PATTERNS` env var
4. Add escape hatch `MCT_DISABLE_REDACTION=true` for debugging (log warning)
5. Document redaction patterns in README

**Estimated Effort:** 1-2 weeks

---

### LOW PRIORITY

#### 8. LocalAdapter Not Fully Tested (Phase 8)

**Issue:** LocalAdapter uses `git` commands for branch/commit detection; no tests for Git-related failures.

**Locations:**
- `adapters/local.py` - Uses `subprocess.run()` directly (should use CommandExecutor)
- No test for "not in a git repo" failure case
- No test for non-standard .git layouts (worktrees, submodules)

**Impact:** Local development breaks on non-standard Git setups

**Severity:** Low - Affects edge cases only

**Fix Approach:**
1. Refactor LocalAdapter to use CommandExecutor (for consistency)
2. Add proper error handling for Git command failures
3. Add tests for edge cases (no .git, detached HEAD, submodules)

**Estimated Effort:** 1 week

---

#### 9. Documentation Gaps

**Issue:** README doesn't exist (mentioned in pyproject.toml but not found).

**Locations:**
- No README.md in repo root
- Project description in pyproject.toml is detailed, but not user-facing docs

**Missing Documentation:**
- Quick start guide
- CLI command reference
- Configuration reference (env vars, flags)
- Architecture overview
- Contributing guidelines

**Impact:** Developers don't know how to set up or use the SDK

**Severity:** Low - Planning docs exist (`.planning/`), but user docs missing

**Fix Approach:**
1. Create README.md with quick start, command reference
2. Create CONTRIBUTING.md for developers
3. Add docstring examples to CLI commands
4. Add inline code comments where logic is non-obvious

**Estimated Effort:** 1-2 weeks

---

#### 10. No Logging Configuration for CI Platforms

**Issue:** Python logging configuration hardcoded; no way to adjust log levels per CI platform.

**Locations:**
- Logging only configured implicitly (getLogger defaults)
- No logging.basicConfig() call in `__main__.py`

**Impact:**
- Jenkins operators can't increase verbosity for debugging
- GitHub Actions can't suppress debug logs for clean output
- No structured logging (JSON format unavailable)

**Severity:** Low - Workaround: grep output or use `--verbose` flag

**Fix Approach:**
1. Add logging setup to `__main__.py`
2. Support `--verbose` and `--quiet` CLI flags
3. Support `MCT_LOG_LEVEL` env var (DEBUG, INFO, WARNING, ERROR)
4. Optionally support `MCT_LOG_FORMAT` (text or JSON)

**Estimated Effort:** 1 week

---

#### 11. Publish Stage Not Idempotent

**Issue:** Publish stage design requires idempotence (runs even on build failure), but Maven publish logic not validated.

**Locations:**
- `backends.py` - MavenBackend.publish() - Currently just `mvn deploy`
- No checks that deploy is safe to retry

**Concern:** If build partially succeeds (artifact built but test fails), publish might corrupt artifact repository

**Severity:** Low - Design concern, not current issue (publish stage needs Phase 6 work)

**Fix Approach:**
1. Document idempotence requirement for publish backend
2. Add integration test: publish → failure → retry publish (should work)
3. Consider version tagging strategy (e.g., `-SNAPSHOT` suffix to avoid overwrites)

**Estimated Effort:** 1 week

---

#### 12. Smoke Tests Default Off (Hidden Feature)

**Issue:** Smoke tests only run if `MCT_ENABLE_SMOKE=true`; easy to forget feature exists.

**Location:**
- `backends.py` - Lines ~45 (if MCT_ENABLE_SMOKE)
- Not well-documented

**Impact:** Many environments never run smoke tests (CI optimizations for speed)

**Severity:** Low - Design decision, not a bug

**Fix Approach:**
1. Add `--enable-smoke-tests` CLI flag (explicit)
2. Document why off-by-default (speed)
3. Add example in README
4. Consider default-on in Phase 7 (when parallel execution improves performance)

**Estimated Effort:** 1 day

---

### DEFERRED (BY DESIGN)

#### 13. No Parallel Stage Execution

**Justification:** Sequential execution improves debugging (correlate failures to stages easily). Parallel execution will be Phase 7 optimization.

**Current Behavior:** Stages run sequentially: PREFLIGHT → RESOLVE_DEPS → LINT → BUILD → ... → NOTIFY

**Future:** Phase 7 will add `--parallel-stages` with DAG-based execution

---

#### 14. No GitLab Adapter (Yet)

**Justification:** MVP targets Jenkins + GitHub Actions. GitLab added Phase 2.

**Track as:** `feature/gitlab-adapter` (future branch)

---

#### 15. No Gradle/npm/dotnet Backends (Yet)

**Justification:** Maven MVP validated the architecture. Other build systems Phase 3+.

**Track as:** `feature/gradle-backend`, `feature/npm-backend`, etc.

---

## Risk Map

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Test suite gaps cause regressions | **High** | High | Phase 8 test coverage |
| Secrets leak in logs | Medium | High | Improve redaction patterns |
| CI config drifts causing silent failures | Medium | Medium | Add docstring, validation |
| Hung Maven builds linger | Low | Medium | Improve timeout handling |
| Custom Maven configs unsupported | Medium | Low | Add env var overrides |
| Documentation missing | High | Low | Write README & CONTRIBUTING |
| Git edge cases break LocalAdapter | Low | Low | Add error handling & tests |

## Suggestions for Future Work

1. **Security Audit** - Review secret handling after Phase 6
2. **Performance Profiling** - Measure startup time, streaming overhead after Phase 5
3. **User Research** - Gather feedback from Jenkins/GitHub teams before Phase 7
4. **Scalability Study** - Test with large Maven projects (1000+ modules) before production
