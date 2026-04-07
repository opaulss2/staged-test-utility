from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import threading
import time
from typing import Callable

from tpms_utility.config import DltConnectionSettings


PayloadCallback = Callable[[str], None]


@dataclass(slots=True)
class DltMessage:
    app_id: str
    ctx_id: str
    payload: str


class DltService:
    """DLT adapter stub for Windows prototyping.

    The class models the required behaviors so the cycle can be executed end-to-end.
    A production integration can replace internals with actual DLT Viewer SDK bindings.
    """

    def __init__(self) -> None:
        self.settings: DltConnectionSettings | None = None
        self.online = False
        self.current_tmp_file: Path | None = None
        self._callbacks: list[PayloadCallback] = []
        self._stream_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def connect(self, settings: DltConnectionSettings) -> None:
        self.settings = settings
        self.online = True

    def disconnect(self) -> None:
        self._stop_streaming()
        self.online = False

    def set_logging_profile(self, profile_id: str) -> None:
        if not self.online:
            raise RuntimeError("DLT connection is offline")
        _ = profile_id

    def start_logging(self, tmp_file: Path) -> None:
        if not self.online:
            raise RuntimeError("DLT connection is offline")
        self.current_tmp_file = tmp_file
        self.current_tmp_file.parent.mkdir(parents=True, exist_ok=True)
        self.current_tmp_file.write_text("", encoding="utf-8")
        self._start_streaming()

    def clear_tmp_log(self) -> None:
        if self.current_tmp_file and self.current_tmp_file.exists():
            self.current_tmp_file.unlink()
        if self.current_tmp_file:
            self.current_tmp_file.write_text("", encoding="utf-8")

    def save_log_to(self, final_file: Path) -> None:
        if not self.current_tmp_file or not self.current_tmp_file.exists():
            raise RuntimeError("No temporary log available")
        final_file.parent.mkdir(parents=True, exist_ok=True)
        final_file.write_text(self.current_tmp_file.read_text(encoding="utf-8"), encoding="utf-8")

    def register_payload_callback(self, callback: PayloadCallback) -> None:
        with self._lock:
            self._callbacks.append(callback)

    def clear_payload_callbacks(self) -> None:
        with self._lock:
            self._callbacks.clear()

    def _append_message(self, message: DltMessage) -> None:
        if not self.current_tmp_file:
            return
        timestamp = datetime.now().isoformat(timespec="seconds")
        line = f"{timestamp}|APP={message.app_id}|CTX={message.ctx_id}|{message.payload}\n"
        with self._lock:
            with self.current_tmp_file.open("a", encoding="utf-8") as handle:
                handle.write(line)
            callbacks = list(self._callbacks)
        for callback in callbacks:
            callback(message.payload)

    def _start_streaming(self) -> None:
        self._stop_streaming()
        self._stop_event.clear()
        self._stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._stream_thread.start()

    def _stop_streaming(self) -> None:
        self._stop_event.set()
        if self._stream_thread and self._stream_thread.is_alive():
            self._stream_thread.join(timeout=1.0)

    def _stream_loop(self) -> None:
        payload_cycle = [
            "heartbeat alive",
            "fault id: 30 debounce status: 1",
            "fault id: 31 debounce status: 1",
            "fault id: 32 debounce status: 1",
            "fault id: 33 debounce status: 1",
            "wheel data update",
        ]
        index = 0
        while not self._stop_event.is_set():
            payload = payload_cycle[index % len(payload_cycle)]
            app_id = "Tawm"
            ctx_id = "LIB" if "fault id" in payload else "SERV"
            self._append_message(DltMessage(app_id=app_id, ctx_id=ctx_id, payload=payload))
            index += 1
            time.sleep(1)
