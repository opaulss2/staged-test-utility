from __future__ import annotations

import os
import socket
import struct
import threading
import time

HOST = os.environ.get("MOCK_DLT_HOST", "0.0.0.0")
PORT = int(os.environ.get("MOCK_DLT_PORT", "3491"))
INTERVAL_SECONDS = float(os.environ.get("MOCK_DLT_INTERVAL_SECONDS", "0.2"))

TOKENS = [
    "fault id: 30 debounce status: 1",
    "fault id: 31 debounce status: 1",
    "fault id: 32 debounce status: 1",
    "fault id: 33 debounce status: 1",
]


def _id4(value: str) -> bytes:
    raw = value.encode("ascii", errors="ignore")[:4]
    return raw.ljust(4, b"\x00")


def build_log_frame(payload_text: str, mcnt: int) -> bytes:
    # Protocol version 1 + UEH + ECU ID + timestamp
    htyp = 0x20 | 0x01 | 0x04 | 0x10
    ecu = _id4("TPMS")
    tms = struct.pack(">I", int(time.monotonic() * 1000) & 0xFFFFFFFF)

    # msin 0x00 + no args + APP/CTX IDs; parser extracts printable payload.
    ext = bytes([0x00, 0x00]) + _id4("Tawm") + _id4("LIB")
    payload = payload_text.encode("latin-1", errors="ignore")

    total_len = 4 + len(ecu) + len(tms) + len(ext) + len(payload)
    std = bytes([htyp, mcnt & 0xFF]) + struct.pack(">H", total_len)
    return std + ecu + tms + ext + payload


def stream_fault_tokens(client: socket.socket) -> None:
    mcnt = 0
    while True:
        for token in TOKENS:
            frame = build_log_frame(token, mcnt)
            try:
                client.sendall(frame)
            except OSError:
                return
            mcnt = (mcnt + 1) % 256
            time.sleep(INTERVAL_SECONDS)


def serve() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(5)
        print(f"DLT mock listening on {HOST}:{PORT}", flush=True)

        while True:
            client, address = server.accept()
            print(f"DLT mock client connected: {address}", flush=True)
            thread = threading.Thread(target=_handle_client, args=(client,), daemon=True)
            thread.start()


def _handle_client(client: socket.socket) -> None:
    with client:
        client.settimeout(0.5)
        streamer = threading.Thread(target=stream_fault_tokens, args=(client,), daemon=True)
        streamer.start()

        while True:
            try:
                data = client.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                return

            if not data:
                return


if __name__ == "__main__":
    serve()
