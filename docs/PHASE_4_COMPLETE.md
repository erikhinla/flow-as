# Phase 4 Complete: OpenClaw Envelope Validation + Routing ✓

**Commit:** `2107daa`  
**Date:** 2026-04-03

---

## What Was Built

### Task Intake Pipeline

**Flow:**
```
POST /intake/task (envelope)
       ↓
Schema validation (JSON schema)
       ↓
Business rules (high-risk requires review, goal specific, etc.)
       ↓
Owner determination (by task_type or preferred_owner)
       ↓
Job record creation (Postgres job_records)
       ↓
Queue enqueue (Redis {owner}:jobs)
       ↓
Response: accepted {job_id, owner, queue} or rejected {error}
```

### 1. EnvelopeValidationService

Validates and routes task envelopes:

**Validation:**
- Schema: JSON schema compliance against `/schemas/task_envelope.schema.json`
- Business rules: governance enforcement (high-risk review, specific goals, valid owners)

**Routing:**
- Determine owner by task_type or preferred_owner
- Create durable job_record in Postgres with status=VALIDATED

**Routing table:**
```
classification → openclaw
rewrite → openclaw
content_prep → openclaw
implementation → agent_zero
skill_extraction → hermes
healthcheck → hermes
```

### 2. RedisQueueService

FIFO job queue management:

**Queues:**
- `flow:openclaw:jobs` — Jobs waiting for OpenClaw
- `flow:hermes:jobs` — Jobs waiting for Hermes
- `flow:agent_zero:jobs` — Jobs waiting for Agent Zero
- `flow:dead_letter` — Failed/abandoned jobs

**Operations:**
- `enqueue_job(owner, job_id)` — Add to queue
- `dequeue_job(owner, timeout)` — Pop from queue (blocking)
- `get_queue_depth(owner)` — Current size
- `get_all_queue_depths()` — All owner depths
- `move_to_dlq(job_id, reason)` — Send to dead-letter
- `get_dlq(count)` — Inspect failed jobs
- `healthcheck()` — Verify Redis connectivity

### 3. OpenClaw Intake API

REST endpoints for task intake:

```
POST   /v1/intake/task          — Accept task envelope
GET    /v1/intake/status        — Intake service health
GET    /v1/intake/queues/status — All queue depths
GET    /v1/intake/dlq           — Dead-letter queue
POST   /v1/intake/queues/clear  — Emergency clear (admin)
```

---

## Job Lifecycle

```
PENDING (arrival) → VALIDATED (schema pass) → QUEUED (Redis) → ACTIVE (worker)
```

**Status flow:**
- Envelope received: PENDING
- Validation passes: VALIDATED
- Enqueued to Redis: QUEUED
- Worker picks up: ACTIVE
- Completes: COMPLETED or FAILED

---

## Governance Rules

### Rule 1: High-Risk Requires Review
```
if risk_tier == 'high' and not review_required:
    reject("High-risk task missing review_required=true")
```

### Rule 2: Goal Must Be Observable
```
if len(goal) < 10 or not goal.is_specific():
    reject("Goal too vague. Must be observable and specific.")
```

### Rule 3: Owner Must Be Valid
```
if preferred_owner not in ['openclaw', 'hermes', 'agent_zero']:
    reject("Invalid preferred_owner")
```

### Rule 4: Task Type Must Be Supported
```
if task_type not in VALID_TASK_TYPES:
    reject("Invalid task_type")
```

---

## API Example

### Accept a task

```bash
curl -X POST http://localhost:8000/v1/intake/task \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task-123",
    "created_at": "2026-04-03T12:00:00Z",
    "source": "webhook",
    "title": "Classify submissions",
    "goal": "Classify all intake submissions by type with 95%+ accuracy",
    "task_type": "classification",
    "risk_tier": "low",
    "output_required": "JSON with classifications",
    "review_required": false,
    "inputs": {
      "files": ["sub1.json", "sub2.json"]
    }
  }'
```

Response:
```json
{
  "status": "accepted",
  "job_id": "task-123",
  "owner": "openclaw",
  "queue": "flow:openclaw:jobs",
  "message": "Task routed to openclaw queue"
}
```

### Check queue depths

```bash
curl http://localhost:8000/v1/intake/queues/status
```

Response:
```json
{
  "timestamp": "2026-04-03T12:00:00Z",
  "queues": {
    "openclaw": 5,
    "hermes": 2,
    "agent_zero": 0
  },
  "total": 7
}
```

### Check service health

```bash
curl http://localhost:8000/v1/intake/status
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2026-04-03T12:00:00Z",
  "checks": {
    "redis": "ok",
    "database": "ok",
    "schema": "ok"
  }
}
```

---

## Files Created

```
services/bizbrain_lite/app/
├── services/
│   ├── envelope_validation_service.py   (Validation + routing)
│   └── redis_queue_service.py           (Queue management)
└── api/
    └── openclaw_intake.py               (5 REST endpoints)

Modified:
└── app/main.py                          (Redis init, startup/shutdown)

docs/
└── PHASE_4_OPENCLAW_ROUTING.md         (Comprehensive guide)
```

---

## Key Features

✓ **One task, one owner** — Single owner per task, no parallel routing  
✓ **Governance enforcement** — High-risk requires review enforcement  
✓ **Observable goals** — Goals must be specific and measurable  
✓ **Queue tracking** — Real-time queue depth visibility  
✓ **Dead-letter queue** — Failed jobs preserved for investigation  
✓ **Health checks** — Redis and schema status visible  
✓ **Async-native** — All operations non-blocking  
✓ **Extensible** — Easy to add new task types and routing rules  

---

## Architecture

```
HTTP POST: Task Envelope
       ↓
OpenClaw Intake
  ├─ EnvelopeValidationService
  │   ├─ Schema validation
  │   ├─ Business rules check
  │   └─ Owner determination
  │
  ├─ Create JobRecord (Postgres)
  │
  └─ RedisQueueService
      └─ Enqueue to {owner}:jobs
```

---

## What's Next

### Phase 5: Agent Zero Review Enforcement

Agent Zero will:
- Gate high-risk tasks behind review artifacts
- Require diff + review.md + rollback.md
- Enforce approver signature
- Execute only with explicit approval

This completes the **trusted execution** layer.

---

## Summary

The task intake and routing layer is now **live**.

Tasks flow through validation → routing → queueing → execution.

All governance rules are enforced. All jobs are traceable. All queues are visible.

The system can now handle incoming work at scale.
