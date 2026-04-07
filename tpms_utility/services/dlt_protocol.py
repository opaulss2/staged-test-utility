from __future__ import annotations

from dataclasses import dataclass
import re
import struct
import time


HTYP_UEH = 0x01
HTYP_MSBF = 0x02
HTYP_WEID = 0x04
HTYP_WSID = 0x08
HTYP_WTMS = 0x10
HTYP_PROTOCOL_VERSION1 = 0x20

MSIN_CONTROL_REQUEST = 0x03

SERVICE_SET_LOG_LEVEL = 0x01
SERVICE_SET_TRACE_STATUS = 0x02
SERVICE_GET_LOG_INFO = 0x03
SERVICE_SET_TIMING_PACKETS = 0x0B
SERVICE_SET_DEFAULT_LOG_LEVEL = 0x11
SERVICE_SET_DEFAULT_TRACE_STATUS = 0x12
SERVICE_GET_SOFTWARE_VERSION = 0x13
SERVICE_SET_VERBOSE_MODE = 0x09

_PRINTABLE_TEXT_RE = re.compile(r"[ -~]{4,}")


@dataclass(slots=True)
class ParsedDltMessage:
    frame: bytes
    app_id: str
    ctx_id: str
    payload_text: str


class DltStreamParser:
    def __init__(self) -> None:
        self._buffer = bytearray()

    def add(self, data: bytes) -> list[ParsedDltMessage]:
        self._buffer.extend(data)
        messages: list[ParsedDltMessage] = []

        while True:
            if len(self._buffer) < 4:
                break

            if self._buffer[:4] == b"DLS\x01":
                del self._buffer[:4]
                if len(self._buffer) < 4:
                    break

            htyp = self._buffer[0]
            if (htyp & 0xE0) != HTYP_PROTOCOL_VERSION1:
                del self._buffer[0]
                continue

            length = struct.unpack(">H", bytes(self._buffer[2:4]))[0]
            if length < 4:
                del self._buffer[0]
                continue
            if len(self._buffer) < length:
                break

            frame = bytes(self._buffer[:length])
            del self._buffer[:length]

            parsed = _parse_frame(frame)
            if parsed is not None:
                messages.append(parsed)

        return messages


def build_control_frame(
    ecu_id: str,
    payload: bytes,
    app_id: str = "APP",
    ctx_id: str = "CON",
    mcnt: int = 0,
) -> bytes:
    htyp = HTYP_UEH | HTYP_WEID | HTYP_WTMS | HTYP_PROTOCOL_VERSION1
    extra = _id4(ecu_id) + struct.pack(">I", int(time.monotonic() * 1000) & 0xFFFFFFFF)
    ext = bytes([MSIN_CONTROL_REQUEST, 1]) + _id4(app_id) + _id4(ctx_id)
    total_len = 4 + len(extra) + len(ext) + len(payload)
    std = bytes([htyp, mcnt & 0xFF]) + struct.pack(">H", total_len)
    return std + extra + ext + payload


def payload_service_u32(service_id: int) -> bytes:
    return struct.pack("<I", service_id)


def payload_set_default_log_level(level: int) -> bytes:
    return struct.pack("<IB4s", SERVICE_SET_DEFAULT_LOG_LEVEL, level & 0xFF, _id4("remo"))


def payload_set_default_trace_status(status: int) -> bytes:
    return struct.pack("<IB4s", SERVICE_SET_DEFAULT_TRACE_STATUS, status & 0xFF, _id4("remo"))


def payload_set_verbose_mode(status: int) -> bytes:
    return struct.pack("<IB", SERVICE_SET_VERBOSE_MODE, status & 0xFF)


def payload_set_timing_packets(enabled: bool) -> bytes:
    return struct.pack("<IB", SERVICE_SET_TIMING_PACKETS, 1 if enabled else 0)


def payload_get_log_info() -> bytes:
    return struct.pack("<IB4s4s4s", SERVICE_GET_LOG_INFO, 7, _id4(""), _id4(""), _id4("remo"))


def payload_set_log_level(app_id: str, ctx_id: str, level: int) -> bytes:
    return struct.pack(
        "<I4s4sB4s",
        SERVICE_SET_LOG_LEVEL,
        _id4(app_id),
        _id4(ctx_id),
        level & 0xFF,
        _id4("remo"),
    )


def make_storage_header(ecu_id: str, epoch_seconds: int | None = None, micros: int | None = None) -> bytes:
    if epoch_seconds is None:
        epoch_seconds = int(time.time())
    if micros is None:
        micros = int((time.time() - int(time.time())) * 1_000_000)
    return b"DLT\x01" + struct.pack("<I", epoch_seconds) + struct.pack("<I", micros) + _id4(ecu_id)


def parse_dlt_file_messages(data: bytes) -> list[ParsedDltMessage]:
    messages: list[ParsedDltMessage] = []
    index = 0
    data_len = len(data)

    while index + 20 <= data_len:
        if data[index : index + 4] != b"DLT\x01":
            index += 1
            continue
        frame_start = index + 16
        if frame_start + 4 > data_len:
            break
        frame_len = struct.unpack(">H", data[frame_start + 2 : frame_start + 4])[0]
        if frame_len < 4 or frame_start + frame_len > data_len:
            index += 1
            continue

        frame = data[frame_start : frame_start + frame_len]
        parsed = _parse_frame(frame)
        if parsed is not None:
            parsed.frame = data[index : frame_start + frame_len]
            messages.append(parsed)
        index = frame_start + frame_len

    return messages


def _parse_frame(frame: bytes) -> ParsedDltMessage | None:
    if len(frame) < 4:
        return None

    htyp = frame[0]
    offset = 4

    if htyp & HTYP_WEID:
        offset += 4
    if htyp & HTYP_WSID:
        offset += 4
    if htyp & HTYP_WTMS:
        offset += 4

    app_id = ""
    ctx_id = ""
    if htyp & HTYP_UEH:
        if len(frame) < offset + 10:
            return None
        app_id = _decode_id(frame[offset + 2 : offset + 6])
        ctx_id = _decode_id(frame[offset + 6 : offset + 10])
        offset += 10

    if offset > len(frame):
        return None

    payload = frame[offset:]
    payload_text = _extract_payload_text(payload)
    return ParsedDltMessage(frame=frame, app_id=app_id, ctx_id=ctx_id, payload_text=payload_text)


def _extract_payload_text(payload: bytes) -> str:
    if not payload:
        return ""
    latin = payload.decode("latin-1", errors="ignore")
    matches = _PRINTABLE_TEXT_RE.findall(latin)
    if matches:
        return " ".join(matches)
    return latin.strip("\x00\r\n\t ")


def _id4(value: str) -> bytes:
    raw = value.encode("ascii", errors="ignore")[:4]
    return raw.ljust(4, b"\x00")


def _decode_id(raw: bytes) -> str:
    return raw.decode("ascii", errors="ignore").strip("\x00 ")
