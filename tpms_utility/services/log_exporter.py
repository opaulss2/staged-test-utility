from __future__ import annotations

from pathlib import Path

from tpms_utility.services.dlt_protocol import parse_dlt_file_messages


class LogExporter:
    def export_filtered_dlt(self, source_file: Path, target_file: Path, app_id: str) -> None:
        raw = source_file.read_bytes()
        messages = parse_dlt_file_messages(raw)
        filtered = [m for m in messages if m.app_id.lower() == app_id.lower()]
        target_file.parent.mkdir(parents=True, exist_ok=True)
        with target_file.open("wb") as handle:
            for message in filtered:
                handle.write(message.frame)

    def export_filtered_ascii(self, source_file: Path, target_file: Path, app_id: str, ctx_id: str) -> None:
        raw = source_file.read_bytes()
        messages = parse_dlt_file_messages(raw)
        filtered = [
            m
            for m in messages
            if m.app_id.lower() == app_id.lower() and m.ctx_id.lower() == ctx_id.lower()
        ]
        target_file.parent.mkdir(parents=True, exist_ok=True)
        with target_file.open("w", encoding="utf-8") as handle:
            for message in filtered:
                if message.payload_text:
                    handle.write(message.payload_text)
                    handle.write("\n")
