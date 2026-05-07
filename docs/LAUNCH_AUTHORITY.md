# Launch Authority

## Purpose

This document is the operating source of truth for FLOW/FAAS launch authority, branch policy, merge expectations, and deploy ownership.

## Current Launch Mode

- Launch mode: bounded production-prep workstream until all full-power launch gates are green.
- Primary governed system: FLOW Agent Architected Schemas (FAAS).
- Functional control plane: Execution Engine.
- Operator authority: Erik.

## Branch And Merge Policy

- Production branch: `main`.
- Confirmed `main` tracks:
  - 424: `main`
  - 425: `main`
- PR approvals: not required.
- Default merge path: feature branch -> PR -> passing checks -> merge to `main`.
- Direct `main` changes: allowed only for urgent operator-approved fixes or documentation-only corrections where the risk is clearly low.
- Required before merge/deploy:
  - working tree diff is reviewed by the operator or implementing agent
  - relevant tests, smoke checks, or documentation verification are recorded
  - rollback path is known for state-changing work

## Deployment Authority

| Property | Production branch | Deploy target | Deployment owner | Status |
|---|---|---|---|---|
| FLOW/FAAS control plane | `main` | Hostinger/VPS path TBD | Erik | Branch confirmed; deploy target needs final host/path confirmation |
| TransformBy10X | `main` for confirmed 424/425 track if applicable | TBD | Erik | Repo audit still blocked from this environment |
| BizBuilders AI | TBD | TBD | Erik | Domain/repo authority unresolved |
| BizBot Mktng | TBD | TBD | Erik | Domain/repo authority unresolved |

## Risk Rules

- High-risk changes include deployment, DNS, secrets, payments, production data, auth, and infrastructure config.
- High-risk changes require an explicit task record, rollback notes, and operator approval before production execution.
- PR approval by another reviewer is optional, but passing checks and clear rollback remain expected for production-impacting work.

## Open Decisions

- Final deploy target and host path for FLOW/FAAS.
- Whether TransformBy10X, BizBuilders AI, and BizBot Mktng live in one repo or separate repos.
- DNS provider and record ownership.
- Payment provider, product IDs, fulfillment destinations.
- CRM and analytics destinations.
- Legal entity and approved policy URLs/text.

