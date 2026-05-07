# FLOW Agent AS Repo Hygiene Manifest

Date: 2026-05-07

Purpose: make the working tree clean without losing intentional FLOW Agent AS runtime, control surface, and deployment work.

## Placement Decision

Primary deployment target: Hostinger.

Reason: Hostinger is the primary FLOW runtime/control stack. It should run the canonical FLOW Agent AS control plane, filesystem-backed queues, validation, audit state, gateway, dashboard, Redis, Postgres, Hermes, and standard workers.

Secondary deployment target: Hetzner.

Reason: Hetzner should remain the Gamma / Agent Zero heavy execution node. It should receive approved high-risk or compute-heavy work after FLOW validation and Gamma approval. It should not become the source of truth for core queues, audit state, or validator logic.

## Commit Bucket

These files represent source, schema, deployment, security, control surface, or documentation changes and should be reviewed for commit:

- `.env.example`
- `.gitignore`
- `DEPLOYMENT.md`
- `Dockerfile`
- `README.md`
- `discord-bot.py`
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `ecosystem.config.cjs`
- `schemas/task_envelope.schema.json`
- `alembic/env.py`
- `alembic/versions/flow_003_add_priority_column.py`
- `alembic/versions/flow_004_create_audit_logs.py`
- `docs/deployment/`
- `rollback/`
- `scripts/flow-ask-hermes.sh`
- `scripts/gamma_runtime.py`
- `scripts/hostinger/`
- `scripts/openclaw_runtime.py`
- `scripts/proof_flow_control.py`
- `services/bizbrain_lite/`
- `services/dashboard/`
- `test_dashboard_auth.sh`
- `test_intake_auth.sh`

Critical fix to preserve:

- `services/bizbrain_lite/app/api/openclaw_intake.py` must keep `owner_role` on `TaskEnvelopeInput`; otherwise `/v1/intake/task` strips a schema-required field and rejects valid FLOW envelopes.

## Archive Or Commit As Evidence

These files are operational evidence. They can be committed if the repo intentionally tracks proof artifacts, or moved to an archive branch/storage if the repo should stay source-only:

- `FLOW_AGENT_AS_CONTROL_LAYER_REPORT.md`
- `HERMES_FINAL_VERDICT.md`
- `HERMES_GOOGLE_PROVIDER_INVESTIGATION.md`
- `runtime/ingress_rate_limit_audit.md`
- `runtime/ingress_rate_limit_diff.md`
- `runtime/ingress_rate_limit_rollback.md`
- `runtime/ingress_rate_limit_test_results.md`
- `runtime/post_rate_limit_auth_regression_results.md`
- `runtime/reviews/live-deployment-sprint/`
- `runtime/validation/`
- `state/reports/`

## Ignore Bucket

These are local/generated and should not be committed:

- `.openclaw/`
- `.DS_Store`
- `**/.DS_Store`
- `__pycache__/`
- `**/__pycache__/`
- `*.pyc`
- `node_modules/`
- `**/node_modules/`
- `.env`
- `*.env.local`

## Deletion Bucket

These are currently deleted from the working tree and need explicit confirmation before finalizing:

- `FLOW_AGENT_OS/memory/hermes/outputs/HERMES-002-intake-system.md`
- `FLOW_AGENT_OS/memory/hermes/outputs/HERMES-004-intake-webhook.md`
- `FLOW_AGENT_OS/runtime/queues/completed/HERMES-002.yaml`
- `FLOW_AGENT_OS/runtime/queues/completed/HERMES-004.yaml`

Recommended decision: keep the deletion only if `FLOW_AGENT_OS` has been intentionally superseded by `FLOW_AGENT_AS`. Otherwise restore these files before committing.

## Deployment Rule

Deploy core FLOW Agent AS to Hostinger first.

Do not deploy core queues, source-of-truth audit state, primary validation, or Gamma approval logic to Railway or Hetzner.

Use Hetzner only as an attached Gamma / Agent Zero execution node after Hostinger control plane health is proven.

## Clean Repo Procedure

1. Commit source/runtime-control changes.
2. Commit or archive evidence reports separately.
3. Confirm whether deleted `FLOW_AGENT_OS` files should remain deleted.
4. Ensure generated directories stay ignored.
5. Rebuild and restart Hostinger runtime from the committed repo.
6. Validate:
   - `/v1/health`
   - `/v1/flow/health`
   - `/v1/intake/task`
   - queue transition
   - artifact creation
   - audit trail
