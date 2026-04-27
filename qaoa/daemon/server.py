"""Persistent JSON-RPC daemon for Kageko agent runtime."""

from __future__ import annotations

import json
import sys
import threading
import traceback
from typing import Any

from .log import StructuredLogger
from .protocol import RequestHandler


class DaemonServer:
    """Persistent daemon that handles JSON-RPC requests over stdio."""

    def __init__(self, *, verbose: bool = False) -> None:
        self.logger = StructuredLogger(verbose=verbose)
        self.handler = RequestHandler(logger=self.logger)
        self._lock = threading.Lock()
        self._shutdown = False

    def run(self) -> int:
        """Main loop: read JSON requests from stdin, write responses to stdout."""
        self.logger.info("daemon started")
        for raw_line in sys.stdin:
            if self._shutdown:
                break
            line = raw_line.strip()
            if line == "":
                continue
            self._handle_line(line)
        self.logger.info("daemon stopped")
        return 0

    def _handle_line(self, line: str) -> None:
        try:
            request = json.loads(line)
        except json.JSONDecodeError as error:
            self._emit({"id": None, "ok": False, "error": f"Invalid JSON: {error.msg}"})
            return

        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if not isinstance(method, str):
            self._emit({"id": req_id, "ok": False, "error": "method must be a string"})
            return
        if not isinstance(params, dict):
            self._emit({"id": req_id, "ok": False, "error": "params must be an object"})
            return

        self.logger.debug("request received", method=method, id=req_id)
        try:
            result = self.handler.handle(method, params, emit=self._emit)
            if method == "daemon.shutdown":
                self._shutdown = True
            self._emit({"id": req_id, "ok": True, "result": result})
            self.logger.debug("request handled", method=method, id=req_id)
        except Exception as error:
            error_msg = f"{type(error).__name__}: {error}"
            if sys.flags.dev_mode:
                error_msg += f"\n{traceback.format_exc()}"
            self.logger.error("request failed", method=method, id=req_id, error=error_msg)
            self._emit({"id": req_id, "ok": False, "error": error_msg})

    def _emit(self, payload: dict[str, Any]) -> None:
        with self._lock:
            sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
            sys.stdout.flush()


def main(argv: list[str] | None = None) -> int:
    verbose = "--verbose" in (argv or [])
    server = DaemonServer(verbose=verbose)
    return server.run()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
