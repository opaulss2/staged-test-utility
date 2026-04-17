from __future__ import annotations

import unittest

from tpms_utility.config import AppSettings, DltConnectionSettings
from tpms_utility.cycle_controller import CycleController
from tpms_utility.stages.default_cycle import build_default_cycle


class DefaultCycleTests(unittest.TestCase):
    def _build_controller(self) -> CycleController:
        return CycleController(
            stages=[],
            app_settings=AppSettings(),
            dlt_settings=DltConnectionSettings(),
            on_state_changed=lambda: None,
            on_log=lambda _: None,
            on_timer_changed=lambda _: None,
        )

    def test_build_default_cycle_from_json(self) -> None:
        controller = self._build_controller()

        stages = build_default_cycle(controller)

        self.assertEqual([stage.stage_id for stage in stages], [0, 1, 2, 3, 4, 5, 6])
        self.assertIsNotNone(stages[0].action)
        self.assertIsNone(stages[2].action)
        self.assertEqual(stages[2].script_name, "(manual)")

    def test_unknown_action_name_raises(self) -> None:
        controller = self._build_controller()

        with self.assertRaises(ValueError):
            controller.resolve_stage_action("unknown-action")


if __name__ == "__main__":
    unittest.main()
