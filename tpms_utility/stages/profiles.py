from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from tpms_utility.models import Stage

if TYPE_CHECKING:
    from tpms_utility.cycle_controller import CycleController


def discover_profiles() -> list[tuple[str, Path]]:
    """Discover all available profile files (*.json) in the stages directory.
    
    Returns:
        List of tuples (profile_name, profile_path) sorted by name.
    """
    stages_dir = Path(__file__).parent
    json_files = sorted(stages_dir.glob("*.json"))
    profiles = [(f.stem, f) for f in json_files]
    return profiles


def load_profile(controller: CycleController, profile_path: Path) -> list[Stage]:
    """Load stages from a profile file.
    
    Args:
        controller: CycleController instance for resolving stage actions.
        profile_path: Path to the profile JSON file.
        
    Returns:
        List of Stage objects.
    """
    import json
    
    raw = profile_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    
    if not isinstance(data, list):
        raise ValueError(f"Profile definition at {profile_path} must be a JSON array")
    
    stages: list[Stage] = []
    for item in data:
        stage_id = item.get("stage_id")
        name = item.get("name")
        script_name = item.get("script_name")
        action_name = item.get("action")

        if not isinstance(stage_id, int):
            raise ValueError(f"Invalid stage_id in {profile_path}: {stage_id!r}")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Invalid name for stage {stage_id} in {profile_path}")
        if not isinstance(script_name, str) or not script_name.strip():
            raise ValueError(f"Invalid script_name for stage {stage_id} in {profile_path}")
        if action_name is not None and not isinstance(action_name, str):
            raise ValueError(f"Invalid action for stage {stage_id} in {profile_path}: {action_name!r}")

        stages.append(
            Stage(
                stage_id=stage_id,
                name=name,
                script_name=script_name,
                action=controller.resolve_stage_action(action_name),
            )
        )

    return stages
