# Code Review Suggestions

Updated: 2026-04-17

## Scope Reviewed
Updated: 2026-04-17 (Post-Profile and Action Refactor)


Previous scope:

- [main.py](main.py)
- [tpms_utility/cycle_controller.py](tpms_utility/cycle_controller.py)
- [tpms_utility/config.py](tpms_utility/config.py)
- [tpms_utility/stages/default_cycle.py](tpms_utility/stages/default_cycle.py)
- [tpms_utility/services/dlt_service.py](tpms_utility/services/dlt_service.py)
- [tpms_utility/services/dlt_protocol.py](tpms_utility/services/dlt_protocol.py)
- [tpms_utility/services/log_exporter.py](tpms_utility/services/log_exporter.py)
- [tpms_utility/services/swut_service.py](tpms_utility/services/swut_service.py)
- [tpms_utility/services/audio_service.py](tpms_utility/services/audio_service.py)
- [tpms_utility/ui/main_window.py](tpms_utility/ui/main_window.py)
- [tools/perf/run_stage_latency.py](tools/perf/run_stage_latency.py)
- [tools/mock_env/dlt_mock_server.py](tools/mock_env/dlt_mock_server.py)
- [tools/mock_env/ssh_mock_server.py](tools/mock_env/ssh_mock_server.py)
- [tools/mock_env/swut_mock_server.py](tools/mock_env/swut_mock_server.py)
- [Jenkinsfile](Jenkinsfile)
Newly added scopes:
- [tpms_utility/dlt_actions.py](tpms_utility/dlt_actions.py)
- [tpms_utility/swut_actions.py](tpms_utility/swut_actions.py)
- [tpms_utility/stages/profiles.py](tpms_utility/stages/profiles.py)


## Findings

- No open findings. The previously logged documentation drifts in [docs/IMPLEMENTATION_NOTES.md](docs/IMPLEMENTATION_NOTES.md) were corrected.

### ✅ PASSED — Core Infrastructure

- **Profile system**: `discover_profiles()` and `load_profile()` correctly discover and load stage definitions from JSON files.
- **Action refactoring**: `DltActions` and `SwutActions` cleanly separate stage action logic. All action resolution uses controller's `resolve_stage_action()` method consistently.
- **Stage flow**: Stage 0-6 sequence remains intact. Fail-fast behavior on SWUT errors preserved. Stage 6 export gating unchanged.
- **SWUT integration**: `SwutActions` execute fail-fast with clear error logging. Tawm SSH restart in stage 3 works with all connection modes.
- **DLT export**: Stage 5 timer completion enforced in `DltActions.action_filter_export()`. Prevents premature export.
- **Tests**: All 37 tests pass (12 existing + 25 new).
- **Compile check**: Passes via `python -m compileall tpms_utility tools`.
- **Sun Valley theme**: Mandatory theme loading enforced.

### ⚠️  MINOR ISSUES

- No open minor issues.

## Assumptions

- Jenkins agent OS is not guaranteed to be Windows.
- DLT traffic in real runs can be high enough for UI and log pressure to matter.

## Validation Snapshot

- Diagnostics: no static errors reported by workspace diagnostics.
- Compile check: passed via `python -m compileall tpms_utility tools`.
- Unit tests: passed via `python -m unittest discover -s tests -p "test_*.py"` (12 tests).
- Pytest was not available in the active venv (`No module named pytest`), so validation used the unittest suite.
- Review focus remained on stage-flow reliability, SWUT/SSH fail-fast behavior, DLT export gating, and optimization pipeline consistency.

## Summary

**Looks good to me.** Profile system and action refactoring are clean, tested, and preserve all critical stage-flow guarantees.
