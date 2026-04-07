from __future__ import annotations

from pathlib import Path


class LogExporter:
    def export_filtered_dlt(self, source_file: Path, target_file: Path, app_id: str) -> None:
        rows = self._read_rows(source_file)
        kept = [row for row in rows if f"APP={app_id}" in row]
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")

    def export_filtered_ascii(self, source_file: Path, target_file: Path, app_id: str, ctx_id: str) -> None:
        rows = self._read_rows(source_file)
        kept_payloads: list[str] = []
        for row in rows:
            if f"APP={app_id}" in row and f"CTX={ctx_id}" in row:
                parts = row.split("|", maxsplit=3)
                payload = parts[3] if len(parts) == 4 else row
                kept_payloads.append(payload)
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text("\n".join(kept_payloads) + ("\n" if kept_payloads else ""), encoding="utf-8")

    @staticmethod
    def _read_rows(source_file: Path) -> list[str]:
        if not source_file.exists():
            raise FileNotFoundError(f"Missing source log file: {source_file}")
        return [line.strip() for line in source_file.read_text(encoding="utf-8").splitlines() if line.strip()]
