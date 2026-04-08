# Bottleneck And Unwanted Behavior Mitigation Suggestions

This document focuses on reducing criticality and operational risk, not only identifying issues.

## Optimization baseline in repository

Current optimization baseline is automated through `Jenkinsfile`.

Baseline execution path:
1. Start mocked endpoints with `docker-compose.mock.yml`.
2. Run `tools/perf/run_stage_latency.py` against stages `0,1,3,4`.
3. Persist metrics to `output/perf/stage_latency.json`.
4. Archive benchmark output and mock service logs.

Implication for remediation work:
- Any performance change should be verified both locally and through the Jenkins optimization pipeline.
- Changes to mock endpoint ports, benchmark arguments, or metrics paths must stay synchronized between `Jenkinsfile`, `README.md`, and implementation docs.

## 1) SWUT Audit Log Write Amplification

Primary location:
- tpms_utility/services/swut_service.py

Current behavior:
- Each audit entry rewrites the full file content.

Why critical:
- Cost grows with file size.
- Larger runs can trigger visible latency during stage operations.

Mitigation strategy:
- Write in append mode only.
- Add lightweight log rotation by size (for example 5-10 MB).
- Keep one active log and one backup to cap disk growth.

Criticality reduction:
- Limits worst-case write time from file-size dependent to near constant per entry.
- Prevents degraded responsiveness late in long test sessions.

Validation checks:
- Measure average and p95 audit write latency before and after.
- Verify log integrity across rotation boundaries.

## 2) UI Execution Log Memory Growth

Primary location:
- tpms_utility/ui/main_window.py

Current behavior:
- Log widget grows without retention limits.

Why critical:
- Memory use and text widget operations scale with run duration.
- Can cause slow scroll and delayed UI updates.

Mitigation strategy:
- Add ring-buffer-like retention (for example max 2000 lines).
- Trim old lines every N appends instead of every append.
- Keep full-fidelity archive in file logs, not in live widget.

Criticality reduction:
- Bounded memory and stable UI behavior regardless of test length.

Validation checks:
- Run 30+ minute simulated log flood and verify UI responsiveness.
- Track process memory growth trend pre/post change.

## 3) Per-Message File Open/Close In DLT Persistence

Primary location:
- tpms_utility/services/dlt_service.py

Current behavior:
- Each parsed message opens and closes the temp log file.

Why critical:
- Heavy filesystem churn under high message rates.
- Elevated I/O overhead can reduce effective capture throughput.

Mitigation strategy:
- Keep a buffered file handle open for the active logging window.
- Flush on interval and on stage boundaries.
- Force final flush and close during disconnect and stop paths.

Criticality reduction:
- Reduces syscall volume and write overhead.
- Improves sustained throughput under bursty DLT traffic.

Validation checks:
- Compare messages/second persisted before and after.
- Confirm no data loss during abrupt stop and normal stop.

## 4) Stage 5 Payload Log Flooding

Primary location:
- tpms_utility/cycle_controller.py

Current behavior:
- Every payload is pushed to UI log.

Why critical:
- Multiplies pressure on UI text growth and rendering.
- Important signals can be drowned by noise.

Mitigation strategy:
- Log only fault-token matches by default.
- Add optional debug mode for full payload logging.
- Add simple rate-limiter (for example one non-critical payload log per second).

Criticality reduction:
- Preserves operator visibility for key events while preventing log storms.

Validation checks:
- Verify all four required fault tokens are still always visible.
- Confirm timer-shortening behavior remains unchanged.

## 5) Runtime Side-Effect Risk In Demo Helper

Primary location:
- tpms_utility/services/swut_demo.py

Current behavior:
- Default argument instantiates DiagnosticLibrary during import.

Why critical:
- Hidden import-time side effects can slow startup and complicate debugging.

Mitigation strategy:
- Replace eager default construction with lazy inside-function initialization.
- Keep demo utilities isolated from production import paths where possible.

Criticality reduction:
- More deterministic module import behavior.
- Lower chance of unexpected initialization failures.

Validation checks:
- Verify import of demo module has no network/device side effects.
- Confirm function behavior unchanged when explicit object is supplied.

## 6) Small But Worthwhile Efficiency/Clarity Updates

Primary locations:
- tpms_utility/cycle_controller.py
- tpms_utility/services/dlt_protocol.py
- tpms_utility/services/dlt_service.py

Mitigation strategy:
- Replace full failure-list creation with first-failure lookup.
- Use a single timestamp source when building storage header time fields.
- Move repeated local imports to module scope for readability consistency.
- Remove unused DltMessage model or wire it meaningfully.

Criticality reduction:
- Low direct runtime impact, moderate maintainability impact.

Validation checks:
- Unit-level behavior parity checks for stage failure paths and DLT parsing.

## Recommended Rollout Order

1. SWUT audit append-only write path plus rotation.
2. UI log retention cap.
3. DLT buffered persistence.
4. Payload logging rate control.
5. Demo import side-effect cleanup.
6. Minor idiomatic cleanups.

Rationale:
- The first three items provide the largest immediate reduction in latency and resource pressure.

## Suggested Safety Gates Before Merge

- Compile and static diagnostics pass for changed files.
- Manual stage progression smoke test through stages 0-6.
- Stage 3 SSH restart still fail-fast on errors.
- Stage 5 timer and shortening logic unchanged.
- Stage 6 export still blocked until timer completion.
- Jenkins optimization pipeline run completes with archived `output/perf/stage_latency.json` artifact.

## Optional Observability Additions

- Add timing logs for audit write duration and DLT flush duration.
- Add counters for dropped/throttled UI payload logs.
- Add periodic memory snapshot logging in debug mode.

These additions make regressions detectable early and simplify future performance tuning.
