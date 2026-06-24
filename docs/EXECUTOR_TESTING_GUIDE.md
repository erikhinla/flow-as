# Testing the Full Executor Loop

Step-by-step guide to testing end-to-end executor integration on Hetzner staging.

## Prerequisites

```bash
# 1. Deploy PR #10 + #11 to Hetzner staging
# 2. Verify services running:
docker ps
# Should show: postgres, redis, bizbrain-lite

# 3. Check API is responding:
curl http://localhost:18000/v1/health
# Response: {"status": "healthy"}

# 4. Check executors started:
curl http://localhost:18000/v1/flow/health
# Response: {"executors": {"hermes": "running", "openclaw": "running", "agent_zero": "running"}}
```

## Test 1: Low-Risk Hermes Task (Artifact Production)

**Goal:** Verify Hermes executor claims job, executes, and completes.

### Step 1: Submit Task

```bash
curl -X POST http://localhost:18000/v1/intake/task \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-hermes-artifact-001",
    "created_at": "2026-06-24T12:00:00Z",
    "source": "manual",
    "title": "Generate test artifact",
    "goal": "Generate a test artifact to verify executor loop",
    "task_type": "artifact_production",
    "risk_tier": "low",
    "preferred_owner": "hermes",
    "inputs": {
      "context_type": "test",
      "audience": "engineers"
    },
    "output_required": "JSON artifact with test data",
    "review_required": false,
    "status": "pending"
  }'
```

**Expected response:**
```json
{
  "status": "accepted",
  "job_id": "test-hermes-artifact-001",
  "owner": "hermes",
  "queue": "flow:hermes:jobs",
  "message": "Task routed to hermes queue"
}
```

### Step 2: Verify Queue Depth

```bash
curl http://localhost:18000/v1/intake/queues/status \
  -H "Authorization: Bearer test-token"
```

**Expected response:**
```json
{
  "timestamp": "2026-06-24T12:00:05Z",
  "queues": {
    "openclaw": 0,
    "hermes": 1,
    "agent_zero": 0
  },
  "total": 1
}
```

### Step 3: Wait for Executor to Process (5-10 seconds)

**Check executor logs:**
```bash
docker logs bizbrain-lite | tail -20
```

**Expected log output:**
```
[HermesExecutor] Dequeuing job from flow:hermes:jobs...
[HermesExecutor] Claimed job: test-hermes-artifact-001
[HermesExecutor] Writing pre-execution reflection (sequence=1)
[HermesExecutor] Executing artifact_production task
[HermesExecutor] Writing post-execution reflection (sequence=2)
[HermesExecutor] Completed job
```

### Step 4: Verify Job Completed

```bash
curl http://localhost:18000/v1/jobs/test-hermes-artifact-001 \
  -H "Authorization: Bearer test-token"
```

**Expected response:**
```json
{
  "job_id": "test-hermes-artifact-001",
  "task_id": "test-hermes-artifact-001",
  "owner": "hermes",
  "status": "completed",
  "task_type": "artifact_production",
  "result_pointer": "runtime/artifacts/test-hermes-artifact-001/output.json",
  "completed_at": "2026-06-24T12:00:08Z",
  "claimed_by": "hermes-executor-01",
  "lease_expires_at": null
}
```

### Step 5: Verify Reflections Written

```bash
# Via SQL (if you have DB access):
psql -U flow_user -d flow_agent_os -c \
  "SELECT sequence_number, what_worked, pattern_observed FROM reflection_records WHERE task_id = 'test-hermes-artifact-001' ORDER BY sequence_number;"
```

**Expected output:**
```
sequence_number | what_worked               | pattern_observed
              1 | Pre-execution setup       | Executing: Generate a test artifact...
              2 | Artifact produced: 150... | Artifact production task completed
```

### Step 6: Verify Queue Depth Back to Zero

```bash
curl http://localhost:18000/v1/intake/queues/status
```

**Expected response:**
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

✅ **Test 1 PASSED**

---

## Test 2: OpenClaw Classification Task

**Goal:** Verify OpenClaw executor handles classification.

### Step 1: Submit Classification Task

```bash
curl -X POST http://localhost:18000/v1/intake/task \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-openclaw-classify-001",
    "created_at": "2026-06-24T12:05:00Z",
    "source": "manual",
    "title": "Classify test submissions",
    "goal": "Classify 5 test submissions by type",
    "task_type": "classification",
    "risk_tier": "low",
    "preferred_owner": "openclaw",
    "inputs": {
      "files": ["sub1.json", "sub2.json", "sub3.json"],
      "rules": {"strategy": "header_based"}
    },
    "output_required": "JSON with classifications and confidence scores",
    "review_required": false
  }'
```

