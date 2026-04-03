# FLOW_AGENT_OS_IMPLEMENTATION_SPEC

## Status
Locked implementation spec for FLOW Agent OS.

## Purpose
FLOW Agent OS is the governed execution system behind the TransformBy10X ecosystem.

Its job is to:
- receive structured work
- route it to the correct owner
- execute safely
- preserve reflections
- extract reusable skills
- improve future execution through recursive learning

It is not the umbrella thesis.
It is the **Execution Engine**.

---

## 1. Core Operating Rule

**One task, one owner, one return path.**

Every task must:
- enter through a task envelope
- have one assigned owner
- produce one observable output
- write one reflection
- return to one review surface

No agent talks directly to another agent.
No agent invents side quests.
No work runs without a task envelope.

---

## 2. FLOW Operating Loop

**Input → WIN → Execution → Output → Reflection → Skill Extraction → Skill Index Update → Next Input**

### Input
A request, problem, file, goal, constraint, or trigger enters the system.

### WIN
The system identifies the one finishable action that matters now.

### Execution
The task is routed to the correct owner and completed.

### Output
A real artifact or state change is produced.

### Reflection
The system records what worked, what failed, and what was learned.

### Skill Extraction
Hermes checks whether the reflection contains a reusable pattern.

### Skill Index Update
If yes, the skill is stored or updated in the queryable skill index.

### Next Input
Future similar work is enriched by skill retrieval before execution starts.

That is the recursive learning loop.

---

## 3. Role Boundaries

### OpenClaw
**Role:** Router + repo worker

#### Owns
- task envelope validation
- routing by task type and risk tier
- repo-native work
- markdown generation
- classification
- rewrite passes
- content prep
- file transforms

#### Does not own
- canon
- strategy
- deployment authority
- long-term learning
- site direction

### Hermes
**Role:** Learning-loop worker

#### Owns
- reflection analysis
- skill extraction
- skill refinement
- recurring task classes
- repeated workflows that benefit from compounding
- skill retrieval for similar future tasks

#### Does not own
- top-level routing
- canon
- broad one-off tool work
- site strategy
- production deployment

### Agent Zero
**Role:** High-risk executor

#### Owns
- reviewed code changes
- file I/O
- browser/API tasks
- approved infra-sensitive work
- diff artifacts
- rollback artifacts
- review artifacts
- controlled implementation

#### Does not own
- intake
- task invention
- canon
- broad orchestration
- brand direction

### You
**Role:** Approval gate

#### Owns
- canon
- priorities
- final approval
- production go / no-go
- architecture decisions
- offer boundaries
- site direction

---

## 4. What Runs Where

### Hostinger
**Purpose:** Control plane

#### Runs
- Agent Zero
- Redis broker
- Postgres
- hermes-control API
- Traefik
- webhook endpoints
- callback handlers
- review artifacts
- minimal logs

### Oracle Always Free
**Purpose:** Hermes worker execution

#### Runs
- Hermes worker
- skill extraction jobs
- skill retrieval jobs
- repetitive structured jobs

### GitHub Actions
**Purpose:** OpenClaw repo-native execution

#### Runs
- classification jobs
- rewrite jobs
- markdown generation
- content prep
- repo transforms
- schema checks

### Cloudflare Workers
**Purpose:** Thin edge/router if needed

#### Runs
- webhook forwarding
- thin intake routing
- auth gating

### Discord
**Status:** delayed

Not trusted until stable.

---

## 5. Required System Components

### A. Task envelope
Every task must use this structure:

```json
{
  "task_id": "uuid",
  "created_at": "iso8601",
  "source": "manual|webhook|github_action|scheduled",
  "title": "short imperative task title",
  "goal": "single finishable outcome",
  "task_type": "classification|rewrite|content_prep|implementation|skill_extraction|healthcheck",
  "risk_tier": "low|medium|high",
  "preferred_owner": "openclaw|hermes|agent_zero",
  "inputs": {
    "files": [],
    "notes": "",
    "context_refs": []
  },
  "output_required": "observable artifact or state change",
  "review_required": true,
  "rollback_required": false,
  "status": "pending"
}
```

### B. Job records
Store in Postgres, not Redis only.

#### `job_records`
- `job_id`
- `task_id`
- `source`
- `owner`
- `status`
- `task_type`
- `risk_tier`
- `created_at`
- `updated_at`
- `started_at`
- `completed_at`
- `result_pointer`
- `review_pointer`
- `rollback_pointer`
- `retry_count`
- `error_message`

