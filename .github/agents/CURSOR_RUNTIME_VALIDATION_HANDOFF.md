# CURSOR: FLOW Agent AS Runtime Validation Protocol

**Status:** Ready for handoff  
**Priority:** P0 (Proof-of-execution before multi-repo deployment)  
**Authority:** Full development delegation  
**Timeline:** Complete before next production tasks  

---

## CONTEXT: What You're Validating

FLOW Agent AS is **not a typical app deployment**. It's an **orchestration runtime** that routes work as task envelopes through a distributed queue system.

**Current state:**
- ✅ FLOW infrastructure live and tested (audit trail, review gates, OpenRouter integration)
- ✅ Single validation job (000...401) proved end-to-end execution
- ❓ **UNPROVEN:** Can FLOW orchestrate real production repos as task envelopes?

**What you're proving:**
- FLOW can accept real task envelopes from actual repos
- Tasks move through queue lifecycle correctly
- Artifacts are generated and persisted
- Audit trail records everything
- Escalation path (Alpha → Beta → Gamma) works
- High-risk approval gates protect production changes

---

## ARCHITECTURE: Control vs. Execution Nodes

**Hostinger (Control Node):**
- Queue management
- Approval orchestration
- Audit logging
- Task envelope validation
- Status tracking

**Hetzner (Execution Node):**
- Task execution
- OpenRouter LLM calls
- Artifact generation
- PM2 processes (Alpha/Beta tasks)
- Docker containers (Gamma tasks)

**Source of Truth:** Filesystem queues (not Redis, not database — actual queue directories)

---

## THE 7-PHASE VALIDATION PROTOCOL

Execute in order. Do NOT skip phases or parallelize. Each phase builds on the previous.

### Phase 1: Create Valid Task Envelope (Prompting Circumstance - Low Risk)

**What to do:**
- Create a valid task envelope JSON for `Prompting Circumstance` discovery task
- Use the task envelope schema from flow-developer.agent.md
- Set: `risk_tier: "low"`, `assigned_agent: "openclaw"`, `task_type: "classification"`
- Example title: "Prompting Circumstance Framework Discovery"
- Example goal: "Inspect Prompting Circumstance repo structure, identify key modules, document architecture"

**Validation:**
- Schema passes envelope validation service
- All required fields present
- No validation errors returned

**Expected output:**
- Valid task envelope JSON
- `status: "pending"` in database
- Entry in `job_records` table

**Proof:** Save the task envelope JSON and the job_id returned

---

### Phase 2: Queue Movement & Lifecycle (Pending → Active → Completed)

**What to do:**
- Drop task into pending queue (via POST `/v1/intake/task`)
- Monitor queue depths in real-time
- Watch task move from pending → active → completed

**Validation:**
- Task appears in pending queue immediately
- Within 5 seconds, worker picks it up (active)
- Within 10 seconds total, task completes
- Queue depth transitions: 1 pending → 0 active → 1 completed

**Proof:** Capture exact timestamps for each transition

```bash
# Commands to run
curl http://localhost:18000/v1/intake/queues/status | jq .  # Before submission
# [wait 2 seconds]
curl http://localhost:18000/v1/intake/queues/status | jq .  # After submission (should show 1 pending)
# [wait 5 seconds]
curl http://localhost:18000/v1/intake/queues/status | jq .  # Task should be active
# [wait 10 seconds]
curl http://localhost:18000/v1/intake/queues/status | jq .  # Task should be completed
```

**Expected output:**
```json
{
  "queues": {
    "openclaw": 0,
    "hermes": 0,
    "agent_zero": 0
  },
  "total": 0
}
```

**Proof:** Screenshot/log of queue transitions with timestamps

---

### Phase 3: Output Artifact Verification

**What to do:**
- Verify artifact was written to `/runtime/reviews/{job_id}/output.md`
- Read the artifact content
- Confirm it's real LLM output (not placeholder)

**Validation:**
- File exists and contains real content (not "placeholder" string)
- Metadata JSON exists with timestamps
- Artifact size > 500 bytes (real work, not stub)

**Proof:** Paste artifact content (first 500 chars) into report

```bash
# Command
cat /app/runtime/reviews/{JOB_ID}/output.md | head -20
```

---

### Phase 4: Audit Trail Recording (All 4 Events)

**What to do:**
- Query audit_logs table for your job_id
- Verify all 4 events recorded in correct sequence:
  1. `job_submitted` (when task accepted at intake)
  2. `job_queued` (when moved to queue)
  3. `job_started` (when worker picked it up)
  4. `job_completed` (when execution finished)

**Validation:**
- All 4 events present
- Timestamps in correct order (submitted < queued < started < completed)
- Time deltas reasonable (submit→queue: <100ms, queue→start: <5s, start→complete: <10s)
- Event metadata contains correct data (agent, task_type, artifact_path)

**Proof:** Full audit trail query result

```bash
# Command
psql -c "
  SELECT 
    audit_id,
    event_type,
    agent,
    action_by,
    created_at,
    event_data
  FROM audit_logs
  WHERE job_id = '{YOUR_JOB_ID}'
  ORDER BY created_at
;"
```

---

### Phase 5: Job Record Persistence (Database Proof)

**What to do:**
- Query job_records for your job_id
- Verify all fields populated correctly

**Validation:**
- `status: "completed"`
- `result_pointer` points to actual artifact file
- `started_at` and `completed_at` are not null
- `completed_at - started_at` < 10 seconds

**Proof:** Full job record query result

```bash
# Command
psql -c "
  SELECT
    job_id,
    owner,
    status,
    created_at,
    started_at,
    completed_at,
    result_pointer
  FROM job_records
  WHERE job_id = '{YOUR_JOB_ID}'
;"
```

---

