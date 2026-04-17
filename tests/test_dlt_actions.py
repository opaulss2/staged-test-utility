from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, call

from tpms_utility.config import AppSettings, DltConnectionSettings
from tpms_utility.dlt_actions import DltActions
from tpms_utility.models import CycleRuntime
from tpms_utility.cycle_controller import CycleController


class DltActionsTests(unittest.TestCase):
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
        self.dlt_actions = DltActions(self.controller)

    def tearDown(self) -> None:
        self.controller.stop()
        self._tmp.cleanup()

    def test_action_start_logging_disconnects_before_connect(self) -> None:
        dlt = Mock()
        self.controller.dlt = dlt
        runtime = self.controller.runtime_context()

        self.dlt_actions.action_start_logging(runtime)

        self.assertEqual(
            dlt.mock_calls,
            [
                call.disconnect(),
                call.connect(self.dlt_settings),
                call.set_logging_profile(self.dlt_settings.logging_profile_id),
                call.start_logging(runtime.temp_log_path),
            ],
        )

    def test_action_start_logging_logs_details(self) -> None:
        dlt = Mock()
        self.controller.dlt = dlt
        runtime = self.controller.runtime_context()

        self.dlt_actions.action_start_logging(runtime)

        start_log_messages = [msg for msg in self.logs if "DLT logging started:" in msg]
        self.assertEqual(len(start_log_messages), 1)
        self.assertIn(self.dlt_settings.hostname, start_log_messages[0])
        self.assertIn(str(self.dlt_settings.port), start_log_messages[0])
        self.assertIn(str(runtime.temp_log_path), start_log_messages[0])

    def test_action_clear_start_test_clears_log_and_resets_state(self) -> None:
        dlt = Mock()
        audio = Mock()
        self.controller.dlt = dlt
        self.controller.audio = audio
        runtime = self.controller.runtime_context()

        with self.controller._state_lock:
            self.controller._fault_tokens_seen.add("some token")
            self.controller._total_duration_seconds = 100

        self.dlt_actions.action_clear_start_test(runtime)

        dlt.clear_tmp_log.assert_called_once()
        with self.controller._state_lock:
            self.assertEqual(len(self.controller._fault_tokens_seen), 0)
            self.assertEqual(self.controller._total_duration_seconds, self.app_settings.test_duration_seconds)

    def test_action_clear_start_test_registers_callback(self) -> None:
        dlt = Mock()
        audio = Mock()
        self.controller.dlt = dlt
        self.controller.audio = audio
        runtime = self.controller.runtime_context()

        self.dlt_actions.action_clear_start_test(runtime)

        dlt.clear_payload_callbacks.assert_called_once()
        dlt.register_payload_callback.assert_called_once()

    def test_action_clear_start_test_beeps(self) -> None:
        dlt = Mock()
        audio = Mock()
        self.controller.dlt = dlt
        self.controller.audio = audio
        runtime = self.controller.runtime_context()

        self.dlt_actions.action_clear_start_test(runtime)

        audio.beep_once.assert_called_once()

    def test_action_clear_start_test_starts_timer(self) -> None:
        dlt = Mock()
        audio = Mock()
        self.controller.dlt = dlt
        self.controller.audio = audio
        runtime = self.controller.runtime_context()

        timer_before = self.controller._timer_thread
        self.dlt_actions.action_clear_start_test(runtime)
        timer_after = self.controller._timer_thread

        self.assertIsNone(timer_before)
        self.assertIsNotNone(timer_after)

    def test_action_clear_start_test_logs_cleared_and_started(self) -> None:
        dlt = Mock()
        audio = Mock()
        self.controller.dlt = dlt
        self.controller.audio = audio
        runtime = self.controller.runtime_context()

        self.dlt_actions.action_clear_start_test(runtime)

        cleared_messages = [msg for msg in self.logs if "Temporary log cleared:" in msg]
        started_messages = [msg for msg in self.logs if "Test timer started:" in msg]
        self.assertEqual(len(cleared_messages), 1)
        self.assertEqual(len(started_messages), 1)

    def test_action_filter_export_fails_if_test_not_finished(self) -> None:
        exporter = Mock()
        self.controller.exporter = exporter
        runtime = self.controller.runtime_context()

        with self.controller._state_lock:
            self.controller._finished = False

        with self.assertRaises(RuntimeError) as cm:
            self.dlt_actions.action_filter_export(runtime)

        self.assertIn("Cannot export yet", str(cm.exception))
        exporter.export_filtered_dlt.assert_not_called()
        exporter.export_filtered_ascii.assert_not_called()

    def test_action_filter_export_succeeds_when_finished(self) -> None:
        exporter = Mock()
        self.controller.exporter = exporter
        runtime = self.controller.runtime_context()

        with self.controller._state_lock:
            self.controller._finished = True

        self.dlt_actions.action_filter_export(runtime)

        exporter.export_filtered_dlt.assert_called_once()
        exporter.export_filtered_ascii.assert_called_once()

    def test_action_filter_export_creates_correct_paths(self) -> None:
        exporter = Mock()
        self.controller.exporter = exporter
        runtime = self.controller.runtime_context()

        with self.controller._state_lock:
            self.controller._finished = True

        self.dlt_actions.action_filter_export(runtime)

        dlt_call = exporter.export_filtered_dlt.call_args
        ascii_call = exporter.export_filtered_ascii.call_args

        self.assertIsNotNone(dlt_call)
        self.assertIsNotNone(ascii_call)

        # Verify the paths are formatted with timestamp
        dlt_export_path = dlt_call[0][1]
        ascii_export_path = ascii_call[0][1]

        self.assertIn(runtime.run_timestamp, str(dlt_export_path))
        self.assertIn(runtime.run_timestamp, str(ascii_export_path))

    def test_action_filter_export_logs_results(self) -> None:
        exporter = Mock()
        self.controller.exporter = exporter
        runtime = self.controller.runtime_context()

        with self.controller._state_lock:
            self.controller._finished = True

        self.dlt_actions.action_filter_export(runtime)

        dlt_messages = [msg for msg in self.logs if "Exported DLT filter file:" in msg]
        ascii_messages = [msg for msg in self.logs if "Exported ASCII filter file:" in msg]

        self.assertEqual(len(dlt_messages), 1)
        self.assertEqual(len(ascii_messages), 1)


if __name__ == "__main__":
    unittest.main()
