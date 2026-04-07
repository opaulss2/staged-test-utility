from __future__ import annotations

from tpms_utility.cycle_controller import CycleController
from tpms_utility.models import Stage


def build_default_cycle(controller: CycleController) -> list[Stage]:
    return [
        Stage(stage_id=0, name="Init", script_name="stage0_init", action=controller.stage0_init),
        Stage(
            stage_id=1,
            name="Overwrite WUIDs",
            script_name="stage1_overwrite_wuids.py",
            action=controller.stage1_overwrite_wuids,
        ),
        Stage(stage_id=2, name="Manual: Set wheel sensors stationary", script_name="(manual)", action=None),
        Stage(
            stage_id=3,
            name="Enter dTPMS debug",
            script_name="stage3_enter_debug.py",
            action=controller.stage3_enter_debug,
        ),
        Stage(
            stage_id=4,
            name="Start logging",
            script_name="stage4_start_logging.py",
            action=controller.stage4_start_logging,
        ),
        Stage(
            stage_id=5,
            name="Clear log and start test",
            script_name="stage5_clear_start_test.py",
            action=controller.stage5_clear_start_test,
        ),
        Stage(
            stage_id=6,
            name="Filter and export",
            script_name="stage6_filter_export.py",
            action=controller.stage6_filter_export,
        ),
    ]


def build_dummy_cycle(controller: CycleController) -> list[Stage]:
    return [
        Stage(stage_id=0, name="Init", script_name="stage0_init", action=controller.stage0_init),
        Stage(
            stage_id=1,
            name="Overwrite WUIDs",
            script_name="stage1_overwrite_wuids.py",
            action=controller.stage1_overwrite_wuids,
        ),
        Stage(stage_id=2, name="Manual: Set wheel sensors stationary", script_name="(manual)", action=None),
        Stage(
            stage_id=3,
            name="Enter dTPMS debug",
            script_name="stage3_enter_debug.py",
            action=controller.stage3_enter_debug,
        ),
        Stage(
            stage_id=4,
            name="Start logging",
            script_name="stage4_start_logging.py",
            action=controller.stage4_start_logging,
        ),
        Stage(
            stage_id=5,
            name="Dummy stage",
            script_name="stage5_dummy.py",
            action=controller.stage_dummy,
        ),
        Stage(
            stage_id=6,
            name="Clear log and start test",
            script_name="stage6_clear_start_test.py",
            action=controller.stage5_clear_start_test,
        ),
        Stage(
            stage_id=7,
            name="Filter and export",
            script_name="stage7_filter_export.py",
            action=controller.stage6_filter_export,
        ),
    ]
