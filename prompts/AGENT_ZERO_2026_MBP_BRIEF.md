# AGENT ZERO — 2026 MacBook Pro FLOW Agent AS Deployment Brief

## Mission

Deploy FLOW Agent AS on a **2026 MacBook Pro** (Apple Silicon — ARM64).

The previous deployment targeted a Hostinger VPS running Ubuntu 22.04.
This deployment targets a local macOS machine with Apple Silicon (M4/M5 generation).
The stack, services, and ports are the same. The **platform is different**.
You must account for every platform difference listed below before executing.

---

## What Was Already Deployed (2015-era VPS Stack)

| Component | 2015 MBP / VPS Target | Notes |
|---|---|---|
| Host OS | Ubuntu 22.04 LTS (Hostinger VPS) | x86_64 |
| Docker runtime | Docker Engine (native Linux) | `/var/run/docker.sock` |
| Firewall | UFW | Ports opened via `ufw allow` |
| Access | Public VPS IP | Direct external access |
| LLM (Ollama) | `qwen2.5:3b` (fits ≤8 GB RAM) | Constrained by VPS memory |
| Data directory | `/opt/flow-agents` | Root-owned |
| Bootstrap | `scripts/bootstrap.sh` via curl | VPS-specific |

---

## Platform Delta — 2026 MacBook Pro

| Dimension | VPS (old) | 2026 MBP (new) | Action Required |
|---|---|---|---|
| Architecture | x86_64 | ARM64 (Apple Silicon) | Verify all images support `linux/arm64` |
| Docker runtime | Docker Engine | Docker Desktop for Mac | Different socket path (see below) |
| OS / Firewall | Ubuntu + UFW | macOS + System Firewall | No `ufw` commands; use macOS firewall or leave open on LAN |
| External access | Public IP | `localhost` by default — Tailscale or Cloudflare Tunnel for remote | Add tunnel step if remote access needed |
| Data directory | `/opt/flow-agents` | `$HOME/flow-agents` | Update all path references |
| Memory / Ollama | ≤8 GB → `qwen2.5:3b` | 24–128 GB unified → run up to 70B | Upgrade model config in `.env` and `config/hermes/config.yaml` |
| Bootstrap script | `bootstrap.sh` (Linux) | macOS Homebrew + Docker Desktop | Do not run `bootstrap.sh`; use macOS setup steps |

---

## Pre-Flight Checklist (Agent Zero must verify before executing)

- [ ] macOS 14+ (Sonoma) or macOS 15+ (Sequoia) confirmed
- [ ] Docker Desktop for Mac installed and running (`docker info` returns healthy)
- [ ] Compose plugin available (`docker compose version`)
- [ ] Homebrew installed (`brew --version`)
- [ ] `$HOME/flow-agents` directory created and writable
- [ ] `.env` file created at `$HOME/flow-agents/.env` from `.env.example`
- [ ] All required secrets filled in (see Required Secrets below)
- [ ] `config/hermes/config.yaml` updated with correct model and Ollama URL
- [ ] Ollama pulled target model (`ollama pull <model>`)
- [ ] Ports 18000, 50080, 50090, 18789, 5000, 9443 are not in use
- [ ] ARM64 image compatibility verified for all services (see Image Compatibility)

---

## Required Secrets

```env
A0_AUTH_LOGIN=admin
A0_AUTH_PASSWORD=<generate: openssl rand -base64 16>

BIZBRAIN_ENV=prod
BIZBRAIN_API_TOKEN=<generate: openssl rand -base64 24>
FLOW_DB_PASSWORD=<generate: openssl rand -base64 16>

OPENAI_API_KEY=sk-...         # or leave as "ollama" if using local-only
OPENAI_BASE_URL=http://ollama:11434/v1

POSTIZ_DOMAIN=localhost:5000
POSTIZ_JWT_SECRET=<generate: openssl rand -base64 32>
POSTIZ_DB_PASSWORD=<generate: openssl rand -base64 16>
```

Optional (leave blank if unused):
```env
GOOGLE_API_KEY=
GROQ_API_KEY=
GITHUB_TOKEN=
DISCORD_TOKEN=
TELEGRAM_BOT_TOKEN=
FIRECRAWL_API_KEY=
```

---

## Model Recommendation by Installed RAM

| Unified Memory | Recommended Model | Notes |
|---|---|---|
| 24 GB | `qwen2.5:14b` or `gemma3:12b` | Solid quality, safe headroom |
| 36 GB | `qwen2.5:32b` | Near-frontier local quality |
| 64 GB | `llama3.3:70b` or `qwen2.5:72b` | Frontier-class local LLM |
| 128 GB | `llama3.3:70b` + parallel workers | Full production quality |

Update `.env` and `config/hermes/config.yaml` with the chosen model before `docker compose up`.

---

## Image Compatibility — ARM64 Verification

All images in `docker-compose.yml` must be confirmed multi-arch (`linux/amd64,linux/arm64`) or ARM64-native. Verify before deploying:

