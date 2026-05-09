#!/usr/bin/env bash
set -euo pipefail

FLOW_AS_ROOT="${FLOW_AS_ROOT:-/opt/flow-as}"
FLOW_HOST_ROOT="${FLOW_HOST_ROOT:-/opt/flow-agent-as}"
LEGACY_ROOT="${FLOW_LEGACY_AGENTS_ROOT:-/opt/flow-agents}"

cd "$FLOW_AS_ROOT"

mkdir -p "$FLOW_HOST_ROOT"/state/tasks/{pending,active,completed,failed,escalated,archive}
mkdir -p "$FLOW_HOST_ROOT"/state/reports "$FLOW_HOST_ROOT"/workspace "$FLOW_HOST_ROOT"/artifacts "$FLOW_HOST_ROOT"/backups
chmod -R 775 "$FLOW_HOST_ROOT"

if [ -f .env ]; then
  touch .env
else
  touch .env
fi

ensure_env() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" .env; then
    sed -i "s#^${key}=.*#${key}=${value}#" .env
  else
    echo "${key}=${value}" >> .env
  fi
}

ensure_env FLOW_HOST_ROOT "$FLOW_HOST_ROOT"
ensure_env DASHBOARD_BASIC_AUTH_USER "admin"
ensure_env DASHBOARD_BASIC_AUTH_PASSWORD "ChangeThisLongPassword123!"
ensure_env POSTIZ_DOMAIN "http://localhost:5000"
ensure_env POSTIZ_JWT_SECRET "ChangeThisPostizJwtSecret123456789!"
ensure_env POSTIZ_DB_PASSWORD "ChangeThisPostizDbPassword123456789!"

chmod +x scripts/submit-campaign-proof.sh || true
chmod +x scripts/migrate_legacy_agents.py || true

python3 scripts/migrate_legacy_agents.py

echo "=== STOP LEGACY AGENT CONTAINERS ONLY AFTER GENERATED OVERLAY EXISTS ==="
if [ -f docker-compose.agents.generated.yml ]; then
  docker rm -f flow-agent-zero-worker flow-hermes-worker flow-openclaw-worker 2>/dev/null || true
else
  echo "Missing generated agent overlay. Refusing to stop legacy agent containers."
  exit 1
fi

echo "=== DEPLOY REPO-BACKED FULL FLOW RUNTIME ==="
docker compose \
  -f docker-compose.yml \
  -f docker-compose.workflow.yml \
  -f docker-compose.agents.generated.yml \
  up -d --build

sleep 25

echo "=== HEALTH ==="
curl -fsS http://localhost:18001/v1/health && echo
curl -fsS http://localhost:8080/health && echo
curl -I http://localhost:5000 || true
curl -I http://localhost:5173 || true

echo "=== CONTAINERS ==="
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'flow-|activepieces|postiz|redis|postgres|agent-zero|hermes|openclaw' || true

echo "=== SHARED MOUNT PROOF ==="
for c in flow-postiz flow-activepieces flow-asset-worker flow-agent-zero-worker flow-hermes-worker flow-openclaw-worker; do
  if docker ps --format '{{.Names}}' | grep -qx "$c"; then
    docker exec "$c" sh -lc "echo ${c}-mounted > /state/reports/${c}-mount-proof.txt && cat /state/reports/${c}-mount-proof.txt" || true
  else
    echo "NOT RUNNING: $c"
  fi
done

echo "=== CAMPAIGN PROOF ==="
TASK_ID=$(FLOW_HOST_ROOT="$FLOW_HOST_ROOT" bash scripts/submit-campaign-proof.sh | head -n 1)
sleep 12
cat "$FLOW_HOST_ROOT/state/reports/$TASK_ID.md"
cat "$FLOW_HOST_ROOT/artifacts/$TASK_ID/result.json"

cat > "$FLOW_HOST_ROOT/state/reports/FLOW_FULL_RUNTIME_VERDICT.md" <<EOF
# FLOW Full Runtime Verdict

Generated: $(date -Iseconds)

## Repo-backed runtime deployed from
$FLOW_AS_ROOT

## Compose files
- docker-compose.yml
- docker-compose.workflow.yml
- docker-compose.agents.generated.yml

## Runtime services expected
- flow-orchestrator
- flow-gateway
- flow-dashboard
- flow-activepieces
- flow-postiz
- flow-asset-worker
- flow-agent-zero-worker
- flow-hermes-worker
- flow-openclaw-worker
- redis
- postgres

## Latest campaign proof
$TASK_ID

Report:
$FLOW_HOST_ROOT/state/reports/$TASK_ID.md

Artifact:
$FLOW_HOST_ROOT/artifacts/$TASK_ID/result.json

## Migration rule
The legacy /opt/flow-agents stack should only be retired after the repo-backed flow-agent-zero-worker, flow-hermes-worker, and flow-openclaw-worker are running and mount proofs exist.
EOF

cat "$FLOW_HOST_ROOT/state/reports/FLOW_FULL_RUNTIME_VERDICT.md"
