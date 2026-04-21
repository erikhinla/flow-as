#!/usr/bin/env bash
set -euo pipefail

# Smoke-test FLOW control plane and intake routing.
# Usage:
#   ./scripts/smoke_test_flow.sh <HOST_OR_IP> [BIZBRAIN_API_TOKEN]

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <HOST_OR_IP> [BIZBRAIN_API_TOKEN]"
  exit 1
fi

HOST_OR_IP="$1"
FLOW_TOKEN="${2:-${BIZBRAIN_API_TOKEN:-}}"
FLOW_HOST="http://${HOST_OR_IP}:18000"

echo "Using FLOW_HOST=${FLOW_HOST}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    exit 1
  fi
}

require_cmd curl
require_cmd python3

echo
echo "1) Health checks"
curl -fsS "${FLOW_HOST}/v1/health" | python3 -m json.tool
curl -fsS "${FLOW_HOST}/v1/flow/health" | python3 -m json.tool
curl -fsS "${FLOW_HOST}/v1/intake/status" | python3 -m json.tool
curl -fsS "${FLOW_HOST}/v1/intake/queues/status" | python3 -m json.tool

echo
echo "2) Submit bounded intake task"
TASK_ID="$(python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
)"

cat <<JSON >/tmp/flow_task_payload.json
{
  "task_id": "${TASK_ID}",
  "created_at": "2026-04-18T12:00:00Z",
  "source": "manual",
  "title": "Draft launch-day hero copy",
  "goal": "Produce bounded launch-day homepage hero copy and CTA options for immediate release.",
  "task_type": "content_prep",
  "risk_tier": "low",
  "preferred_owner": "hermes",
  "inputs": {
    "notes": "Focus on launch readiness and urgency."
  },
  "output_required": "Persisted hero-copy draft ready for review",
  "review_required": false,
  "rollback_required": false,
  "status": "pending"
}
JSON

curl -fsS -X POST "${FLOW_HOST}/v1/intake/task" \
  -H "Content-Type: application/json" \
  --data-binary @/tmp/flow_task_payload.json | python3 -m json.tool

echo
echo "3) Queue state after intake"
curl -fsS "${FLOW_HOST}/v1/intake/queues/status" | python3 -m json.tool

if [[ -n "${FLOW_TOKEN}" ]]; then
  echo
  echo "4) Protected endpoint check (/v1/agents)"
  curl -fsS "${FLOW_HOST}/v1/agents" -H "x-api-token: ${FLOW_TOKEN}" | python3 -m json.tool
else
  echo
  echo "4) Skipping protected endpoint check (no token supplied)"
fi

echo
echo "Web surfaces:"
echo "- BizBrain Docs: ${FLOW_HOST}/docs"
echo "- Agent Zero:   http://${HOST_OR_IP}:50080"
echo "- Postiz:       http://${HOST_OR_IP}:5000"
echo "- Portainer:    https://${HOST_OR_IP}:9443"