| Service | Image | ARM64 Status |
|---|---|---|
| portainer | `portainer/portainer-ce:latest` | ✅ Multi-arch |
| portainer-agent | `portainer/agent:latest` | ✅ Multi-arch |
| mercury-2 | `ghcr.io/erikhinla/mercury-2:latest` | ⚠️ Verify with owner |
| agent-zero | `agent0ai/agent-zero:latest` | ⚠️ Verify on Docker Hub |
| ollama | `ollama/ollama:latest` | ✅ ARM64 native (M-series optimized) |
| hermes | `ghcr.io/erikhinla/hermes-agent:latest` | ⚠️ Verify with owner |
| bizbrain-lite | Built locally | ✅ Local build matches host arch |
| postgres | `postgres:17-alpine` | ✅ Multi-arch |
| redis | `redis:7.2-alpine` | ✅ Multi-arch |
| postiz | `ghcr.io/gitroomhq/postiz-app:latest` | ⚠️ Verify manifest |

For any `⚠️` image: run `docker manifest inspect <image> | grep -i arm64` to confirm before pulling.
If an image lacks ARM64 support, add `platform: linux/amd64` to that service in `docker-compose.yml`
and Docker Desktop's Rosetta emulation will handle the translation (with a performance penalty).

---

## Docker Socket — macOS Difference

Docker Desktop on macOS exposes the socket at:
```
/var/run/docker.sock   (symlinked by Docker Desktop — same path works)
```
The compose file mounts `/var/run/docker.sock` into Portainer and Agent Zero.
This **works unchanged** on macOS with Docker Desktop. No edits required.

---

## Data Directory

All work happens in `$HOME/flow-agents`. Before starting:

```bash
mkdir -p ~/flow-agents
cp .env.example ~/flow-agents/.env
# Edit ~/flow-agents/.env with actual secrets
cp -r config ~/flow-agents/config
cp docker-compose.yml ~/flow-agents/docker-compose.yml
cp -r runtime ~/flow-agents/runtime
```

Run all `docker compose` commands from `~/flow-agents/`.

---

## Networking — Local vs Remote Access

| Access Type | How |
|---|---|
| Local browser | `localhost:<port>` — works immediately |
| LAN access (same network) | `<mac-local-ip>:<port>` — no extra config |
| Remote/external access | Install Tailscale (`brew install --cask tailscale`) and share Tailscale IP, OR use Cloudflare Tunnel |
| Public internet | Cloudflare Tunnel (`cloudflared tunnel`) — maps `tunnel.yourdomain.com` → `localhost:5000` etc. |

macOS does not use UFW. If the macOS system firewall is enabled (`System Settings → Network → Firewall`),
add Docker to the allowlist or set to "Block incoming connections" only (Docker Desktop handles exceptions).

---

## Scope of This Deployment

Agent Zero is responsible for:

1. Setting up `~/flow-agents/` directory and copying files
2. Editing `.env` with provided secrets
3. Updating `config/hermes/config.yaml` for the chosen model and memory
4. Verifying ARM64 image compatibility
5. Running `docker compose up -d --build`
6. Running smoke tests per `docs/SMOKE_TEST_RUNBOOK.md`
7. Writing a reflection and deployment record to `runtime/reviews/{job_id}/`

Agent Zero is **not** responsible for:
- Generating secrets (operator generates and provides them)
- Purchasing Tailscale or Cloudflare subscriptions
- Model selection (operator confirms based on RAM)
- macOS system administration outside Docker scope

---

## Review Artifacts Required

This is a `risk_tier: high` deployment task. Before Agent Zero executes, the following must exist:

```
runtime/reviews/{job_id}/task.diff
runtime/reviews/{job_id}/task.review.md   (with Approver: <name>, YYYY-MM-DD)
runtime/reviews/{job_id}/task.rollback.md
```

Rollback plan: `docker compose down` and restore prior `.env` from backup.
Recovery time: < 5 minutes (no data loss — Postgres volumes persist).

---

## Success Criteria

- [ ] All containers report `Up` in `docker compose ps`
- [ ] `curl http://localhost:18000/v1/health` returns `200`
- [ ] `curl http://localhost:18000/v1/flow/health` returns `200`
- [ ] Agent Zero UI loads at `http://localhost:50080`
- [ ] Portainer loads at `https://localhost:9443`
- [ ] Postiz loads at `http://localhost:5000`
- [ ] Ollama responds: `curl http://localhost:11434/api/tags`
- [ ] Smoke test task envelope accepted and routed (see `docs/SMOKE_TEST_RUNBOOK.md`)
- [ ] Reflection written to `runtime/reviews/{job_id}/`
- [ ] Deployment record saved with timestamp, operator, model version

---

## Escalate If

- ARM64 incompatible image has no Rosetta fallback path
- Docker Desktop resources (CPU/RAM limits) prevent container startup — increase in Docker Desktop → Settings → Resources
- Ollama model pull fails — check available disk (`df -h ~`) and memory headroom
- Postgres healthcheck fails after 5 retries — check volume permissions under `~/flow-agents/`
- Any gate artifact missing — do not proceed; request artifacts from operator
