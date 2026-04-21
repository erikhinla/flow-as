# Tomorrow Launch Plan

## WIN

Deploy the smallest working FLOW Agent AS surface that can:

- accept bounded tasks through the control plane
- route work to the right agent surface
- support website build work
- support content generation work
- support social scheduling through Postiz
- give one human operator surface for review and intervention

This plan favors working leverage over architectural completeness.

## Launch Principle

Do not try to deploy every idea in the system.

Deploy only the components required to make the existing execution model usable:

- BizBrain Lite as the control plane and intake API
- Postgres for durable FLOW state
- Redis for queue routing
- Agent Zero for high-risk execution and direct operator access
- Hermes as bounded execution worker
- OpenClaw as intake/router and repo-native worker surface
- Postiz for social publishing and scheduling
- Portainer for stack visibility only

Do not block tomorrow's launch on voice, learner automation, monitoring, Discord, or additional service sprawl.

## Minimal Runtime

### Required services

1. `bizbrain-lite`
2. `flow-postgres`
3. `flow-redis`
4. `agent-zero`
5. `hermes`
6. `openclaw`
7. `postiz`
8. `postiz-postgres`
9. `postiz-redis`
10. `portainer`

### Human-facing surfaces

- Agent Zero UI on a public port for direct operator use
- Postiz UI for social scheduling and posting
- Portainer for stack status and logs
- BizBrain Lite API docs or simple API surface for task submission

### Non-goals for tomorrow

- voice gateway
- dynamic agent registry
- sandbox runner
- nightly fine-tuning loop
- Prometheus and Grafana
- Discord front door

## Current Strengths Already Present

The repo already contains the core FLOW scaffolding needed for launch:

- durable task, reflection, and skill state
- queue-based intake and routing
- recursive learning through reflections and skill extraction
- review gating for high-risk execution
- explicit task envelope governance

This means the main gap is deployment plumbing, not missing architecture.

## Current Status

The main repo-side blockers have been cleared:

- BizBrain Lite is containerized
- root compose now includes `bizbrain-lite`, `flow-postgres`, and `flow-redis`
- runtime dependencies have been added for SQLAlchemy, `asyncpg`, Alembic, and `jsonschema`
- Redis configuration is normalized through `BIZBRAIN_REDIS_URL`
- BizBrain Lite is exposed on host port `18000`
- Notion has been removed from the active runtime path

## Remaining Deployment Risks

### 1. Fresh-host build has not been executed yet

The repo is ready for deployment, but the updated stack has not been built and started on the actual host from this environment.

Result:

- container build issues, image pull failures, or host-specific networking problems may still appear during first boot

### 2. Docker is unavailable in the current local environment

Docker commands cannot be run from this workspace session.

Result:

- first real validation must happen on the target host with `docker compose`

### 3. Live secrets and host configuration are still required

The stack now expects real values for control-plane auth, FLOW Postgres, agent credentials, and Postiz secrets.

Result:

- the deployment cannot complete until the host `.env` is populated

### 4. Public worker exposure is still broader than ideal

OpenClaw and Hermes remain publicly exposed in the current stack to preserve launch momentum.

Result:

- acceptable for immediate launch if controlled carefully, but should be tightened after launch behind a reverse proxy or internal-only routing

## Tomorrow Deployment Shape

### Public ports

- `9443` Portainer
- `50080` Agent Zero UI
- `5000` Postiz
- `18789` OpenClaw API only if needed
- `50090` Hermes API only if needed
- `18000` BizBrain Lite API

### Preferred operator workflow

1. Use Agent Zero UI for direct execution and intervention.
2. Use BizBrain Lite for governed task intake and flow visibility.
3. Use Postiz for queueing and publishing social content.
4. Use Portainer only to inspect services, logs, and restart behavior.

This gives one usable operational lane without inventing a second architecture.

## Execution Order

### Phase 1. Make BizBrain Lite deployable

Required work:

- add a Dockerfile for `services/bizbrain_lite`
- add missing runtime dependencies
- normalize Redis environment variable handling
- confirm Postgres connection settings for durable FLOW state

Definition of done:

- `bizbrain-lite` builds as a container
- startup succeeds with Redis and Postgres attached
- `/v1/health` and `/v1/flow/health` return success

### Phase 2. Extend the root Docker stack

Required work:

- add `flow-postgres`
- add `flow-redis`
- add `bizbrain-lite`
- wire environment variables for database and queue connectivity
- expose BizBrain Lite on a non-conflicting public port

Definition of done:

- the stack comes up with control plane plus workers
- Portainer shows the full set of running services

### Phase 3. Validate end-to-end FLOW paths

Smoke checks:

- `GET /v1/health`
- `GET /v1/flow/health`
- `GET /v1/intake/status`
- `GET /v1/intake/queues/status`
- `POST /v1/intake/task`
- `GET /v1/agent-zero/reviews/{job_id}/status`

Definition of done:

- a task envelope is accepted
- a job record is created
- the queue depth changes
- the assigned owner is correct

### Phase 4. Prove launch use cases

Use case 1: Website build work

- submit a bounded implementation or content-prep task
- route to Hermes or Agent Zero based on risk
- persist output location and review state

Use case 2: Content generation

- submit a bounded content-prep or rewrite task
- verify reflection writing and skill reuse path remains intact

Use case 3: Social scheduling

- generate content through FLOW
- move approved output into Postiz
- schedule tomorrow's launch posts inside Postiz

## Recommended First Tasks

### Website task

- title: Build launch page sections from canon
- task_type: `implementation`
- risk_tier: `medium`
- preferred_owner: `hermes`
- output_required: committed page copy or component draft in the target repo

### Content task

- title: Draft launch-day social asset pack
- task_type: `content_prep`
- risk_tier: `low`
- preferred_owner: `hermes`
- output_required: approved social copy set with platform variants

### Social task

- title: Schedule launch-day posts in Postiz
- task_type: `implementation`
- risk_tier: `high`
- preferred_owner: `agent_zero`
- review_required: `true`
- rollback_required: `true`

## What To Ignore Until After Launch

- voice interface
- recursive model fine-tuning automation
- advanced observability
- multi-host orchestration refinement
- broader edge/router redesign

Those are valid later improvements, but they are not required to get leverage from the agents tomorrow.

## Bottom Line

The fastest path to value is not a new architecture.

It is to deploy the existing FLOW control plane and wire it into the current agent stack so that:

- intake works
- routing works
- memory works
- review gating works
- Postiz handles outbound social execution

If that slice is live, FLOW Agent AS can begin helping with websites, content, and launch operations immediately.