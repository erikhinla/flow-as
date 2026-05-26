# FAAS Hermes Worker Contract

## Decision

FAAS means **FLOW Agent Architected Schemas**. FAAS is the governed execution
and proof layer coordinating specialized AI workers.

Hermes will be introduced as a standalone **FAAS-governed canon-and-learning
execution worker**. Hermes is not the Execution Engine, not the runtime
governor, and not authorized to determine whether a result ships.

This document is the contract gate for the future `flow-worker-hermes` adapter.
It does not assert that the adapter or worker container is already deployed.

## Ownership

| Concern | Authority |
| --- | --- |
| Canon, priorities, production approvals, commercial activation | Erik |
| Work orders, envelopes, routing, risk tiers, approvals, proof, audit, terminal job state | FAAS |
| Canon-aware synthesis, bounded artifact creation, reflection, skill learning | Hermes |

## Existing Runtime Findings

The repository currently contains two relevant execution paths:

1. Postgres/Redis-backed intake and skill-loop APIs in `services/bizbrain_lite`.
2. A filesystem-backed Alpha/Beta/Gamma control proof in
   `flow_filesystem_control.py` and `scripts/proof_flow_control.py`.

The Hermes adapter must not write into both state models or quietly select a
third model. Postgres-backed FAAS job, artifact, reflection, and audit records
are the target authoritative contract for worker integration. The filesystem
proof path remains useful evidence and must be migrated or explicitly marked
legacy before production worker activation.

## Required API Contract Before Adapter Wiring

The FAAS control plane must expose authenticated operations equivalent to:

| Operation | Purpose |
| --- | --- |
| `POST /v1/tasks` or existing intake equivalent | Create/validate a task envelope and route it |
| `POST /v1/jobs/{task_id}/claim` | Atomically claim queued work using a lease |
| `GET /v1/jobs/{task_id}` | Read terminal or in-progress status for proving-run polling |
| `POST /v1/jobs/{task_id}/complete` | Persist artifact references and terminal result |
| `POST /v1/jobs/{task_id}/fail` | Persist failure with retry/escalation status |
| `POST /v1/jobs/{task_id}/reflections` | Persist sequence-numbered reflections |
| `POST /v1/jobs/{task_id}/escalate` | Return out-of-tier or approval-sensitive work to FAAS |

A worker must use the API and must not write directly to Postgres.

## Job Lifecycle

The canonical worker-facing job lifecycle is:

```text
submitted -> validated -> queued -> claimed -> in_progress
                                     |             |
                                     |             +-> completed
                                     |             +-> failed
                                     |             +-> needs_review
                                     |             +-> escalated
                                     +-> expired lease -> queued retry
```

The adapter implementation must map existing status values to this lifecycle
explicitly rather than changing behavior implicitly.

## Idempotency And Replay Safety

- `task_id` is the idempotency key for task execution.
- Claiming a job is an atomic FAAS state transition, not a read-then-write check.
- A successful claim creates a lease with `worker_id`, `attempt_number`, and
  expiry timestamp.
- A task already claimed under a valid lease is not executed again.
- A completed task returns its recorded artifacts on replay.
- A failed task is retried only under FAAS policy and with an incremented
  attempt number.
- Each Hermes task uses an isolated workspace keyed by `task_id` and attempt.
- Reflections are append-only and sequence-numbered per `task_id`; retries do
  not overwrite previous evidence.
- Queue acknowledgement occurs only after FAAS accepts write-back.

## Routing And Risk Contract

Hermes' initial permitted work is bounded artifact production at `low` or
`medium` risk. Introduce a Hermes-routable task type such as
`artifact_production`; do not reuse an existing type if it currently maps to a
different worker.

Use one canonical risk vocabulary in adapter-facing APIs:

| Risk Tier | Examples | Hermes Default Permission |
| --- | --- | --- |
| `low` | draft specification, classification, documentation artifact | execute within envelope |
| `medium` | reviewed source changes without deployment | execute only when allowed by policy and require artifact review |
| `high` | secrets, DNS, database mutation, production deployment, billing, rollback-sensitive changes | escalate; do not execute |

Existing `reputation`, `time_loss`, and `downtime_security_money` routing terms
must be translated or retired deliberately; they are not interchangeable with
the API risk tiers without a mapping decision.

## Review Semantics

These are separate controls and must not be conflated:

- `review_required`: the produced artifact requires human acceptance before it
  becomes canonical or ships.
- `execution_approval_required`: execution itself is blocked until explicit
  approval because it can create material risk.

A low-risk TBTX component specification may set `review_required: true` and
`execution_approval_required: false`.

## Security Boundary For The Proving Run

For the first real Hermes assignment:

- use a dedicated non-root worker identity when containerized;
- provide only the model credential and limited FAAS callback credential;
- provide no deployment, billing, DNS, or production database credentials;
- do not mount a host Docker socket;
- disable general terminal execution unless a separately reviewed sandbox
  boundary is implemented;
- retain worker output as evidence and log suspicious content rather than
  silently rewriting generated artifacts.

## First Real Proving Task

The first Hermes assignment should be useful but non-destructive:

```yaml
task_type: artifact_production
title: Produce TBTX Fog Diagnostic UI implementation specification
goal: >
  Using the attached canonical Fog Diagnostic questions and answer/scoring
  logic, produce an implementation specification and JSON data contract for
  the TBTX web rendering layer, including question navigation, validation,
  scoring transition, result-band display, and Fog Lift Kit CTA handoff.
preferred_owner: hermes
risk_tier: low
review_required: true
execution_approval_required: false
outputs:
  - runtime/artifacts/<task_id>/spec.md
  - runtime/artifacts/<task_id>/component.schema.json
```

The envelope must attach the canonical completed diagnostic logic; Hermes must
not infer it from a description alone.

## Implementation Gates

1. Correct current documentation and authority language.
2. Confirm canonical deployment host and staging role.
3. Implement or reconcile the Postgres-backed job APIs and risk/status model.
4. Add the Hermes adapter and worker service with idempotent claiming.
5. Execute the real proving task in staging.
6. Demonstrate replay returns existing artifacts without re-execution.
7. Review evidence before any production promotion.
