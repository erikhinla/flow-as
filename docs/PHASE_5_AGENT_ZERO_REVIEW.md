# Phase 5: Agent Zero Review Enforcement

## Overview

Agent Zero is the **trusted execution engine** for FLOW Agent OS.

**Core Rule:** High-risk tasks cannot execute without three review artifacts:
1. **task.diff** — Unified diff showing proposed changes
2. **task.review.md** — Review document with approver signature
3. **task.rollback.md** — Rollback plan with detection and actions

All three must pass validation before execution is allowed.

**Flow:**
```
High-Risk Task Arrives
       ↓
Status: QUEUED
       ↓
You create 3 review artifacts
       ↓
POST /v1/agent-zero/reviews/{job_id}/submit
       ↓
POST /v1/agent-zero/execute
       ↓
Validation: all artifacts present + valid + approver signature
       ↓
YES → Job status = ACTIVE (execution allowed)
NO → Blocked with detailed error message
```

---

## What Was Built

### 1. ReviewEnforcementService

Validates all three review artifacts before execution:

**Artifact Classes:**
- `DiffArtifact` — Unified diff validator
  - Validates format (--- a/, +++ b/, @@, +/- lines)
  - Checks size (max 10000 lines)
  - Extracts list of files changed

- `ReviewArtifact_` — Review document validator
  - Requires: What changed, Why, Impact, Testing, Rollback, Risks, Approver
  - Validates approver signature format: "Approver: Name, YYYY-MM-DD"
  - Returns approver name and date

- `RollbackArtifact` — Rollback plan validator
  - Requires: Detection, Immediate Actions, Validation
  - Checks for completeness (no TODO/TBD)
  - Ensures specific, actionable steps

**Methods:**
- `check_review_artifacts(job_id)` → Returns detailed status of all 3 artifacts
- `block_if_missing_artifacts(job_id)` → Gates execution, returns error if incomplete
- `save_artifacts(job_id, diff, review, rollback)` → Persists to disk

### 2. Agent Zero Review API

REST endpoints for review submission and execution gating:

```
GET    /v1/agent-zero/reviews/{job_id}/status             — Check artifact status
POST   /v1/agent-zero/reviews/{job_id}/submit             — Submit all artifacts
POST   /v1/agent-zero/execute                             — Gate execution
GET    /v1/agent-zero/reviews/{job_id}/artifacts/{type}   — Retrieve specific artifact
```

---

## Artifact Templates

### task.diff - Unified Diff

```diff
--- a/src/module.py
+++ b/src/module.py
@@ -10,5 +10,8 @@
 def existing_function():
     existing_code
-    old_implementation
+    new_implementation
+    improved_logic
+    better_performance
 
 def another_function():
```

### task.review.md - Review Document

```markdown
# Review: [Task Title]

## What changed
[Brief summary of changes, e.g., "Modified connection pool from 1 to 5 connections"]

## Why
[Justification, e.g., "Single connection was bottleneck, reducing latency by 40%"]

## Impact
[What's affected, e.g., "Hermes latency reduced", "Postgres connection pool increases"]

## Testing
[How tested, e.g., "Load test: 100 concurrent requests all successful"]
- Test result 1: PASS
- Test result 2: PASS
- Regression suite: 50/50 tests pass

## Rollback
[How to revert if needed, e.g., "Set POOL_SIZE=1 in .env and redeploy"]

## Risks
[Known risks, e.g., "Connection pool leak would exhaust connections"]
- Risk 1 and mitigation
- Risk 2 and mitigation

## Approver
[Your name and approval date]
erikhinla, 2026-04-03
```

### task.rollback.md - Rollback Plan

```markdown
# Rollback Plan: [Task Title]

## Detection
[How to know if rollback is needed]
- Hermes workers report "connection pool exhausted"
- Postgres connection count exceeds 50
- Response latency increases > 50%

## Immediate Actions
[Steps to take in first 5 minutes]
1. Revert code: `git revert <commit>`
2. Redeploy: `docker-compose up -d hermes`
3. Monitor: Check error logs for recovery

## Validation
[Confirm rollback worked]
1. `curl https://hermes.domain.com/health` returns 200
2. Check Postgres connections: `SELECT count(*) FROM pg_stat_activity`
3. Run integration test: `pytest integration_test.py`
4. Verify no errors in Hermes logs: `docker logs hermes`

## Root Cause Analysis
[After rollback, investigate]
- Check Hermes logs for connection leak patterns
- Review new code for resource handling issues
- Verify pool configuration matches production specs
```

---

## API Examples

### 1. Submit Review Artifacts

```bash
curl -X POST http://localhost:8000/v1/agent-zero/reviews/job-123/submit \
  -H "Content-Type: application/json" \
  -d '{
    "diff": "--- a/file.py\n+++ b/file.py\n@@ -10 @@\n-old\n+new",
    "review": "# Review\n\n## What changed\nAdded connection pooling\n\n## Approver\nerikhinla, 2026-04-03",
    "rollback": "# Rollback\n\n## Detection\nConnection pool exhausted\n\n## Immediate Actions\nRevert commit\n\n## Validation\nCheck health endpoint"
  }'
