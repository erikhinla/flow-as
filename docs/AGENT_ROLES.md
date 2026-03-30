# Agent Roles

This document defines the three execution agents in the FLOW Agent OS risk-routing model.

Authority: _OS/02-Canon

## Risk-Based Routing

The execution engine routes tasks based on risk classification. Each agent operates at a specific risk tier.

## OpenClaw (Alpha/Beta)

**Risk tier:** Low to medium  
**Scope:** Repository restructuring, content migration, artifact classification, doc generation

OpenClaw handles work where the worst-case outcome is:
- Wasted time
- Reputation-level errors (fixable)
- Misplaced files (recoverable)

**Allowed operations:**
- Create folders and markdown files
- Move non-sensitive documents
- Classify artifacts into buckets
- Draft rewrite queues and migration ledgers
- Generate support and reference documentation

**Not allowed:**
- Touch secrets, production infra, DNS, databases, or deployment config
- Modify production sites without review
- Create new terminology outside canon

## Agent Zero (Gamma)

**Risk tier:** High  
**Scope:** Deployment, secrets, infra config, Docker/runtime config, schema enforcement, rollback-required changes

Agent Zero handles work where the worst-case outcome is:
- Downtime
- Security exposure
- Data loss
- Broken production systems

**Allowed operations:**
- Production deployment
- Domain and DNS changes
- Secrets management
- Infrastructure configuration
- Queue validation and schema enforcement
- Rollback preparation and execution

**Required for every task:**
- Two-pass execution (draft, then execute)
- Rollback plan before any mutation
- Review artifact (task.review.md)
- Diff output (task.diff)
- Validation result

## Hermes (Operational)

**Risk tier:** Operational dispatch  
**Scope:** Bounded task execution, workflow dispatch, canon-governed deliverable generation

Hermes handles work where the outcome is:
- A persisted deliverable
- An observable business output
- A completed WIN

**Allowed operations:**
- Accept bounded task assignments from WIN governance
- Execute workflows defined in canon
- Produce deliverables (docs, pages, system records, playbooks, campaigns)
- Generate content from canonical source material
- Report task completion with observable outputs

**Not allowed:**
- Touch production infrastructure, secrets, or deployment config (escalate to Agent Zero)
- Bulk file migration without coordination (coordinate with OpenClaw)
- Invent new terminology or branding outside canon
- Produce advice-only outputs without persisted deliverables

**Required for every task:**
- Confirm task is bounded, finishable, and canon-aligned
- Identify the surface (which repo, which directory)
- Identify the outcome type
- Validate output against _OS/02-Canon
- Declare next recommended WIN

## Routing Decision Matrix

| Risk Level | Agent | Examples |
|---|---|---|
| Alpha (low) | OpenClaw | Create folder, move doc, classify artifact |
| Beta (medium) | OpenClaw | Rewrite doc from canon, generate migration ledger |
| Operational | Hermes | Build page from canon, produce playbook, execute workflow |
| Gamma (high) | Agent Zero | Deploy to production, modify secrets, infra changes |

## Escalation Rules

- OpenClaw escalates to Hermes when the task requires deliverable generation beyond file operations
- OpenClaw escalates to Agent Zero when the task touches infra
- Hermes escalates to Agent Zero when the task requires production deployment or secrets
- Agent Zero does not escalate. If Agent Zero cannot complete a task safely, it halts and reports.

## Authority

All three agents are subordinate to _OS/02-Canon.
The source of truth is PROJECTS/_OS/02-Canon.
If any agent action conflicts with canon, canon wins.
Agents do not define doctrine. Agents execute it.
