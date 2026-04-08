---
name: docker-desktop-optimization-pipeline
description: "Use when setting up, extending, debugging, or documenting a containerized optimization test pipeline with Docker Desktop, docker compose mock services, Jenkinsfile automation, stage latency benchmarking, or TPMS performance baselines. Keywords: Docker Desktop, Jenkinsfile, docker compose, mock endpoints, stage latency, optimization pipeline, performance baseline, benchmark artifacts."
---

# Docker Desktop Optimization Pipeline

## Purpose

Use this skill to build or maintain a deterministic optimization workflow for the TPMS repository using Docker Desktop, docker compose mock services, and Jenkins automation.

This skill is repository-scoped. It assumes:
- the stage order remains 0-6
- stage 3 still restarts Tawm over the SSH hop before SWUT debug commands
- stages 4-6 continue using the standalone DLT service and parser
- optimization checks use mocked endpoints, not real hardware

## Primary Outcome

Produce or maintain a working optimization pipeline that:
1. starts mocked endpoints in containers
2. runs stage-level latency measurements against those endpoints
3. archives benchmark artifacts
4. tears down the environment cleanly
5. keeps repo docs and Jenkins behavior in sync

## Files Usually Involved

- `Jenkinsfile`
- `docker-compose.mock.yml`
- `tools/mock_env/dlt_mock_server.py`
- `tools/mock_env/ssh_mock_server.py`
- `tools/mock_env/swut_mock_server.py`
- `tools/perf/run_stage_latency.py`
- `tpms_utility/config.py`
- `tpms_utility/cycle_controller.py`
- `tpms_utility/services/swut_service.py`
- `README.md`
- `AGENTS.md`
- `docs/IMPLEMENTATION_NOTES.md`
- `docs/ARCHITECTURE.md`

## Workflow

### 1. Confirm optimization scope

Identify which part of the pipeline is being changed:
- mock container topology
- benchmark runner behavior
- Jenkins execution flow
- metric output format or artifact path
- documentation and onboarding

If the change touches ports, benchmark flags, or output paths, plan to update code, Jenkins, and docs in the same change.

### 2. Verify current contract boundaries

Read these files first:
- `README.md`
- `AGENTS.md`
- `tpms_utility/stages/default_cycle.py`
- `tpms_utility/cycle_controller.py`
- `tpms_utility/config.py`
- `Jenkinsfile`

Check these constraints before editing:
- stage order is fixed
- stage 1 must fail fast on SWUT command errors
- stage 3 must perform SSH restart before the SWUT debug command
- stage 6 must remain blocked until the stage 5 timer completes
- no runtime dependency on dlt-viewer may be introduced

### 3. Keep mock routing opt-in

When adding or changing optimization behavior:
- preserve production defaults
- route to mocks only through environment variables
- avoid changing default runtime flow for the desktop app

Expected optimization environment variables:
- `TPMS_DLT_HOST`
- `TPMS_DLT_PORT`
- `TPMS_SWUT_MOCK_URL`
- `TPMS_SSH_MOCK_URL`
- `TPMS_TEST_DURATION_SECONDS`
- `TPMS_SHORTENED_DURATION_SECONDS`

### 4. Design containerized mocks for determinism

For Docker Desktop-based optimization checks:
- use docker compose for local and Jenkins startup
- isolate DLT, SSH, and SWUT mocks in separate services
- keep ports explicit and stable
- prefer deterministic happy-path responses first
- add configurable latency or failure injection only when needed

Mock expectations:
- DLT mock must speak the framing the parser already accepts
- SSH mock must preserve stage 3 success and failure semantics
- SWUT mock must preserve command-level pass/fail behavior

### 5. Keep benchmark scope narrow first

Default benchmark target:
- stage-level latency for stages `0,1,3,4`

Reasoning:
- these stages exercise initialization plus key external boundaries
- they avoid timer-driven duration from stages 5 and 6 in the baseline path
- they provide a stable starting point for regression tracking

If extending to stages 5 and 6 later:
- preserve timer-shortening behavior
- avoid hiding export gating rules
- make duration overrides explicit

### 6. Structure Jenkins for low-friction execution

Preferred Jenkins flow:
1. checkout
2. preflight for `python3`, `docker`, and `docker compose`
3. install project with `python3 -m pip install -e . --no-deps`
4. compile check with `python3 -m compileall tpms_utility tools`
5. start mock stack with `docker compose -f docker-compose.mock.yml up -d`
6. run benchmark runner
7. summarize JSON metrics in log output
8. always collect service logs and tear down containers
9. archive `output/perf` artifacts

Keep Jenkins non-interactive and deterministic.
Do not add private dependency installation to the optimization stages.

### 7. Update docs together

When the optimization pipeline changes, update these together when applicable:
- `Jenkinsfile`
- `README.md`
- `AGENTS.md`
- `docs/IMPLEMENTATION_NOTES.md`
- `docs/ARCHITECTURE.md`

At minimum, ensure these stay accurate:
- compose startup command
- benchmark command
- artifact paths
- required tools on Jenkins agents
- optimization pipeline stage order

### 8. Validate before finishing

Run the smallest appropriate validation set.

Preferred validation:
```powershell
python -m compileall tpms_utility tools
```

Optimization validation when Docker Desktop is available:
```powershell
docker compose -f docker-compose.mock.yml up -d
python tools/perf/run_stage_latency.py --iterations 3 --stages 0,1,3,4 --output output/perf/stage_latency.json
docker compose -f docker-compose.mock.yml down
```

If Docker Desktop is not available:
- say so explicitly
- validate the same endpoint contracts with local mock processes if practical
- do not claim compose validation was completed when it was not

## Decision Points

### When to change only docs

Change docs only when:
- commands or artifact locations changed previously and docs are now stale
- onboarding material is missing optimization pipeline guidance
- Jenkins behavior is already implemented and only documentation is lagging

### When to change runtime code

Change runtime code only when:
- a new mock endpoint variable is needed
- benchmark setup cannot target mocks without code support
- runtime behavior must expose a deterministic optimization seam

Avoid refactoring unrelated stage logic while doing optimization pipeline work.

### When to change benchmark schema

If `tools/perf/run_stage_latency.py` output changes:
- update Jenkins summary parsing in the same change
- update docs that reference artifact contents
- keep old consumers in mind or add a schema version field

## Completion Criteria

Consider the task complete when all of these are true:
- mocked endpoints can be started through docker compose
- benchmark runner can execute against the mock endpoints
- Jenkinsfile reflects the actual optimization workflow
- artifact locations are stable and documented
- onboarding docs tell future agents where to look first
- compile checks pass for changed Python files
- any unavailable validation, such as missing Docker Desktop, is called out explicitly

## Common Failure Modes

- changing compose ports without updating environment variables in Jenkins
- changing benchmark flags without updating docs
- accidentally coupling optimization checks to real credentials or real targets
- breaking stage 3 sequencing by bypassing restart semantics
- treating stage 5 and 6 timing rules as optional
- introducing runtime dependence on dlt-viewer tools

## Example Prompts

- "Set up a Docker Desktop optimization pipeline for this TPMS repo and add Jenkins support."
- "Update the mock compose services and Jenkinsfile after changing stage latency artifact paths."
- "Debug why the Docker Desktop optimization benchmark passes locally but fails in Jenkins."
- "Document the optimization pipeline so future agents can extend it safely."
