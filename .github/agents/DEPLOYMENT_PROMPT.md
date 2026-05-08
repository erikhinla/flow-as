# FLOW Agent AS — Live Deployment Handoff Prompt

**Target:** Move from verified infrastructure (6-proof validated) → production task routing → live autonomous execution  
**Timeline:** Single focused sprint  
**Success Criteria:** First autonomous task from OpenClaw → Hermes → Agent Zero with human review gate working  

---

## THE EXACT PROMPT (Use This)

```
You are flow-developer, the full-stack authority for FLOW Agent AS.

The infrastructure is verified operational:
- PostgreSQL accepting connections ✅
- Redis healthy, all 3 workers connected ✅
- BizBrain API healthy ✅
- Shared /runtime/reviews mounts verified ✅

Your mission: Move FLOW from operational infrastructure to LIVE AUTONOMOUS EXECUTION.

This is a single, focused deployment sprint. You will not:
- Add new features
- Refactor architecture
- Build dashboards
- Optimize performance

You WILL:
1. Verify task envelope reaches all three queues intact
2. Implement end-to-end test task that flows: OpenClaw → Hermes → Agent Zero
3. Verify PostgreSQL audit trail records every step
4. Test high-risk review gate (Agent Zero requires human approval before touching production)
5. Confirm first skill extraction and confidence scoring
6. Document exact API calls and expected outputs for live operations

PHASE 1: TEST TASK SUBMISSION (Do This First)
==============================================

Step 1: Create test task envelope
- Use the task envelope schema from flow-developer agent
- Set assigned_agent: "openclaw"
- Set risk_level: "low"
- Objective: "Inspect /workspace repo structure and create site map"
- Output: /runtime/reviews/test-task-001-openclaw-discovery.md

Step 2: Submit to BizBrain API
POST http://localhost:18000/v1/tasks
Header: Authorization: Bearer ${BIZBRAIN_API_TOKEN}
Body: test task envelope (JSON)

Step 3: Monitor Redis queue pickup
docker exec flow-redis redis-cli LRANGE openclaw 0 -1
Should show task appears, then disappears as worker picks it up

Step 4: Verify artifact creation
docker exec flow-openclaw-worker cat /runtime/reviews/test-task-001-openclaw-discovery.md
Expected: Actual discovery output (repo structure, files found, etc.)

Step 5: Query database for task record
docker exec flow-postgres psql -U flow_user -d flow_agent_os \
  -c "SELECT task_id, status, assigned_agent FROM tasks ORDER BY created_at DESC LIMIT 1"
Expected: task_id, status: completed, assigned_agent: openclaw

PHASE 2: ESCALATION CHAIN TEST
===============================

Step 1: Create escalation task
- Set assigned_agent: "hermes"
- Set inputs: ["/runtime/reviews/test-task-001-openclaw-discovery.md"]
- Objective: "Review discovery output, extract reusable patterns, enrich context"
- Output: /runtime/reviews/test-task-002-hermes-enrichment.md

Step 2: Submit to API (this task will be picked up by hermes worker, NOT openclaw)
POST http://localhost:18000/v1/tasks

Step 3: Monitor queue and verify pickup
docker exec flow-redis redis-cli LRANGE hermes 0 -1
docker logs flow-hermes-worker --tail=20

Step 4: Verify Hermes output
docker exec flow-hermes-worker cat /runtime/reviews/test-task-002-hermes-enrichment.md
Expected: Structured context enrichment, pattern suggestions

Step 5: Query database
SELECT * FROM tasks WHERE assigned_agent = 'hermes' ORDER BY created_at DESC LIMIT 1;
Expected: status: completed

PHASE 3: HIGH-RISK EXECUTION & REVIEW GATE
===========================================

Step 1: Create high-risk task (simulated production change)
- Set assigned_agent: "agent_zero"
- Set risk_level: "high"
- Objective: "Review proposed schema migration for Supabase"
- Inputs: ["/runtime/reviews/proposed-migration.sql"]
- Rules:
  - "Requires human approval before execution"
  - "Must generate rollback plan"
  - "Must include diff of changes"
- Output: /runtime/reviews/test-task-003-agent-zero-review.md

Step 2: Submit to API
POST http://localhost:18000/v1/tasks

Step 3: Verify Agent Zero worker receives it
docker logs flow-agent-zero-worker --tail=20
Expected: Task received, waiting for approval flag

Step 4: Check approval requirement in database
SELECT task_id, risk_level, status FROM tasks WHERE risk_level = 'high';
Expected: status should be "awaiting_approval" or "pending_review", NOT executing

Step 5: Simulate approval (update database)
UPDATE tasks SET approved_by = 'human-reviewer', approved_at = NOW(), status = 'approved' 
  WHERE task_id = 'test-task-003-agent-zero-review';

Step 6: Trigger worker to retry
(This depends on your worker retry logic — check if it polls for status changes or needs manual trigger)

Step 7: Verify execution and review artifacts
docker exec flow-agent-zero-worker cat /runtime/reviews/test-task-003-agent-zero-review.md
Expected: Contains diff, rollback plan, execution summary

PHASE 4: SKILL EXTRACTION & CONFIDENCE TRACKING
================================================

Step 1: Verify reflection was written for completed task
SELECT * FROM reflections WHERE task_id = 'test-task-001-openclaw-discovery';
Expected: what_worked, what_failed, pattern_observed, confidence

Step 2: Run skill extraction job (if not automatic)
python -m app.learning.extractor
(Check if this runs as background job or manual command)

Step 3: Verify skill was indexed
SELECT skill_id, pattern, confidence FROM skills ORDER BY created_at DESC LIMIT 5;
Expected: Skills from test tasks, confidence starting at 0.5

Step 4: Submit similar task to test skill retrieval
- Create new discovery task (similar to test-task-001)
- Before agent executes, check if high-confidence skill is retrieved and added to context
- Submit task, verify execution uses retrieved skill

Step 5: Update confidence score based on success/failure
If task succeeded: confidence should increase (+0.1)
If task failed: confidence should decrease (-0.15)
SELECT * FROM skills WHERE skill_id = 'skill-from-test-001' ORDER BY updated_at DESC LIMIT 1;
Expected: Updated confidence score

PHASE 5: AUDIT TRAIL VERIFICATION
==================================

Step 1: Query complete audit trail for test tasks
SELECT * FROM audit_log WHERE task_id IN ('test-task-001', 'test-task-002', 'test-task-003') 
  ORDER BY created_at;
Expected: Every action recorded (submission, queue pickup, execution, approval, completion)

Step 2: Verify all three agents appear in trail
Expected entries:
- openclaw: task received, executed, completed
- hermes: task received, enriched, completed
- agent_zero: task received, awaiting approval, approved, executed, completed

Step 3: Check for any gaps or missing records
If any step is missing from audit trail, that's a bug to fix before production

PHASE 6: DOCUMENTATION FOR LIVE OPS
====================================

Step 1: Document exact API endpoints for operations team
- Task submission (POST /v1/tasks)
- Task status query (GET /v1/tasks/{task_id})
- Task approval (PATCH /v1/tasks/{task_id}/approve)
- Queue inspection (GET /v1/queues/status)

Step 2: Document queue commands for debugging
docker exec flow-redis redis-cli LRANGE {queue_name} 0 -1
docker logs flow-{agent}-worker --tail=100
docker exec flow-postgres psql ... SELECT queries for common troubleshooting

Step 3: Create runbook for common issues
- Task stuck in queue? (Check worker health, Redis connection)
- Skill extraction not running? (Check background job status)
- High-risk task not executing? (Verify approval record in database)
- Audit trail missing? (Check PostgreSQL connection)

Step 4: Document success metrics for each phase
- Proof 1: Task submission → Redis queue pickup within 5 seconds
- Proof 2: Worker execution → artifact appears in /runtime/reviews within 10 seconds
- Proof 3: PostgreSQL record → task status updated to "completed" within 30 seconds
- Proof 4: Audit trail → every step recorded with timestamps
- Proof 5: Skill extraction → pattern indexed with confidence 0.5 within 60 seconds
- Proof 6: Confidence update → skill confidence changes on next similar task

DEPLOYMENT SUCCESS CHECKLIST
=============================

□ Test task flows from OpenClaw → queue → worker → /runtime/reviews artifact → PostgreSQL record
□ Escalation test: Hermes worker picks up task from hermes queue
□ High-risk execution: Agent Zero respects review gate, doesn't execute without approval
□ Audit trail: All three agents' actions recorded in audit_log
□ Skill extraction: Pattern indexed with initial confidence 0.5
□ Confidence scoring: Confidence updated on repeat task (+0.1 success, -0.15 failure)
□ Operations docs: API endpoints, queue commands, debugging runbook complete
□ Live deployment: All 6 proofs passing with actual tasks, not test data

OUTPUT DELIVERABLES
====================

When you complete this prompt, deliver:

1. test-task-results.md
   - Results from all 6 phases
   - Exact API payloads that worked
   - Exact database queries and their results
   - Any errors encountered and how you fixed them

2. api-operations-guide.md
   - Exact curl commands for task submission/approval/status
   - Expected HTTP responses
   - Common error codes and fixes
   - Redis/PostgreSQL debugging commands

3. deployment-readiness-checklist.md
   - All 6 proofs documented as PASS/FAIL with timestamps
   - Any known issues and workarounds
   - Go/no-go decision for live deployment

4. NEXT-STEPS.md
   - What was proven this sprint
   - What blocks production rollout (if anything)
   - Exact next actions for live deployment
   - Timeline estimate for first real autonomous task

CONSTRAINTS & GUARDRAILS
========================

You MUST:
- Use only existing containers/APIs (no new services)
- Test with low-risk tasks first (openclaw level 0)
- Only test high-risk gates, don't actually deploy changes
- Leave all audit trails intact for compliance review
- Document every step (ops team will run these exact commands)

You MUST NOT:
- Add new features mid-sprint
- Refactor any code
- Skip the review gate test (this is non-negotiable for production)
- Delete any test data (keep artifacts for audit)

DEFINITION OF DONE
==================

This sprint is complete when:

✅ All 6 proofs documented with actual task data
✅ Operations team can submit a task via API and watch it flow through all three agents
✅ High-risk review gate works and prevents unapproved execution
✅ Audit trail is complete and traceable
✅ Skill extraction is working (confidence scores visible)
✅ No open bugs blocking live deployment
✅ Exact API calls documented for production use
✅ Team confident enough to route first real work through FLOW

LIVE DEPLOYMENT TRIGGER
=======================

After this sprint, FLOW is ready for production when:

1. First real task (not test) submitted from actual source (OpenClaw discovery of real repo)
2. Hermes enriches it with real patterns
3. Agent Zero executes with human review and approval
4. Audit trail records everything
5. Team leader approves deployment to production queues

This is the gate between verified infrastructure and live autonomous execution.

Go execute this prompt. Report back with results.
```

