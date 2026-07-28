# FLOW Agent AS Deployment

This file is the top-level deployment index. The detailed deployment runbooks live in:

- `docs/deployment/hostinger-vps.md`
- `docs/deployment/portainer-stack.md`

## Current Deployment Shape

FLOW Agent AS is deployed as a Docker Compose stack with:

- `flow-gateway` for intake webhook traffic
- `flow-orchestrator` for the BizBrain Lite control plane
- `flow-hermes-worker` routing Alpha work to the official Hermes Agent runtime
- `flow-openclaw-worker` routing Beta work to the official OpenClaw runtime
- `flow-agent-zero-worker` routing approval-gated Gamma work to the official Agent Zero runtime
- `postgres` for durable job, audit, and learning state
- `redis` for queues and cache
- optional local LLM services when the `local-llm` profile is enabled

The agent runtimes are digest-pinned official images. Their repositories, upstream
commits, image digests, and noninteractive entrypoints are locked in
`config/agent-sources.lock.json`. A healthy control plane does not prove that an
agent is working; each runtime must complete a task-specific job through its
assigned FLOW queue.

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
- `OPENROUTER_API_KEY`

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
curl -fsS http://<VPS_IP>:18001/v1/health
curl -fsS http://<VPS_IP>:8080/health
```

## Runtime Readiness Gate

Before trusting a GO decision, verify all of the following:

Treat production as NO-GO until all of these are true:

1. `hermes-agent`, `openclaw-agent`, and `agent-zero` are healthy on the internal Docker network.
2. The Hermes container executes the real `hermes` binary.
3. The OpenClaw container executes the real `/app/openclaw.mjs` CLI.
4. The Agent Zero container answers through its official `/api/message` endpoint.
5. Three distinct FLOW jobs complete through Alpha, Beta, and approved Gamma.
6. Each artifact records its execution engine and upstream provenance.
7. The proof survives a stack restart.

## Public Ports

- `22` SSH
- `9443` Portainer HTTPS
- `9000` Portainer HTTP
- `18001` FLOW orchestrator API
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
