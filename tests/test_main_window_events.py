from __future__ import annotations

import queue
import unittest
from unittest.mock import Mock

from tpms_utility.ui.main_window import MainWindow


class MainWindowEventQueueTests(unittest.TestCase):
    def _build_window_stub(self) -> MainWindow:
        window = MainWindow.__new__(MainWindow)
        window._ui_event_queue = queue.SimpleQueue()
        window._append_log = Mock()
        window._refresh_stage_buttons = Mock()
        window._apply_timer_update = Mock()
        window.root = Mock()
        window.root.after = Mock()
        return window

    def test_process_ui_events_routes_log_state_and_latest_timer(self) -> None:
        window = self._build_window_stub()
        window._ui_event_queue.put(("log", "first"))
        window._ui_event_queue.put(("timer", 10))
        window._ui_event_queue.put(("state", None))
        window._ui_event_queue.put(("timer", 7))
        window._ui_event_queue.put(("log", "second"))

        window._process_ui_events()

        window._append_log.assert_any_call("first")
        window._append_log.assert_any_call("second")
        self.assertEqual(window._append_log.call_count, 2)
        window._refresh_stage_buttons.assert_called_once()
        window._apply_timer_update.assert_called_once_with(7)
        window.root.after.assert_called_once_with(100, window._process_ui_events)

    def test_process_ui_events_ignores_invalid_event_payloads(self) -> None:
        window = self._build_window_stub()
        window._ui_event_queue.put(("log", 42))
        window._ui_event_queue.put(("timer", "not-int"))
        window._ui_event_queue.put(("unknown", "x"))

        window._process_ui_events()

        window._append_log.assert_not_called()
        window._refresh_stage_buttons.assert_not_called()
        window._apply_timer_update.assert_not_called()
        window.root.after.assert_called_once_with(100, window._process_ui_events)

    def test_process_ui_events_empty_queue_still_schedules_next_poll(self) -> None:
        window = self._build_window_stub()

        window._process_ui_events()

        window._append_log.assert_not_called()
        window._refresh_stage_buttons.assert_not_called()
        window._apply_timer_update.assert_not_called()
        window.root.after.assert_called_once_with(100, window._process_ui_events)

    def test_select_initial_profile_name_prefers_default_cycle(self) -> None:
        window = MainWindow.__new__(MainWindow)
        window.profiles = [
            ("alpha", Mock()),
            ("default_cycle", Mock()),
        ]
        window.profiles_by_name = {
            "alpha": Mock(),
            "default_cycle": Mock(),
        }

        selected = window._select_initial_profile_name()

        self.assertEqual(selected, "default_cycle")

    def test_select_initial_profile_name_falls_back_to_first_profile(self) -> None:
        window = MainWindow.__new__(MainWindow)
        window.profiles = [
            ("alpha", Mock()),
            ("beta", Mock()),
        ]
        window.profiles_by_name = {
            "alpha": Mock(),
            "beta": Mock(),
        }

        selected = window._select_initial_profile_name()

        self.assertEqual(selected, "alpha")

    def test_select_initial_profile_name_returns_empty_when_no_profiles(self) -> None:
        window = MainWindow.__new__(MainWindow)
        window.profiles = []
        window.profiles_by_name = {}

        selected = window._select_initial_profile_name()

        self.assertEqual(selected, "")


if __name__ == "__main__":
    unittest.main()
