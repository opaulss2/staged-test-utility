from __future__ import annotations

from pathlib import Path

from tpms_utility.cycle_controller import CycleController
from tpms_utility.models import Stage
from tpms_utility.stages.profiles import load_profile


def build_default_cycle(controller: CycleController) -> list[Stage]:
    """Load the default cycle from default_cycle.json."""
    cycle_path = Path(__file__).with_name("default_cycle.json")
    return load_profile(controller, cycle_path)
