# FLOW_AGENT_OS_IMPLEMENTATION_PROMPT_PACK

## Status
Locked implementation prompt pack for FLOW Agent OS.

## Purpose
This prompt pack turns the locked FLOW Agent OS implementation spec into bounded execution prompts for ChatAgents, OpenClaw, Hermes, and Agent Zero.

Use these in order.

---

## 1. ChatAgents master implementation prompt

```text
Act as the lead implementation operator for FLOW Agent OS.

Your job is to turn the locked FLOW Agent OS implementation spec into an executable build plan across OpenClaw, Hermes, and Agent Zero.

This is not a brainstorm.
This is not a naming exercise.
This is not permission to redesign the whole ecosystem.
This is not permission to invent new components outside the locked spec.

Authority:
The locked source of truth is the FLOW Agent OS implementation spec.

Core truths:
- FLOW Agent OS is the Execution Engine
- One task, one owner, one return path
- OpenClaw = router + repo worker
- Hermes = learning-loop worker
- Agent Zero = high-risk executor
- Postgres = durable state
- Redis = hot queue state
- Canon outranks all workers

Your tasks:
1. convert the implementation spec into a phased build plan
2. define dependencies between phases
3. define what must exist before Hermes skill extraction can work
4. define what must exist before Agent Zero can safely act
5. define what OpenClaw should create first
6. define what should be built on Hostinger, Oracle, and GitHub Actions
7. end with:
   A. phase order
   B. exact next 5 actions
   C. worker assignments
   D. risks if sequence is violated

Hard rules:
- no new architecture
- no extra agents
- no Discord expansion
- no broad platform redesign
- no placeholder language
- no em dashes
- use plain operator-first language

Success condition:
The FLOW Agent OS build is broken into a realistic, ordered execution chain with bounded worker assignments.
```

---

## 2. OpenClaw setup prompt

```text
Perform a bounded FLOW Agent OS setup pass.

Authority:
Use the locked FLOW Agent OS implementation spec as the source of truth.

Your job:
Create or update the repo-facing documentation and schema scaffolding needed to support the Execution Engine.

Create or update only these surfaces if missing:
- FLOW_AGENT_OS/docs/EXECUTION_ENGINE_OVERVIEW.md
- FLOW_AGENT_OS/docs/RISK_ROUTING.md
- FLOW_AGENT_OS/docs/AGENT_ROLES.md
- FLOW_AGENT_OS/docs/TASK_ENVELOPES.md
- FLOW_AGENT_OS/docs/VALIDATION_AND_ROLLBACK.md
- FLOW_AGENT_OS/docs/MEMORY_POLICY.md
- FLOW_AGENT_OS/docs/SKILL_LOOP_SPEC.md
- FLOW_AGENT_OS/docs/QUEUE_HYGIENE.md
- FLOW_AGENT_OS/docs/POSITIONING.md
- FLOW_AGENT_OS/schemas/task_envelope.schema.json
- FLOW_AGENT_OS/schemas/job_record.schema.json
- FLOW_AGENT_OS/schemas/reflection_record.schema.json
- FLOW_AGENT_OS/schemas/skill_record.schema.json

Requirements:
1. Use only the locked terminology
2. Use:
   - System Architecture
   - Execution Engine
   - Context Architecture
   - WIN
   - Agent Roles
   - Capabilities
   - Principles
   - Profile
   - Context
   - Initialize
   - Cadence
3. Do not use deprecated terms
4. Keep all docs implementation-facing, not marketing-facing
5. Keep schemas minimal and useful

Hard rules:
- no commits
- no deploys
- no Discord work
- no new components outside the requested surfaces
- no canon edits
- no questions
- no placeholder nonsense

Reply only with:
- files created
- files updated
- schemas created
- any conflicts with existing files
```

---

## 3. OpenClaw queue and status prompt

```text
Perform a bounded queue and status hardening pass for FLOW Agent OS.

Authority:
Use the locked FLOW Agent OS implementation spec.

Your tasks:
1. create or update the queue/status documentation
2. define the allowed task statuses exactly as locked
3. define dead-letter behavior
4. define idempotency expectations
5. define retry rules
6. create or update:
   - FLOW_AGENT_OS/docs/QUEUE_HYGIENE.md
   - FLOW_AGENT_OS/runtime/reviews/README.md
   - FLOW_AGENT_OS/runtime/rollback/README.md
   - FLOW_AGENT_OS/runtime/logs/README.md

Allowed statuses:
- pending
- validated
- queued
- active
- review_required
- completed
- failed
- dead_letter
- blocked
- escalated
- archived

Hard rules:
- no new statuses
- no architecture drift
- no commits
- no deploys
- no questions

Reply only with:
- files created
- files updated
- retry rules documented
- dead-letter rules documented
```

---

## 4. Hermes skill-loop implementation prompt

