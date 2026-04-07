from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class DltConnectionSettings:
    hostname: str = "169.254.4.10"
    port: int = 3491
    auto_reconnect_timeout_seconds: int = 5
    default_log_level: str = "Info"
    default_trace_status: str = "Off"
    verbose_mode: str = "Verbose Mode"
    write_dltv2_storage_header: bool = False
    timing_packets_from_ecu: bool = False
    send_get_log_info_if_online: bool = True
    send_get_sw_version_if_online: bool = True
    send_default_levels_if_online: bool = True
    logging_profile_id: str = (
        "Tawm:{DRM:{LogLevel: verbose},LCM:{LogLevel: verbose},"
        "LIB:{LogLevel: verbose},EVNT:{LogLevel: verbose},"
        "FSHA:{LogLevel: verbose},SERV:{LogLevel: verbose},"
        "Tawm:{LogLevel: verbose}}"
    )


@dataclass(slots=True)
class AppSettings:
    output_root: Path = Path("C:/Users/dTPMSTestUtility")
    temp_log_template: str = "{timestamp}_dlt-viewer-tmpfile.dlt"
    final_log_template: str = "{timestamp}_test.dlt"
    tawm_export_template: str = "{timestamp}_Tawm_filtered.dlt"
    tawm_lib_export_template: str = "{timestamp}_Tawm_LIB_ascii.txt"
    test_duration_seconds: int = 10 * 60
    shortened_duration_seconds: int = 2 * 60
    fault_tokens: set[str] = field(
        default_factory=lambda: {
            "fault id: 30 debounce status: 1",
            "fault id: 31 debounce status: 1",
            "fault id: 32 debounce status: 1",
            "fault id: 33 debounce status: 1",
        }
    )


DEFAULT_DLT_SETTINGS = DltConnectionSettings()
DEFAULT_APP_SETTINGS = AppSettings()
