# FLOW Agent AS — 2026 MacBook Pro Deployment Guide

This guide replaces the VPS-specific `DEPLOYMENT.md` for local macOS deployments on Apple Silicon hardware (M4/M5 generation, 2026 MacBook Pro).

---

## Prerequisites

### 1. Docker Desktop for Mac

Download and install from https://www.docker.com/products/docker-desktop/

After install:
- Open Docker Desktop → Settings → Resources
- Set **Memory** to at least 16 GB (32 GB+ recommended for 30B+ models)
- Set **CPUs** to at least 8
- Enable **Rosetta** (Settings → General → "Use Rosetta for x86/amd64 emulation") as a fallback for any image not yet ARM64-native
- Apply & Restart

Verify:
```bash
docker info
docker compose version
```

### 2. Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 3. Ollama (local LLM runner)

```bash
brew install ollama
# Or: download the macOS app from https://ollama.com
```

Pull your target model based on available unified memory:

```bash
# 24 GB Mac
ollama pull qwen2.5:14b

# 36 GB Mac
ollama pull qwen2.5:32b

# 64 GB Mac
ollama pull llama3.3:70b

# 128 GB Mac
ollama pull llama3.3:70b   # can run multiple workers
```

Verify Ollama is running:
```bash
curl http://localhost:11434/api/tags
```

---

## Step 1: Set Up Working Directory

```bash
mkdir -p ~/flow-agents
cd ~/flow-agents

# Copy required files from repo
cp /path/to/flow-as/.env.example .env
cp /path/to/flow-as/docker-compose.yml .
cp -r /path/to/flow-as/config ./config
cp -r /path/to/flow-as/runtime ./runtime
cp -r /path/to/flow-as/services ./services
cp -r /path/to/flow-as/schemas ./schemas
```

---

## Step 2: Configure Environment Variables

```bash
nano ~/flow-agents/.env
```

Fill in all required secrets. Generate secure values:

```bash
# Generate passwords / secrets
openssl rand -base64 32   # for JWT secrets
openssl rand -base64 16   # for DB passwords and API tokens
```

**Required minimum:**

```env
A0_AUTH_LOGIN=admin
A0_AUTH_PASSWORD=<generated>

BIZBRAIN_ENV=prod
BIZBRAIN_API_TOKEN=<generated>
FLOW_DB_PASSWORD=<generated>

# OpenAI (or leave as "ollama" for fully local)
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=http://ollama:11434/v1

# Use your Mac's LAN IP or localhost
POSTIZ_DOMAIN=localhost:5000
POSTIZ_JWT_SECRET=<generated>
POSTIZ_DB_PASSWORD=<generated>
```

---

## Step 3: Configure Hermes for Your Model

Edit `~/flow-agents/config/hermes/config.yaml`:

```yaml
# 24 GB Mac
provider: custom
base_url: http://ollama:11434/v1
model: qwen2.5:14b
context_length: 32768
api_key: "ollama"
```

```yaml
# 36 GB Mac
provider: custom
base_url: http://ollama:11434/v1
model: qwen2.5:32b
context_length: 32768
api_key: "ollama"
```

```yaml
# 64 GB+ Mac (OpenAI-quality local)
provider: custom
base_url: http://ollama:11434/v1
model: llama3.3:70b
context_length: 32768
api_key: "ollama"
```

Also update `.env`:
```env
HERMES_DEFAULT_MODEL=qwen2.5:14b   # match model above
```

---

## Step 4: Verify ARM64 Image Compatibility

For each third-party image, confirm multi-arch support:

```bash
docker manifest inspect portainer/portainer-ce:latest | grep -i arm64
docker manifest inspect agent0ai/agent-zero:latest | grep -i arm64
docker manifest inspect ghcr.io/gitroomhq/postiz-app:latest | grep -i arm64
docker manifest inspect ghcr.io/erikhinla/mercury-2:latest | grep -i arm64
docker manifest inspect ghcr.io/erikhinla/hermes-agent:latest | grep -i arm64
```

If any image **lacks ARM64**, add `platform: linux/amd64` to that service in `docker-compose.yml`.
Docker Desktop's Rosetta emulation handles the translation automatically.

Example patch for a non-ARM64 service:
```yaml
  mercury-2:
    image: ${MERCURY2_IMAGE:-ghcr.io/erikhinla/mercury-2:latest}
    platform: linux/amd64          # add this line
    container_name: mercury-2
    ...
```

---

## Step 5: Adjust Ollama Service in docker-compose.yml

The `ollama` service in `docker-compose.yml` is designed for Linux GPU/CPU. On macOS,
**Ollama runs natively outside Docker** (as a macOS app or Homebrew service) and performs best that way.

Option A — Use **native macOS Ollama** (recommended for best M-series performance):

1. Comment out the `ollama` service in `docker-compose.yml`
2. Remove the `ollama` volume from the volumes section
3. Remove `depends_on: ollama` from the `hermes` service
4. Change the Hermes base URL to point to the host:

In `config/hermes/config.yaml`:
```yaml
base_url: http://host.docker.internal:11434/v1
```

In `.env`:
```env
OPENAI_BASE_URL=http://host.docker.internal:11434/v1
```

