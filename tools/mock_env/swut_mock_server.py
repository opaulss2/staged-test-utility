from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = os.environ.get("MOCK_SWUT_HOST", "0.0.0.0")
PORT = int(os.environ.get("MOCK_SWUT_PORT", "8082"))
DELAY_SECONDS = float(os.environ.get("MOCK_SWUT_DELAY_SECONDS", "0.02"))
FAIL_ON = {
    value.strip().upper()
    for value in os.environ.get("MOCK_SWUT_FAIL_ON", "").split(",")
    if value.strip()
}


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json({"status": "ok"})
            return
        self._send_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/run":
            self._send_json({"error": "not found"}, status=404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b"{}"
        payload = json.loads(body.decode("utf-8", errors="ignore") or "{}")

        normalized = str(payload.get("normalized_command", "")).strip().upper()
        time.sleep(DELAY_SECONDS)

        if normalized in FAIL_ON:
            self._send_json(
                {
                    "success": False,
                    "details": f"simulated SWUT failure for {normalized}",
                    "command": payload.get("command", ""),
                }
            )
            return

        self._send_json(
            {
                "success": True,
                "details": f"simulated SWUT success for {normalized}",
                "command": payload.get("command", ""),
            }
        )


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"SWUT mock listening on {HOST}:{PORT}", flush=True)
    server.serve_forever()
