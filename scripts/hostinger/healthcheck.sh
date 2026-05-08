#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-localhost}"

curl -fsS "http://${HOST}:8080/health" | python3 -m json.tool
curl -fsS "http://${HOST}:18000/v1/health" | python3 -m json.tool
curl -fsS "http://${HOST}:18000/v1/flow/health" | python3 -m json.tool

echo "Healthcheck complete."
