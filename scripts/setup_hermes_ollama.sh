#!/usr/bin/env bash
# =============================================================================
# setup_hermes_ollama.sh
# Zero-interaction installer for Hermes + Ollama (local or VPS).
#
# Usage:
#   ./scripts/setup_hermes_ollama.sh [--vps <ip_or_host>] [--model <model>]
#
# Options:
#   --vps <ip>      Point Hermes at a remote Ollama endpoint instead of localhost
#   --model <name>  Model to use (default: qwen2.5:3b)
#
# Requirements:
#   - Python 3.10+
#   - Ollama installed (https://ollama.com/download)
#   - git
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
MODEL="qwen2.5:3b"
OLLAMA_HOST="127.0.0.1"
OLLAMA_PORT="11434"
HERMES_VENV="${HOME}/.hermes-venv"
HERMES_CONFIG_DIR="${HOME}/.hermes"
HERMES_CONFIG="${HERMES_CONFIG_DIR}/config.yaml"
HERMES_REPO="https://github.com/NousResearch/hermes-agent.git"
HERMES_SRC="${HOME}/.hermes-src"
CONTEXT_LENGTH="32768"

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --vps)
      OLLAMA_HOST="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--vps <ip_or_host>] [--model <model>]"
      exit 1
      ;;
  esac
done

OLLAMA_BASE_URL="http://${OLLAMA_HOST}:${OLLAMA_PORT}/v1"