Option B — Keep **Ollama inside Docker** (simpler, slightly less performance):

No changes needed. The existing Docker Compose config works as-is.
Ollama inside Docker on Apple Silicon still uses the Metal GPU backend.

---

## Step 6: Start the Stack

```bash
cd ~/flow-agents
docker compose up -d --build
```

Wait ~2–3 minutes for all services to initialize (Postgres and Redis healthchecks must pass first).

Monitor startup:
```bash
docker compose ps
docker compose logs -f --tail=50
```

---

## Step 7: Pull Ollama Model into Container (Option B only)

If using Ollama inside Docker:

```bash
docker exec ollama ollama pull qwen2.5:14b
# Wait for download to complete, then verify:
docker exec ollama ollama list
```

---

## Step 8: Verify Services

```bash
docker compose ps
```

All containers should show `Up` or `Up (healthy)`.

Service URLs (local):

| Service | URL | Login |
|---|---|---|
| **Portainer** (Dashboard) | https://localhost:9443 | admin / set on first login |
| **BizBrain Lite** (Control Plane) | http://localhost:18000/docs | x-api-token header |
| **Postiz** (Social Media) | http://localhost:5000 | Create first account |
| **Mercury 2** (Orchestrator) | http://localhost:18789 | (API only) |
| **Agent Zero** (Executor) | http://localhost:50080 | admin / A0_AUTH_PASSWORD |
| **Hermes** (Specialist) | http://localhost:50090 | (API only) |
| **Ollama** (LLM) | http://localhost:11434 | (API only) |

---

## Step 9: Run Smoke Tests

Follow `docs/SMOKE_TEST_RUNBOOK.md`. Set:

```bash
export FLOW_HOST=http://localhost:18000
export FLOW_TOKEN=<your BIZBRAIN_API_TOKEN>
```

Then run each check in order. All expected responses must pass before marking deployment complete.

---

## Remote / External Access

### LAN access (same Wi-Fi network)

Find your Mac's local IP:
```bash
ipconfig getifaddr en0
```

Use that IP in place of `localhost` for other devices on your network.
Update `POSTIZ_DOMAIN=<lan-ip>:5000` in `.env` and restart Postiz if needed.

### Remote access via Tailscale (recommended)

```bash
brew install --cask tailscale
# Open Tailscale, sign in, get your Tailscale IP
```

Services are then available at `<tailscale-ip>:<port>` from any device in your Tailscale network.

### Public access via Cloudflare Tunnel (optional)

```bash
brew install cloudflared
cloudflared tunnel login
cloudflared tunnel create flow-as
cloudflared tunnel route dns flow-as flow.yourdomain.com
cloudflared tunnel run --url http://localhost:5000 flow-as
```

---

## macOS-Specific Maintenance Commands

### Start/stop the full stack

```bash
cd ~/flow-agents
docker compose up -d       # start
docker compose down        # stop (preserves volumes)
docker compose down -v     # stop + delete all data (destructive)
```

### Backup Postgres

```bash
# FLOW database
docker exec flow-postgres pg_dump -U flow_user flow_agent_os > ~/flow-backup-$(date +%Y%m%d).sql

# Postiz database
docker exec postiz-postgres pg_dump -U postiz-user postiz-db > ~/postiz-backup-$(date +%Y%m%d).sql
```

### Update to latest images

```bash
cd ~/flow-agents
docker compose pull
docker compose up -d
```

### Free disk space

```bash
docker system df
docker system prune       # removes stopped containers + dangling images
docker system prune -a    # WARNING: removes all unused images
```

---

## Troubleshooting

### Containers not starting / unhealthy

```bash
docker compose logs <service-name>
# e.g.:
docker compose logs bizbrain-lite
docker compose logs agent-zero
docker compose logs ollama
```

### Postgres not initializing

```bash
docker compose logs flow-postgres
docker volume rm flow-agents_flow_postgres_data   # wipe and recreate (loses data)
docker compose up -d flow-postgres
```

### Port already in use

```bash
lsof -i :50080   # find what's using the port
# Kill by PID if needed: kill -9 <PID>
```

### Docker Desktop out of memory

Open Docker Desktop → Settings → Resources → increase Memory limit.
Restart Docker Desktop after changing.

### Ollama model not loading

```bash
# Native macOS Ollama
ollama list
ollama pull <model>
curl http://localhost:11434/api/generate -d '{"model":"qwen2.5:14b","prompt":"hi"}'

# Docker Ollama
docker exec ollama ollama list
docker exec ollama ollama pull <model>
```

### ARM64 image error ("exec format error")

```bash
# Add platform override to the service in docker-compose.yml:
#   platform: linux/amd64
# Then re-pull:
docker compose pull <service>
docker compose up -d <service>
```

---

## What Does Not Apply from DEPLOYMENT.md

The following VPS-specific instructions in `DEPLOYMENT.md` do **not apply** to macOS:

- `bash <(curl -fsSL .../bootstrap.sh)` — Linux VPS only
- `ufw allow` / `ufw reload` — macOS uses its own firewall
- `/opt/flow-agents` paths — use `~/flow-agents` instead
- `ssh root@<VPS_IP>` — not applicable for local deployment
- Hostinger VPS provisioning steps
