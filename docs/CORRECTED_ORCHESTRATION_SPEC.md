# CORRECTED_ORCHESTRATION_SPEC

## Status
Locked operating spec for the current constrained infrastructure phase.

## Purpose
This document defines the corrected orchestration model for FLOW Agent OS under current budget and infrastructure constraints.

Its purpose is to:
- reduce burden
- reduce drift
- preserve role clarity
- prevent parallel truths
- keep execution bounded
- support production-ready work without overextending infrastructure

---

## 1. Core Rule

**One task, one owner, one return path.**

All work must route through a controlled task envelope.

Rules:
- agents receive task envelopes only
- agents do not contact each other directly
- work is routed by task type and risk tier
- no agent expands scope beyond the assigned goal
- every task must have one owner
- every task must return to a known review surface

---

## 2. Control Model

### Hostinger
Hostinger is the **control plane**.

Keep on Hostinger:
- Agent Zero
- Redis broker
- Postgres
- hermes-control / coordinator API
- Traefik
- webhook endpoints
- callback handlers
- minimal logs and review artifacts

Hostinger should not become a bloated multi-purpose sandbox.

### Oracle Always Free
Oracle Always Free is the **Hermes worker surface**.

Run on Oracle:
- Hermes worker process
- repetitive structured jobs
- skill retrieval and execution tasks
- recurring workflow tasks that benefit from compounding

Do not use Oracle for:
- canon
- top-level routing
- source-of-truth storage
- authority decisions
- broad orchestration

### GitHub Actions
GitHub Actions is the **OpenClaw repo-work surface**.

Run in GitHub Actions:
- file classification passes
- markdown generation
- rewrite jobs
- repo content prep
- schema checks
- event-driven build helpers
- bounded documentation transforms

Do not use GitHub Actions for:
- long-running orchestration
- authority
- persistent state
- freeform planning
- strategy
- canon definition

### Cloudflare Workers
Cloudflare Workers is the **thin edge/router** if needed.

Use it for:
- webhook intake
- simple routing
- auth gating
- forwarding requests

Do not use it for:
- memory
- authority
- heavy orchestration
- task ownership
- business logic sprawl

### Discord
Discord is **delayed**.

It is not the current front door.
It should not be treated as trusted until stability is proven and prior crash-loop concerns are fully resolved.

---

## 3. Agent Role Boundaries

### OpenClaw
Role:
**Router + repo worker**

OpenClaw owns:
- envelope validation
- dispatch by task type and risk tier
- repo-native work
- file transforms
- classification passes
- rewrite passes
- content prep
- bounded documentation work

OpenClaw does not own:
- canon
- strategy
- deployment authority
- long-term learning
- product direction

### Hermes
Role:
**Learning-loop worker**

Hermes owns:
- repetitive structured tasks
- skill extraction
- skill refinement
- recurring task classes
- repeated workflows that benefit from compounding
- user-model-aware repeated outputs if explicitly bounded

Hermes does not own:
- canon
- top-level routing
- broad one-off tool work
- brand strategy
- site direction

### Agent Zero
Role:
**High-risk executor**

Agent Zero owns:
- reviewed code changes
- file I/O
- browser and API tasks
- approved infra-sensitive work
- diff artifacts
- rollback artifacts
- review artifacts
- controlled implementation

Agent Zero does not own:
- intake
- task invention
- canon
- broad orchestration
- brand direction

### You
Role:
**Approval gate**

You own:
- canon
- priorities
- final approval for review-tier work
- production go / no-go
- architecture decisions
- offer boundaries
- site direction

---

## 4. What Runs Where

### Hostinger
Purpose:
Control plane

Allowed work:
- broker
- persistence
- coordination
- Agent Zero
- callback handling
- minimal review artifacts

Not allowed:
- uncontrolled service sprawl
- broad background experimentation
- parallel authority surfaces

### Oracle Always Free
Purpose:
Hermes worker execution

Allowed work:
- repetitive structured tasks
- skill-based execution
- recurring worker jobs

Not allowed:
- routing
- canon
- top-level state
- authority

### GitHub Actions
Purpose:
OpenClaw repo-native execution

Allowed work:
- classification
- rewrites
- content prep
- file transforms
- documentation passes

Not allowed:
- long-running orchestration
- persistent state
- canon
- strategy

### Cloudflare Workers
Purpose:
Edge routing

Allowed work:
- webhook forwarding
- intake routing
- thin logic
- basic auth gating

Not allowed:
- authority
- memory
- orchestration sprawl

### Discord
Purpose:
future front door only after stability

Allowed work:
- nothing critical yet

Not allowed:
- primary intake
- trusted command surface
- control-plane responsibility

---

## 5. Keep / Change / Delay

