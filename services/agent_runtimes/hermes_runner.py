"""Internal HTTP adapter for the official NousResearch Hermes Agent image."""

from __future__ import annotations

import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


HOST = "0.0.0.0"
PORT = int(os.getenv("FLOW_RUNTIME_PORT", "18789"))
MODEL = os.getenv("HERMES_AGENT_MODEL", "openai/gpt-4o-mini")
UPSTREAM_REPOSITORY = "https://github.com/NousResearch/hermes-agent"
UPSTREAM_COMMIT = os.getenv("HERMES_UPSTREAM_COMMIT", "unknown")


def hermes_version() -> str:
    result = subprocess.run(
        ["hermes", "--version"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = (result.stdout or result.stderr).strip()
    if result.returncode != 0:
        raise RuntimeError(output or f"hermes --version exited {result.returncode}")
    return output


def run_hermes(prompt: str) -> str:
    result = subprocess.run(
        [
            "hermes",
            "--provider",
            "openrouter",
            "--model",
            MODEL,
            "--oneshot",
            prompt,
        ],
        capture_output=True,
        text=True,
        timeout=int(os.getenv("FLOW_RUNTIME_TIMEOUT_SECONDS", "900")),
        check=False,
        cwd="/workspace",
    )
    output = result.stdout.strip()
    if result.returncode != 0:
        error = result.stderr.strip() or output
        raise RuntimeError(error or f"Hermes exited {result.returncode}")
    if not output:
        raise RuntimeError("Hermes returned an empty response")
    return output


class Handler(BaseHTTPRequestHandler):
    server_version = "FLOWHermesAdapter/1.0"

    def _send(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path not in {"/health", "/healthz"}:
            self._send(404, {"ok": False, "error": "not found"})
            return
        try:
            version = hermes_version()
            self._send(
                200,
                {
                    "ok": True,
                    "engine": "hermes",
                    "version": version,
                    "upstream_repository": UPSTREAM_REPOSITORY,
                    "upstream_commit": UPSTREAM_COMMIT,
                },
            )
        except Exception as exc:
            self._send(503, {"ok": False, "engine": "hermes", "error": str(exc)})

    def do_POST(self) -> None:
        if self.path != "/run":
            self._send(404, {"ok": False, "error": "not found"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length) or b"{}")
            prompt = str(payload.get("prompt") or "").strip()
            if not prompt:
                self._send(400, {"ok": False, "error": "prompt is required"})
                return
            final = run_hermes(prompt)
            self._send(
                200,
                {
                    "ok": True,
                    "engine": "hermes",
                    "final": final,
                    "upstream_repository": UPSTREAM_REPOSITORY,
                    "upstream_commit": UPSTREAM_COMMIT,
                },
            )
        except subprocess.TimeoutExpired:
            self._send(504, {"ok": False, "engine": "hermes", "error": "execution timed out"})
        except Exception as exc:
            self._send(500, {"ok": False, "engine": "hermes", "error": str(exc)})

    def log_message(self, format: str, *args: object) -> None:
        print(f"hermes-runner: {format % args}", flush=True)


if __name__ == "__main__":
    print(
        f"Hermes Agent adapter listening on {HOST}:{PORT} "
        f"(upstream {UPSTREAM_COMMIT})",
        flush=True,
    )
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
