from __future__ import annotations

from dataclasses import dataclass
import shutil
import socket
from pathlib import Path
import threading
from typing import Callable

from tpms_utility.config import DltConnectionSettings
from tpms_utility.services.dlt_protocol import (
    DltStreamParser,
    ParsedDltMessage,
    build_control_frame,
    make_storage_header,
    payload_get_log_info,
    payload_service_u32,
    payload_set_default_log_level,
    payload_set_default_trace_status,
    payload_set_log_level,
    payload_set_timing_packets,
    payload_set_verbose_mode,
    SERVICE_GET_SOFTWARE_VERSION,
)


PayloadCallback = Callable[[str], None]


@dataclass(slots=True)
class DltMessage:
    app_id: str
    ctx_id: str
    payload: str


class DltService:
    def __init__(self) -> None:
        self.settings: DltConnectionSettings | None = None
        self.online = False
        self.current_tmp_file: Path | None = None
        self._callbacks: list[PayloadCallback] = []
        self._callback_lock = threading.Lock()
        self._socket: socket.socket | None = None
        self._receive_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._parser = DltStreamParser()
        self._socket_lock = threading.Lock()
        self._mcnt = 0
        self._profile_levels: list[tuple[str, str, int]] = []
        self._tmp_file_lock = threading.Lock()

    def connect(self, settings: DltConnectionSettings) -> None:
        self.settings = settings
        self._stop_event.clear()
        self._parser = DltStreamParser()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((settings.hostname, settings.port))
        sock.settimeout(1)

        self._socket = sock
        self.online = True

        self._send_initial_control_messages()
        if self._profile_levels:
            self._apply_profile_levels()

        self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._receive_thread.start()

    def disconnect(self) -> None:
        self._stop_event.set()
        self.online = False
        sock = self._socket
        self._socket = None
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        if self._receive_thread and self._receive_thread.is_alive():
            self._receive_thread.join(timeout=2)

    def set_logging_profile(self, profile_id: str) -> None:
        self._profile_levels = self._parse_profile(profile_id)
        if self.online:
            self._apply_profile_levels()

    def start_logging(self, tmp_file: Path) -> None:
        if not self.online:
            raise RuntimeError("DLT connection is offline")
        self.current_tmp_file = tmp_file
        self.current_tmp_file.parent.mkdir(parents=True, exist_ok=True)
        with self._tmp_file_lock:
            self.current_tmp_file.write_bytes(b"")

    def clear_tmp_log(self) -> None:
        if not self.current_tmp_file:
            raise RuntimeError("No temporary log configured")
        with self._tmp_file_lock:
            self.current_tmp_file.write_bytes(b"")

    def save_log_to(self, final_file: Path) -> None:
        if not self.current_tmp_file or not self.current_tmp_file.exists():
            raise RuntimeError("No temporary log available")
        final_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.current_tmp_file, final_file)

    def register_payload_callback(self, callback: PayloadCallback) -> None:
        with self._callback_lock:
            self._callbacks.append(callback)

    def clear_payload_callbacks(self) -> None:
        with self._callback_lock:
            self._callbacks.clear()

    def _receive_loop(self) -> None:
        while not self._stop_event.is_set():
            sock = self._socket
            if not sock:
                return
            try:
                data = sock.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                self.online = False
                return

            if not data:
                self.online = False
                return

            messages = self._parser.add(data)
            for message in messages:
                self._persist_message(message)
                if message.payload_text:
                    self._emit_payload(message.payload_text)

    def _persist_message(self, message: ParsedDltMessage) -> None:
        if not self.current_tmp_file:
            return
        with self._tmp_file_lock:
            if not self.current_tmp_file:
                return
            with self.current_tmp_file.open("ab") as handle:
                header = make_storage_header(self.settings.ecu_id if self.settings else "TPMS")
                handle.write(header)
                handle.write(message.frame)

    def _emit_payload(self, payload_text: str) -> None:
        callbacks: list[PayloadCallback]
        with self._callback_lock:
            callbacks = list(self._callbacks)
        for callback in callbacks:
            callback(payload_text)

    def _send_initial_control_messages(self) -> None:
        if not self.settings:
            return

        if self.settings.send_get_sw_version_if_online:
            self._send_control_payload(payload_service_u32(SERVICE_GET_SOFTWARE_VERSION))

        if self.settings.send_default_levels_if_online:
            self._send_control_payload(payload_set_default_log_level(self._map_log_level(self.settings.default_log_level)))
            self._send_control_payload(
                payload_set_default_trace_status(self._map_trace_status(self.settings.default_trace_status))
            )
            self._send_control_payload(payload_set_verbose_mode(self._map_verbose_mode(self.settings.verbose_mode)))

        self._send_control_payload(payload_set_timing_packets(self.settings.timing_packets_from_ecu))

        if self.settings.send_get_log_info_if_online:
            self._send_control_payload(payload_get_log_info())

    def _apply_profile_levels(self) -> None:
        for app_id, ctx_id, level in self._profile_levels:
            self._send_control_payload(payload_set_log_level(app_id, ctx_id, level))

    def _send_control_payload(self, payload: bytes) -> None:
        if not self.settings:
            return
        frame = build_control_frame(
            ecu_id=self.settings.ecu_id,
            payload=payload,
            mcnt=self._next_mcnt(),
        )
        self._send_frame(frame)

    def _send_frame(self, frame: bytes) -> None:
        sock = self._socket
        if not sock:
            raise RuntimeError("DLT connection is offline")
        with self._socket_lock:
            sock.sendall(frame)

    def _next_mcnt(self) -> int:
        current = self._mcnt
        self._mcnt = (self._mcnt + 1) % 256
        return current

    @staticmethod
    def _map_log_level(value: str) -> int:
        normalized = value.strip().lower()
        mapping = {
            "off": 0,
            "fatal": 1,
            "error": 2,
            "warn": 3,
            "info": 4,
            "debug": 5,
            "verbose": 6,
        }
        return mapping.get(normalized, 4)

    @staticmethod
    def _map_trace_status(value: str) -> int:
        normalized = value.strip().lower()
        if normalized == "on":
            return 1
        return 0

    @staticmethod
    def _map_verbose_mode(value: str) -> int:
        normalized = value.strip().lower()
        if normalized == "non-verbose mode":
            return 0
        return 1

    @staticmethod
    def _parse_profile(profile_id: str) -> list[tuple[str, str, int]]:
        import re

        app_match = re.match(r"\s*([A-Za-z0-9_]+)\s*:\s*\{(.+)\}\s*$", profile_id)
        if not app_match:
            return []
        app_id = app_match.group(1)
        content = app_match.group(2)

        ctx_matches = re.finditer(r"([A-Za-z0-9_]+)\s*:\s*\{\s*LogLevel\s*:\s*([A-Za-z]+)\s*\}", content)
        parsed: list[tuple[str, str, int]] = []
        for match in ctx_matches:
            ctx_id = match.group(1)
            level_text = match.group(2)
            parsed.append((app_id, ctx_id, DltService._map_log_level(level_text)))
        return parsed
