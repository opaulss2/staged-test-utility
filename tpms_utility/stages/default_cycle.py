from __future__ import annotations

import json
from pathlib import Path

from tpms_utility.cycle_controller import CycleController
from tpms_utility.models import Stage


def build_default_cycle(controller: CycleController) -> list[Stage]:
    cycle_path = Path(__file__).with_name("default_cycle.json")
    stage_definitions = _read_stage_definitions(cycle_path)

    stages: list[Stage] = []
    for item in stage_definitions:
        stage_id = item.get("stage_id")
        name = item.get("name")
        script_name = item.get("script_name")
        action_name = item.get("action")

        if not isinstance(stage_id, int):
            raise ValueError(f"Invalid stage_id in {cycle_path}: {stage_id!r}")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Invalid name for stage {stage_id} in {cycle_path}")
        if not isinstance(script_name, str) or not script_name.strip():
            raise ValueError(f"Invalid script_name for stage {stage_id} in {cycle_path}")
        if action_name is not None and not isinstance(action_name, str):
            raise ValueError(f"Invalid action for stage {stage_id} in {cycle_path}: {action_name!r}")

        stages.append(
            Stage(
                stage_id=stage_id,
                name=name,
                script_name=script_name,
                action=controller.resolve_stage_action(action_name),
            )
        )

    return stages


def _read_stage_definitions(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError(f"Cycle definition at {path} must be a JSON array")
    return data
