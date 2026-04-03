# QUEUE_HYGIENE

## Purpose

This document defines status transitions, dead-letter rules, and queue management for FLOW Agent OS.

---

## Status Lifecycle

Every task transitions through states. No jumps allowed.

```
pending
  ↓
validated
  ↓
queued
  ↓
active
  ├→ review_required (if review_required flag set)
  │   ↓
  │   [awaiting approval]
  │   ↓
  │   completed
  │
  └→ completed [if no review required]

[error paths]
active → failed → dead_letter [after max_retries exceeded]
active → blocked [dependency unmet]
active → escalated [manual intervention required]
```

---

## Status Definitions

### pending
Task envelope received. Not yet routed.
- Owner: unassigned
- Action: Validation
- Next: `validated` (if valid), or `blocked` (if schema fails)

### validated
Task passed schema validation and business rules check.
- Owner: assigned (OpenClaw will route)
- Action: Route to correct owner
- Next: `queued`

### queued
Task in the queue for its assigned owner.
- Owner: assigned
- Action: Waiting for available worker
- Next: `active`

### active
Task is being executed.
- Owner: assigned
- Action: Execution in progress
- Next: `review_required` (if review flag set) OR `completed` (if no review)

### review_required
Task completed. Awaiting human approval.
- Owner: assigned
- Action: Review artifacts (diff, rollback plan) exist
- Next: `completed` (if approved) OR `failed` (if rejected)
- Timeout: 24h (escalate if no approval)

### completed
Task finished successfully.
- Owner: assigned
- Action: Write reflection, trigger skill extraction
- Result: Artifact stored in `runtime/completed/job_id/`
- Next: `archived` (after 30 days)

### failed
Task execution failed.
- Owner: assigned
- Action: Log error, increment retry_count
- Next: If `retry_count < max_retries`: `queued` (retry). Else: `dead_letter`

### dead_letter
Task failed permanently. Requires explicit retry or abandonment.
- Owner: assigned
- Action: Escalate to human (you)
- Escalation: Email notification to escalation contact
- Next: Manual `queued` (explicit retry) OR `archived` (abandon)

### blocked
Task cannot proceed due to unmet dependency.
- Owner: assigned
- Action: Check dependency status
- Unblock trigger: Dependency task completed
- Next: `queued` (when dependency met)

### escalated
Task requires manual intervention. Similar to dead-letter but not necessarily a failure.
- Owner: assigned
- Action: Escalate to you
- Example: "Agent Zero needs your approval for production deployment"
- Next: Manual decision (`queued` to retry, `completed` to accept, or `archived`)

### archived
Task is complete or abandoned. Read-only.
- Action: None
- Duration: Kept for 7 years for audit

---

## Dead-Letter Rules

A job enters `dead_letter` if:

1. **Retry exhaustion:** `retry_count >= max_retries` AND `status = failed`
2. **Timeout:** Task active for > 24 hours (configurable per risk_tier)
3. **Escalation marked:** Manual escalation by you

On dead-letter:
- Set `status = dead_letter`
- Set `escalation_triggered_at = now()`
- Send email to `escalation_notified_to`
- Preserve full payload in `job_records` and `runtime/escalated/job_id/`
- Do not retry automatically

Dead-letter recovery:
- Manual retry: Set `retry_count = 0`, `status = queued`
- Abandon: Set `status = archived`

---

## Timeout Rules

### By Risk Tier

| Tier | Active Timeout | Review Timeout | Reason |
|------|---|---|---|
| low | 6 hours | 24 hours | Repo work, can afford to wait |
| medium | 2 hours | 12 hours | Operational tasks, need faster feedback |
| high | 30 minutes | 4 hours | Production, must escalate quickly |

On timeout:
- Set `status = escalated` (not failed)
- Preserve execution context
- Notify escalation contact

---

## Retry Policy

### Configuration

```
default max_retries = 3
exponential backoff: 2^attempt seconds (2s, 4s, 8s)
```

