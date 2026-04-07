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
- Starts temp logging file `<timestamp>_dlt-viewer-tmpfile.dlt`.

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

## Known prototype constraints for your design decision

- DLT integration is currently a local simulation adapter, not embedded native DLT viewer.
- SWUT adapter is currently dry-run logging due to custom repository/API-key install constraints.
- Stage sequencing behavior currently auto-wraps from stage 6 to stage 0 on next advance.
