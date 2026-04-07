from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class UdsCommandResult:
    command: str
    success: bool
    details: str


class SwutService:
    """SWUT adapter.

    This implementation is safe for local prototyping: if SWUT is unavailable,
    commands are logged to a local file as dry-runs.
    """

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log = self.output_dir / "swut_audit.log"

    def run_uds_command(self, command: str) -> UdsCommandResult:
        timestamp = datetime.now().isoformat(timespec="seconds")
        line = f"{timestamp} | DRY-RUN | {command}\n"
        self.audit_log.write_text(
            self.audit_log.read_text(encoding="utf-8") + line if self.audit_log.exists() else line,
            encoding="utf-8",
        )
        return UdsCommandResult(command=command, success=True, details="Logged as dry-run")

    def run_batch(self, commands: list[str]) -> list[UdsCommandResult]:
        return [self.run_uds_command(command) for command in commands]
