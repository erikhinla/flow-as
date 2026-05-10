#!/usr/bin/env bash
set -euo pipefail

FLOW_AS_ROOT="${FLOW_AS_ROOT:-/opt/flow-as}"
FLOW_HOST_ROOT="${FLOW_HOST_ROOT:-/opt/flow-agent-as}"
cd "$FLOW_AS_ROOT"

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$FLOW_HOST_ROOT/backups/git-local-$STAMP"
mkdir -p "$BACKUP_DIR"

cp docker-compose.yml "$BACKUP_DIR/docker-compose.yml.local-before-reset" 2>/dev/null || true
cp docker-compose.workflow.yml "$BACKUP_DIR/docker-compose.workflow.yml.local-before-reset" 2>/dev/null || true
cp docker-compose.agents.generated.yml "$BACKUP_DIR/docker-compose.agents.generated.yml.local-before-reset" 2>/dev/null || true
cp .env "$BACKUP_DIR/.env.local-before-reset" 2>/dev/null || true

echo "Backup saved to: $BACKUP_DIR"

git fetch origin main
git reset --hard origin/main

if [ -f "$BACKUP_DIR/.env.local-before-reset" ]; then
  cp "$BACKUP_DIR/.env.local-before-reset" .env
else
  touch .env
fi

set_env() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" .env; then
    sed -i "s#^${key}=.*#${key}=${value}#" .env
  else
    echo "${key}=${value}" >> .env
  fi
}

set_env DASHBOARD_BASIC_AUTH_USER "admin"
set_env DASHBOARD_BASIC_AUTH_PASSWORD "ChangeThisLongPassword123!"
set_env FLOW_HOST_ROOT "$FLOW_HOST_ROOT"
set_env ACTIVEPIECES_URL "http://localhost:8081"
set_env POSTIZ_DOMAIN "http://localhost:5000"

chmod +x scripts/fix_dashboard_runtime.sh || true

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.workflow.yml"
if [ -f docker-compose.agents.generated.yml ]; then
  COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.agents.generated.yml"
fi

sh -c "docker compose $COMPOSE_FILES up -d --build --force-recreate flow-dashboard"
sleep 10

echo "=== DASHBOARD STATUS ==="
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep flow-dashboard || true

echo "=== DASHBOARD HTTP ==="
curl -I http://localhost:5173 || true

echo "=== DASHBOARD LOGS ==="
docker logs --tail=100 flow-dashboard || true

mkdir -p "$FLOW_HOST_ROOT/state/reports"
cat > "$FLOW_HOST_ROOT/state/reports/dashboard-git-repair-verdict.md" <<EOF
# Dashboard Git Repair Verdict

Generated: $(date -Iseconds)

Backup:
$BACKUP_DIR

Actions:
- backed up local compose/env files
- hard-synced /opt/flow-as to origin/main
- restored .env
- set dashboard auth env values
- recreated flow-dashboard
- checked localhost:5173

Success state:
- flow-dashboard is Up
- localhost:5173 returns HTTP 401, 200, or 30x
EOF

cat "$FLOW_HOST_ROOT/state/reports/dashboard-git-repair-verdict.md"