---

## HOW TO USE THIS PROMPT

**Who sends it:**
You send this to flow-developer agent (or hand to a developer)

**When:**
After verifying infrastructure is stable (already done ✅)

**Expected turnaround:**
- Phases 1-3: 2-4 hours (task routing, escalation, review gates)
- Phase 4-5: 1-2 hours (skill extraction, audit verification)
- Phase 6: 1 hour (documentation)
- Total: One focused work sprint

**What you get back:**
- Proof that tasks flow end-to-end
- Evidence that review gates work
- Audit trail showing complete visibility
- Production-ready API documentation
- Clear go/no-go decision for live deployment

---

## WHY THIS PROMPT WORKS

**It is specific:**
- Not "test the system" but "submit this exact task with this exact payload"
- Not "check the database" but "run this exact query and show me these exact columns"
- Not "verify escalation" but "watch task move from openclaw → hermes → agent_zero queue"

**It is achievable in one sprint:**
- No architecture changes
- No new services
- No refactoring
- Just: submit → route → execute → audit → document

**It is production-focused:**
- Every phase tests something ops team will do live
- Every output is operations documentation
- Every success metric is measurable and repeatable

**It is governance-first:**
- High-risk review gate is not optional, it's phase 3
- Audit trail is verified in phase 5
- Approval workflow is tested before going live

**It unblocks autonomous execution:**
- After this, OpenClaw can submit real discovery tasks
- Hermes can enrich with real patterns
- Agent Zero can handle real high-risk work with human approval
- FLOW becomes productive, not just demonstrated

---

## THE NEXT MILESTONE

After this prompt completes successfully, you will have:

✅ Verified task routing (end-to-end)  
✅ Proven escalation pipeline (OpenClaw → Hermes → Agent Zero)  
✅ Working review gates (high-risk requires approval)  
✅ Complete audit trail (compliance ready)  
✅ Active learning loop (skills extracting, confidence scoring)  
✅ Production documentation (ops can operate it)  

**Then:** Submit first real work (TransformBy10X discovery, BizBuilders schema review, BizBot marketing task)  
**Result:** FLOW goes live with actual business value

This is the prompt that moves you from demo to production.

---

**Created:** 2025-05-03  
**Status:** Ready to execute  
**Next:** Send to flow-developer or lead engineer, expect results in 4-6 hours
