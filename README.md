# TPMS Test Utility

Desktop Python/Tkinter utility for running the TPMS validation cycle (stages 0-6), executing SWUT routines, collecting DLT logs, and exporting filtered artifacts.

## What this tool does

- Stage-driven test flow advanced by Space key.
- SWUT command execution for stage 1 and stage 3 routines.
- SWUT command results shown as PASS/FAIL with captured SWUT console output in Execution log.
- Stage 3 Tawm restart over SSH hop (SGA -> VCU) before debug routine.
- Live DLT capture, timer-based test run, and post-test export.
- Mandatory Sun Valley ttk theme.

## Prerequisites

1. Windows with Python 3.11+.
2. Network access to SGA and VCU targets.
3. Sun Valley theme submodule initialized at vendor/sun-valley-ttk-theme.
4. Access to your internal Artifactory PyPI mirror.

## Setup (step-by-step)

1. Initialize submodules (required for mandatory Sun Valley theme):

```powershell
git submodule update --init --recursive
```

The repository pins the Sun Valley theme to a fixed commit via submodule gitlink.

2. Create a virtual environment:

```powershell
python -m venv .venv
```

3. Manually create .venv/pip.ini for your Artifactory mirror.

Example template (replace placeholders):

```ini
[global]
index-url = https://<ARTIFACTORY_HOST>/artifactory/api/pypi/<PYPI_REPO>/simple
trusted-host = <ARTIFACTORY_HOST>

[install]
trusted-host = <ARTIFACTORY_HOST>
```

If your mirror requires credentials, use your approved internal method (token, keyring, or URL format required by your organization).

4. Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

5. Install project dependencies:

```powershell
python -m pip install -e .
```

6. Create local runtime config:

```powershell
Copy-Item .env.example .env
```

7. Edit .env with your target credentials and SWUT PIN.

## .env configuration

The application reads .env at startup.

Required keys for stage 3 restart flow:

- TPMS_TARGET_HOST
- TPMS_SGA_HOST
- TPMS_SGA_USER
- TPMS_SGA_PASSWORD
- TPMS_VCU_HOST
- TPMS_VCU_USER
- TPMS_VCU_PASSWORD
- TPMS_TAWM_RESTART_COMMAND
- TPMS_SSH_TIMEOUT_SECONDS

SWUT key:

- SWUT_HPA_PIN

Behavior:

- TPMS_TARGET_HOST is used by DLT and as the default for TPMS_SGA_HOST.
- If TPMS_SGA_PASSWORD or TPMS_VCU_PASSWORD is set, stage 3 uses Paramiko password-based SSH.
- If both passwords are empty, stage 3 falls back to key-based OpenSSH batch mode.

## Run the application

```powershell
python .\main.py
```

## Containerized mock environment for timing

Use the mock stack to run deterministic timing checks without real SGA/VCU/SWUT targets.

1. Start mocked endpoints:

```powershell
docker compose -f docker-compose.mock.yml up -d
```

2. Load mock profile variables for the active shell:

```powershell
Get-Content .env.mock | ForEach-Object {
	if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
	$key, $value = $_ -split '=', 2
	[System.Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim(), 'Process')
}
```

3. Run stage-level latency measurement:

```powershell
python .\tools\perf\run_stage_latency.py --iterations 10 --stages 0,1,3,4
```

4. Review generated report:

- output/perf/stage_latency.json

5. Stop mocked endpoints:

```powershell
docker compose -f docker-compose.mock.yml down
```

Mock routing is opt-in and only active when these environment variables are set:

- TPMS_SWUT_MOCK_URL
- TPMS_SSH_MOCK_URL
- TPMS_DLT_HOST and TPMS_DLT_PORT

## How to use the tool during a cycle

1. Start the app.
2. Confirm stage 0 is selected.
3. Press Space to execute the current stage and advance.
4. Continue through stages in order:
- Stage 0: initialize cycle context.
- Stage 1: overwrite WUIDs via SWUT.
- Stage 2: manual operation stage.
- Stage 3: restart Tawm via SSH hop, then enter debug via SWUT.
- Stage 4: connect DLT and start logging.
- Stage 5: clear temp log and start timer.
- Stage 6: export filtered DLT and ASCII outputs after timer completion.

If a stage fails, progression is halted on that stage. Press Space again to re-run the same stage from the start.

5. Wait for stage 5 timer to complete before stage 6 export.

## Output artifacts

Output root:

- %LOCALAPPDATA%/dTPMSTestUtility

Per run, generated files include:

- <timestamp>_dlt_tmpfile.dlt
- <timestamp>_test.dlt
- <timestamp>_Tawm_filtered.dlt
- <timestamp>_Tawm_LIB_ascii.txt

## Troubleshooting

- pip install fails:
	verify .venv/pip.ini points to the correct Artifactory index and trusted host.
- Stage 3 SSH restart fails:
	verify .env host/user/password values and target reachability.
- Theme load fails:
	run git submodule update --init --recursive and verify vendor/sun-valley-ttk-theme/sv_ttk/sv.tcl exists.
- Stage 6 export blocked:
	stage 5 timer must finish first.
- Mock timing run fails to connect:
	verify docker containers are running and TPMS_SWUT_MOCK_URL, TPMS_SSH_MOCK_URL, TPMS_DLT_HOST, TPMS_DLT_PORT are set in the current shell.

## Notes

- Do not commit secrets in .env or .venv/pip.ini.
- Keep repository-level docs in sync when stage flow changes.

## AI Agent Onboarding

Future AI coding agents should start with AGENTS.md before making changes.

## Documentation

- docs/ARCHITECTURE.md
- docs/IMPLEMENTATION_NOTES.md