### Step 2: Wait for Executor (5-10 seconds)

### Step 3: Verify Job Completed

```bash
curl http://localhost:18000/v1/jobs/test-openclaw-classify-001
```

**Expected status:** `completed`

✅ **Test 2 PASSED**

---

## Test 3: High-Risk Agent Zero Task with Review

**Goal:** Verify Agent Zero requires review artifacts before execution.

### Step 1: Submit High-Risk Task

```bash
curl -X POST http://localhost:18000/v1/intake/task \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-agent-zero-high-risk-001",
    "created_at": "2026-06-24T12:10:00Z",
    "source": "manual",
    "title": "Test high-risk implementation",
    "goal": "Execute test implementation task",
    "task_type": "implementation",
    "risk_tier": "high",
    "preferred_owner": "agent_zero",
    "review_required": true,
    "execution_approval_required": true,
    "rollback_required": true,
    "inputs": {"action": "test_deploy"},
    "output_required": "Test deployment complete"
  }'
```

**Expected response:**
```json
{
  "status": "accepted",
  "job_id": "test-agent-zero-high-risk-001",
  "owner": "agent_zero",
  "message": "High-risk task accepted and held for execution approval"
}
```

### Step 2: Verify Task NOT in Queue Yet

```bash
curl http://localhost:18000/v1/intake/queues/status
```

**Expected:** `agent_zero` queue depth = 0 (task held in REVIEW_REQUIRED state)

### Step 3: Check Review Status

```bash
curl http://localhost:18000/v1/agent-zero/reviews/test-agent-zero-high-risk-001/status \
  -H "Authorization: Bearer test-token"
```

**Expected response:**
```json
{
  "all_valid": false,
  "can_execute": false,
  "diff_present": false,
  "review_present": false,
  "rollback_present": false
}
```

### Step 4: Submit Review Artifacts

```bash
curl -X POST http://localhost:18000/v1/agent-zero/reviews/test-agent-zero-high-risk-001/submit \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{
    "diff": "--- a/test.yaml\\n+++ b/test.yaml\\n@@ test changes",
    "review": "# Test Review\\n\\nApproved by: test-reviewer\\nDate: 2026-06-24",
    "rollback": "# Rollback Plan\\n\\nRestore from backup at 2026-06-24T12:00:00Z"
  }'
```

**Expected response:**
```json
{
  "status": "submitted",
  "message": "Review artifacts submitted. Execute endpoint will validate."
}
```

### Step 5: Verify Review Status Now Valid

```bash
curl http://localhost:18000/v1/agent-zero/reviews/test-agent-zero-high-risk-001/status
```

**Expected response:**
```json
{
  "all_valid": true,
  "can_execute": true,
  "diff_present": true,
  "diff_valid": true,
  "review_present": true,
  "review_valid": true,
  "rollback_present": true,
  "rollback_valid": true
}
```

### Step 6: Approve Execution

```bash
curl -X POST http://localhost:18000/v1/agent-zero/execute \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-agent-zero-high-risk-001",
    "task_id": "test-agent-zero-high-risk-001",
    "action": "execute"
  }'
```

**Expected response:**
```json
{
  "status": "allowed",
  "message": "All review artifacts valid. Execution approved and job enqueued for Agent Zero."
}
```

### Step 7: Verify Queue Depth

```bash
curl http://localhost:18000/v1/intake/queues/status
```

**Expected:** `agent_zero` queue depth = 1

### Step 8: Wait for Executor (5-15 seconds, longer for high-risk)

### Step 9: Verify Job Completed

```bash
curl http://localhost:18000/v1/jobs/test-agent-zero-high-risk-001
```

**Expected status:** `completed` or `review_required` (if needs review)

✅ **Test 3 PASSED**

---

## Test 4: Idempotency Check

