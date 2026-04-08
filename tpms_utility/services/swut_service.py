from __future__ import annotations

import contextlib
from dataclasses import dataclass
from datetime import datetime
import io
import json
import os
from pathlib import Path
from typing import Any, Callable
import urllib.error
import urllib.request

try:
    from swut.library.diagnostic_library import DiagnosticLibrary
except ImportError:  # pragma: no cover - depends on private package installation
    DiagnosticLibrary = None  # type: ignore[assignment]


@dataclass(slots=True)
class UdsCommandResult:
    command: str
    success: bool
    details: str


class SwutService:
    """SWUT adapter backed by DiagnosticLibrary.

    Expected cycle commands are mapped to explicit SWUT routines for HPA.
    """

    def __init__(self, output_dir: Path, mock_url: str = "") -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log = self.output_dir / "swut_audit.log"
        self.mock_url = (mock_url or os.environ.get("TPMS_SWUT_MOCK_URL", "")).strip().rstrip("/")
        self.hpa_host = os.environ.get("SWUT_HPA_HOST", os.environ.get("TPMS_TARGET_HOST", "169.254.4.10"))
        os.environ.setdefault("SWUT_HPA_HOST", self.hpa_host)
        self.hpa_pin = os.environ.get(
            "SWUT_HPA_PIN",
            "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",
        )
        self._diag_obj = None
        self._diag_obj_initialised = False

    def _get_diag_object(self):
        if not self._diag_obj_initialised:
            self._diag_obj_initialised = True
            if DiagnosticLibrary is not None:
                self._diag_obj = DiagnosticLibrary()
        return self._diag_obj

    @staticmethod
    def _normalize_command(command: str) -> str:
        parts = command.strip().split()
        if not parts:
            return ""
        if len(parts) > 1 and parts[0].upper() == "1D12":
            parts = parts[1:]
        return "".join(parts).upper()

    @staticmethod
    def _format_hex_bytes(hex_string: str) -> str:
        if len(hex_string) % 2 != 0:
            return hex_string
        return " ".join(hex_string[i : i + 2] for i in range(0, len(hex_string), 2))

    def _send_hpa_request(self, request_hex: str, expected: str | None = None, timeout: int | None = None) -> Any:
        if self._get_diag_object() is None:
            raise RuntimeError(
                "SWUT is not installed. Install SWUT from the private repository before running UDS stages."
            )

        args: list[object] = [request_hex, "to", "HPA"]
        if expected:
            args.append(expected)

        kwargs: dict[str, object] = {}
        if timeout is not None:
            kwargs["timeout"] = timeout

        return self._get_diag_object().send_request(*args, **kwargs)

    def _unlock_security_area(self, area: str) -> Any:
        if self._get_diag_object() is None:
            raise RuntimeError(
                "SWUT is not installed. Install SWUT from the private repository before running UDS stages."
            )
        return self._get_diag_object().unlock_security_area(
            area,
            "on",
            "HPA",
            pin=self.hpa_pin,
        )

    def _execute_mapped_command(self, normalized_command: str) -> Any:
        if normalized_command == "1003":
            return self._send_hpa_request("10 03", "response should contain 32 01 F4")
        if normalized_command == "2717":
            return self._unlock_security_area("17")
        if normalized_command == "2705":
            return self._unlock_security_area("05")
        if normalized_command == "2E20EB20000001200000022000000320000004":
            return self._send_hpa_request(
                "2E 20 EB 20000001200000022000000320000004",
                "response should match 6E 20 EB",
                timeout=10,
            )
        if normalized_command == "3101DF04":
            return self._send_hpa_request(
                "31 01 DF 04",
                "response should contain 71 01 DF 04 30",
            )

        return self._send_hpa_request(self._format_hex_bytes(normalized_command))

    @staticmethod
    def _to_jsonable(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, bytes):
            return value.hex()
        if isinstance(value, dict):
            return {str(k): SwutService._to_jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [SwutService._to_jsonable(v) for v in value]
        if hasattr(value, "__dict__"):
            return {
                k: SwutService._to_jsonable(v)
                for k, v in vars(value).items()
                if not k.startswith("_")
            }
        return str(value)

    def _response_to_json(self, response: Any) -> str:
        payload = self._to_jsonable(response)
        return json.dumps(payload, ensure_ascii=True, default=str)

    @staticmethod
    def _capture_console(call: Callable[[], Any]) -> tuple[Any, str]:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            result = call()
        return result, buffer.getvalue().strip()

    def _compose_details(self, response: Any, console_output: str) -> str:
        parts = [f"response={self._response_to_json(response)}"]
        if console_output:
            parts.append(f"stdout={console_output}")
        return " | ".join(parts)

    def _append_audit_log(self, command: str, result: str) -> None:
        timestamp = datetime.now().isoformat(timespec="seconds")
        line = f"{timestamp} | {result} | {command}\n"
        self.audit_log.write_text(
            self.audit_log.read_text(encoding="utf-8") + line if self.audit_log.exists() else line,
            encoding="utf-8",
        )

    def startup_self_check(self) -> UdsCommandResult:
        command = "SELF_CHECK 22F186"
        try:
            response, console_output = self._capture_console(
                lambda: self._send_hpa_request("22 F1 86", "response should match 62 F1 86 01")
            )
            self._append_audit_log(command, "OK")
            return UdsCommandResult(
                command=command,
                success=True,
                details=self._compose_details(response, console_output),
            )
        except Exception as exc:  # noqa: BLE001
            self._append_audit_log(command, "ERROR")
            return UdsCommandResult(command=command, success=False, details=str(exc))

    def run_uds_command(self, command: str) -> UdsCommandResult:
        normalized = self._normalize_command(command)
        if not normalized:
            return UdsCommandResult(command=command, success=False, details="Empty command")

        if self.mock_url:
            return self._run_mock_command(command=command, normalized_command=normalized)

        console_output = ""
        try:
            response, console_output = self._capture_console(lambda: self._execute_mapped_command(normalized))
            self._append_audit_log(command, "OK")
            return UdsCommandResult(
                command=command,
                success=True,
                details=self._compose_details(response, console_output),
            )
        except Exception as exc:  # noqa: BLE001
            self._append_audit_log(command, "ERROR")
            detail = str(exc)
            if console_output:
                detail = f"{detail} | stdout={console_output}"
            return UdsCommandResult(command=command, success=False, details=detail)

    def run_batch(self, commands: list[str]) -> list[UdsCommandResult]:
        return [self.run_uds_command(command) for command in commands]

    def _run_mock_command(self, command: str, normalized_command: str) -> UdsCommandResult:
        payload = {
            "command": command,
            "normalized_command": normalized_command,
            "hpa_host": self.hpa_host,
        }
        request = urllib.request.Request(
            url=f"{self.mock_url}/run",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310 - local/mock endpoint
                body = response.read().decode("utf-8", errors="ignore")
            parsed = json.loads(body) if body else {}
            success = bool(parsed.get("success", True))
            details = str(parsed.get("details", "mock response"))
            self._append_audit_log(command, "OK" if success else "ERROR")
            return UdsCommandResult(command=command, success=success, details=details)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            self._append_audit_log(command, "ERROR")
            return UdsCommandResult(command=command, success=False, details=f"mock SWUT request failed: {exc}")
