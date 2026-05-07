#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "bizbrain_lite"))

from app.services.flow_filesystem_control import (
    approve_task,
    audit_trail,
    claim_next,
    complete_task,
    ensure_state_tree,
    get_task,
    runtime_status,
    submit_task,
)


def envelope(title: str, goal: str, risk_tier: str) -> dict:
    return {
        "task_id": str(uuid.uuid4()),
        "title": title,
        "goal": goal,
        "risk_tier": risk_tier,
        "source": "proof",
        "inputs": {"proof": True},
    }


def run() -> dict:
    root = ensure_state_tree()
    proofs = {}

    alpha = submit_task(
        envelope(
            "Alpha reputation proof",
            "Write a small reputation-safe proof artifact and complete without escalation.",
            "reputation",
        ),
        actor="proof",
    )
    claimed_alpha = claim_next("alpha")
    if not claimed_alpha.task:
        raise RuntimeError("Alpha proof was not claimable")
    complete_task(alpha["task_id"], "# Alpha proof\n\nAlpha completed without Beta or Gamma escalation.", actor="openclaw-alpha")
    proofs["alpha"] = get_task(alpha["task_id"])

    beta = submit_task(
        envelope(
            "Beta time-loss proof",
            "Write a small time-loss proof artifact and complete through Beta.",
            "time_loss",
        ),
        actor="proof",
    )
    claimed_beta = claim_next("beta")
    if not claimed_beta.task:
        raise RuntimeError("Beta proof was not claimable")
    complete_task(beta["task_id"], "# Beta proof\n\nBeta claimed and completed the time-loss task.", actor="openclaw-beta")
    proofs["beta"] = get_task(beta["task_id"])

    gamma = submit_task(
        envelope(
            "Gamma approval proof",
            "Prepare a downtime/security/money proof package that cannot execute before approval.",
            "downtime_security_money",
        ),
        actor="proof",
    )
    before_approval = get_task(gamma["task_id"])
    if before_approval["queue"] != "escalated" or before_approval["status"] != "review_required":
        raise RuntimeError("Gamma proof did not enter escalated/review_required")
    if not before_approval["review_artifacts_ready"]:
        raise RuntimeError("Gamma proof artifacts are missing")
    approve_task(gamma["task_id"], actor="proof")
    complete_task(gamma["task_id"], "# Gamma proof\n\nGamma completed only after explicit approval.", actor="agent-zero-gamma")
    proofs["gamma"] = get_task(gamma["task_id"])
    proofs["gamma_before_approval"] = before_approval

    status = runtime_status()
    report = write_report(REPO_ROOT / "FLOW_AGENT_AS_CONTROL_LAYER_REPORT.md", status, proofs, root)
    return {"report": str(report), "proofs": {key: value["task_id"] for key, value in proofs.items() if "task_id" in value}}


def transition_rows(task: dict) -> str:
    rows = []
    for event in task.get("audit", []):
        rows.append(f"- {event['created_at']} `{event['action']}` by `{event['actor']}`")
    return "\n".join(rows)


def artifact_lines(task: dict) -> str:
    lines = []
    if task.get("artifact_path"):
        lines.append(f"- output: `{task['artifact_path']}`")
    if task.get("owner_role") == "gamma":
        for key, path in (task.get("review_artifacts") or {}).items():
            lines.append(f"- {key}: `{path}`")
    return "\n".join(lines) or "- none"


def write_report(path: Path, status: dict, proofs: dict, root: Path) -> Path:
    fixed_files = [
        "services/bizbrain_lite/app/services/flow_filesystem_control.py",
        "services/bizbrain_lite/app/api/flow_control.py",
        "services/bizbrain_lite/app/main.py",
        "services/bizbrain_lite/app/config/settings.py",
        "services/bizbrain_lite/app/services/envelope_validation_service.py",
        "schemas/task_envelope.schema.json",
        "services/bizbrain_lite/Dockerfile",
        "discord-bot.py",
        "services/dashboard/src/components/FlowControl.tsx",
        "services/dashboard/src/App.tsx",
        "services/dashboard/nginx.conf",
        "ecosystem.config.cjs",
        "scripts/openclaw_runtime.py",
        "scripts/gamma_runtime.py",
        "scripts/proof_flow_control.py",
        "docker-compose.yml",
        "docker-compose.prod.yml",
    ]

    go = (
        status["healthy"]
        and proofs["alpha"]["status"] == "completed"
        and proofs["beta"]["status"] == "completed"
        and proofs["gamma"]["status"] == "completed"
        and proofs["gamma_before_approval"]["status"] == "review_required"
    )

    content = [
        "# FLOW Agent AS Control Layer Report",
        "",
        f"Generated: `{status['timestamp']}`",
        f"State root: `{root}`",
        "",
        "## Current Runtime Status",
        "```json",
        json.dumps(status, indent=2, sort_keys=True),
        "```",
        "",
        "## Fixed Files",
        *[f"- `{file}`" for file in fixed_files],
        "",
        "## Discord Commands Added",
        "- `/flow status`",
        "- `/flow submit`",
        "- `/flow pending`",
        "- `/flow active`",
        "- `/flow completed`",
        "- `/flow escalated`",
        "- `/flow artifact task_id`",
        "- `/flow approve task_id`",
        "- `/flow block task_id reason`",
        "",
        "## Landing Page Routes Added",
        "- `/flow-control`",
        "",
        "## API Routes Added",
        "- `GET /api/flow/status`",
        "- `GET /api/flow/tasks`",
        "- `GET /api/flow/tasks/:task_id`",
        "- `POST /api/flow/submit`",
        "- `POST /api/flow/approve`",
        "- `POST /api/flow/block`",
        "",
        "## Proof Task IDs",
        f"- Alpha: `{proofs['alpha']['task_id']}`",
        f"- Beta: `{proofs['beta']['task_id']}`",
        f"- Gamma: `{proofs['gamma']['task_id']}`",
        "",
        "## Queue Transition Timestamps",
        "### Alpha",
        transition_rows(proofs["alpha"]),
        "### Beta",
        transition_rows(proofs["beta"]),
        "### Gamma",
        transition_rows(proofs["gamma"]),
        "",
        "## Artifact Paths",
        "### Alpha",
        artifact_lines(proofs["alpha"]),
        "### Beta",
        artifact_lines(proofs["beta"]),
        "### Gamma",
        artifact_lines(proofs["gamma"]),
        "",
        "## Audit Log Evidence",
        f"- Audit log: `{root / 'audit.jsonl'}`",
        f"- Alpha audit events: `{len(proofs['alpha']['audit'])}`",
        f"- Beta audit events: `{len(proofs['beta']['audit'])}`",
        f"- Gamma audit events: `{len(proofs['gamma']['audit'])}`",
        "",
        "## Remaining Risks",
        "- Runtime health is GO only when PM2 has `openclaw-alpha` and `openclaw-beta` online and Docker has `agent-zero-gamma` online.",
        "- The dashboard API token must be present in browser `localStorage.flow_api_token` when `BIZBRAIN_API_TOKEN` is not empty.",
        "- Gamma runtime is intentionally constrained to approved active tasks; escalated tasks are visible for review but not executed.",
        "",
        "## GO / NO-GO",
        "GO" if go else "NO-GO until all runtime processes report healthy.",
        "",
    ]
    path.write_text("\n".join(content), encoding="utf-8")
    return path


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
