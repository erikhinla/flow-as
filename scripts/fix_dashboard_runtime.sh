#!/usr/bin/env bash
set -euo pipefail

cd "${FLOW_AS_ROOT:-/opt/flow-as}"
touch .env

if grep -q '^DASHBOARD_BASIC_AUTH_USER=' .env; then
  sed -i 's#^DASHBOARD_BASIC_AUTH_USER=.*#DASHBOARD_BASIC_AUTH_USER=admin#' .env
else
  echo 'DASHBOARD_BASIC_AUTH_USER=admin' >> .env
fi

if grep -q '^DASHBOARD_BASIC_AUTH_PASSWORD=' .env; then
  sed -i 's#^DASHBOARD_BASIC_AUTH_PASSWORD=.*#DASHBOARD_BASIC_AUTH_PASSWORD=ChangeThisLongPassword123!#' .env
else
  echo 'DASHBOARD_BASIC_AUTH_PASSWORD=ChangeThisLongPassword123!' >> .env
fi

COMPOSE_FILES='-f docker-compose.yml -f docker-compose.workflow.yml'
if [ -f docker-compose.agents.generated.yml ]; then
  COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.agents.generated.yml"
fi

sh -c "docker compose $COMPOSE_FILES up -d --build --force-recreate flow-dashboard"
sleep 10

docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep flow-dashboard || true
curl -I http://localhost:5173 || true
docker logs --tail=100 flow-dashboard || true

mkdir -p "${FLOW_HOST_ROOT:-/opt/flow-agent-as}/state/reports"
cat > "${FLOW_HOST_ROOT:-/opt/flow-agent-as}/state/reports/dashboard-runtime-fix.md" <<EOF
# Dashboard Runtime Fix

Generated: $(date -Iseconds)

The script set dashboard auth env values, recreated flow-dashboard, checked HTTP on port 5173, and tailed logs.

Success state: flow-dashboard is Up and localhost:5173 returns HTTP 401, 200, or 30x.
EOF
cat "${FLOW_HOST_ROOT:-/opt/flow-agent-as}/state/reports/dashboard-runtime-fix.md"
