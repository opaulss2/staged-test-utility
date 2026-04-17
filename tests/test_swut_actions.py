from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, MagicMock

from tpms_utility.config import AppSettings, DltConnectionSettings
from tpms_utility.swut_actions import SwutActions
from tpms_utility.models import CycleRuntime
from tpms_utility.cycle_controller import CycleController


class SwutTestResult:
    """Mock SWUT result object matching the structure expected by action methods."""

    def __init__(self, success: bool, command: str, details: str) -> None:
        self.success = success
        self.command = command
        self.details = details


class SwutActionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.logs: list[str] = []
        self.timer_updates: list[int] = []

        self.app_settings = AppSettings(
            output_root=Path(self._tmp.name),
            test_duration_seconds=600,
            shortened_duration_seconds=120,
            log_all_dlt_payloads=False,
            fault_tokens={
                "fault id: 30 debounce status: 1",
                "fault id: 31 debounce status: 1",
                "fault id: 32 debounce status: 1",
                "fault id: 33 debounce status: 1",
            },
        )
        self.dlt_settings = DltConnectionSettings()

        self.controller = CycleController(
            stages=[],
            app_settings=self.app_settings,
            dlt_settings=self.dlt_settings,
            on_state_changed=lambda: None,
            on_log=self.logs.append,
            on_timer_changed=self.timer_updates.append,
        )
        self.swut_actions = SwutActions(self.controller)

    def tearDown(self) -> None:
        self.controller.stop()
        self._tmp.cleanup()

    def test_action_overwrite_wuids_runs_batch_commands(self) -> None:
        swut = Mock()
        swut.run_batch.return_value = [
            SwutTestResult(True, "1D12 1003", "success"),
            SwutTestResult(True, "1D12 2717", "success"),
            SwutTestResult(True, "1D12 2705", "success"),
            SwutTestResult(True, "1D12 2E20EB20000001200000022000000320000004", "success"),
        ]
        self.controller.swut = swut
        runtime = CycleRuntime(
            cycle_started_at=None,
            run_timestamp="20260417_120000",
            temp_log_path=Path(self._tmp.name) / "temp.dlt",
            final_log_path=Path(self._tmp.name) / "final.dlt",
        )

        self.swut_actions.action_overwrite_wuids(runtime)

        swut.run_batch.assert_called_once()
        commands = swut.run_batch.call_args[0][0]
        self.assertEqual(
            commands,
            [
                "1D12 1003",
                "1D12 2717",
                "1D12 2705",
                "1D12 2E20EB20000001200000022000000320000004",
            ],
        )

    def test_action_overwrite_wuids_logs_results(self) -> None:
        swut = Mock()
        swut.run_batch.return_value = [
            SwutTestResult(True, "1D12 1003", "success"),
        ]
        self.controller.swut = swut
        runtime = CycleRuntime(
            cycle_started_at=None,
            run_timestamp="20260417_120000",
            temp_log_path=Path(self._tmp.name) / "temp.dlt",
            final_log_path=Path(self._tmp.name) / "final.dlt",
        )

        self.swut_actions.action_overwrite_wuids(runtime)

        pass_messages = [msg for msg in self.logs if "SWUT test PASS" in msg]
        self.assertEqual(len(pass_messages), 1)
        self.assertIn("1D12 1003", pass_messages[0])

    def test_action_overwrite_wuids_raises_on_failure(self) -> None:
        swut = Mock()
        swut.run_batch.return_value = [
            SwutTestResult(True, "1D12 1003", "success"),
            SwutTestResult(False, "1D12 2717", "command failed"),
        ]
        self.controller.swut = swut
        runtime = CycleRuntime(
            cycle_started_at=None,
            run_timestamp="20260417_120000",
            temp_log_path=Path(self._tmp.name) / "temp.dlt",
            final_log_path=Path(self._tmp.name) / "final.dlt",
        )

        with self.assertRaises(RuntimeError) as cm:
            self.swut_actions.action_overwrite_wuids(runtime)

        self.assertIn("Stage 1 failed", str(cm.exception))
        self.assertIn("1D12 2717", str(cm.exception))

    def test_action_overwrite_wuids_logs_halt_message_on_failure(self) -> None:
        swut = Mock()
        swut.run_batch.return_value = [
            SwutTestResult(False, "1D12 1003", "failure"),
        ]
        self.controller.swut = swut
        runtime = CycleRuntime(
            cycle_started_at=None,
            run_timestamp="20260417_120000",
            temp_log_path=Path(self._tmp.name) / "temp.dlt",
            final_log_path=Path(self._tmp.name) / "final.dlt",
        )

        with self.assertRaises(RuntimeError):
            self.swut_actions.action_overwrite_wuids(runtime)

        halt_messages = [msg for msg in self.logs if "Stage 1 halted" in msg]
        self.assertEqual(len(halt_messages), 1)
        self.assertIn("stage will not advance", halt_messages[0])

    def test_action_enter_debug_restarts_tawm(self) -> None:
        swut = Mock()
        swut.run_batch.return_value = [
            SwutTestResult(True, "1D12 2705", "success"),
            SwutTestResult(True, "1D12 3101DF04", "success"),
        ]
        self.controller.swut = swut
        self.controller._restart_tawm_in_hpa = Mock()
        runtime = CycleRuntime(
            cycle_started_at=None,
            run_timestamp="20260417_120000",
            temp_log_path=Path(self._tmp.name) / "temp.dlt",
            final_log_path=Path(self._tmp.name) / "final.dlt",
        )

        self.swut_actions.action_enter_debug(runtime)

        self.controller._restart_tawm_in_hpa.assert_called_once()

    def test_action_enter_debug_runs_batch_commands(self) -> None:
        swut = Mock()
        swut.run_batch.return_value = [
            SwutTestResult(True, "1D12 2705", "success"),
            SwutTestResult(True, "1D12 3101DF04", "success"),
        ]
        self.controller.swut = swut
        self.controller._restart_tawm_in_hpa = Mock()
        runtime = CycleRuntime(
            cycle_started_at=None,
            run_timestamp="20260417_120000",
            temp_log_path=Path(self._tmp.name) / "temp.dlt",
            final_log_path=Path(self._tmp.name) / "final.dlt",
        )

        self.swut_actions.action_enter_debug(runtime)

        swut.run_batch.assert_called_once()
        commands = swut.run_batch.call_args[0][0]
        self.assertEqual(commands, ["1D12 2705", "1D12 3101DF04"])

    def test_action_enter_debug_logs_results(self) -> None:
        swut = Mock()
        swut.run_batch.return_value = [
            SwutTestResult(True, "1D12 2705", "success"),
            SwutTestResult(True, "1D12 3101DF04", "success"),
        ]
        self.controller.swut = swut
        self.controller._restart_tawm_in_hpa = Mock()
        runtime = CycleRuntime(
            cycle_started_at=None,
            run_timestamp="20260417_120000",
            temp_log_path=Path(self._tmp.name) / "temp.dlt",
            final_log_path=Path(self._tmp.name) / "final.dlt",
        )

        self.swut_actions.action_enter_debug(runtime)

        pass_messages = [msg for msg in self.logs if "SWUT test PASS" in msg]
        self.assertEqual(len(pass_messages), 2)

    def test_action_enter_debug_raises_on_failure(self) -> None:
        swut = Mock()
        swut.run_batch.return_value = [
            SwutTestResult(True, "1D12 2705", "success"),
            SwutTestResult(False, "1D12 3101DF04", "debug command failed"),
        ]
        self.controller.swut = swut
        self.controller._restart_tawm_in_hpa = Mock()
        runtime = CycleRuntime(
            cycle_started_at=None,
            run_timestamp="20260417_120000",
            temp_log_path=Path(self._tmp.name) / "temp.dlt",
            final_log_path=Path(self._tmp.name) / "final.dlt",
        )

        with self.assertRaises(RuntimeError) as cm:
            self.swut_actions.action_enter_debug(runtime)

        self.assertIn("Stage 3 failed", str(cm.exception))
        self.assertIn("1D12 3101DF04", str(cm.exception))

    def test_action_enter_debug_logs_halt_message_on_failure(self) -> None:
        swut = Mock()
        swut.run_batch.return_value = [
            SwutTestResult(False, "1D12 2705", "failure"),
        ]
        self.controller.swut = swut
        self.controller._restart_tawm_in_hpa = Mock()
        runtime = CycleRuntime(
            cycle_started_at=None,
            run_timestamp="20260417_120000",
            temp_log_path=Path(self._tmp.name) / "temp.dlt",
            final_log_path=Path(self._tmp.name) / "final.dlt",
        )

        with self.assertRaises(RuntimeError):
            self.swut_actions.action_enter_debug(runtime)

        halt_messages = [msg for msg in self.logs if "Stage 3 halted" in msg]
        self.assertEqual(len(halt_messages), 1)
        self.assertIn("stage will not advance", halt_messages[0])


if __name__ == "__main__":
    unittest.main()
