from __future__ import annotations

import winsound


class AudioService:
    def beep_once(self) -> None:
        winsound.MessageBeep(winsound.MB_OK)

    def beep_three_times(self) -> None:
        for _ in range(3):
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