```text
You are implementing the Hermes learning loop for FLOW Agent OS.

Authority:
Use the locked FLOW Agent OS implementation spec.

Your role:
Hermes is the learning-loop worker.
Your job is to turn reflections into reusable skills that can enrich future similar tasks.

Build only the minimal viable skill loop.

Your tasks:
1. define the reflection-to-skill extraction path
2. define the minimum skill record structure
3. define the skill confidence update logic
4. define the skill retrieval flow for new similar tasks
5. create or update:
   - FLOW_AGENT_OS/docs/SKILL_LOOP_SPEC.md
   - FLOW_AGENT_OS/prompts/HERMES_SKILL_EXTRACTION_PROMPT.md
   - FLOW_AGENT_OS/docs/MEMORY_POLICY.md

Minimum skill record fields:
- skill_id
- name
- task_type
- context_type
- pattern
- tool_sequence
- success_signal
- failure_signal
- confidence
- times_used
- last_used_at
- source_reflection_id
- status

Confidence rules:
- start at 0.5
- success with reuse: +0.1
- repeated success: +0.05
- failure on reuse: -0.15
- repeated failure: retire or mark low confidence
- cap between 0.0 and 1.0

Skill statuses:
- active
- low_confidence
- retired

Hard rules:
- do not invent a giant ML system
- do not overbuild
- do not change agent boundaries
- do not own canon
- do not create broad orchestration logic
- no commits
- no deploys
- no questions

Reply only with:
- files created
- files updated
- extraction flow documented
- retrieval flow documented
- confidence logic documented
```

---

## 5. Hermes recurring-workflow prompt

```text
You are extracting recurring workflow classes for Hermes.

Authority:
Use the locked FLOW Agent OS implementation spec.

Your job:
Identify the repeatable workflow categories Hermes should own and document them for future use.

Create or update:
- FLOW_AGENT_OS/docs/HERMES_RECURRING_WORKFLOWS.md

Document only workflow classes that fit Hermes:
- repetitive
- structured
- pattern-bearing
- improvable over time
- safe to enrich with prior skill records

Include:
1. workflow class name
2. input type
3. expected output
4. success signal
5. skill retrieval trigger
6. confidence update trigger

Do not include:
- broad one-off exploratory work
- canon decisions
- site strategy
- high-risk implementation

Hard rules:
- no drift
- no new agent roles
- no Discord
- no commits
- no deploys

Reply only with:
- files created
- workflow classes documented
```

---

## 6. Agent Zero control and review prompt

```text
You are implementing the control and review requirements for Agent Zero.

Authority:
Use the locked FLOW Agent OS implementation spec.

Your role:
Agent Zero is the high-risk executor.
It must not act without review artifacts.

Your tasks:
1. define the required pre-execution artifacts
2. define the required post-execution artifacts
3. define the exact review gate
4. create or update:
   - FLOW_AGENT_OS/docs/VALIDATION_AND_ROLLBACK.md
   - FLOW_AGENT_OS/prompts/AGENT_ZERO_EXECUTION_PROMPT.md
   - FLOW_AGENT_OS/runtime/reviews/README.md
   - FLOW_AGENT_OS/runtime/rollback/README.md

Required artifacts before action:
- task.diff
- task.review.md
- task.rollback.md

Requirements:
- no direct production mutation
- no canon edits
- no task invention
- no acting without approved envelope
- two-pass execution required

Hard rules:
- do not implement code changes here
- do not touch production
- do not expand into site strategy
- no commits
- no deploys
- no questions

Reply only with:
- files created
- files updated
- review gate documented
- rollback requirements documented
```

---

## 7. Agent Zero Hostinger prompt

```text
You are preparing the Hostinger control-plane role for FLOW Agent OS.

Authority:
Use the locked FLOW Agent OS implementation spec.

Your tasks:
1. document the Hostinger role as control plane
2. document what should remain on Hostinger
3. document what should not be added to Hostinger
4. create or update:
   - FLOW_AGENT_OS/docs/HOSTINGER_CONTROL_PLANE.md

Hostinger should include:
- Agent Zero
- Redis broker
- Postgres
- hermes-control API
- Traefik
- webhook endpoints
- callback handlers
- minimal review artifacts

Hostinger should not become:
- a dumping ground
- a second canon
- a broad experiment surface
- a competing site deployment authority

Hard rules:
- no new services beyond the locked spec
- no production deploy actions
- no Discord addition
- no questions

Reply only with:
- files created
- files updated
- control-plane rules documented
```

---

## 8. Hermes Oracle prompt

```text
You are preparing the Oracle Always Free role for FLOW Agent OS.

Authority:
Use the locked FLOW Agent OS implementation spec.

Your tasks:
1. document the Oracle role as Hermes worker surface
2. define what Hermes runs there
3. define what Hermes must not own there
4. create or update:
   - FLOW_AGENT_OS/docs/ORACLE_HERMES_WORKER.md

Oracle should run:
- Hermes worker
- skill extraction jobs
- skill retrieval jobs
- repetitive structured jobs

Oracle should not run:
- canon
- routing
- top-level state
- authority
- broad orchestration

Hard rules:
- no new surfaces
- no deployment actions
- no questions

Reply only with:
- files created
- files updated
- worker boundaries documented
```

