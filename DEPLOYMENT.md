# FLOW Agent AS Deployment

This file is the top-level deployment index. The detailed deployment runbooks live in:

- `docs/deployment/hostinger-vps.md`
- `docs/deployment/portainer-stack.md`

## Current Deployment Shape

FLOW Agent AS is deployed as a Docker Compose stack with:

- `flow-gateway` for intake webhook traffic
- `flow-orchestrator` for the BizBrain Lite control plane
- `flow-worker` services for queued execution
- `postgres` for durable job, audit, and learning state
- `redis` for queues and cache
- optional local LLM services when the `local-llm` profile is enabled

The standalone Hermes container is not part of the production readiness gate unless it is explicitly reintroduced and verified. The validated production path is through FLOW workers.

## Local Or VPS Quick Start

```bash
cp .env.example .env
# edit .env with real secrets

docker compose config
docker compose build
docker compose up -d
```

Optional local Ollama profile:

```bash
docker compose --profile local-llm up -d
```

## Required Environment Values

At minimum, configure:

- `FLOW_DB_PASSWORD`
- `BIZBRAIN_API_TOKEN`
- `WEBHOOK_API_KEY`
- `OPENAI_API_KEY` or an OpenAI-compatible provider configuration

Use `.env.example` as the full reference and keep production secrets out of git.

## Hostinger VPS

Use the Hostinger runbook:

```bash
ssh root@<VPS_IP>
mkdir -p /opt/flow-as
cd /opt/flow-as
git clone https://github.com/erikhinla/flow-as.git .
bash scripts/hostinger/bootstrap_vps.sh
bash scripts/hostinger/deploy.sh /opt/flow-as
```

Validate:

```bash
bash scripts/hostinger/healthcheck.sh localhost
docker compose ps
docker compose logs -f --tail=100 flow-orchestrator
```

## Portainer

Use the Portainer runbook:

- Repository URL: `https://github.com/erikhinla/flow-as.git`
- Compose path: `docker-compose.yml`
- Optional additional file: `docker-compose.prod.yml`
- Environment values: paste from `.env.example` into the Portainer stack UI

Post-deploy checks:

```bash
docker compose ps
docker compose logs --tail=100 flow-orchestrator
curl -fsS http://<VPS_IP>:18000/v1/health
curl -fsS http://<VPS_IP>:8080/health
```

## Runtime Readiness Gate

Before trusting a GO decision, verify all of the following:

```bash
python3 scripts/proof_flow_control.py
curl -fsS http://localhost:18789/health
curl -fsS http://localhost:18790/health
curl -fsS http://localhost:18800/health
```

The generated `FLOW_AGENT_AS_CONTROL_LAYER_REPORT.md` is authoritative for the Alpha/Beta/Gamma control-layer gate. Treat production as NO-GO if Alpha, Beta, or Gamma are not healthy.

## Public Ports

- `22` SSH
- `9443` Portainer HTTPS
- `9000` Portainer HTTP
- `18000` FLOW orchestrator API
- `8080` FLOW gateway intake API
- `50090` FLOW worker gateway, if enabled

Do not expose Postgres or Redis publicly.

## Rollback

Hostinger:

```bash
bash scripts/hostinger/rollback.sh /opt/flow-as
```

Portainer:

- redeploy a previous known-good commit SHA or tag; or
- use the CLI fallback from `docs/deployment/portainer-stack.md`.