### C. Reflection records

#### `reflection_records`
- `reflection_id`
- `task_id`
- `job_id`
- `owner`
- `what_worked`
- `what_failed`
- `pattern_observed`
- `context_type`
- `tool_sequence`
- `success_signal`
- `failure_signal`
- `skills_used`
- `skill_helped`
- `created_at`

### D. Skill index

#### `skill_records`
- `skill_id`
- `name`
- `task_type`
- `context_type`
- `pattern`
- `tool_sequence`
- `success_signal`
- `failure_signal`
- `confidence`
- `times_used`
- `last_used_at`
- `source_reflection_id`
- `status`

---

## 6. Status Model

Allowed statuses:
- `pending`
- `validated`
- `queued`
- `active`
- `review_required`
- `completed`
- `failed`
- `dead_letter`
- `blocked`
- `escalated`
- `archived`

### Rules
- every task starts as `pending`
- OpenClaw validates before routing
- no task jumps directly to `completed`
- any repeated failure becomes `dead_letter`
- high-risk tasks require `review_required` before completion is final
- legacy status migration must be explicit before cutover

---

## 7. Routing Rules

### OpenClaw gets
- classification
- markdown generation
- rewrite passes
- repo content prep
- file transforms
- source mapping

### Hermes gets
- reflection analysis
- skill extraction
- skill retrieval
- recurring structured tasks
- repeated workflow classes

### Agent Zero gets
- approved implementation
- reviewed code changes
- browser/API tasks
- infra-sensitive actions
- rollback-required work

### Routing rule
No task may be owned by more than one agent at once.

---

## 8. Hermes Skill Loop

This is the missing loop that closes recursive learning.

### Current bad state
execute → reflect → store

### Required state
execute → reflect → extract skill → index skill → retrieve on next similar task → enrich execution → update confidence

### Hermes skill-loop steps

#### Step 1. Task completes
The owner returns output and reflection.

#### Step 2. Reflection is written
Reflection must include:
- what worked
- what failed
- pattern observed
- context type
- tool sequence
- success/failure signal
- skills_used
- skill_helped

#### Step 3. Skill extraction check
Hermes evaluates:
- is there a reusable pattern here?
- is the pattern tied to a repeatable task type?
- was the output successful enough to store?
- is this net-new or an update to an existing skill?

#### Step 4. Skill record created or updated
If reusable:
- create new skill if none exists
- update existing skill if similar one exists

#### Step 5. Skill indexed
Skill becomes queryable by:
- task type
- context type
- keywords
- prior success confidence

#### Step 6. Next similar task arrives
Before execution, Hermes queries:
- similar task type
- similar context type
- related prior patterns

#### Step 7. Execution context enriched
Matching skills are inserted into the task context.
Thread metadata is the preferred skill-context carrier when a thread model exists.

#### Step 8. Confidence updated
After the task finishes:
- raise confidence if skill helped
- lower confidence if skill failed
- retire skill if repeatedly wrong

---

## 9. Minimal Hermes Extraction Logic

A reflection qualifies for skill extraction if all are true:
- task type is repeatable
- success signal is observable
- pattern is clear enough to reuse
- tool sequence is identifiable
- output is not a one-off accident

### Confidence model
Start at `0.5`

Then:
- success with reuse: `+0.1`
- repeated success: `+0.05`
- failure on reuse: `-0.15`
- repeated failure: retire or mark low confidence

Cap between `0.0` and `1.0`

### Skill status
- `active`
- `low_confidence`
- `retired`

### Retrieval behavior
- retrieve top 3 matching skills
- any skill below `0.4` confidence is treated as `experimental`
- experimental skills may inform context but must not dominate execution

---

## 10. File and Folder Structure

