from __future__ import annotations

import threading

from flask import Flask, jsonify, request
from PySide6.QtCore import QObject, Signal


class RequestBridge(QObject):
    request_received = Signal(dict)


class LocalAPI:
    def __init__(self, bridge: RequestBridge, host: str = "127.0.0.1", port: int = 5057) -> None:
        self.bridge = bridge
        self.host = host
        self.port = port
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        def run_server() -> None:
            app = Flask(__name__)

            @app.get("/health")
            def health():
                return jsonify({"ok": True, "service": "gsg3-player-api"})

            @app.post("/request")
            def request_media():
                data = request.get_json(silent=True) or {}
                url = str(data.get("url", "")).strip()
                requested_by = str(data.get("requestedBy", "")).strip()
                request_type = str(data.get("type", "youtube")).strip()

                if not url:
                    return jsonify({"ok": False, "error": "Missing url"}), 400

                payload = {
                    "url": url,
                    "requestedBy": requested_by,
                    "type": request_type,
                }

                self.bridge.request_received.emit(payload)
                return jsonify({"ok": True, "accepted": True, "payload": payload})

            app.run(
                host=self.host,
                port=self.port,
                debug=False,
                use_reloader=False,
                threaded=True,
            )

        self._thread = threading.Thread(target=run_server, daemon=True)
        self._thread.start()