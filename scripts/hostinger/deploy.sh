#!/usr/bin/env bash
set -euo pipefail

# Deploy FLOW Agent AS on Hostinger VPS.
# Usage: ./scripts/hostinger/deploy.sh [repo_dir]

REPO_DIR="${1:-/opt/flow-as}"

if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "Repository not found in $REPO_DIR"
  exit 1
fi

cd "$REPO_DIR"

git fetch origin
git pull --ff-only

test -f .env || { echo "Missing .env file. Copy .env.example first."; exit 1; }

docker compose -f docker-compose.yml -f docker-compose.prod.yml config >/dev/null
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

docker compose ps
