# Implementation Notes

## Runtime behavior

- Current cycle contains configured stages 0 through 6.
- UI renders stages 0 through 9; 7-9 are shown as not configured placeholders.
- Spacebar triggers the current stage action (if any) and advances to next stage.
- Stage 6 requires stage 5 timer completion; otherwise it raises an execution error.

## Stage details

### Stage 0: Init
- Marks system as ready.

### Stage 1: Overwrite WUIDs
- Executes UDS command batch:
  - `1D12 1003`
  - `1D12 2717`
  - `1D12 2705`
  - `1D12 2E20EB20000001200000022000000320000004`

### Stage 2: Manual
- No script execution. Tester performs manual wheel-sensor operation.

### Stage 3: Enter dTPMS debug
- Executes UDS command batch:
  - `1D12 2705`
  - `1D12 3101DF04`

### Stage 4: Start logging
- Creates DLT connection using configured defaults:
  - Hostname: `169.254.4.10`
  - Port: `3491`
  - Auto reconnect timeout: `5s`
  - Default log level: `Info`
  - Default trace: `Off`
  - Verbose mode enabled
- Applies logging profile id for Tawm contexts.
- Starts temp logging file `<timestamp>_dlt_tmpfile.dlt`.

### Stage 5: Clear log and start test
- Deletes/clears temp DLT file.
- Emits one beep on timer start.
- Starts test timer at configured duration (default 10 minutes).
- Monitors incoming payload text for all four fault tokens:
  - `fault id: 30 debounce status: 1`
  - `fault id: 31 debounce status: 1`
  - `fault id: 32 debounce status: 1`
  - `fault id: 33 debounce status: 1`
- When all four are observed, timer is reduced to 2 minutes.
- At timeout:
  - emits three beeps
  - saves final log to `C:/Users/dTPMSTestUtility/<timestamp>_test.dlt`
  - closes DLT connection
  - keeps saved log available for stage 6 processing

### Stage 6: Filter and export
- Applies filter `APP=Tawm` and exports DLT file.
- Applies filter `APP=Tawm` and `CTX=LIB` and exports ASCII file.

## Config knobs

`tpms_utility/config.py` contains adjustable parameters:
- test duration and shortened duration
- output paths and naming templates
- DLT default connection settings
- optional DLT port override (`TPMS_DLT_PORT`)
- optional optimization mock endpoints (`TPMS_SWUT_MOCK_URL`, `TPMS_SSH_MOCK_URL`)

## Optimization pipeline (Jenkins)

Pipeline entrypoint:
- `Jenkinsfile`

Pipeline purpose:
- execute deterministic stage-level latency checks in a containerized mock environment and archive output/perf artifacts.

Pipeline flow:
1. Checkout.
2. Verify tooling (`python3`, `docker`, `docker compose`).
3. Install project with `python3 -m pip install -e . --no-deps`.
4. Compile check with `python3 -m compileall tpms_utility tools`.
5. Start mock stack with `docker compose -f docker-compose.mock.yml up -d`.
6. Run benchmark with `python3 tools/perf/run_stage_latency.py --iterations <N> --stages 0,1,3,4 --output output/perf/stage_latency.json`.
7. Summarize metrics from JSON.
8. Always collect compose logs and tear down containers.

Mock components used by pipeline:
- `tools/mock_env/dlt_mock_server.py`
- `tools/mock_env/ssh_mock_server.py`
- `tools/mock_env/swut_mock_server.py`

Generated optimization artifacts:
- `output/perf/stage_latency.json`
- `output/perf/mock_services.log`

Default optimization environment values in pipeline:
- `TPMS_DLT_HOST=127.0.0.1`
- `TPMS_DLT_PORT=3491`
- `TPMS_SWUT_MOCK_URL=http://127.0.0.1:8082`
- `TPMS_SSH_MOCK_URL=http://127.0.0.1:8081`
- `TPMS_TEST_DURATION_SECONDS=5`
- `TPMS_SHORTENED_DURATION_SECONDS=2`

## Known prototype constraints for your design decision

- DLT integration is currently a local simulation adapter, not embedded native DLT viewer.
- SWUT adapter supports both real SWUT runtime behavior and optional mock endpoint mode for optimization tests.
- Stage sequencing behavior currently auto-wraps from stage 6 to stage 0 on next advance.
