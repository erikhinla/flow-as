#!/usr/bin/env bash
set -euo pipefail

FLOW_ROOT="${FLOW_HOST_ROOT:-/opt/flow-agent-as}"
TASK_ID="campaign-proof-$(date +%Y%m%d-%H%M%S)"
TASK_FILE="$FLOW_ROOT/state/tasks/pending/${TASK_ID}.json"

mkdir -p "$FLOW_ROOT/state/tasks/pending"

cat > "$TASK_FILE" <<EOF
{
  "task_id": "$TASK_ID",
  "source": "manual-proof",
  "source_system": "host-cli",
  "instruction": "Create a proof campaign asset workflow task. Validate intake, route it, produce an artifact, and write completion report.",
  "workflow_type": "campaign_asset",
  "campaign": {
    "name": "FLOW Proof Campaign",
    "channels": ["postiz", "manual_review"],
    "asset_types": ["caption", "post_brief", "publishing_package"]
  },
  "risk_class": "time_loss",
  "status": "pending",
  "created_at": "$(date -Iseconds)"
}
EOF

echo "$TASK_ID"
echo "$TASK_FILE"
