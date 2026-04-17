from __future__ import annotations

from typing import TYPE_CHECKING

from tpms_utility.models import CycleRuntime

if TYPE_CHECKING:
    from tpms_utility.cycle_controller import CycleController


class SwutActions:
    def __init__(self, controller: CycleController) -> None:
        self.controller = controller

    def action_overwrite_wuids(self, _: CycleRuntime) -> None:
        commands = [
            "1D12 1003",
            "1D12 2717",
            "1D12 2705",
            "1D12 2E20EB20000001200000022000000320000004",
        ]
        results = self.controller.swut.run_batch(commands)
        self.controller._log_swut_test_results(results)
        failures = [result for result in results if not result.success]
        if failures:
            self.controller.on_log("❌ Stage 1 halted: SWUT test failure detected; stage will not advance")
            raise RuntimeError(f"Stage 1 failed: {failures[0].command} -> {failures[0].details}")

    def action_enter_debug(self, _: CycleRuntime) -> None:
        self.controller._restart_tawm_in_hpa()
        commands = ["1D12 2705", "1D12 3101DF04"]
        results = self.controller.swut.run_batch(commands)
        self.controller._log_swut_test_results(results)
        failures = [result for result in results if not result.success]
        if failures:
            self.controller.on_log("❌ Stage 3 halted: SWUT test failure detected; stage will not advance")
            raise RuntimeError(f"Stage 3 failed: {failures[0].command} -> {failures[0].details}")
