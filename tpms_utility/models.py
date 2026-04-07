from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable


StageAction = Callable[["CycleRuntime"], None]


@dataclass(slots=True)
class Stage:
    stage_id: int
    name: str
    script_name: str
    action: StageAction | None = None

    @property
    def is_manual(self) -> bool:
        return self.action is None


@dataclass(slots=True)
class CycleRuntime:
    cycle_started_at: datetime
    run_timestamp: str
    temp_log_path: Path
    final_log_path: Path
