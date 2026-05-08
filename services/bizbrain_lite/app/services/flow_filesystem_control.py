"""
Filesystem-backed FLOW control layer.

This module is the shared choke point for Discord, the dashboard, proof tasks,
and lightweight agent runtimes. It keeps the documented queue folders as source
of truth and enforces the Alpha/Beta/Gamma routing and Gamma approval gate.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


QUEUE_NAMES = ("pending", "active", "completed", "escalated", "blocked", "archive")
REQUIRED_DIRS = (
    "tasks/pending",
    "tasks/active",
    "tasks/completed",
    "tasks/escalated",
    "tasks/blocked",
    "tasks/archive",
    "status",
    "artifacts",
)
ROUTING = {
    "reputation": "alpha",
    "time_loss": "beta",
    "downtime_security_money": "gamma",
}
AGENTS = {
    "alpha": {"name": "Alpha", "process": "openclaw-alpha", "port": 18789},
    "beta": {"name": "Beta", "process": "openclaw-beta", "port": 18790},
    "gamma": {"name": "Gamma", "container": "agent-zero-gamma", "port": 18800},
}


class FlowControlError(ValueError):
    """Raised when a task envelope or transition violates FLOW rules."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_state_root() -> Path:
    return Path(os.getenv("FLOW_STATE_DIR", "~/.openclaw/state")).expanduser()


def ensure_state_tree(root: Path | None = None) -> Path:
    root = root or get_state_root()
    for relative in REQUIRED_DIRS:
        (root / relative).mkdir(parents=True, exist_ok=True)
    audit_path = root / "audit.jsonl"
    audit_path.touch(exist_ok=True)
    return root


