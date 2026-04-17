from __future__ import annotations

try:
    import winsound
except ImportError:  # pragma: no cover - platform-specific import
    winsound = None


class AudioService:
    def beep_once(self) -> None:
        if winsound is None:
            return
        winsound.MessageBeep(winsound.MB_OK)

    def beep_three_times(self) -> None:
        if winsound is None:
            return
        for _ in range(3):
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
