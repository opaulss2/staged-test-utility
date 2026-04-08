# TPMS Utility — Master Performance Baseline

**Date:** 2026-04-08
**Branch:** master
**Commit:** ac379ca
**Artifact:** `output/perf/master_stage_latency_baseline.json`

This document records the official performance baseline for the `master` branch before any
bottleneck remediation is applied. Use these numbers as the regression threshold when comparing
changes from feature or performance branches.

---

## Benchmark Setup

| Parameter | Value |
|---|---|
| Iterations | 10 |
| Stages measured | 0, 1, 3, 4 |
| Startup samples | 5 |
| DLT mock | `127.0.0.1:3491` |
| SSH mock | `http://127.0.0.1:8081` |
| SWUT mock | `http://127.0.0.1:8082` |
| `TPMS_TEST_DURATION_SECONDS` | 5 |
| `TPMS_SHORTENED_DURATION_SECONDS` | 2 |

### Reproduce

```powershell
# 1. Start the mock stack
docker compose -f docker-compose.mock.yml up -d

# 2. Set environment
$env:TPMS_DLT_HOST='127.0.0.1'
$env:TPMS_DLT_PORT='3491'
$env:TPMS_SWUT_MOCK_URL='http://127.0.0.1:8082'
$env:TPMS_SSH_MOCK_URL='http://127.0.0.1:8081'
$env:TPMS_TEST_DURATION_SECONDS='5'
$env:TPMS_SHORTENED_DURATION_SECONDS='2'

# 3. Run benchmark
.\.venv\Scripts\python.exe tools\perf\run_stage_latency.py `
    --iterations 10 --stages 0,1,3,4 --startup-samples 5 `
    --output output\perf\master_stage_latency_baseline.json

# 4. Tear down
docker compose -f docker-compose.mock.yml down -v --remove-orphans
```

---

## Startup Import Time

Cold-process startup cost measured by importing `tpms_utility` in a clean subprocess (5 samples).

| Metric | Value (ms) |
|---|---|
| Average | **930.356** |
| Min | 799.588 |
| Max | 998.721 |
| p95 | 994.032 |

> Root cause (identified, not yet fixed on master): eager import of
> `swut.library.diagnostic_library` at module load time pulls in CLR and `one_dad.dll_helpers`,
> adding ~630 ms to every cold start. See `perf/remediation-1-2-swut-ui-log` for the lazy-import
> fix that reduces startup to ~206 ms avg.

---

## Stage Latency

All timings in milliseconds, 10 iterations over mock endpoints.

| Stage | Description | Min (ms) | Avg (ms) | Max (ms) |
|---|---|---|---|---|
| 0 | Cycle reset / ready | 0.002 | **0.004** | 0.014 |
| 1 | SWUT overwrite sequence | 103.121 | **130.373** | 295.679 |
| 3 | Tawm SSH restart + debug | 104.062 | **106.990** | 116.386 |
| 4 | DLT logging start | 3.615 | **5.288** | 10.525 |

> Stage 1 shows a high max (295.679 ms) on the first iteration, which is typical — the first run
> incurs additional cold-path overhead. Subsequent iterations cluster between 103–125 ms.

---

## Per-Iteration Records

| Iter | Stage 0 | Stage 1 | Stage 3 | Stage 4 |
|---|---|---|---|---|
| 1 | 0.002 | 295.679 | 107.340 | 5.780 |
| 2 | 0.003 | 104.532 | 107.668 | 4.105 |
| 3 | 0.014 | 125.132 | 105.346 | 5.467 |
| 4 | 0.003 | 125.603 | 105.144 | 3.615 |
| 5 | 0.002 | 112.145 | 106.155 | 10.525 |
| 6 | 0.002 | 105.013 | 108.086 | 4.377 |
| 7 | 0.003 | 106.650 | 104.831 | 4.257 |
| 8 | 0.002 | 122.307 | 104.882 | 5.784 |
| 9 | 0.002 | 103.121 | 104.062 | 4.070 |
| 10 | 0.003 | 103.543 | 116.386 | 4.900 |

---

## Reference Ranges (Regression Thresholds)

Any future branch that regresses **above** these bounds on a 10-iteration run should be
investigated before merging:

| Stage | Avg threshold | Max threshold |
|---|---|---|
| 0 | < 0.1 ms | < 1.0 ms |
| 1 | < 150 ms | < 320 ms |
| 3 | < 125 ms | < 140 ms |
| 4 | < 15 ms | < 25 ms |
| Startup import | < 1 000 ms avg | — |

---

## Known Improvements Available

The `perf/remediation-1-2-swut-ui-log` branch contains the following improvements relative
to this baseline:

| Metric | Master (this doc) | Remediated branch |
|---|---|---|
| Startup avg | 930 ms | ~206 ms (−74.8 %) |
| Startup p95 | 994 ms | ~237 ms (−72.7 %) |
| SWUT audit write | O(n) full-file rewrite | Append + 5 MB rotation |
| UI log widget | Unbounded growth | Capped at 2 000 lines |
