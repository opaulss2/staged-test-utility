# Architecture

## Implemented architecture (prototype)

```mermaid
flowchart LR
    UI["Tkinter UI\nMainWindow"] --> CC["CycleController"]
    CC --> ST["Stage Definitions\n(default_cycle)"]
    CC --> SW["SwutService\nUDS command adapter"]
    CC --> DLT["DltService\nconnection/logging adapter"]
    CC --> EX["LogExporter\nfilter + export"]
    CC --> AU["AudioService\nbeeps"]
    DLT --> TMP["tmp DLT file"]
    DLT --> FINAL["final test DLT file"]
    EX --> OUT1["Tawm filtered DLT"]
    EX --> OUT2["Tawm+LIB ASCII"]
```

## Stage execution sequence (0-6)

```mermaid
sequenceDiagram
    participant User
    participant UI
    participant Controller
    participant SWUT
    participant DLT
    participant Exporter

    User->>UI: Space on stage 0
    UI->>Controller: stage0_init()

    User->>UI: Space on stage 1
    UI->>Controller: stage1_overwrite_wuids()
    Controller->>SWUT: run 4 UDS commands

    User->>UI: Space on stage 2
    UI->>Controller: manual stage advance

    User->>UI: Space on stage 3
    UI->>Controller: stage3_enter_debug()
    Controller->>SWUT: run 2 UDS commands

    User->>UI: Space on stage 4
    UI->>Controller: stage4_start_logging()
    Controller->>DLT: connect + set config + start tmp logging

    User->>UI: Space on stage 5
    UI->>Controller: stage5_clear_start_test()
    Controller->>DLT: clear tmp file
    Controller->>DLT: monitor incoming payloads
    Controller->>Controller: start timer
    Note over Controller: if all 4 fault payloads found, reduce timer to 2 minutes
    Controller->>DLT: save final log and disconnect at timeout

    User->>UI: Space on stage 6
    UI->>Controller: stage6_filter_export()
    Controller->>Exporter: export Tawm DLT
    Controller->>Exporter: export Tawm+LIB ASCII
    Controller->>UI: next space returns to stage 0
```

## Key extension points

- Real SWUT integration: `tpms_utility/services/swut_service.py`
- Embedded DLT viewer integration: `tpms_utility/services/dlt_service.py`
- Stage behavior customization: `tpms_utility/stages/default_cycle.py`
- UI design changes (layout/visual flow): `tpms_utility/ui/main_window.py`