---

## 9. OpenClaw GitHub Actions prompt

```text
You are preparing the GitHub Actions role for FLOW Agent OS.

Authority:
Use the locked FLOW Agent OS implementation spec.

Your tasks:
1. define the exact repo-native jobs OpenClaw may run in GitHub Actions
2. define what it must never do there
3. create or update:
   - FLOW_AGENT_OS/docs/GITHUB_ACTIONS_OPENCLAW.md
   - FLOW_AGENT_OS/prompts/OPENCLAW_EXECUTION_PROMPT.md

Allowed OpenClaw Actions work:
- file classification
- markdown generation
- rewrite jobs
- content prep
- file transforms
- schema checks
- event-driven build helpers

Not allowed:
- long-running orchestration
- persistent state
- canon authority
- strategy
- broad planning

Hard rules:
- no commits
- no deploys
- no new architecture
- no questions

Reply only with:
- files created
- files updated
- allowed job types documented
```

---

## 10. Database spec prompt

```text
Create the database implementation spec for FLOW Agent OS durable state.

Authority:
Use the locked FLOW Agent OS implementation spec.

Your tasks:
1. define the Postgres-backed records required
2. define the purpose of each table
3. create:
   - FLOW_AGENT_OS/docs/POSTGRES_STATE_SPEC.md

Required tables:
- job_records
- reflection_records
- skill_records

For each table include:
- table purpose
- required fields
- field meanings
- relationships
- when records are created
- when records are updated

Hard rules:
- no extra tables unless absolutely necessary
- no speculative analytics tables
- no drift
- no questions

Reply only with:
- files created
- tables documented
- relationships documented
```

---

## 11. Health and failure prompt

```text
Create the health, failure, and dead-letter implementation spec for FLOW Agent OS.

Authority:
Use the locked FLOW Agent OS implementation spec.

Your tasks:
1. define required health checks
2. define failure states
3. define dead-letter behavior
4. define explicit retry behavior
5. create:
   - FLOW_AGENT_OS/docs/HEALTH_AND_FAILURE_SPEC.md

Required health surfaces:
- hermes-control /health
- Redis connectivity
- Postgres connectivity
- callback reachability
- worker liveness

Required failure controls:
- failed state
- dead_letter state
- explicit retry only
- preserve payload and logs
- no silent retry loops

Hard rules:
- no extra architecture
- no vague monitoring language
- no questions

Reply only with:
- files created
- health checks documented
- failure rules documented
- dead-letter rules documented
```

---

## 12. Final ChatAgents synthesis prompt

```text
Act as the final synthesis operator for FLOW Agent OS implementation.

Authority:
Use the locked FLOW Agent OS implementation spec and all generated docs created by OpenClaw, Hermes, and Agent Zero prompts.

Your tasks:
1. assess whether the spec has been fully translated into implementable docs
2. identify any missing critical gap
3. produce:
   - FLOW_AGENT_OS/docs/IMPLEMENTATION_CHECKLIST.md
   - FLOW_AGENT_OS/docs/NEXT_WIN.md

IMPLEMENTATION_CHECKLIST.md must include:
- required docs present
- schemas present
- durable state spec present
- skill-loop spec present
- routing rules present
- review gate present
- health/failure spec present

NEXT_WIN.md must define only one next implementation target.

Rules:
- no new strategy
- no architecture changes
- no expansion
- one next WIN only
- no questions

Reply only with:
- files created
- files updated
- missing gaps if any
- next WIN selected
```

---

## Exact Run Order

Run them in this order:

1. ChatAgents master implementation prompt  
2. OpenClaw setup prompt  
3. OpenClaw queue and status prompt  
4. Database spec prompt  
5. Hermes skill-loop implementation prompt  
6. Hermes recurring-workflow prompt  
7. Agent Zero control and review prompt  
8. Agent Zero Hostinger prompt  
9. Hermes Oracle prompt  
10. OpenClaw GitHub Actions prompt  
11. Health and failure prompt  
12. Final ChatAgents synthesis prompt  

---

## Locked Role Split

- **ChatAgents** = phase planning, synthesis, checklist, next WIN
- **OpenClaw** = docs, schemas, queue rules, GitHub Actions role
- **Hermes** = skill loop, recurring workflow classes
- **Agent Zero** = control, rollback, review gate, Hostinger execution boundary
- **You** = approval gate

---

## Operator Note

Do not let any one worker own the whole implementation.

The correct path is:
1. lock docs and schemas
2. lock durable state
3. lock skill loop
4. lock review gate
5. lock worker surfaces
6. lock health/failure
7. synthesize
8. choose next WIN

That closes the loop and keeps the system governed.
