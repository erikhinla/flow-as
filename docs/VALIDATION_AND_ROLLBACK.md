# VALIDATION_AND_ROLLBACK

## Purpose

This document defines how tasks are validated before routing, and how rollback is managed for high-risk work.

---

## Task Validation (OpenClaw)

Before a task enters the system, OpenClaw validates:

### Schema Validation

```python
# Task envelope must conform to /schemas/task_envelope.schema.json
def validate_envelope(task_envelope):
    validator = jsonschema.Draft7Validator(TASK_ENVELOPE_SCHEMA)
    if not validator.is_valid(task_envelope):
        return False, validator.iter_errors()
    return True, None
```

**Invalid envelope → `status = blocked`**

### Business Rules

```python
def validate_business_rules(task):
    # Rule 1: High-risk tasks MUST have review_required = true
    if task.risk_tier == 'high' and not task.review_required:
        return False, "High-risk task missing review_required = true"
    
    # Rule 2: High-risk tasks MUST have a rollback plan if mutating state
    if task.risk_tier == 'high' and task.rollback_required and not has_rollback_artifact(task):
        return False, "Rollback plan required but not present"
    
    # Rule 3: Task goal must be specific and observable
    if len(task.goal) < 10:
        return False, "Goal too vague"
    
    # Rule 4: Preferred owner must be valid
    if task.preferred_owner not in ['openclaw', 'hermes', 'agent_zero']:
        return False, f"Unknown preferred_owner: {task.preferred_owner}"
    
    return True, None
```

**Invalid business rules → `status = blocked`**

---

## Review Artifacts (Agent Zero Only)

Before Agent Zero executes, these artifacts must exist:

### 1. task.diff

A unified diff showing the proposed changes.

**Location:** `runtime/reviews/{job_id}/task.diff`

**Format:**
```
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -10,5 +10,8 @@
 def existing_function():
-    old_code
+    new_code
```

**Purpose:** Reviewer can see exactly what changes before approval.

### 2. task.review.md

A review document explaining the change.

**Location:** `runtime/reviews/{job_id}/task.review.md`

**Required sections:**

```markdown
# Review: [Task Title]

## What changed
[Brief summary of changes]

## Why
[Justification aligned with canon and requirements]

## Impact
[What parts of the system are affected?]

## Testing
[How was this tested? What test results?]

## Rollback
[If rolled back, what state reverts?]

## Risks
[Known risks or edge cases]

## Approver
[Your name and date of approval]
```

**Example:**
```markdown
# Review: Add Redis connection pooling to hermes-control

## What changed
Modified `hermes/control.py` to use asyncpg connection pool instead of single connection.

## Why
Single connection was bottleneck. Pool improves throughput from 10 req/s to 50 req/s.

## Impact
- hermes-control API latency reduced
- Postgres connection count increased from 1 to 5
- Backward compatible (same API)

## Testing
- Load test: 100 concurrent requests, all successful
- Existing test suite: all pass
- Manual integration test: 5m run time

## Rollback
Set `POOL_SIZE=1` in .env and redeploy. Old code still compatible.

## Risks
- If Postgres is down, pool waits instead of failing fast
- Connection leaks would exhaust pool (requires monitoring)

## Approver
erikhinla, 2026-04-03
```

### 3. task.rollback.md

A rollback plan if the change causes issues.

**Location:** `runtime/reviews/{job_id}/task.rollback.md`

**Format:**
```markdown
# Rollback Plan: [Task Title]

## Detection
[How do we know this change caused the issue?]

Example:
- Hermes workers start reporting "connection pool exhausted"
- Postgres connection count exceeds 50

## Immediate Actions (0-5 minutes)
[Emergency steps]

1. Revert code: `git revert <commit>`
2. Redeploy: `docker-compose up -d hermes-control`
3. Monitor: Check error logs for recovery

## Validation
[How do we confirm rollback worked?]

1. `curl https://hermes.domain.com/health` returns 200
2. Check Postgres active connections: `SELECT count(*) FROM pg_stat_activity`
3. Run integration test: `pytest integration_test.py`

## Communication
Notify: ops@example.com, @erikhinla in #ops Slack

## Root Cause Analysis
[After rollback, investigate]

- Check Postgres logs for error patterns
- Review new code for connection leak
- Check system resources at time of failure
```

---

## Review Enforcement

### Gate: Before Execution

```python
@app.post("/tasks/agent-zero")
async def route_to_agent_zero(task_envelope):
    job_id = str(uuid.uuid4())
    
    # Require all three artifacts
    required_artifacts = [
        f"runtime/reviews/{job_id}/task.diff",
        f"runtime/reviews/{job_id}/task.review.md",
        f"runtime/reviews/{job_id}/task.rollback.md"
    ]
    
    missing = []
    for artifact_path in required_artifacts:
        if not file_exists(artifact_path):
            missing.append(artifact_path)
    
    if missing:
        return {
            "status": 403,
            "error": f"Cannot execute without review artifacts. Missing: {missing}"
        }
    
    # Parse review to extract approver and date
    review = load_file(f"runtime/reviews/{job_id}/task.review.md")
    if not has_approver_signature(review):
        return {
            "status": 403,
            "error": "Review missing approver signature"
        }
    
    # All checks passed, proceed
    return await execute_with_agent_zero(task_envelope, job_id)
```

---

## Rollback Execution

If an issue occurs and rollback is needed:

```python
async def trigger_rollback(job_id):
    # Load rollback plan
    rollback_plan = load_file(f"runtime/reviews/{job_id}/task.rollback.md")
    
    # Execute detection logic to confirm issue
    if not rollback_plan.detection_signal_present():
        return {"error": "Rollback detection criteria not met"}
    
    # Execute immediate actions
    for action in rollback_plan.immediate_actions:
        result = await execute_action(action)
        if not result.success:
            return {"error": f"Rollback action failed: {action}"}
    
    # Validate rollback
    for validation in rollback_plan.validation_steps:
        if not await validate(validation):
            return {"error": f"Rollback validation failed: {validation}"}
    
    # Log rollback
    log_rollback(job_id, "Rollback completed successfully")
    
    # Notify
    notify_escalation(job_id, "Rollback executed. RCA pending.")
    
    return {"status": "rollback_complete"}
```

---

## For Low / Medium Risk Tasks

Low and medium risk tasks do not require review artifacts.

They still must pass:
1. Schema validation
2. Business rules validation
3. Task envelope has `review_required = false`

They proceed directly to execution.

---

## Review Workflow

1. **You write the task envelope** and push to GitHub or Hostinger
2. **OpenClaw routes it** (validation + assignment)
3. **Agent Zero picks it up** (if assigned to agent_zero)
4. **Agent Zero generates diff** and notifies you
5. **You write review.md and rollback.md** in `runtime/reviews/{job_id}/`
6. **You approve** (add signature to review.md)
7. **Agent Zero checks for artifacts**, executes if all present
8. **On completion**, artifact location is recorded in `job_records.review_pointer`

---

## Artifact Storage

All review artifacts are version-controlled and auditable:

```
runtime/
└── reviews/
    └── {job_id}/
        ├── task.diff
        ├── task.review.md
        ├── task.rollback.md
        └── execution_log.txt [added after execution]
```

Archived after task completes (for 7-year audit trail).

---

## No Production Changes Without Review

This is the line:

**Rule: Agent Zero cannot mutate production state without all three review artifacts and your explicit signature.**

Violations result in:
- Immediate escalation
- Manual audit of change
- Potential rollback