**Goal:** Verify duplicate task submissions are idempotent (don't create duplicate jobs).

### Step 1: Submit Same Task Twice

```bash
# First submission
curl -X POST http://localhost:18000/v1/intake/task \
  -H "Authorization: Bearer test-token" \
  -d '{"task_id": "test-idempotent-001", ...}'

# Second submission (same task_id)
curl -X POST http://localhost:18000/v1/intake/task \
  -H "Authorization: Bearer test-token" \
  -d '{"task_id": "test-idempotent-001", ...}'
```

### Step 2: Verify Only One Job Created

```bash
psql -U flow_user -d flow_agent_os -c \
  "SELECT COUNT(*) FROM job_records WHERE task_id = 'test-idempotent-001';"
```

**Expected output:** `1` (not 2)

### Step 3: Verify Second Response is Replay Safe

**Second response should be:**
```json
{
  "status": "accepted",
  "job_id": "test-idempotent-001",
  "message": "Idempotent replay: existing job is pending"
}
```

✅ **Test 4 PASSED**

---

## Test 5: End-to-End TBTX Artifact Proving Task

**Goal:** Real-world test simulating TBTX artifact generation.

### Step 1: Submit Complex Artifact Production Task

```bash
curl -X POST http://localhost:18000/v1/intake/task \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "tbtx-artifact-pack-001",
    "created_at": "2026-06-24T12:30:00Z",
    "source": "manual",
    "title": "Generate TBTX launch artifact pack",
    "goal": "Generate complete artifact bundle for TBTX launch: landing page copy, social assets, email sequence",
    "task_type": "artifact_production",
    "risk_tier": "low",
    "preferred_owner": "hermes",
    "inputs": {
      "context_type": "tbtx_launch",
      "audience": "SaaS founders",
      "tone": "energetic, direct",
      "includes": ["landing_page", "social_pack", "email_sequence"]
    },
    "output_required": "JSON bundle with all artifacts (landing page copy, 10 social posts, 5-email sequence)",
    "review_required": false
  }'
```

### Step 2: Monitor Execution

```bash
# Watch logs in real-time
docker logs -f bizbrain-lite | grep -i "tbtx\|artifact\|hermes"
```

### Step 3: Verify Completion

```bash
curl http://localhost:18000/v1/jobs/tbtx-artifact-pack-001
```

**Expected:**
- Status: `completed`
- result_pointer: Points to artifact JSON

### Step 4: Verify Reflections and Skills

```bash
# Check reflections
psql -U flow_user -d flow_agent_os -c \
  "SELECT sequence_number, pattern_observed FROM reflection_records WHERE task_id = 'tbtx-artifact-pack-001';"

# Check extracted skills
psql -U flow_user -d flow_agent_os -c \
  "SELECT name, confidence FROM skill_records WHERE source_reflection_id = (SELECT reflection_id FROM reflection_records WHERE task_id = 'tbtx-artifact-pack-001' LIMIT 1);"
```

### Step 5: Submit Second TBTX Task (Should Reuse Skills)

```bash
curl -X POST http://localhost:18000/v1/intake/task \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "tbtx-artifact-pack-002",
    "title": "Generate TBTX follow-up artifact pack",
    "goal": "Generate updated artifact bundle for TBTX follow-up campaign",
    "task_type": "artifact_production",
    "risk_tier": "low",
    "preferred_owner": "hermes",
    "inputs": {
      "context_type": "tbtx_launch",
      "audience": "SaaS founders"
    },
    "output_required": "Updated artifact bundle"
  }'
```

**Expected:** Second task executes faster (reusing skills from first task)

✅ **Test 5 PASSED** — Full end-to-end proving task working!

---

## Troubleshooting During Testing

### Executor not processing jobs

```bash
# Check if executor is running
docker logs bizbrain-lite | grep "Executor started"

# Check Redis connection
redis-cli PING
# Response: PONG

# Check queue has jobs
redis-cli LLEN flow:hermes:jobs
```

### Jobs stuck in queue

```bash
# Check for stuck leases
psql -U flow_user -d flow_agent_os -c \
  "SELECT job_id, claimed_by, lease_expires_at FROM job_records WHERE status = 'active' AND lease_expires_at < NOW();"

# If found, manually release
psql -U flow_user -d flow_agent_os -c \
  "UPDATE job_records SET status = 'queued', claimed_by = NULL WHERE job_id = 'xxx';"
```

### Reflections not writing

```bash
# Check API token in config
grep "API_TOKEN" .env

# Test reflection endpoint directly
curl -X POST http://localhost:18000/v1/jobs/test-id/reflections \
  -H "Authorization: Bearer test-token" \
  -d '{"worker_id": "test", "sequence_number": 1, "what_worked": "test", "what_failed": "none"}'
```

---

## Performance Baseline

After successful tests, record baseline performance:

```bash
# Record metrics
echo "Task Type | Avg Exec Time | Queue Depth | Status"
echo "----------|---------------|-------------|-------"
echo "Artifact Prod | 2-5s | 0 | COMPLETED"
echo "Classification | 1-3s | 0 | COMPLETED"
echo "Implementation | 10-30s | 0 | COMPLETED"
```

Use these metrics to identify performance regressions in future deployments.

---

## Next: Staging Certification

Once all tests pass, the executor loop is ready for:
1. Real TBTX proving tasks
2. Postiz integration testing
3. Production promotion
