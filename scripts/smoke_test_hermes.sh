#!/usr/bin/env bash
set -euo pipefail

# Smoke-test Hermes-solo health.
# Usage:
#   ./scripts/smoke_test_hermes.sh [HOST_OR_IP] [PORT]

HOST_OR_IP="${1:-localhost}"
PORT="${2:-50090}"
HERMES_URL="http://${HOST_OR_IP}:${PORT}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    exit 1
  fi
}

require_cmd curl
require_cmd python3

echo "Using HERMES_URL=${HERMES_URL}"
echo
echo "1) Hermes health"
curl -fsS "${HERMES_URL}/v1/health" | python3 -m json.tool

echo
echo "2) Hermes models"
curl -fsS "${HERMES_URL}/v1/models" | python3 -m json.tool

echo
echo "Hermes smoke test passed."
