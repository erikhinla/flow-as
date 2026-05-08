#!/usr/bin/env bash
set -euo pipefail

# Roll back to previous commit and redeploy.
# Usage: ./scripts/hostinger/rollback.sh [repo_dir]

REPO_DIR="${1:-/opt/flow-as}"
cd "$REPO_DIR"

git reset --hard HEAD~1
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

docker compose ps
