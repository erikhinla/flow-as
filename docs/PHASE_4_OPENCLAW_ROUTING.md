# Phase 4: OpenClaw Envelope Validation + Routing

## Overview

OpenClaw is the **intake router** for FLOW Agent OS.

**Responsibilities:**
1. Validate task envelopes (schema + business rules)
2. Determine owner (routing decision)
3. Create durable job record (Postgres)
4. Enqueue job to owner's Redis queue
5. Enforce governance rules

**Flow:**
```
Task Envelope (HTTP POST)
       ↓
Schema Validation (JSON schema)
       ↓
Business Rules (high-risk requires review, goal is specific, etc.)
       ↓
Owner Determination (by task_type or preferred_owner)
       ↓
Job Record Creation (Postgres job_records table)
       ↓
Queue Enqueue (Redis {owner}:jobs list)
       ↓
Response: accepted/rejected with job_id
```

---

## What Was Built

### 1. EnvelopeValidationService (`envelope_validation_service.py`)

Core validation and routing logic:

**Methods:**

- `validate_schema(envelope)` → JSON schema validation
  - Checks against `/schemas/task_envelope.schema.json`
  - Returns: (bool, error_message)

- `validate_business_rules(envelope)` → Governance enforcement
  - High-risk must have review_required=true
  - Goal must be specific (>= 10 chars)
  - Owner must be valid
  - Task type must be in routing rules
  - Returns: (bool, error_message)

- `determine_owner(envelope)` → Routing decision
  - If preferred_owner set: use it
  - Otherwise: use ROUTING_RULES by task_type
  - Returns: owner (openclaw, hermes, agent_zero)

- `validate_and_create_job(db, envelope, source)` → Full pipeline
  - Runs schema + business rules validation
  - Creates JobRecord in Postgres
  - Sets status=VALIDATED (not PENDING)
  - Returns: (success, error_msg, job_record)

**Routing Rules** (task_type → owner):
```python
{
    'classification': 'openclaw',
    'rewrite': 'openclaw',
    'content_prep': 'openclaw',
    'implementation': 'agent_zero',
    'skill_extraction': 'hermes',
    'healthcheck': 'hermes',
}
```

### 2. RedisQueueService (`redis_queue_service.py`)

Redis queue management for job distribution:

**Queues:**
- `flow:openclaw:jobs` — Jobs for OpenClaw router
- `flow:hermes:jobs` — Jobs for Hermes worker
- `flow:agent_zero:jobs` — Jobs for Agent Zero executor
- `flow:dead_letter` — Failed/abandoned jobs

**Methods:**

- `enqueue_job(owner, job_id)` → Add job to queue (FIFO)
- `dequeue_job(owner, timeout)` → Pop job from queue (blocking)
- `get_queue_depth(owner)` → Current queue size
- `get_all_queue_depths()` → Depths for all owners
- `move_to_dlq(job_id, reason)` → Send to dead-letter queue
- `get_dlq(count)` → Retrieve DLQ jobs
- `clear_queue(owner)` → Emergency clear (DANGEROUS)
- `healthcheck()` → Check Redis connectivity

### 3. OpenClaw Intake API (`openclaw_intake.py`)

REST endpoints for task intake and routing:

**POST `/v1/intake/task`** — Accept task envelope
```json
{
  "task_id": "task-123",
  "created_at": "2026-04-03T12:00:00Z",
  "source": "webhook",
  "title": "Classify intake submissions",
  "goal": "Classify all intake submissions by type with 95%+ accuracy",
  "task_type": "classification",
  "risk_tier": "low",
  "preferred_owner": null,
  "output_required": "JSON file with classifications",
  "review_required": false,
  "inputs": {
    "files": ["submission_1.json", "submission_2.json"],
    "context_refs": ["docs/INTAKE_RULES.md"]
  }
}
```

Response (accepted):
```json
{
  "status": "accepted",
  "job_id": "task-123",
  "owner": "openclaw",
  "queue": "flow:openclaw:jobs",
  "message": "Task routed to openclaw queue"
}
```

Response (rejected):
```json
{
  "status": "rejected",
  "error": "High-risk task missing review_required=true"
}
```

**GET `/v1/intake/status`** — Intake service health
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

**GET `/v1/intake/queues/status`** — All queue depths
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

**GET `/v1/intake/dlq`** — Dead-letter queue
```json
{
  "status": "ok",
  "count": 2,
  "items": [
    {
      "job_id": "job-456",
      "reason": "max retries exceeded",
      "timestamp": "2026-04-03T11:00:00Z"
    }
  ]
}
```

**POST `/v1/intake/queues/clear`** — Emergency clear (admin)
```json
?owner=openclaw&confirm=true
→
{
  "status": "cleared",
  "queue": "flow:openclaw:jobs",
  "message": "All pending jobs removed (DESTRUCTIVE)"
}
```