def audit_event(
    action: str,
    task_id: str | None = None,
    actor: str = "system",
    details: dict[str, Any] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    root = ensure_state_tree(root)
    event = {
        "audit_id": str(uuid.uuid4()),
        "created_at": utc_now(),
        "action": action,
        "task_id": task_id,
        "actor": actor,
        "details": details or {},
    }
    with (root / "audit.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return event


def _task_path(queue: str, task_id: str, root: Path | None = None) -> Path:
    return (root or get_state_root()) / "tasks" / queue / f"{task_id}.json"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _try_read_json(path: Path) -> dict[str, Any] | None:
    try:
        return _read_json(path)
    except (OSError, json.JSONDecodeError):
        return None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def find_task_file(task_id: str, root: Path | None = None) -> tuple[str, Path] | None:
    root = ensure_state_tree(root)
    for queue in QUEUE_NAMES:
        path = _task_path(queue, task_id, root)
        if path.exists():
            return queue, path
    return None


def validate_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    payload = dict(envelope)
    payload.setdefault("task_id", str(uuid.uuid4()))
    payload.setdefault("created_at", utc_now())
    payload.setdefault("source", "manual")
    payload.setdefault("status", "pending")
    payload.setdefault("inputs", {})

    required = ("task_id", "created_at", "source", "title", "goal", "risk_tier")
    missing = [field for field in required if not payload.get(field)]
    if missing:
        raise FlowControlError(f"Missing required task envelope fields: {', '.join(missing)}")

    risk_tier = payload["risk_tier"]
    owner_role = payload.get("owner_role") or payload.get("preferred_owner")
    expected_owner = ROUTING.get(risk_tier)
    if expected_owner is None:
        raise FlowControlError(
            "Invalid risk_tier. Expected one of: reputation, time_loss, downtime_security_money"
        )

    if owner_role and owner_role != expected_owner:
        raise FlowControlError(
            f"Invalid routing combination: risk_tier={risk_tier} requires owner_role={expected_owner}"
        )

    payload["owner_role"] = expected_owner
    payload["task_type"] = payload.get("task_type") or risk_tier
    payload["preferred_owner"] = expected_owner
    payload["review_required"] = expected_owner == "gamma"
    payload["rollback_required"] = expected_owner == "gamma"
    payload["updated_at"] = utc_now()
    return payload


def create_gamma_review_artifacts(task: dict[str, Any], root: Path | None = None) -> dict[str, str]:
    root = ensure_state_tree(root)
    artifact_dir = root / "artifacts" / task["task_id"]
    artifact_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "diff": artifact_dir / "task.diff",
        "review": artifact_dir / "task.review.md",
        "rollback": artifact_dir / "task.rollback.md",
    }
    if not files["diff"].exists():
        files["diff"].write_text(
            f"# Proposed Gamma Diff\n\nTask: {task['title']}\n\nNo production mutation has been executed.\n",
            encoding="utf-8",
        )
    if not files["review"].exists():
        files["review"].write_text(
            "# Gamma Review\n\nPass 1: proposed only.\n\nPass 2: review required before execution.\n",
            encoding="utf-8",
        )
    if not files["rollback"].exists():
        files["rollback"].write_text(
            "# Rollback Plan\n\nDetection: monitor FLOW health and runtime logs.\n\nAction: revert the approved change package.\n\nValidation: confirm Alpha, Beta, Gamma health checks pass.\n",
            encoding="utf-8",
        )
    return {key: str(path) for key, path in files.items()}


def review_artifacts_ready(task_id: str, root: Path | None = None) -> tuple[bool, dict[str, str]]:
    root = ensure_state_tree(root)
    artifact_dir = root / "artifacts" / task_id
    files = {
        "diff": artifact_dir / "task.diff",
        "review": artifact_dir / "task.review.md",
        "rollback": artifact_dir / "task.rollback.md",
    }
    return all(path.exists() and path.stat().st_size > 0 for path in files.values()), {
        key: str(path) for key, path in files.items()
    }


def submit_task(envelope: dict[str, Any], actor: str = "api", root: Path | None = None) -> dict[str, Any]:
    root = ensure_state_tree(root)
    task = validate_envelope(envelope)
    if find_task_file(task["task_id"], root):
        raise FlowControlError(f"Task already exists: {task['task_id']}")

    if task["owner_role"] == "gamma":
        task["status"] = "review_required"
        task["queue"] = "escalated"
        task["review_artifacts"] = create_gamma_review_artifacts(task, root)
        target_queue = "escalated"
    else:
        task["status"] = "pending"
        task["queue"] = "pending"
        target_queue = "pending"

    _write_json(_task_path(target_queue, task["task_id"], root), task)
    audit_event(
        "task_submitted",
        task["task_id"],
        actor,
        {"queue": target_queue, "risk_tier": task["risk_tier"], "owner_role": task["owner_role"]},
        root,
    )
    if task["owner_role"] == "gamma":
        audit_event("gamma_review_required", task["task_id"], "system", task["review_artifacts"], root)
    return task


def move_task(task_id: str, to_queue: str, status: str, actor: str, details: dict[str, Any] | None = None, root: Path | None = None) -> dict[str, Any]:
    root = ensure_state_tree(root)
    found = find_task_file(task_id, root)
    if not found:
        raise FlowControlError(f"Task not found: {task_id}")
    from_queue, source = found
    task = _read_json(source)
    task["status"] = status
    task["queue"] = to_queue
    task["updated_at"] = utc_now()
    if details:
        task.setdefault("events", []).append({"created_at": utc_now(), "actor": actor, **details})
    target = _task_path(to_queue, task_id, root)
    _write_json(target, task)
    if target != source:
        source.unlink()
    audit_event(
        "task_transition",
        task_id,
        actor,
        {"from": from_queue, "to": to_queue, "status": status, **(details or {})},
        root,
    )
    return task


def approve_task(task_id: str, actor: str = "api", root: Path | None = None) -> dict[str, Any]:
    root = ensure_state_tree(root)
    found = find_task_file(task_id, root)
    if not found:
        raise FlowControlError(f"Task not found: {task_id}")
    queue, path = found
    task = _read_json(path)
    if task.get("owner_role") != "gamma":
        raise FlowControlError("Only Gamma tasks use the approval gate")
    if queue != "escalated" or task.get("status") != "review_required":
        raise FlowControlError("Gamma task is not awaiting approval")
    ready, artifacts = review_artifacts_ready(task_id, root)
    if not ready:
        raise FlowControlError("Gamma approval denied: task.diff, task.review.md, and task.rollback.md must exist")

    approved = move_task(
        task_id,
        "active",
        "active",
        actor,
        {"approval": "explicit", "review_artifacts": artifacts},
        root,
    )
    audit_event("gamma_approved", task_id, actor, {"review_artifacts": artifacts}, root)
    return approved


def block_task(task_id: str, reason: str, actor: str = "api", root: Path | None = None) -> dict[str, Any]:
    return move_task(task_id, "blocked", "blocked", actor, {"reason": reason}, root)


def complete_task(task_id: str, summary: str, actor: str = "agent", root: Path | None = None) -> dict[str, Any]:
    root = ensure_state_tree(root)
    found = find_task_file(task_id, root)
    if not found:
        raise FlowControlError(f"Task not found: {task_id}")
    from_queue, path = found
    task = _read_json(path)
    artifact_dir = root / "artifacts" / task_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    output_path = artifact_dir / "output.md"
    output_path.write_text(summary + "\n", encoding="utf-8")
    task["artifact_path"] = str(output_path)
    task["status"] = "completed"
    task["queue"] = "completed"
    task["updated_at"] = utc_now()
    task.setdefault("events", []).append(
        {"created_at": utc_now(), "actor": actor, "artifact_path": str(output_path)}
    )
    target = _task_path("completed", task_id, root)
    _write_json(target, task)
    if target != path:
        path.unlink()
    audit_event(
        "task_transition",
        task_id,
        actor,
        {"from": from_queue, "to": "completed", "status": "completed", "artifact_path": str(output_path)},
        root,
    )
    return task


def list_tasks(queue: str | None = None, root: Path | None = None) -> list[dict[str, Any]]:
    root = ensure_state_tree(root)
    queues = [queue] if queue else list(QUEUE_NAMES)
    tasks: list[dict[str, Any]] = []
    for queue_name in queues:
        for path in sorted((root / "tasks" / queue_name).glob("*.json")):
            item = _try_read_json(path)
            if item is None:
                continue
            item["queue"] = queue_name
            tasks.append(item)
    return sorted(tasks, key=lambda item: item.get("updated_at") or item.get("created_at") or "")


def get_task(task_id: str, root: Path | None = None) -> dict[str, Any]:
    found = find_task_file(task_id, root)
    if not found:
        raise FlowControlError(f"Task not found: {task_id}")
    queue, path = found
    task = _read_json(path)
    task["queue"] = queue
    ready, artifacts = review_artifacts_ready(task_id, root)
    task["review_artifacts_ready"] = ready
    task["review_artifacts"] = artifacts
    task["audit"] = audit_trail(task_id, root)
    return task


def audit_trail(task_id: str | None = None, root: Path | None = None) -> list[dict[str, Any]]:
    root = ensure_state_tree(root)
    events = []
    for line in (root / "audit.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if task_id is None or event.get("task_id") == task_id:
            events.append(event)
    return events


def queue_counts(root: Path | None = None) -> dict[str, int]:
    root = ensure_state_tree(root)
    return {queue: len(list((root / "tasks" / queue).glob("*.json"))) for queue in QUEUE_NAMES}


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _pm2_names() -> set[str]:
    try:
        result = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=2, check=False)
        if result.returncode != 0:
            return set()
        return {item.get("name") for item in json.loads(result.stdout or "[]")}
    except Exception:
        return set()


def _docker_names() -> set[str]:
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode != 0:
            return set()
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}
    except Exception:
        return set()