### Phase 6: Node Execution Verification (Hostinger vs. Hetzner)

**What to do:**
- Confirm task executed on correct node (Hetzner execution, logged from Hostinger control)
- Check worker logs to prove execution location
- Verify queue management happened on Hostinger

**Validation:**
- Worker logs show execution on Hetzner
- Audit events logged to Hostinger audit_logs
- Queue depth changes came from Hostinger control layer

**Proof:** Worker log excerpt showing execution + node context

```bash
# Command
docker logs flow-openclaw-worker --tail=50 | grep -i "job_id={YOUR_JOB_ID}"
```

---

### Phase 7: Test High-Risk Escalation (Beta → Gamma Approval Gate)

**What to do:**
- Create NEW high-risk task (different task_id)
- Set: `risk_tier: "high"`, `assigned_agent: "agent_zero"`, `review_required: true`
- Submit to intake
- Verify task is held in `REVIEW_REQUIRED` status (NOT queued)
- Verify audit log records `review_requested` event
- Simulate approval (update database or call approval API)
- Verify task moves to agent_zero queue
- Verify audit log records `approval_granted` event

**Validation:**
- Task created but not queued (status = REVIEW_REQUIRED)
- Audit event: `review_requested` recorded
- After approval simulation, status changes to `queued`
- Audit event: `approval_granted` recorded
- Task executes on Agent Zero (Gamma level)

**Proof:** Before/after status, audit events for approval workflow

```bash
# Command 1: Check status before approval
psql -c "SELECT job_id, status FROM job_records WHERE job_id = '{HIGH_RISK_JOB_ID}';"

# Command 2: Check audit trail shows review_requested
psql -c "
  SELECT event_type, created_at FROM audit_logs 
  WHERE job_id = '{HIGH_RISK_JOB_ID}' 
  ORDER BY created_at
;"

# Command 3: Simulate approval (depends on your approval API)
# [Approve the task via your review system]

# Command 4: Check status after approval
psql -c "SELECT job_id, status FROM job_records WHERE job_id = '{HIGH_RISK_JOB_ID}';"

# Command 5: Check audit trail shows approval_granted
psql -c "
  SELECT event_type, created_at FROM audit_logs 
  WHERE job_id = '{HIGH_RISK_JOB_ID}' 
  ORDER BY created_at
;"
```

---

## DELIVERABLE: Runtime Validation Report

After completing all 7 phases, create a report with:

### Section 1: Executive Summary
- GO or NO-GO decision
- Single sentence reason
- Date/time of validation

### Section 2: Phase Results

For each phase (1-7):
- **Objective:** What was being tested
- **Result:** PASS or FAIL
- **Evidence:** Exact command output, timestamps, or query results
- **Time taken:** Duration for that phase

### Section 3: End-to-End Timeline

```
[06:12:31Z] Task envelope created (job_id: TASK-0001)
[06:12:34Z] Task submitted to intake (/v1/intake/task)
[06:12:35Z] Task queued to openclaw queue (queue depth: 1)
[06:12:36Z] Worker picked up task (job_started event)
[06:12:41Z] OpenRouter called, artifact written
[06:12:42Z] Task marked completed (queue depth: 0)
[06:12:43Z] All 4 audit events recorded
```

### Section 4: Proof Artifacts

- Task envelope JSON
- All query results (paste output)
- Artifact file excerpt (first 500 chars)
- Audit trail (all events)
- Worker logs showing execution
- High-risk approval workflow proof

### Section 5: Known Issues (if any)

- What failed or was unexpected
- Workaround applied (if any)
- Impact on production readiness

### Section 6: Next Steps

- What validation proved
- What's ready for next phase
- Any blockers or gaps

---

## CONSTRAINTS & RULES

❌ **DO NOT:**
- Deploy multiple repos before proof passes
- Scale or optimize infrastructure
- Create arbitrary test tasks (use provided examples)
- Modify audit trail manually
- Skip any phase
- Parallelize phases

✅ **DO:**
- Run phases sequentially
- Document exact timestamps
- Capture actual command output
- Verify on both Hostinger (control) and Hetzner (execution)
- Report any unexpected behavior immediately

---

## SUCCESS CRITERIA

You'll know validation is complete when:

1. ✅ Low-risk Prompting Circumstance task executes end-to-end
2. ✅ All 4 audit events recorded (submitted, queued, started, completed)
3. ✅ Artifact written and readable
4. ✅ Queue transitions correct (pending → active → completed)
5. ✅ High-risk task held in REVIEW_REQUIRED (not auto-queued)
6. ✅ Approval gate functional (review_requested → approval_granted)
7. ✅ Node separation confirmed (Hostinger control, Hetzner execution)

**All 7 = GO for multi-repo production deployment.**

---

## QUESTIONS FOR CLARIFICATION

If you hit any issues, answer these before asking for help:

1. What exact error message or unexpected behavior occurred?
2. Which phase failed?
3. What was the command that failed?
4. What did you expect vs. what happened?
5. Are both nodes (Hostinger + Hetzner) accessible and responding?

---

## TIMELINE

**Estimated duration:** 1-2 hours (depending on whether Hetzner execution node is reachable)

**Blocking issue:** If Hetzner is unreachable, tasks won't execute. Verify connectivity first.

---

## HANDOFF COMPLETE

When you finish:
1. Save this validation report to `.github/agents/RUNTIME_VALIDATION_REPORT.md`
2. Include all 7 phase results
3. Report GO/NO-GO decision
4. Post completion summary to team

**After GO decision: Ready to deploy real repos as FLOW task envelopes.**

---

**Prepared by:** Gordon (Infrastructure Architect)  
**For:** Cursor (Development Authority)  
**Date:** 2025-05-04  
**Authority:** Full delegation to execute and report
