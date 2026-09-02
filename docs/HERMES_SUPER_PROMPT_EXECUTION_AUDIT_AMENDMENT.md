# Hermes Super-Prompt Execution Audit Amendment

## Status

This amendment supersedes runtime-role and deployment-state claims in
`docs/HERMES_SUPER_PROMPT_EXECUTION_AUDIT.md` pending an inline rewrite of that
historical audit.

## Corrected Claims

| Prior claim or implication | Corrected ground truth |
| --- | --- |
| Hermes is documented as the runtime governor. | Hermes is a planned standalone **FAAS-governed canon-and-learning execution worker**. FAAS owns orchestration authority, approval, evidence, audit, and final state. |
| Hermes may be treated as an available production control-plane service. | Hermes artifacts and historical compose definitions exist; the current root `docker-compose.yml` does not deploy a Hermes service. |
| FLOW workers are deployed by the current root compose configuration. | The current root compose configuration defines control-plane, gateway, dashboard, Notion bridge, Redis, and Postgres services; worker services have not yet been integrated into that compose topology. |
| Current production readiness can rely on Alpha/Beta/Gamma proof artifacts alone. | The control-layer report proves a local runtime-specific path; production readiness requires a reconciled compose topology and a host-specific proving run. |
| Deployment-host authority was not settled. | **Hetzner VPS is staging** for proving runs. **Hostinger VPS is production** after evidence review, rollback readiness, and Erik's approval. |

## Locked Architecture

- FAAS means **FLOW Agent Architected Schemas**.
- FAAS is the governed execution and proof layer coordinating specialized AI workers.
- Hermes is a standalone-capable FAAS-governed worker, not the Execution Engine
  and not the runtime governor.
- Hermes integration requires a worker adapter using FAAS APIs, atomic job
  claiming, idempotent replay, task-scoped workspaces, and proof write-back.
- Hermes must not receive production deploy, billing, DNS, or unrestricted
  infrastructure authority for the first proving run.
- Hetzner staging is the first worker proving environment; Hostinger production
  receives only an explicitly approved promotion.

## Evidence Boundary

Implemented and locally evidenced components include BizBrain APIs, Hermes
skill-loop endpoints, task/routing and approval logic, historical deployment
artifacts, and a local Alpha/Beta/Gamma control-layer report.

Not yet proven by current checked-in deployment configuration:

- a deployed standalone Hermes FAAS worker;
- a Hermes adapter consuming governed FAAS jobs and writing results back;
- a Hetzner staging host running the approved worker topology;
- a Hostinger production promotion of that topology;
- a real TBTX or BBAI delivery completed through the integrated Hermes lane.

## Next Verified Milestone

The next milestone is contract reconciliation followed by a Hetzner staging
proving run in which a FAAS-routed Hermes task produces the TBTX Fog Diagnostic
UI implementation specification and component schema from attached canonical
source logic, with artifact review, proof, reflection, and idempotent replay.

See `docs/architecture/FAAS_HERMES_WORKER_CONTRACT.md` and `DEPLOYMENT.md` for
the controlling implementation and deployment guidance.
