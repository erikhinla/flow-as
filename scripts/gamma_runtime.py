#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "bizbrain_lite"))
sys.path.insert(0, str(REPO_ROOT))

from app.services.flow_filesystem_control import complete_task, ensure_state_tree, list_tasks, runtime_status


def worker(interval: float) -> None:
    ensure_state_tree()
    while True:
        for task in list_tasks(queue="active"):
            if task.get("owner_role") != "gamma":
                continue
            summary = (
                f"# {task['title']}\n\n"
                "Gamma execution proof ran only after explicit approval moved the task to active.\n\n"
                f"Review artifacts: {json.dumps(task.get('review_artifacts', {}), indent=2)}\n"
            )
            complete_task(task["task_id"], summary, actor="agent-zero-gamma")
        time.sleep(interval)


class Handler(BaseHTTPRequestHandler):
    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/health", "/status"):
            self._json({"status": "ok", "role": "gamma", "runtime": runtime_status()})
            return
        self._json({"error": "not found"}, status=404)

    def log_message(self, format: str, *args) -> None:
        print("agent-zero-gamma: " + format % args)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18800)
    parser.add_argument("--interval", type=float, default=2)
    args = parser.parse_args()
    threading.Thread(target=worker, args=(args.interval,), daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print(f"agent-zero-gamma listening on {args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