def runtime_status(root: Path | None = None) -> dict[str, Any]:
    root = ensure_state_tree(root)
    pm2_names = _pm2_names()
    docker_names = _docker_names()
    agents = {}
    for role, info in AGENTS.items():
        port_ok = port_open(info["port"])
        runtime_ok = (
            info.get("process") in pm2_names
            if "process" in info
            else info.get("container") in docker_names
        )
        agents[role] = {
            **info,
            "port_open": port_ok,
            "runtime_registered": runtime_ok,
            "healthy": port_ok and runtime_ok,
        }
    dirs = {relative: (root / relative).exists() for relative in REQUIRED_DIRS}
    return {
        "timestamp": utc_now(),
        "state_root": str(root),
        "agents": agents,
        "queues": queue_counts(root),
        "directories": dirs,
        "healthy": all(agent["healthy"] for agent in agents.values()) and all(dirs.values()),
    }


@dataclass
class ClaimResult:
    task: dict[str, Any] | None
    queue: str | None


def claim_next(owner_role: str, root: Path | None = None) -> ClaimResult:
    root = ensure_state_tree(root)
    for path in sorted((root / "tasks" / "pending").glob("*.json")):
        task = _try_read_json(path)
        if task is None:
            continue
        if task.get("owner_role") == owner_role:
            active = move_task(task["task_id"], "active", "active", owner_role, {"claimed": True}, root)
            return ClaimResult(active, "active")
    return ClaimResult(None, None)


def archive_runtime_snapshot(destination: Path, root: Path | None = None) -> None:
    root = ensure_state_tree(root)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(root, destination)
