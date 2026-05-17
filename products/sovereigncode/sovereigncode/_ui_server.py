from __future__ import annotations

import json
import socket
import webbrowser
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

ApiHandler = Callable[[str, str, dict[str, Any] | None], tuple[int, dict[str, Any]]]


def find_available_port(host: str, preferred_port: int, *, attempts: int = 50) -> int:
    start = preferred_port if preferred_port > 0 else 0
    if start == 0:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind((host, 0))
            return int(probe.getsockname()[1])

    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((host, port))
            except OSError:
                continue
            return port
    raise OSError(f"No available port found from {preferred_port} to {preferred_port + attempts - 1}")


def serve_dashboard(
    *,
    product_name: str,
    html: str,
    api_handler: ApiHandler,
    host: str,
    port: int,
    open_browser: bool = False,
    api_path_prefixes: tuple[str, ...] = ("/api/",),
    api_exact_paths: tuple[str, ...] = (),
) -> int:
    actual_port = find_available_port(host, port)
    exact_paths = set(api_exact_paths)

    def is_api_path(path: str) -> bool:
        return path in exact_paths or any(path.startswith(prefix) for prefix in api_path_prefixes)

    class Handler(BaseHTTPRequestHandler):
        server_version = "AbteeXProductUI/0.1"

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler method name
            path = urlparse(self.path).path
            if path == "/":
                self._send_text(200, html, "text/html; charset=utf-8")
                return
            if is_api_path(path):
                self._send_api("GET", path, None)
                return
            self._send_json(404, {"ok": False, "error": "not_found"})

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler method name
            path = urlparse(self.path).path
            if not is_api_path(path):
                self._send_json(404, {"ok": False, "error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8") if length else "{}"
                payload = json.loads(raw)
                if not isinstance(payload, dict):
                    raise ValueError("JSON body must be an object")
                self._send_api("POST", path, payload)
            except Exception as exc:  # defensive API boundary
                self._send_json(400, {"ok": False, "error": str(exc)})

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

        def _send_api(
            self,
            method: str,
            path: str,
            payload: dict[str, Any] | None,
        ) -> None:
            try:
                status, response = api_handler(method, path, payload)
            except Exception as exc:  # defensive API boundary
                status, response = 500, {"ok": False, "error": str(exc)}
            self._send_json(status, response)

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, status: int, body: str, content_type: str) -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer((host, actual_port), Handler)
    url = f"http://{host}:{actual_port}/"
    print(f"{product_name} UI listening on {url}")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"{product_name} UI stopped")
    finally:
        server.server_close()
    return 0
