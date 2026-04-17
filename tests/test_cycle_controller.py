from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, call

from tpms_utility.config import AppSettings, DltConnectionSettings
from tpms_utility.cycle_controller import CycleController


class CycleControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.logs: list[str] = []
        self.timer_updates: list[int] = []
        self.state_change_count = 0

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
            on_state_changed=self._on_state_changed,
            on_log=self.logs.append,
            on_timer_changed=self.timer_updates.append,
        )

    def tearDown(self) -> None:
        self.controller.stop()
        self._tmp.cleanup()

    def _on_state_changed(self) -> None:
        self.state_change_count += 1

    def test_reset_cycle_disconnects_dlt_and_clears_state(self) -> None:
        dlt = Mock()
        self.controller.dlt = dlt
        self.controller.current_index = 4
        self.controller.runtime = self.controller.runtime_context()

        with self.controller._state_lock:
            self.controller._finished = True
            self.controller._fault_tokens_seen.add("fault id: 30 debounce status: 1")
            self.controller._total_duration_seconds = 5

        self.controller.reset_cycle()

        self.assertEqual(self.controller.current_index, 0)
        self.assertIsNone(self.controller.runtime)
        self.assertFalse(self.controller.is_test_finished)
        with self.controller._state_lock:
            self.assertEqual(len(self.controller._fault_tokens_seen), 0)
            self.assertEqual(self.controller._total_duration_seconds, self.app_settings.test_duration_seconds)
        dlt.disconnect.assert_called_once()
        dlt.clear_payload_callbacks.assert_called_once()
        self.assertIn(0, self.timer_updates)

    def test_action_start_logging_disconnects_before_connect(self) -> None:
        dlt = Mock()
        self.controller.dlt = dlt
        runtime = self.controller.runtime_context()

        self.controller.action_start_logging(runtime)

        self.assertEqual(
            dlt.mock_calls,
            [
                call.disconnect(),
                call.connect(self.dlt_settings),
                call.set_logging_profile(self.dlt_settings.logging_profile_id),
                call.start_logging(runtime.temp_log_path),
            ],
        )

    def test_on_payload_logs_only_fault_tokens_by_default(self) -> None:
        self.controller._on_payload("unrelated payload noise")
        self.assertFalse(any(message.startswith("DLT payload:") for message in self.logs))

        self.controller._on_payload("prefix fault id: 30 debounce status: 1 suffix")
        self.assertTrue(any("DLT fault token matched: fault id: 30 debounce status: 1" in message for message in self.logs))

    def test_on_payload_reduces_timer_once_all_tokens_seen(self) -> None:
        for token in sorted(self.app_settings.fault_tokens):
            self.controller._on_payload(f"message with {token}")

        with self.controller._state_lock:
            self.assertEqual(self.controller._total_duration_seconds, self.app_settings.shortened_duration_seconds)

        reductions = [
            entry
            for entry in self.logs
            if "All four debounce fault payloads found" in entry
        ]
        self.assertEqual(len(reductions), 1)

    def test_on_payload_logs_full_payload_in_debug_mode(self) -> None:
        self.controller.app_settings.log_all_dlt_payloads = True

        self.controller._on_payload("sample payload")

        self.assertTrue(any("DLT payload: sample payload" in message for message in self.logs))


if __name__ == "__main__":
    unittest.main()
