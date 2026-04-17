from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from tpms_utility.config import DltConnectionSettings
from tpms_utility.services.dlt_service import DltService


class _FakeSocket:
    def __init__(self) -> None:
        self.timeout_calls: list[float] = []
        self.connected_to: tuple[str, int] | None = None
        self.closed = False
        self.shutdown_called = False
        self.sent_frames: list[bytes] = []

    def settimeout(self, value: float) -> None:
        self.timeout_calls.append(value)

    def connect(self, endpoint: tuple[str, int]) -> None:
        self.connected_to = endpoint

    def shutdown(self, _: int) -> None:
        self.shutdown_called = True

    def close(self) -> None:
        self.closed = True

    def sendall(self, frame: bytes) -> None:
        self.sent_frames.append(frame)


class _AliveThread:
    def is_alive(self) -> bool:
        return True

    def join(self, timeout: float | None = None) -> None:
        _ = timeout


class _FakeThread:
    def __init__(self, target, daemon: bool = False) -> None:
        self.target = target
        self.daemon = daemon
        self.started = False

    def start(self) -> None:
        self.started = True

    def is_alive(self) -> bool:
        return self.started


class DltServiceTests(unittest.TestCase):
    def test_connect_disconnects_existing_session_before_new_connection(self) -> None:
        service = DltService()
        service._receive_thread = _AliveThread()
        service.disconnect = Mock()

        with patch("tpms_utility.services.dlt_service.socket.socket", return_value=_FakeSocket()), patch(
            "tpms_utility.services.dlt_service.threading.Thread",
            _FakeThread,
        ):
            service.connect(DltConnectionSettings(hostname="127.0.0.1", port=3491))

        service.disconnect.assert_called_once()
        self.assertTrue(service.online)

    def test_disconnect_closes_socket_and_marks_offline(self) -> None:
        service = DltService()
        fake_socket = _FakeSocket()
        service._socket = fake_socket
        service.online = True

        service.disconnect()

        self.assertFalse(service.online)
        self.assertTrue(fake_socket.shutdown_called)
        self.assertTrue(fake_socket.closed)
        self.assertIsNone(service._socket)


if __name__ == "__main__":
    unittest.main()
