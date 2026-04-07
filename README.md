# TPMS Test Utility Prototype

Python/Tkinter prototype for TPMS cycle execution with staged scripts, SWUT adapter integration points, and DLT logging workflow.

## Scope covered

- Stage model with spacebar-driven progression for stages 0-6.
- SWUT command stage execution for stages 1 and 3 (safe dry-run audit log in prototype mode).
- DLT logging lifecycle for stages 4-5 with configurable timer and early-shortening logic based on fault payloads.
- Log filtering and export for stage 6.
- Tkinter/ttk desktop UI with optional Sun Valley theme loading.

## Run

1. Create/activate a local Python 3.11+ virtual environment.
2. Optional: clone Sun Valley theme into `vendor/sun-valley-ttk-theme`.
3. Start the app:

```powershell
python main.py
```

## Sun Valley theme

Theme file expected at:

- `vendor/sun-valley-ttk-theme/sun-valley.tcl`

If missing, application falls back to default ttk theme.

## SWUT integration note

This prototype intentionally avoids calling remote/private package repositories. SWUT calls are represented through a local adapter writing to `output/swut_audit.log`.

Once SWUT is manually installed in your environment, replace the adapter internals in `tpms_utility/services/swut_service.py` with real SWUT API calls.

## DLT integration note

The current DLT implementation is a local adapter stub that models connection, live payload feed, and file exports. Production integration should replace internals in `tpms_utility/services/dlt_service.py` using DLT Viewer SDK/embedded mechanism approved by your design direction.

## Documentation

- Architecture and sequence diagrams: `docs/ARCHITECTURE.md`
- Detailed stage behavior and design notes: `docs/IMPLEMENTATION_NOTES.md`
