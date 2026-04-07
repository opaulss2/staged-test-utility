# Code Review Suggestions (No Code Changes Applied)

Scope reviewed:
- `main.py`
- `tpms_utility/**/*.py`
- Packaging metadata in `pyproject.toml`

Excluded from review scope:
- `vendor/` submodule code (third-party dependency)
- Generated egg-info metadata

## High Priority

1. **Avoid O(n^2) audit-log writes in SWUT service**
- File: `tpms_utility/services/swut_service.py`
- Issue: `_append_audit_log()` reads the full log file then writes full content back each time.
- Risk: As `swut_audit.log` grows, each write becomes slower and memory-heavy.
- Suggestion: Open the file in append mode (`"a"`, `encoding="utf-8"`) and write a single line.

2. **Prevent unbounded execution log growth in UI**
- File: `tpms_utility/ui/main_window.py`
- Issue: `_append_log()` continuously appends to `tk.Text` with no retention cap.
- Risk: Long runs can degrade UI responsiveness due to large in-memory text buffer.
- Suggestion: Keep only the last N lines (for example 1000-5000), trimming older lines periodically.

3. **Reduce high-frequency disk open/close in DLT capture path**
- File: `tpms_utility/services/dlt_service.py`
- Issue: `_persist_message()` opens/closes the temp file for every parsed message.
- Risk: High message rates can incur significant filesystem overhead and reduce throughput.
- Suggestion: Maintain a buffered file handle during stage 4-5 logging lifecycle, flush periodically, and close on disconnect.

## Medium Priority

4. **Limit payload logging verbosity during stage 5**
- File: `tpms_utility/cycle_controller.py`
- Issue: `_on_payload()` logs every incoming payload string to the UI log.
- Risk: This can flood the UI and amplify the unbounded-log performance issue.
- Suggestion: Log only matched fault tokens or rate-limit payload logging (for example, sample every N messages).

5. **Remove or use dead data model**
- File: `tpms_utility/services/dlt_service.py`
- Issue: `DltMessage` dataclass is defined but not used.
- Risk: Superfluous code increases maintenance burden and cognitive load.
- Suggestion: Remove it, or wire it into the parsing/persistence API if intended for future use.

6. **Avoid expensive list creation when only first failure is needed**
- File: `tpms_utility/cycle_controller.py`
- Issue: Stage methods build full `failures` lists, but only `failures[0]` is used.
- Risk: Minor inefficiency and unnecessary allocation.
- Suggestion: Use `next((r for r in results if not r.success), None)`.

7. **Fix default argument instantiation anti-pattern**
- File: `tpms_utility/services/swut_demo.py`
- Issue: `itpms_did_read_sw_version(diag_obj: DiagnosticLibrary = DiagnosticLibrary())` creates an object at import time.
- Risk: Surprising side effects, potential startup overhead, and shared mutable state.
- Suggestion: Use `diag_obj: DiagnosticLibrary | None = None` and instantiate inside the function.

## Low Priority / Idiomatic Improvements

8. **Use `time.time()` once for storage header generation**
- File: `tpms_utility/services/dlt_protocol.py`
- Issue: `make_storage_header()` calls `time.time()` twice for seconds/micros.
- Risk: Small inconsistency between second and microsecond parts and minor redundant work.
- Suggestion: Capture one timestamp value, then derive both parts.

9. **Hoist regex import to module scope**
- File: `tpms_utility/services/dlt_service.py`
- Issue: `_parse_profile()` imports `re` per call.
- Risk: Tiny overhead and style inconsistency.
- Suggestion: Move `import re` to top-level for cleaner idiomatic style.

10. **Consider explicit type for SWUT diagnostic object accessor**
- File: `tpms_utility/services/swut_service.py`
- Issue: `_get_diag_object()` has implicit dynamic return type.
- Risk: Lower static-analysis clarity.
- Suggestion: Add a concrete return annotation (or `Any | None`) and tighten usage sites.

## Validation Snapshot

- Static diagnostics in workspace: no current errors reported.
- This review made **no source-code behavior changes**.