log() { echo "[hermes-setup] $*"; }
err() { echo "[hermes-setup] ERROR: $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# 1. Verify prerequisites
# ---------------------------------------------------------------------------
log "Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || err "python3 not found. Install Python 3.10+."
command -v git    >/dev/null 2>&1 || err "git not found."

PY_OK=$(python3 -c "import sys; print('ok' if sys.version_info >= (3, 10) else 'fail')")
if [[ "${PY_OK}" != "ok" ]]; then
  PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
  err "Python 3.10+ required (found ${PY_VER})."
fi

# ---------------------------------------------------------------------------
# 2. Start / verify Ollama
# ---------------------------------------------------------------------------
log "Checking Ollama at ${OLLAMA_HOST}:${OLLAMA_PORT}..."

if [[ "${OLLAMA_HOST}" == "127.0.0.1" || "${OLLAMA_HOST}" == "localhost" ]]; then
  if ! curl -fsS "http://${OLLAMA_HOST}:${OLLAMA_PORT}/api/tags" >/dev/null 2>&1; then
    log "Ollama not running locally — attempting to start..."
    if command -v ollama >/dev/null 2>&1; then
      nohup ollama serve >/tmp/ollama.log 2>&1 &
      OLLAMA_PID=$!
      log "Started Ollama (PID ${OLLAMA_PID}). Waiting 5s..."
      sleep 5
    else
      err "Ollama binary not found. Install from https://ollama.com/download"
    fi
  fi
fi

# Confirm Ollama is reachable
curl -fsS "http://${OLLAMA_HOST}:${OLLAMA_PORT}/api/tags" >/dev/null \
  || err "Ollama is not reachable at http://${OLLAMA_HOST}:${OLLAMA_PORT}. Start it first."
log "Ollama is reachable."

# ---------------------------------------------------------------------------
# 3. Pull model if not already present
# ---------------------------------------------------------------------------
log "Checking for model '${MODEL}'..."
MODELS_JSON=$(curl -fsS "http://${OLLAMA_HOST}:${OLLAMA_PORT}/api/tags")
if echo "${MODELS_JSON}" | grep -q "\"${MODEL}\""; then
  log "Model '${MODEL}' already present."
else
  if [[ "${OLLAMA_HOST}" == "127.0.0.1" || "${OLLAMA_HOST}" == "localhost" ]]; then
    log "Pulling model '${MODEL}' (this may take several minutes)..."
    ollama pull "${MODEL}"
  else
    log "WARNING: Model '${MODEL}' not found on remote Ollama at ${OLLAMA_HOST}."
    log "Run on the remote host:  ollama pull ${MODEL}"
  fi
fi

# ---------------------------------------------------------------------------
# 4. Clean install — remove stale state
# ---------------------------------------------------------------------------
log "Removing stale Hermes config and virtualenv (if any)..."
rm -rf "${HERMES_CONFIG_DIR}" "${HERMES_VENV}" "${HERMES_SRC}"

# ---------------------------------------------------------------------------
# 5. Clone Hermes agent source
# ---------------------------------------------------------------------------
log "Cloning hermes-agent from ${HERMES_REPO}..."
git clone --depth=1 "${HERMES_REPO}" "${HERMES_SRC}"

# ---------------------------------------------------------------------------
# 6. Patch: bypass 64 K context minimum
# ---------------------------------------------------------------------------
log "Patching 64K context minimum check..."

# Search specifically for comparison/validation of 64K context limits.
# Patterns intentionally narrow: look for variables being compared to the
# 64K literal, not arbitrary occurrences of the number.
PATCH_TARGETS=$(grep -rn \
  --include="*.py" \
  -E "(context|ctx|window).*(>=|<=|>|<|==)\s*(65536|64000)|(65536|64000)\s*(>=|<=|>|<|==).*(context|ctx|window)" \
  "${HERMES_SRC}" 2>/dev/null || true)

if [[ -n "${PATCH_TARGETS}" ]]; then
  log "Found context-minimum comparisons — patching..."
  # Replace only context-window comparison literals, anchored to word boundaries
  find "${HERMES_SRC}" -name "*.py" -exec \
    perl -i -pe \
      's/(?<=(context|ctx|window).*(?:>=|<=|>|<|==)\s*)65536\b/'"${CONTEXT_LENGTH}"'/g;
       s/\b65536\b(?=\s*(?:>=|<=|>|<|==).*(?:context|ctx|window))/'"${CONTEXT_LENGTH}"'/g;
       s/(?<=(context|ctx|window).*(?:>=|<=|>|<|==)\s*)64000\b/'"${CONTEXT_LENGTH}"'/g;
       s/\b64000\b(?=\s*(?:>=|<=|>|<|==).*(?:context|ctx|window))/'"${CONTEXT_LENGTH}"'/g' \
      {} +
  log "Patch applied."
else
  log "No 64K context-limit comparison found in source (config sets context_length to ${CONTEXT_LENGTH})."
fi

# ---------------------------------------------------------------------------
# 7. Create Python virtual environment and install dependencies
# ---------------------------------------------------------------------------
log "Creating virtual environment at ${HERMES_VENV}..."
python3 -m venv "${HERMES_VENV}"

VENV_PIP="${HERMES_VENV}/bin/pip"
VENV_PYTHON="${HERMES_VENV}/bin/python"

log "Installing hermes-agent and dependencies..."
"${VENV_PIP}" install --upgrade pip --quiet

# Install from local (patched) source
"${VENV_PIP}" install -e "${HERMES_SRC}" --quiet

# Ensure all expected extras are present (some may not be in setup.cfg)
"${VENV_PIP}" install --quiet \
  pyyaml \
  python-dotenv \
  httpx \
  prompt_toolkit \
  fire \
  openai

log "Dependencies installed."

# ---------------------------------------------------------------------------
# 8. Write Hermes config
# ---------------------------------------------------------------------------
log "Writing Hermes config to ${HERMES_CONFIG}..."
mkdir -p "${HERMES_CONFIG_DIR}"

cat > "${HERMES_CONFIG}" <<YAML
version: "1.0"

provider: custom
base_url: ${OLLAMA_BASE_URL}
model: ${MODEL}
context_length: ${CONTEXT_LENGTH}

# Ollama does not require a real API key
api_key: "ollama"

gateway:
  enabled: false
YAML

log "Config written."

# ---------------------------------------------------------------------------
# 9. Smoke test — verify Ollama OpenAI-compat endpoint
# ---------------------------------------------------------------------------
log "Smoke-testing Ollama OpenAI-compatible endpoint..."
HTTP_STATUS=$(curl -fsS -o /dev/null -w "%{http_code}" \
  "http://${OLLAMA_HOST}:${OLLAMA_PORT}/v1/models" || echo "000")

if [[ "${HTTP_STATUS}" == "200" ]]; then
  log "Ollama /v1/models → OK (200)"
else
  log "WARNING: /v1/models returned HTTP ${HTTP_STATUS}. Check Ollama logs."
fi

# ---------------------------------------------------------------------------
# 10. Run Hermes with a test prompt
# ---------------------------------------------------------------------------
HERMES_BIN="${HERMES_VENV}/bin/hermes"

if [[ ! -x "${HERMES_BIN}" ]]; then
  # Some installs put the entrypoint under a different name
  HERMES_BIN=$(find "${HERMES_VENV}/bin" -name "hermes*" | head -n1 || true)
fi

if [[ -z "${HERMES_BIN}" ]]; then
  log "WARNING: hermes binary not found in venv. Run manually:"
  log "  source ${HERMES_VENV}/bin/activate && hermes chat"
  exit 0
fi

log "Launching Hermes with test prompt: 'what does FLOW stand for?'"
log "(Hermes output follows)"
echo "---"

# Non-interactive single-turn: pipe the prompt if hermes supports --prompt flag,
# otherwise fall back to echo-pipe into interactive mode.
if "${HERMES_BIN}" --help 2>&1 | grep -q "\-\-prompt"; then
  "${HERMES_BIN}" --prompt "what does FLOW stand for?" --no-setup
else
  # Pipe prompt to stdin; hermes will respond then exit on EOF
  echo "what does FLOW stand for?" | "${HERMES_BIN}" --no-setup 2>/dev/null \
    || echo "what does FLOW stand for?" | "${HERMES_BIN}" 2>/dev/null \
    || log "Interactive mode required — run: source ${HERMES_VENV}/bin/activate && hermes"
fi

echo "---"
log "Setup complete."
log ""
log "To use Hermes:"
log "  source ${HERMES_VENV}/bin/activate"
log "  hermes"
