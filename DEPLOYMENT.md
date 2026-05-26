# FLOW Agent AS Deployment

This file describes the checked-in Docker Compose runtime and separates it
from planned worker deployment work. Detailed deployment runbooks live in:

- `docs/deployment/hostinger-vps.md`
- `docs/deployment/portainer-stack.md`

## Canonical Runtime Statement

FAAS means **FLOW Agent Architected Schemas**. FAAS is the governed execution
and proof layer coordinating specialized AI workers.

Hermes is a planned standalone **FAAS-governed canon-and-learning execution
worker**. Hermes is not the Execution Engine and not a runtime governor. A
Hermes installation is not part of FAAS runtime until a worker adapter,
write-back contract, proof run, and approval gate are implemented and verified.

## Host Authority

The approved host roles are:

| Environment | Host | Purpose | Promotion Rule |
| --- | --- | --- | --- |
| Staging | Hetzner VPS | Build verification and FAAS/Hermes proving runs | No production traffic or production authority |
| Production | Hostinger VPS | Approved FAAS runtime after promotion | Deploy only after staging evidence is reviewed and Erik approves promotion |

Hetzner is the proving environment for the first Hermes worker integration.
Hostinger is the production destination; it must not receive the new worker
topology until the staging proving run, idempotency test, proof review, and
operator approval have succeeded.

## Current Checked-In Compose Shape

The current root `docker-compose.yml` defines:

- `flow-gateway` for intake webhook traffic, exposed on port `8080`;
- `bizbrain-lite` / container `flow-orchestrator` for the FAAS control-plane
  API, exposed on port `18001`;
- `notion-flow-bridge` for polling and forwarding Notion tasks;
- `flow-dashboard` for operator visibility, exposed on port `5173`;
- optional `flow-discord-bot` under the `discord` profile;
- `postgres` for durable application state;
- `redis` for queues and cache.

The current compose file does **not** define `flow-worker-hermes`, OpenClaw
worker services, Agent Zero Gamma, Portainer, Postiz, or local-LLM services.
Do not describe any of those as active production services solely from this
repository configuration.

`docker-compose.prod.yml` currently references `agent-zero-gamma`, which is
not present in the root compose file. Treat that production override as
unreconciled and do not apply it until it is updated alongside an approved
worker topology.

## Planned Hermes Worker Introduction

Hermes will be introduced through a separate reviewed implementation after the
FAAS worker contract is locked. The worker introduction must include:

1. a standalone `flow-worker-hermes` service with restricted credentials;
2. a FAAS Hermes Worker Adapter, rather than direct database writes;
3. atomic claim and idempotent replay using `task_id`;
4. explicit risk-tier enforcement and separate artifact-review versus
   execution-approval fields;
5. a real proving run on Hetzner that returns an artifact, reflection, and proof to FAAS;
6. explicit operator approval before any promotion to Hostinger production.

See `docs/architecture/FAAS_HERMES_WORKER_CONTRACT.md` for the required
contract before implementation begins.

## Local Or Staging Control-Plane Quick Start

```bash
cp .env.example .env
# edit .env with environment-appropriate secrets

docker compose config
docker compose build
docker compose up -d
```

## Required Environment Values

At minimum for the currently defined compose stack, configure:

- `FLOW_DB_PASSWORD`
- `BIZBRAIN_API_TOKEN`
- `WEBHOOK_API_KEY`
- Notion bridge values only if `notion-flow-bridge` will be used
- provider credentials only for features that invoke a hosted model

Use `.env.example` as the reference when it matches the current compose file,
and keep production secrets out of git. Do not reuse production secrets in
Hetzner staging unless specifically approved and scoped for staging.

## Validation For The Current Compose Stack

After deploying the current control-plane stack to Hetzner staging, verify only
the services actually defined by `docker-compose.yml`:

```bash
docker compose config
docker compose ps
curl -fsS http://localhost:18001/v1/health
curl -fsS http://localhost:8080/health
```

The existing `scripts/proof_flow_control.py` and
`FLOW_AGENT_AS_CONTROL_LAYER_REPORT.md` demonstrate a local Alpha/Beta/Gamma
proof path from an earlier/runtime-specific configuration. They are evidence
of implemented control logic, not evidence that those worker services are
currently deployed by the root compose stack.

## Promotion Gate: Hetzner To Hostinger

A worker-enabled topology may be promoted to Hostinger production only when:

1. current compose and deployment documentation describe the same services;
2. the Hermes adapter uses FAAS APIs with atomic claim and idempotent replay;
3. the real TBTX proving task completes on Hetzner with artifact, reflection,
   proof, and successful replay evidence;
4. required secrets are separately configured for production;
5. rollback steps are documented against the promoted commit SHA;
6. Erik gives explicit production approval.

## Public Ports In The Current Compose File

- `8080` FLOW gateway intake API
- `18001` FAAS control-plane API
- `5173` FLOW dashboard

Do not expose Postgres or Redis publicly.

## Rollback

The Hostinger production runbook must define the rollback procedure and known-good
commit SHA for any promoted worker topology. Do not rely on an unreconciled
override file for rollback-sensitive deployment.