---

## Validation Rules

### Schema Validation

Task envelope must conform to `/schemas/task_envelope.schema.json`:
- task_id: UUID
- created_at: ISO8601 timestamp
- source: enum (manual, webhook, github_action, scheduled)
- title: 5-200 chars
- goal: 10-1000 chars (observable and specific)
- task_type: enum (classification, rewrite, implementation, etc.)
- risk_tier: enum (low, medium, high)
- review_required: boolean
- rollback_required: boolean

### Business Rules

**Rule 1: High-risk requires review**
```python
if risk_tier == 'high' and not review_required:
    return False, "High-risk task missing review_required=true"
```

**Rule 2: Goal must be observable**
```python
if len(goal) < 10:
    return False, "Goal too vague. Must be >= 10 chars and observable."
```

**Rule 3: Owner must be valid**
```python
if preferred_owner not in ['openclaw', 'hermes', 'agent_zero']:
    return False, f"Invalid preferred_owner"
```

**Rule 4: Task type must be supported**
```python
if task_type not in VALID_TASK_TYPES:
    return False, f"Invalid task_type"
```

---

## Routing Decisions

### By Task Type

| Task Type | Owner | Why |
|-----------|-------|-----|
| classification | openclaw | File analysis, repo-native |
| rewrite | openclaw | Content transformation, repo-native |
| content_prep | openclaw | File preparation, repo-native |
| implementation | agent_zero | Code changes, requires review |
| skill_extraction | hermes | Pattern analysis, learning |
| healthcheck | hermes | Service monitoring |

### Override: preferred_owner

If task envelope explicitly sets `preferred_owner`, use it instead of routing rule.

```python
if envelope.preferred_owner in VALID_OWNERS:
    return envelope.preferred_owner
else:
    return ROUTING_RULES[task_type]
```

---

## Job Lifecycle

```
pending (envelope arrival)
   ↓
VALIDATED (schema + rules pass)
   ↓
QUEUED (enqueued to Redis)
   ↓
ACTIVE (worker picks up)
   ↓
COMPLETED or FAILED
```

---

## Testing the Intake

### 1. Write a task envelope

```bash
curl -X POST http://localhost:8000/v1/intake/task \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task-intake-001",
    "created_at": "2026-04-03T12:00:00Z",
    "source": "manual",
    "title": "Test classification",
    "goal": "Classify 100 intake submissions by type",
    "task_type": "classification",
    "risk_tier": "low",
    "output_required": "JSON with classifications",
    "review_required": false,
    "inputs": {
      "files": ["test1.json", "test2.json"]
    }
  }'
```

Response:
```json
{
  "status": "accepted",
  "job_id": "task-intake-001",
  "owner": "openclaw",
  "queue": "flow:openclaw:jobs"
}
```

### 2. Check queue status

```bash
curl http://localhost:8000/v1/intake/queues/status
```

Response:
```json
{
  "timestamp": "2026-04-03T...",
  "queues": {
    "openclaw": 1,
    "hermes": 0,
    "agent_zero": 0
  },
  "total": 1
}
```

### 3. Check intake status

```bash
curl http://localhost:8000/v1/intake/status
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2026-04-03T...",
  "checks": {
    "redis": "ok",
    "database": "ok",
    "schema": "ok"
  }
}
```

### 4. Test rejection (high-risk without review)

```bash
curl -X POST http://localhost:8000/v1/intake/task \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task-bad-001",
    "created_at": "2026-04-03T12:00:00Z",
    "source": "manual",
    "title": "Deploy to production",
    "goal": "Deploy latest code to production server",
    "task_type": "implementation",
    "risk_tier": "high",
    "output_required": "Deployment confirmation",
    "review_required": false
  }'
```

Response:
```json
{
  "status": "rejected",
  "error": "High-risk task missing review_required=true (GOVERNANCE VIOLATION)"
}
```

---

## Environment Variables

```bash
# Redis
REDIS_URL=redis://localhost:6379

# Optional
REDIS_POOL_SIZE=10
REDIS_TIMEOUT=5
```

---

## Key Features

✓ **One task, one owner** — No parallel routing, single owner per task  
✓ **Governance enforcement** — High-risk requires review  
✓ **Observable goals** — No vague or unmeasurable tasks  
✓ **Queue tracking** — Real-time queue depth visibility  
✓ **Dead-letter queue** — Failed jobs preserved for inspection  
✓ **Health checks** — Redis and database status visible  
✓ **Async-native** — All operations non-blocking  

---

## Next Phase

Phase 5: **Agent Zero Review Enforcement**

Agent Zero will:
- Gate high-risk tasks behind review artifacts
- Require diff + review.md + rollback.md
- Enforce approver signature
- Execute only after approval
