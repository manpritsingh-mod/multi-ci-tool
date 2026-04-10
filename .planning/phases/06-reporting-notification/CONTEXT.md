---
phase: 6
name: "Reporting & Notification"
gathered: 2026-04-10
status: "Ready for planning"
dependencies: ["Phase 5: Pipeline Orchestrator"]
---

# Phase 6: Reporting & Notification

## Phase Boundary

Parse test results (JUnit XML from Maven surefire, checkstyle violations), generate human-readable build summaries, and deliver notifications via multiple channels (console, Slack, email).

This phase makes the SDK **production-grade** by adding visibility into build results beyond just pass/fail status.

**What gets delivered:**
1. **Reporting subsystem** — Extract & summarize test results + lint violations
2. **Summary generation** — Human-readable markdown summary with test counts, lint counts, stage timing
3. **Multi-channel notifiers** — Console (always), Slack (optional), Email (optional)
4. **Graceful degradation** — Notification failures never crash the pipeline

## Success Criteria (What Must Be TRUE)

1. ✓ JUnit parser extracts correct test counts from Maven surefire XML
2. ✓ Malformed XML handled gracefully (log warning, return zeros, don't crash)
3. ✓ Build summary always prints to console (no dependencies, uses stdlib xml.etree)
4. ✓ Slack/email notification failures are logged but never crash the pipeline

## Design Decisions

### XML Parsing Strategy
- **Decision:** Use stdlib `xml.etree` only (no external deps)
- **Rationale:** Keep core SDK lean, minimal attack surface
- **Implementation:** xpath-like queries to extract test counts from surefire reports

### Notification Architecture
- **Decision:** Notifier interface + pluggable implementations (Console, Slack, Email)
- **Rationale:** Easy to add new channels (Teams, PagerDuty, etc) in future
- **Pattern:** Similar to adapter pattern used for CI platforms — one ABC, multiple impls

### Slack Integration
- **Decision:** Use urllib.request + JSON stdlib (no requests library)
- **Rationale:** Zero dependencies; webhook acceptance built into Slack API
- **Error handling:** Webhook timeouts, 4xx/5xx responses, JSON marshalling errors → logged, not fatal

### Email Integration
- **Decision:** Use stdlib smtplib
- **Rationale:** No external deps; SMTP ubiquitous
- **Error handling:** SMTP connection failures, auth failures → logged, not fatal
- **TLS:** Support STARTTLS on configurable port (default 587)

### Summary Format
- **Decision:** Markdown with emoji status badges, stage table, test summary
- **Rationale:** Human-readable in CI logs, embeddable in Slack messages
- **Structure:** CI context → stage results table → test summary → timing

### the Agent's Discretion (Unspecified Areas)

These implementation details are explicitly NOT locked by requirements:

1. **JUnit XML schema variations** — Different Maven versions produce slightly different XML; how to handle version variations?
2. **Checkstyle severity mapping** — How to weight ERROR vs WARNING in final lint status?
3. **Notification timeout values** — How long to wait for Slack/email before giving up?
4. **Result redaction in summaries** — Should secrets be redacted from test output? (Probably yes, but not specified)
5. **Artifact attachment** — Should summaries attach surefire/checkstyle XML to notifications? (Probably no for v1)
6. **Batch notifications** — If multiple stages have issues, do we send one notification per stage or aggregate into single message?

## Architectural Context

### From Phase 5: Orchestrator Changes Needed

The orchestrator currently has both NOTIFY and PUBLISH stages. These need to be wired to the new notifier implementations:

- **NOTIFY stage** — Calls all notification channels (console, Slack, email)
- **PUBLISH stage** — Produces `ci-result.json` + summary (already partially implemented)

### File Additions

**New modules:**
- `multi_ci_tools/reporting.py` — JUnit + Checkstyle parsers
- `multi_ci_tools/notifiers.py` — Abstract Notifier + Console/Slack/Email impls

**Modified modules:**
- `multi_ci_tools/orchestrator.py` — Wire notifiers into NOTIFY stage
- `multi_ci_tools/types.py` — Add result summary dataclass

### From Phase 5 Codebase Review

The deep code review identified non-critical issues:
- **WR-02:** Executor returns tuple instead of CommandResult (data loss for timing)
- **WR-03:** Exception handling code smell (confusing control flow)
- **WR-04:** StageResult instantiation type mismatch

These CAN be addressed in Phase 6 if time permits, but are not blockers.

## Requirements Coverage

**Phase 6 Requirements:**

| ID | Requirement | Plan | Notes |
|-----|-------------|------|-------|
| RPT-01 | JUnit parser extracts test counts from surefire XML | 06-01 | |
| RPT-02 | Checkstyle parser extracts violation counts | 06-01 | |
| RPT-03 | Handle malformed XML gracefully | 06-01 | Log warning, return zeros |
| RPT-04 | Generate ci-result.json with stages + timing | 06-02 | Partially done in Phase 5 |
| RPT-05 | Generate summary.md with stage table + test summary | 06-02 | Human-readable output |
| NOTIF-01 | Console notification outputs build summary | 06-02 | Always enabled |
| NOTIF-02 | Slack notification via webhook | 06-02 | Optional, configured via env var |
| NOTIF-03 | Email notification via SMTP | 06-02 | Optional, configured via env vars |
| NOTIF-04 | Notification failures never crash pipeline | 06-02 | Caught + logged |

**Related Requirements from Other Phases:**

- CLI-05, CLI-06 — Output flags (`--emit-json`, `--emit-summary`) — Already in Phase 1, integrated in Phase 5
- PIPE-04, PIPE-05 — Notify/Publish always run — Already in Phase 5

## Canonical References

**Roadmap:** [ROADMAP.md](../../ROADMAP.md) — Phase 6 section  
**Requirements:** [REQUIREMENTS.md](../../REQUIREMENTS.md) — RPT-* and NOTIF-* sections  
**Architecture:** [.planning/codebase/ARCHITECTURE.md](../../codebase/ARCHITECTURE.md) — Pipeline orchestrator section

## Assumptions from Prior Phases

- ✓ Adapters return normalized CIContext
- ✓ Executor streams output in real-time
- ✓ Orchestrator produces PipelineResult with stages array and timing
- ✓ Maven always produces surefire reports in `target/surefire-reports/`
- ✓ No external dependencies (stdlib only) — maintained through Phase 6

## Open Questions for Planning

1. **JUnit XML schema:** Which fields are required vs optional? Should we validate against schema or just extract available fields?
2. **Checkstyle XML:** Same — strict validation or lenient extraction?
3. **Notification ordering:** Console first, then Slack, then email? Or parallel would be nice but adds complexity
4. **Retry logic for notifications:** Should we retry failed Slack/email, or fail-fast on first attempt?
5. **Aggregation:** Should we show per-stage test counts or just total across all stages?

## Ready to Plan

All context gathered. Phase 6 can proceed to detailed planning:

**Next:** `/gsd-plan-phase 6` to create 06-01-PLAN.md and 06-02-PLAN.md
