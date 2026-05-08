# FLOW Agent AS

Production-focused FLOW Agent AS stack for Hostinger VPS, designed for Docker Compose and Portainer stack deployments.

## Architecture runtime

Execution path (default):

1. **Gateway** (`flow-gateway`) receives intake.
2. **Orchestrator** (`flow-orchestrator`) validates context readiness (Quad Keystone baseline).
3. **Risk Router** classifies by money/time/reputation/security/downtime.
4. **Executor** (`flow-worker`) handles low-risk execution.
5. Medium-risk routes to observer review APIs before completion.
6. High-risk requires human approval before execution.
7. Completed work writes reflection state to durable storage.

## Services

- `flow-gateway` – intake webhook API (FastAPI)
- `flow-orchestrator` – control-plane API and routing (BizBrain Lite)
- `flow-worker` – Hermes execution worker
- `redis` – queue/cache
- `postgres` – durable state (`pgvector/pgvector:pg17`)
- `ollama` – optional local model runtime (`local-llm` profile)

## Quick start (local or VPS shell)

```bash
cp .env.example .env
# edit .env with real secrets

docker compose config
docker compose build
docker compose up -d
```

With optional Ollama container:

```bash
docker compose --profile local-llm up -d
```

## Health checks

```bash
curl -fsS http://localhost:8080/health
curl -fsS http://localhost:18000/v1/health
curl -fsS http://localhost:18000/v1/flow/health
```

## Logs

```bash
docker compose logs -f flow-orchestrator
docker compose logs -f flow-worker
docker compose logs -f flow-gateway
```

## Deployment docs

- Hostinger deployment guide: `docs/deployment/hostinger-vps.md`
- Portainer stack guide: `docs/deployment/portainer-stack.md`
- VPS scripts: `scripts/hostinger/`