### Retry transitions

1. Execution started: `status = active`
2. Execution fails: `status = failed`, `retry_count += 1`
3. If `retry_count < max_retries`: `status = queued` (re-enter queue with backoff)
4. If `retry_count >= max_retries`: `status = dead_letter` (escalate)

### Idempotent retries

All retried jobs must be safe to re-execute:
- No duplicate writes to output
- Callbacks are idempotent (check job already completed before writing)
- Tool invocations don't mutate state twice

---

## Queue State Management

### Redis Hot Layer

```
hermes:jobs → list of pending job IDs (FIFO)
agent_zero:jobs → list of pending high-risk jobs
openclaw:jobs → list of pending router/repo jobs
```

Entries are pushed on `queued` status, popped on `active` status.

### Postgres Durable Layer

All job transitions logged to `job_records` with timestamps.

### Reconciliation

Every 5 minutes, hermes-control checks:
- Jobs in Redis but not in Postgres: log error, remove from Redis
- Jobs in Postgres with `status = active` but not in Redis: Re-enqueue (worker may have crashed)
- Jobs in Postgres with `updated_at > 24h` and `status = active`: Escalate (timeout)

---

## Queue Depth Monitoring

Alert if:
- `pending` + `queued` > 50 jobs (backlog growing)
- `active` > 10 jobs per owner (worker overloaded)
- `dead_letter` > 5 jobs (recurring failures)
- `escalated` > 1 job (awaiting your action)

---

## Example Status Transitions

### Happy Path (Low-Risk Task, No Review)

```
1. Task envelope received
   status = pending
   
2. OpenClaw validates
   status = validated
   
3. Routed to Hermes
   status = queued
   
4. Hermes picks it up
   status = active
   
5. Hermes completes
   status = completed
   reflection written
   skill extraction triggered
   
6. After 30 days
   status = archived
```

### High-Risk Task with Review

```
1. Task envelope received
   status = pending, review_required = true
   
2. OpenClaw validates
   status = validated
   
3. Routed to Agent Zero
   status = queued
   
4. Agent Zero executes
   status = active
   
5. Agent Zero completes
   status = review_required
   artifacts written: diff, rollback, review docs
   
6. You approve
   status = completed
   reflection written
   
7. After 30 days
   status = archived
```

### Task with Failure and Retry

```
1-4. Same as above, task is active

5. Agent Zero fails (e.g., network error)
   status = failed
   error_message = "connection timeout"
   retry_count = 1
   
6. Backoff 2 seconds, re-enqueue
   status = queued
   
7. Retry begins
   status = active
   
8. Succeeds this time
   status = completed
```

### Dead-Letter Escalation

```
1-4. Same setup

5. Agent Zero fails
   status = failed, retry_count = 1
   
6. Retry 1 fails
   status = failed, retry_count = 2
   
7. Retry 2 fails
   status = failed, retry_count = 3
   
8. max_retries exceeded
   status = dead_letter
   escalation_triggered_at = now()
   Email sent to escalation_notified_to
   
9. You investigate, fix root cause
   
10. Manual retry
    Set retry_count = 0, status = queued
    
11. Task re-enters normal flow
```

---

## Health Checks

hermes-control `/health` should return:

```json
{
  "status": "healthy",
  "queues": {
    "pending": 3,
    "queued": 5,
    "active": 2,
    "dead_letter": 0,
    "escalated": 0
  },
  "db_connection": "ok",
  "redis_connection": "ok",
  "oldest_dead_letter": null
}
```

Health is `degraded` if:
- `dead_letter > 1`
- `escalated > 0`
- `active > 10`
- DB or Redis unreachable

---

## No Implicit Retries

Core rule: **If a job fails, it does not retry automatically without logging and recording.**

Every retry must be:
1. Logged to `job_records`
2. Traceable in audit trail
3. Bounded by `max_retries`

Silent retries are banned.