```

Response:
```json
{
  "status": "submitted",
  "job_id": "job-123",
  "artifacts": {
    "diff": "runtime/reviews/job-123/task.diff",
    "review": "runtime/reviews/job-123/task.review",
    "rollback": "runtime/reviews/job-123/task.rollback"
  }
}
```

### 2. Check Review Status

```bash
curl http://localhost:8000/v1/agent-zero/reviews/job-123/status
```

Response:
```json
{
  "job_id": "job-123",
  "diff_present": true,
  "diff_valid": true,
  "review_present": true,
  "review_valid": true,
  "review_approver": {
    "name": "erikhinla",
    "date": "2026-04-03"
  },
  "rollback_present": true,
  "rollback_valid": true,
  "all_valid": true,
  "can_execute": true,
  "timestamp": "2026-04-03T12:00:00Z"
}
```

### 3. Execute High-Risk Task (with valid artifacts)

```bash
curl -X POST http://localhost:8000/v1/agent-zero/execute \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job-123",
    "task_id": "task-123",
    "action": "execute"
  }'
```

Response (success):
```json
{
  "status": "allowed",
  "job_id": "job-123",
  "message": "All review artifacts valid. Execution approved and job set to ACTIVE."
}
```

### 4. Try Execute Without Artifacts (blocked)

```bash
curl -X POST http://localhost:8000/v1/agent-zero/execute \
  -H "Content-Type: application/json" \
  -d '{"job_id": "job-456", "task_id": "task-456", "action": "execute"}'
```

Response (blocked):
```json
{
  "status": "blocked",
  "job_id": "job-456",
  "error": "Cannot execute without complete review artifacts. Missing: task.diff, task.review, task.rollback."
}
```

---

## Validation Rules

### Diff Validation
- Must be in unified diff format (--- a/, +++ b/)
- Must have content lines (+, -, @@)
- Max 10,000 lines
- Returns list of files changed

### Review Validation
- Must have all 7 sections: What changed, Why, Impact, Testing, Rollback, Risks, Approver
- Approver signature required: "Approver: Name, YYYY-MM-DD"
- Returns approver name and date

### Rollback Validation
- Must have 3 sections: Detection, Immediate Actions, Validation
- Must be complete (no TODO, TBD, or "TBC")
- Must have specific, executable steps

---

## Execution Lifecycle

```
QUEUED (waiting for review)
   ↓
Review artifacts submitted
   ↓
All artifacts valid?
   ├─ NO → Error, blocked from execution
   └─ YES → ACTIVE (execution allowed)
   ↓
Execution starts
   ↓
Success → COMPLETED
Failure → trigger rollback
```

---

## Key Features

✓ **Three-layer enforcement** — All artifacts must exist, be valid, and have approver signature  
✓ **Specific validation rules** — Each artifact type has its own validation logic  
✓ **Approver tracking** — Review document must include name and date  
✓ **Rollback readiness** — Rollback plan required before execution  
✓ **Error clarity** — If blocked, exact errors reported (missing artifacts, invalid format, etc.)  
✓ **Artifact retrieval** — Can fetch any artifact by job_id and type  

---

## No Production Changes Without Review

This is the core principle enforced by Agent Zero:

**Rule:** Agent Zero cannot execute high-risk tasks without:
1. Diff showing exactly what changes
2. Review with approver signature
3. Rollback plan with detection logic

**Violations result in:**
- Immediate execution block
- Detailed error message
- No silent failures

---

## Next Steps

Phase 5 completes the **trusted execution** layer.

Your FLOW Agent OS now has:
- ✓ Phase 1: Durable state (Postgres)
- ✓ Phase 2: Health monitoring
- ✓ Phase 3: Skill loop (recursive learning)
- ✓ Phase 4: Intake + routing (validation + queuing)
- ✓ Phase 5: Review enforcement (trusted execution)

All components are in place. The system is production-ready.

---

## Architecture Summary

```
Task Intake (OpenClaw)
       ↓
Validation + Routing
       ↓
Queue to Owner
       ↓
Skill Retrieval (Hermes)
       ↓
Enriched Execution Context
       ↓
Execute Task
       ↓
High-Risk? → Review Enforcement Gate (Agent Zero)
       ↓
Write Reflection
       ↓
Extract Skill (Hermes)
       ↓
Next Task Benefits from Learning
```

Full cycle complete.
