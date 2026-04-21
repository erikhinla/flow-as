#!/usr/bin/env bash
set -euo pipefail

# Deploy FLOW stack.
# Usage:
#   ./scripts/deploy_minimal_stack.sh [--agents-only|--full-stack]
# Default:
#   --agents-only

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MODE="--agents-only"
if [[ $# -gt 0 ]]; then
  case "$1" in
    --agents-only|--full-stack)
      MODE="$1"
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--agents-only|--full-stack]"
      exit 1
      ;;
  esac
fi

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
  A0_AUTH_PASSWORD
  OPENAI_API_KEY
)

if [[ "$MODE" == "--full-stack" ]]; then
  required_vars+=(
    BIZBRAIN_API_TOKEN
    FLOW_DB_PASSWORD
    POSTIZ_JWT_SECRET
    POSTIZ_DB_PASSWORD
  )
fi

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

if [[ "$MODE" == "--agents-only" ]]; then
  echo "Building and starting agents-only stack..."
  docker compose up -d --build \
    mercury-2 \
    hermes \
    agent-zero
else
  echo "Building and starting full launch stack..."
  docker compose up -d --build \
    flow-postgres \
    flow-redis \
    bizbrain-lite \
    mercury-2 \
    hermes \
    agent-zero \
    postiz \
    postiz_postgres \
    postiz_redis \
    portainer
fi

echo
echo "Container status:"
docker compose ps

if [[ "$MODE" == "--full-stack" ]]; then
  echo
  echo "Recent BizBrain logs:"
  docker compose logs --tail=80 bizbrain-lite
fi

echo
echo "Done."
