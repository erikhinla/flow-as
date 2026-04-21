#!/usr/bin/env bash
set -euo pipefail

# Deploy only the minimal FLOW Agent AS launch surface.
# Usage:
#   ./scripts/deploy_minimal_stack.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker is not installed or not in PATH."
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "Error: .env file is missing at repo root."
  echo "Copy .env.example to .env and fill required secrets first."
  exit 1
fi

required_vars=(
  OPENCLAW_GATEWAY_TOKEN
  A0_AUTH_PASSWORD
  BIZBRAIN_API_TOKEN
  FLOW_DB_PASSWORD
  OPENAI_API_KEY
  POSTIZ_JWT_SECRET
  POSTIZ_DB_PASSWORD
)

missing=0
for key in "${required_vars[@]}"; do
  value="$(grep -E "^${key}=" .env | head -n1 | cut -d= -f2- || true)"
  if [[ -z "${value}" ]]; then
    echo "Missing required .env value: ${key}"
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  echo "Fix missing .env values and re-run."
  exit 1
fi

echo "Building and starting minimal FLOW stack..."
docker compose up -d --build \
  flow-postgres \
  flow-redis \
  bizbrain-lite \
  openclaw \
  hermes \
  agent-zero \
  postiz \
  postiz_postgres \
  postiz_redis \
  portainer

echo
echo "Container status:"
docker compose ps

echo
echo "Recent BizBrain logs:"
docker compose logs --tail=80 bizbrain-lite

echo
echo "Done. Next: run ./scripts/smoke_test_flow.sh <HOST_OR_IP>"
