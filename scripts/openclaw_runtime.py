#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "bizbrain_lite"))
sys.path.insert(0, str(REPO_ROOT))

from app.services.flow_filesystem_control import claim_next, complete_task, ensure_state_tree, runtime_status


def worker(role: str, interval: float) -> None:
    ensure_state_tree()
    while True:
        claimed = claim_next(role)
        if claimed.task:
            task = claimed.task
            summary = (
                f"# {task['title']}\n\n"
                f"Owner: {role}\n\n"
                f"Risk tier: {task['risk_tier']}\n\n"
                "Proof output: OpenClaw processed this filesystem-queued task without Gamma escalation."
            )
            complete_task(task["task_id"], summary, actor=f"openclaw-{role}")
        time.sleep(interval)


class Handler(BaseHTTPRequestHandler):
    role = "alpha"

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/health", "/status"):
            self._json({"status": "ok", "role": self.role, "runtime": runtime_status()})
            return
        self._json({"error": "not found"}, status=404)

    def log_message(self, format: str, *args) -> None:
        print(f"openclaw-{self.role}: " + format % args)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=["alpha", "beta"], required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--interval", type=float, default=float(os.getenv("OPENCLAW_POLL_INTERVAL", "2")))
    args = parser.parse_args()

    Handler.role = args.role
    threading.Thread(target=worker, args=(args.role, args.interval), daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print(f"openclaw-{args.role} listening on {args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
