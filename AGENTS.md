# AI Agent Onboarding

This document is the first stop for any AI agent working in this repository.

## 1. Mission

Maintain and extend the TPMS desktop utility safely.

Primary goals:

- Keep the stage-driven workflow (stages 0-6) reliable.
- Preserve SWUT integration behavior.
- Preserve standalone DLT behavior (no runtime dependency on dlt-viewer code).
- Keep operator workflow simple and deterministic.

## 2. First 5 Minutes Checklist

1. Read README.md fully.
2. Read tpms_utility/stages/default_cycle.py to understand stage order.
3. Read tpms_utility/cycle_controller.py to understand stage actions and side effects.
4. Read tpms_utility/config.py to understand runtime/env configuration.
5. Verify current diagnostics before editing (focus changed files).
6. Make minimal edits only; avoid unrelated refactors.

## 3. Setup Expectations

The user environment may require a custom mirror. Respect existing local setup.

- Python dependencies install via: python -m pip install -e .
- Custom package index may be configured manually in .venv/pip.ini.
- Runtime variables are loaded from .env by tpms_utility/config.py.
- Sun Valley theme is a git submodule under vendor/sun-valley-ttk-theme.
- Initialize submodules before runtime checks: git submodule update --init --recursive.

Never commit secrets from .env or .venv/pip.ini.

## 4. Runtime Architecture (Current)

- UI entrypoint: main.py
- Main window: tpms_utility/ui/main_window.py
- Stage orchestration: tpms_utility/cycle_controller.py
- Stage list: tpms_utility/stages/default_cycle.py
- SWUT adapter: tpms_utility/services/swut_service.py
- DLT runtime service: tpms_utility/services/dlt_service.py
- DLT protocol/parser helpers: tpms_utility/services/dlt_protocol.py
- Export logic: tpms_utility/services/log_exporter.py

## 5. Stage-Specific Rules

- Stage 1: executes SWUT overwrite sequence and must fail fast on command errors.
- Stage 3: must restart Tawm over SSH hop (SGA -> VCU) before running debug command.
- Stage 4-6: rely on standalone DLT service and parser.
- Stage 6 export requires stage 5 timer completion.

Do not reorder stages unless explicitly requested by the user.

## 6. Hard Constraints

- Do not reintroduce runtime dependency on dlt-viewer binaries/tools for stage flow.
- Keep Sun Valley theme mandatory.
- Keep Sun Valley theme pinned through submodule commit updates only.
- Preserve output location under LOCALAPPDATA/dTPMSTestUtility unless asked otherwise.
- Avoid changing public behavior silently; log important operational changes.

## 7. Edit Workflow

1. Gather context with targeted file reads/search.
2. Explain intent briefly before edits.
3. Apply smallest patch possible.
4. Validate with diagnostics and compile checks for changed Python files.
5. Summarize user-visible behavior changes.

Preferred validation command:

python -m compileall tpms_utility

## 8. Security and Safety

- Never print or hardcode credentials.
- Do not copy sensitive local config into tracked files.
- If a change touches SSH/auth/config, call it out explicitly in the summary.

## 9. Common Pitfalls

- Treating README text as source of truth when code has moved: always verify code.
- Editing .venv or generated caches as part of feature work.
- Breaking stage timing/export assumptions in cycle_controller.py.
- Changing .env.example with real credentials.

## 10. When Unsure

If requirements are ambiguous, ask one focused clarification question with options and defaults.