```text
FLOW_AGENT_OS/
├── docs/
│   ├── EXECUTION_ENGINE_OVERVIEW.md
│   ├── RISK_ROUTING.md
│   ├── AGENT_ROLES.md
│   ├── TASK_ENVELOPES.md
│   ├── VALIDATION_AND_ROLLBACK.md
│   ├── MEMORY_POLICY.md
│   ├── SKILL_LOOP_SPEC.md
│   ├── QUEUE_HYGIENE.md
│   └── POSITIONING.md
│
├── runtime/
│   ├── queues/
│   │   ├── pending/
│   │   ├── active/
│   │   ├── completed/
│   │   ├── escalated/
│   │   └── archive/
│   ├── tasks/
│   ├── reviews/
│   ├── rollback/
│   └── logs/
│
├── schemas/
│   ├── task_envelope.schema.json
│   ├── job_record.schema.json
│   ├── reflection_record.schema.json
│   └── skill_record.schema.json
│
├── prompts/
│   ├── OPENCLAW_EXECUTION_PROMPT.md
│   ├── HERMES_SKILL_EXTRACTION_PROMPT.md
│   └── AGENT_ZERO_EXECUTION_PROMPT.md
│
├── services/
│   ├── hermes-control/
│   ├── hermes-worker/
│   ├── openclaw-router/
│   └── callbacks/
│
└── archive/
```

---

## 11. Governance Requirements

### A. Postgres-backed persistence
Required now.

Redis is hot-state only.
Postgres is durable state.

### B. Idempotency
All callbacks and retries must be safe to replay once.

### C. Dead-letter logic
After repeated failure:
- mark `dead_letter`
- preserve payload
- do not loop forever
- require explicit retry

### D. Health checks
Minimum:
- hermes-control `/health`
- Redis connectivity
- Postgres connectivity
- callback reachability
- worker liveness

### E. Secret rotation
Worker and callback secrets must rotate on a schedule.

### F. Intake control
All intake paths must POST into the governed registry flow.
No flat JSON side path may bypass task records.

### G. Handoff control
The handoff endpoint is the only legal cross-agent communication path.

---

## 12. Review Artifacts

Before Agent Zero acts, these must exist:
- `task.diff`
- `task.review.md`
- `task.rollback.md`

No reviewed implementation without all three.

Agent Zero execution must be technically blocked when they are missing.

---

## 13. Production Governance

### GitHub
Source-control authority

Rules:
- feature branch first
- no direct main mutation
- review before merge

### Runtime
This repo deploys through the existing Docker + Hostinger path.
GitHub Actions supports bounded repo-native jobs.

### Hostinger
Control plane only for orchestration.
Not a competing site authority.

---

## 14. Canon Rule

Canon outranks all workers.

Authority is defined by:
- `_OS/02-Canon/CANONICAL_SOURCE_OF_TRUTH.md`
- `_OS/02-Canon/SYSTEM_ARCHITECTURE.md`
- `_OS/02-Canon/OPERATING_LOOP.md`
- `_OS/02-Canon/BRAND_ROLES.md`
- `_OS/02-Canon/OFFER_PATH.md`
- `_OS/02-Canon/NAMING_GLOSSARY.md`
- `_OS/02-Canon/ANTI_DRIFT_RULES.md`

If worker output conflicts with canon, canon wins.

---

## 15. Exact Next Implementation Order

### Phase 1
Lock this spec as authority.

### Phase 2
Implement durable state:
1. Postgres `job_records`
2. Postgres `reflection_records`
3. Postgres `skill_records`

### Phase 3
Implement Hermes skill loop:
4. reflection write endpoint
5. skill extraction worker
6. skill index query path
7. confidence update logic

### Phase 4
Implement routing hardening:
8. envelope validation
9. owner routing rules
10. dead-letter logic
11. idempotency keys
12. handoff endpoint enforcement

### Phase 5
Implement review controls:
13. diff/review/rollback artifact enforcement for Agent Zero

### Phase 6
Move bounded execution:
14. OpenClaw repo jobs into GitHub Actions
15. Hermes worker to Oracle
16. keep Agent Zero on Hostinger

---

## 16. Definition of Done

FLOW Agent OS is implemented when:
- tasks are envelope-driven
- every task has one owner
- durable job state exists in Postgres
- reflections are written for completed tasks
- Hermes extracts reusable skills
- skill retrieval enriches future similar tasks
- confidence updates over time
- failed jobs route to dead-letter instead of looping forever
- Agent Zero cannot act without review artifacts
- OpenClaw is bounded to repo-native work
- Discord is not required for the system to function

---

## 17. Settled Operating Truth

**FLOW Agent OS is the Execution Engine. OpenClaw routes and handles repo work. Hermes turns reflections into reusable skills. Agent Zero executes approved high-risk work. Postgres holds durable state. Redis handles hot queue state. The system learns only when memory feeds back into future execution.**

---

## 18. Next WIN

**Implement Postgres job persistence, reflection records, and Hermes skill extraction before adding any new surfaces.**

That closes the loop.
