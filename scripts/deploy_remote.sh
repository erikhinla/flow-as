#!/usr/bin/env bash
set -euo pipefail

# One-command remote deployment helper.
# Usage:
#   ./scripts/deploy_remote.sh <ssh_target> [remote_dir] [--agents-only|--full-stack] [--no-pull]
#
# Examples:
#   ./scripts/deploy_remote.sh root@203.0.113.10
#   ./scripts/deploy_remote.sh root@203.0.113.10 /opt/flow-agents --full-stack

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <ssh_target> [remote_dir] [--agents-only|--full-stack] [--no-pull]"
  exit 1
fi

SSH_TARGET="$1"
shift

REMOTE_DIR="/opt/flow-agents"
DEPLOY_MODE="--agents-only"
DO_PULL="true"

if [[ $# -gt 0 && "${1:0:2}" != "--" ]]; then
  REMOTE_DIR="$1"
  shift
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agents-only)
      DEPLOY_MODE="--agents-only"
      ;;
    --full-stack)
      DEPLOY_MODE="--full-stack"
      ;;
    --no-pull)
      DO_PULL="false"
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
  shift
done

if [[ "$DO_PULL" == "true" ]]; then
  REMOTE_CMD="set -euo pipefail; cd '$REMOTE_DIR'; git pull --ff-only; ./scripts/deploy_minimal_stack.sh $DEPLOY_MODE"
else
  REMOTE_CMD="set -euo pipefail; cd '$REMOTE_DIR'; ./scripts/deploy_minimal_stack.sh $DEPLOY_MODE"
fi

echo "Deploying on ${SSH_TARGET} in ${REMOTE_DIR} with mode ${DEPLOY_MODE}..."
ssh "$SSH_TARGET" "$REMOTE_CMD"

echo "Remote deploy command finished."
