from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path


def _load_local_env() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_local_env()


def _target_host_default() -> str:
    return os.environ.get("TPMS_TARGET_HOST", "169.254.4.10")


@dataclass(slots=True)
class DltConnectionSettings:
    ecu_id: str = "TPMS"
    hostname: str = os.environ.get("TPMS_DLT_HOST", _target_host_default())
    port: int = int(os.environ.get("TPMS_DLT_PORT", "3491"))
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
    output_root: Path = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "dTPMSTestUtility"
    enable_swut_startup_self_check: bool = False
    ssh_timeout_seconds: int = int(os.environ.get("TPMS_SSH_TIMEOUT_SECONDS", "15"))
    ssh_mock_url: str = os.environ.get("TPMS_SSH_MOCK_URL", "")
    sga_host: str = os.environ.get("TPMS_SGA_HOST", _target_host_default())
    sga_user: str = os.environ.get("TPMS_SGA_USER", "swupdate")
    sga_password: str = os.environ.get("TPMS_SGA_PASSWORD", "")
    vcu_host: str = os.environ.get("TPMS_VCU_HOST", "198.19.0.1")
    vcu_user: str = os.environ.get("TPMS_VCU_USER", "root")
    vcu_password: str = os.environ.get("TPMS_VCU_PASSWORD", "")
    tawm_restart_command: str = os.environ.get(
        "TPMS_TAWM_RESTART_COMMAND",
        "/opt/csp/bin/em_control --restart tyre_and_wheel_monitor",
    )
    temp_log_template: str = "{timestamp}_dlt_tmpfile.dlt"
    swut_mock_url: str = os.environ.get("TPMS_SWUT_MOCK_URL", "")
    final_log_template: str = "{timestamp}_test.dlt"
    tawm_export_template: str = "{timestamp}_Tawm_filtered.dlt"
    tawm_lib_export_template: str = "{timestamp}_Tawm_LIB_ascii.txt"
    test_duration_seconds: int = int(os.environ.get("TPMS_TEST_DURATION_SECONDS", str(10 * 60)))
    shortened_duration_seconds: int = int(os.environ.get("TPMS_SHORTENED_DURATION_SECONDS", str(2 * 60)))
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
