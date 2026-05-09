#!/usr/bin/env python3
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("FLOW_AS_ROOT", "/opt/flow-as"))
LEGACY = Path(os.environ.get("FLOW_LEGACY_AGENTS_ROOT", "/opt/flow-agents"))
FLOW_HOST_ROOT = os.environ.get("FLOW_HOST_ROOT", "/opt/flow-agent-as")
OUT = ROOT / "docker-compose.agents.generated.yml"
BACKUP_ROOT = Path(FLOW_HOST_ROOT) / "backups"

TARGETS = [
    "flow-agent-zero-worker",
    "flow-hermes-worker",
    "flow-openclaw-worker",
]

CANONICAL_BINDS = [
    {"type": "bind", "source": f"{FLOW_HOST_ROOT}/state", "target": "/state"},
    {"type": "bind", "source": f"{FLOW_HOST_ROOT}/workspace", "target": "/workspace"},
    {"type": "bind", "source": f"{FLOW_HOST_ROOT}/artifacts", "target": "/artifacts"},
]


def run(cmd, cwd=None, check=True):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=check)


def load_legacy_config():
    if not (LEGACY / "docker-compose.yml").exists():
        raise SystemExit(f"Missing legacy compose file: {LEGACY / 'docker-compose.yml'}")
    proc = run(["docker", "compose", "config", "--format", "json"], cwd=LEGACY)
    return json.loads(proc.stdout)


def normalize_service(name, service):
    s = copy.deepcopy(service)

    # Preserve the running service's identity so migration actually takes ownership.
    s["container_name"] = name
    s["restart"] = s.get("restart") or "unless-stopped"

    # Attach to repo-backed FLOW network.
    networks = s.get("networks") or {}
    if isinstance(networks, list):
        networks = {n: None for n in networks}
    networks["flow-internal"] = None
    s["networks"] = networks

    # Add canonical shared mounts without removing existing mounts.
    volumes = s.get("volumes") or []
    existing_targets = set()
    for vol in volumes:
        if isinstance(vol, dict) and vol.get("target"):
            existing_targets.add(vol.get("target"))
        elif isinstance(vol, str) and ":" in vol:
            existing_targets.add(vol.split(":", 2)[1])

    for bind in CANONICAL_BINDS:
        if bind["target"] not in existing_targets:
            volumes.append(bind)
    s["volumes"] = volumes

    return s


def dump_yaml(data):
    # Minimal YAML writer for Docker Compose-compatible objects.
    def scalar(v):
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return str(v)
        text = str(v)
        if text == "" or any(c in text for c in [":", "#", "{", "}", "[", "]", ",", "&", "*", "!", "|", ">", "'", '"', "%", "@", "`", "\n"]):
            return json.dumps(text)
        if text.lower() in ["true", "false", "null", "yes", "no", "on", "off"]:
            return json.dumps(text)
        return text

    def write(obj, indent=0):
        pad = "  " * indent
        lines = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    lines.append(f"{pad}{k}:")
                    lines.extend(write(v, indent + 1))
                else:
                    lines.append(f"{pad}{k}: {scalar(v)}")
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    lines.append(f"{pad}-")
                    lines.extend(write(item, indent + 1))
                else:
                    lines.append(f"{pad}- {scalar(item)}")
        else:
            lines.append(f"{pad}{scalar(obj)}")
        return lines

    return "\n".join(write(data)) + "\n"


def main():
    cfg = load_legacy_config()
    services = cfg.get("services", {})
    selected = {}
    missing = []

    for name in TARGETS:
        if name in services:
            selected[name] = normalize_service(name, services[name])
        else:
            missing.append(name)

    if not selected:
        raise SystemExit("No legacy agent services found to migrate.")

    generated = {
        "services": selected,
        "networks": {
            "flow-internal": {
                "external": True,
                "name": "flow-internal",
            }
        },
    }

    OUT.write_text(dump_yaml(generated), encoding="utf-8")

    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = run(["date", "+%Y%m%d-%H%M%S"]).stdout.strip()
    backup_dir = BACKUP_ROOT / f"legacy-agent-migration-{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / "docker-compose.agents.generated.yml").write_text(OUT.read_text(encoding="utf-8"), encoding="utf-8")
    (backup_dir / "legacy-compose-rendered.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    print(f"Generated: {OUT}")
    print(f"Backup: {backup_dir}")
    print("Migrated services:")
    for name in selected:
        print(f"- {name}")
    if missing:
        print("Missing services:")
        for name in missing:
            print(f"- {name}")


if __name__ == "__main__":
    main()