### Keep
- Agent Zero on Hostinger
- Redis and Postgres on Hostinger
- Hermes worker on Oracle
- OpenClaw repo work on GitHub Actions
- Cloudflare as thin edge/router if needed
- task envelope discipline
- risk-tier routing
- artifact and log discipline

### Change
- reframe Hostinger as the control plane, not the everything-box
- make OpenClaw in GitHub Actions repo-only
- make Hermes worker-only
- require Postgres-backed job persistence
- require review artifacts before Agent Zero touches live code or infra

### Delay
- Discord bot sidecar
- any official front-door promotion
- extra UI surfaces
- anything that expands input surfaces before canon and build flow are locked

---

## 6. Governance Additions Required

### A. Job Persistence
Use Postgres-backed job records.

Redis alone is not enough because restart loses state.

Every job should have:
- job_id
- owner
- source
- status
- created_at
- updated_at
- retry_count
- result_pointer
- review_pointer if applicable

### B. Health Checks
Add explicit health checks.

Minimum:
- hermes-control `/health`
- worker liveness checks
- callback reachability checks
- Redis connectivity checks
- Postgres connectivity checks

### C. Secret Rotation
Rotate shared secrets and worker secrets on a schedule.
Do not leave static secrets in place indefinitely.

### D. Idempotency
All jobs must be safe to replay once.

Callbacks, retries, and reruns must not duplicate outputs or corrupt state.

### E. Dead-Letter / Timeout Rules
If Hermes or GitHub Actions fails:
- mark failed
- retain payload
- require explicit retry
- do not silently loop
- preserve the review path

---

## 7. Routing Rules

### Low / Medium Risk
Preferred owner:
- OpenClaw
- Hermes if repetitive and structured

Typical task types:
- file classification
- markdown generation
- rewrite passes
- repo content prep
- repeated bounded workflows

### High Risk
Preferred owner:
- Agent Zero

Typical task types:
- repo implementation after approval
- code changes
- file mutations with rollback requirement
- infra-sensitive changes
- approved execution against live systems

### Rule
No task may be owned by more than one agent at the same time.

---

## 8. Review Requirements

### Before Agent Zero acts
The following must exist:
- approved task envelope
- clear owner
- clear target files or systems
- `task.diff`
- `task.review.md`
- `task.rollback.md`

### Before production-related work
The following must exist:
- canon alignment confirmed
- source files approved
- design direction approved
- rollback path defined

---

## 9. Production Governance

### Source-Control Authority
GitHub is the source-control authority.

Rules:
- no direct main-branch mutation
- feature branch first
- review before merge
- no production-by-chat

### Deployment Authority
For this repo, deployment authority is the existing Docker + Hostinger runtime path, not Vercel.

Rules:
- Hostinger runs orchestration surfaces
- GitHub Actions supports bounded repo-native work
- no parallel deploy truth

### Legacy Rule
Do not allow multiple surfaces to become competing production authorities for the same runtime behavior.

---

## 10. Canon and Authority

Canon lives above all worker behavior.

Authority is defined by:
- `_OS/02-Canon/CANONICAL_SOURCE_OF_TRUTH.md`
- `_OS/02-Canon/SYSTEM_ARCHITECTURE.md`
- `_OS/02-Canon/OPERATING_LOOP.md`
- `_OS/02-Canon/BRAND_ROLES.md`
- `_OS/02-Canon/OFFER_PATH.md`
- `_OS/02-Canon/NAMING_GLOSSARY.md`
- `_OS/02-Canon/ANTI_DRIFT_RULES.md`

Rule:
If any local file or worker output conflicts with canon, canon wins.

No agent defines canon.

---

## 11. Current Priority Order

### First
Lock canon and implementation direction.

### Second
Use OpenClaw for:
- classification
- rewrite queues
- repo content prep

### Third
Use Hermes for:
- reusable repeated workflow patterns
- learning-loop extraction after approved work exists

### Fourth
Use Agent Zero for:
- controlled implementation
- reviewed higher-risk actions only

### Fifth
Add new front-door surfaces only after the above is stable.

---

## 12. Exact Next 5 Actions

1. Save this corrected orchestration spec as the locked operating document.
2. Add Postgres-backed job persistence.
3. Add hermes-control health checks.
4. Move OpenClaw repo-native jobs into GitHub Actions.
5. Keep Discord delayed until the system is stable and the current build path is working.

---

## 13. Settled Operating Truth

**Hostinger is the control plane. Oracle runs Hermes worker jobs. GitHub Actions runs OpenClaw repo jobs. Agent Zero handles approved high-risk execution. Discord stays delayed until stable.**

This is the corrected orchestration model.
Everything else is subordinate to that.
