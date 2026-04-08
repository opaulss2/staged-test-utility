# TPMS Utility Performance Baseline

Date established: 2026-04-08

## Scope

This baseline captures current stage-level latency for `tpms_utility` using the repository's mocked optimization environment.

Measured stages:
- Stage 0: Init
- Stage 1: Overwrite WUIDs
- Stage 3: Enter dTPMS debug
- Stage 4: Start logging

Stages 5 and 6 are intentionally excluded from the initial baseline because they include timer-driven behavior and export work that would make the first regression baseline less stable.

## Benchmark setup

Command:

```powershell
.\.venv\Scripts\python.exe tools\perf\run_stage_latency.py --iterations 10 --stages 0,1,3,4 --startup-samples 5 --output output\perf\stage_latency.json
```

Environment:

```text
TPMS_DLT_HOST=127.0.0.1
TPMS_DLT_PORT=3491
TPMS_SWUT_MOCK_URL=http://127.0.0.1:8082
TPMS_SSH_MOCK_URL=http://127.0.0.1:8081
TPMS_TEST_DURATION_SECONDS=5
TPMS_SHORTENED_DURATION_SECONDS=2
```

Mock infrastructure:
- `docker compose -f docker-compose.mock.yml up -d`
- DLT mock: `tools/mock_env/dlt_mock_server.py`
- SSH mock: `tools/mock_env/ssh_mock_server.py`
- SWUT mock: `tools/mock_env/swut_mock_server.py`

Artifacts:
- `output/perf/stage_latency.json`
- `output/perf/stage_latency_rerun.json`
- `output/perf/mock_services.log`

Startup baseline metric (captured in each stage latency artifact):
- `startup_import_ms.avg_ms`
- `startup_import_ms.p95_ms`

## Results

Two 10-iteration passes were collected to reduce single-run noise.

### Pass 1 averages

| Stage | Avg ms | Min ms | Max ms |
| --- | ---: | ---: | ---: |
| 0 | 0.001 | 0.001 | 0.002 |
| 1 | 129.981 | 101.817 | 254.045 |
| 3 | 119.456 | 104.678 | 149.560 |
| 4 | 10.824 | 3.491 | 29.574 |

### Pass 2 averages

| Stage | Avg ms | Min ms | Max ms |
| --- | ---: | ---: | ---: |
| 0 | 0.002 | 0.001 | 0.004 |
| 1 | 120.796 | 105.706 | 146.163 |
| 3 | 114.710 | 104.031 | 130.527 |
| 4 | 10.562 | 3.579 | 27.204 |

## Recommended baseline for comparisons

Use the two-pass average range below as the current baseline reference for remediation work.

| Stage | Reference avg range ms | Notes |
| --- | ---: | --- |
| 0 | 0.001 to 0.002 | Effectively negligible |
| 1 | 120.796 to 129.981 | Current dominant cost; one outlier spike to 254.045 ms observed |
| 3 | 114.710 to 119.456 | Second-largest consistent cost |
| 4 | 10.562 to 10.824 | Low average but occasional spikes into high 20 ms range |

## Interpretation

- Stage 1 and stage 3 are the primary latency contributors in the current mocked baseline.
- Stage 4 is relatively small on average but has moderate jitter.
- Stage 0 is not meaningful as an optimization target.

## How to use this baseline

For each remediation:
1. Run the same docker compose mock stack.
2. Run the same benchmark command with the same stage list and iteration count.
3. Compare new results against the ranges above.
4. Keep a change only if the improvement is measurable and repeatable.

Suggested validation sequence:

```powershell
docker compose -f docker-compose.mock.yml up -d
.\.venv\Scripts\python.exe tools\perf\run_stage_latency.py --iterations 10 --stages 0,1,3,4 --startup-samples 5 --output output\perf\stage_latency.json
docker compose -f docker-compose.mock.yml logs > output\perf\mock_services.log
docker compose -f docker-compose.mock.yml down -v --remove-orphans
```

## Notes

- During baseline collection, docker compose emitted a warning that the `version` field in `docker-compose.mock.yml` is obsolete. This did not block execution but should be cleaned up separately.
- This baseline was collected against mocked endpoints only. It is intended for regression comparisons inside the optimization pipeline, not for predicting real hardware timing.