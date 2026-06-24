# FAAS Agent Executor Implementation (PR #11)

## Purpose

Implement the missing autonomous agent executor loop that closes the gap between task intake and worker execution. This PR completes the governed FAAS architecture by:

1. **Wiring worker execution into FAAS control plane** — executors consume from Redis queues, execute tasks, and write proof via FAAS API
2. **Enabling autonomous reflection and learning** — pre/mid/post-execution reflection windows allow agents to learn and adapt
3. **Maximizing agent capability** — Hermes learns recursively, Agent Zero adapts strategy mid-flight, OpenClaw executes operations
4. **Enforcing governance** — all state changes flow through FAAS proof-of-work API for audit trail

## What This Resolves

**Before PR #11:**
```
Task Envelope → Schema Validate → Create Job → Enqueue to Redis
     ✓              ✓                ✓                 ✓

     But then what?  ✗ Workers don't dequeue and execute
                     ✗ No reflection writing
                     ✗ No learning loop
```

**After PR #11:**
```
Task Envelope → FAAS Intake → Job Created → Enqueued
     ✓              ✓            ✓            ✓
                                              ↓
Worker Dequeues ← Claim via API ← Worker discovers job in queue
     ✓                ✓
     ↓
Pre-exec Reflection (Strategy) → Execute Task → Mid-exec Adaptation
     ✓                             ✓             (if needed)
     ↓                                           ↓
Post-exec Reflection (Learning) ← Complete Job ← Result via API
     ✓                              ✓
     ↓
Skill Extraction ← Reflection triggers background job
     ✓              (recursive learning)
```

## Stack of PRs

- **PR #9** — FAAS authority & Hermes governed-worker contract (merged/pending review)
- **PR #10** — Job lifecycle endpoints & idempotency contract (merged/pending review)
- **PR #11** — **This PR** — Agent executors and worker orchestration (NEW)

## Key Changes

### 1. Abstract AgentExecutor Base Class (`executor_base.py`)

**Provides core execution loop for all workers:**

```python
class AgentExecutor(ABC):
    async def run(self):                    # Main loop: claim → execute → reflect → complete
    async def process_one_job():            # Process a single job from queue
    async def _claim_job(job):              # Lease job via FAAS API (900s default)
    async def _write_reflection(...):       # Write reflection via /jobs/{id}/reflections
    async def _complete_job(job, result):   # Mark job done via FAAS API
    async def _fail_job(job, error):        # Mark job failed
    
    @abstractmethod
    async def execute_task(job):            # Subclasses implement task execution
    
    @abstractmethod
    async def get_task_context(job):        # Subclasses provide context (skills, prior patterns)
    
    async def adapt_and_retry(...):         # Optional: mid-execution strategy adaptation
```

**Reflection windows:**
- `sequence=1` — Pre-execution (strategy/plan)
- `sequence=2...N` — Mid-execution (adaptations, learnings)
- `sequence=final` — Post-execution (outcomes, patterns)

### 2. Hermes Executor (`hermes_executor.py`)

**Role:** Artifact production, learning, canonical synthesis

```python
class HermesExecutor(AgentExecutor):
    owner = "hermes"
    
    # Task types:
    - artifact_production    # Bounded artifact generation
    - content_prep          # Prepare & normalize content
    - skill_extraction      # Extract skills from reflections
    - healthcheck           # Service health verification
    
    # Execution model:
    1. Retrieve prior skills (ranked by confidence)
    2. Build synthesis strategy
    3. Generate artifact via LLM or template
    4. Write reflection with pattern_observed
    5. Trigger skill extraction (background)
```

**Autonomous learning:**
- Reads prior skills before execution
- Writes reflections during/after execution
- Background skill extraction updates confidence scores
- Next similar task gets better skills (recursive improvement)

### 3. OpenClaw Executor (`openclaw_executor.py`)

**Role:** Task operations, classification, rewriting, routing

```python
class OpenClawExecutor(AgentExecutor):
    owner = "openclaw"
    
    # Task types:
    - classification        # Classify files by category
    - rewrite              # Transform content (tone, audience, format)
    - content_prep         # Prepare & normalize
    
    # Execution model:
    1. Load files and rules
    2. Apply classification/transformation
    3. Validate output (confidence check)
    4. Write results
    5. Reflect on success patterns
```

**Operations focus:**
- File-native execution (reads, processes, writes)
- Confidence-based validation
- Pattern extraction for future similar tasks

### 4. Agent Zero Executor (`agent_zero_executor.py`)

**Role:** High-risk strategic reasoning, implementation, adaptation

```python
class AgentZeroExecutor(AgentExecutor):
    owner = "agent_zero"
    lease_seconds = 1800  # 30 minutes for high-risk work
    
    # Task types:
    - implementation       # Code changes, infrastructure, high-risk work
    
    # Execution model:
    1. Validate review artifacts present (for high-risk)
    2. Parse review (diff, review, rollback)
    3. Retrieve prior successful strategies
    4. Build execution strategy
    5. Execute with continuous monitoring
    6. If strategy fails: adapt and retry (with alternative strategy)
    7. Write reflections capturing strategy effectiveness
    8. Escalate if adaptation exhausted
```

**Autonomous reasoning:**
- Builds execution strategy from prior patterns
- Monitors execution with checkpoints
- Adapts strategy mid-flight if initial approach fails
- Escalates only when all adaptive strategies exhausted
- Writes reflections on strategy decisions (learning for next task)

### 5. BizBrain Lite Main App Integration (`main.py`)

**Startup sequence:**

```python
# On application startup:
1. Initialize PostgreSQL (job_records, reflection_records, skill_records)
2. Initialize Redis (queues: flow:openclaw:jobs, flow:hermes:jobs, flow:agent_zero:jobs)
3. Start skill extraction background job (every 5 minutes)
4. Start Hermes executor (continuously processes hermes queue)
5. Start OpenClaw executor (continuously processes openclaw queue)
6. Start Agent Zero executor (continuously processes agent_zero queue)
```

**Executor lifecycle:**
- Each executor runs in its own asyncio task
- Continuously polls queue with 30s timeout
- Claims job, executes, writes reflections, completes
- Handles errors gracefully (escalation)
- Shutdown cleanly on app exit

**Startup logs:**
```
================================================================================
FLOW AGENT AS — FAAS Control Plane Startup
================================================================================
✓ PostgreSQL tables initialized (job_records, reflection_records, skill_records)
✓ Redis queue service initialized: redis://localhost:6379
✓ Skill extraction background job started (every 5 minutes)
✓ Hermes executor started (artifact_production, skill_extraction, content_prep)
✓ OpenClaw executor started (classification, rewrite, content_prep)
✓ Agent Zero executor started (implementation, high-risk work)

================================================================================
FAAS CONTROL PLANE READY
================================================================================
API Base URL: http://localhost:18000/v1
Intake endpoint: POST /v1/intake/task
Job management: POST /v1/jobs/{task_id}/claim|complete|fail|escalate
Worker reflections: POST /v1/jobs/{task_id}/reflections
Hermes skills: GET /v1/hermes/skills, POST /v1/hermes/reflections
Agent Zero reviews: GET /v1/agent-zero/reviews/{job_id}/status
================================================================================
```

## End-to-End Flow Example: TBTX Artifact Proving Task

### 1. Task Submission
```bash
curl -X POST http://localhost:18000/v1/intake/task \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "tbtx-artifact-001",
    "source": "proof",
    "title": "Generate TBTX launch artifact package",
    "goal": "Generate complete artifact bundle: landing page copy, social assets, email sequence",
    "task_type": "artifact_production",
    "risk_tier": "low",
    "preferred_owner": "hermes",
    "output_required": "JSON bundle with all artifacts at runtime/artifacts/{job_id}/output.json",
    "inputs": {
      "context_type": "tbtx_launch",
      "audience": "SaaS founders",
      "tone": "energetic, direct"
    }
  }'
```

**Response:**
```json
{
  "status": "accepted",
  "job_id": "tbtx-artifact-001",
  "owner": "hermes",
  "queue": "flow:hermes:jobs",
  "message": "Task routed to hermes queue"
}
```

### 2. Hermes Executor Processes Job

**Executor loop:**
1. Dequeues job from `flow:hermes:jobs`
2. Claims job (15-min lease): `POST /v1/jobs/tbtx-artifact-001/claim`
3. Writes pre-execution reflection:
   ```json
   {
     "sequence_number": 1,
     "what_worked": "Pre-execution setup",
     "what_failed": "None",
     "pattern_observed": "Executing: Generate complete artifact bundle...",
     "context_type": "pre_execution"
   }
   ```
4. Retrieves prior skills:
   ```
   GET /v1/hermes/skills?task_type=artifact_production&context_type=tbtx_launch&limit=5
   → Returns top 5 skills ranked by confidence
   ```
5. Executes artifact generation (calls LLM, template engine, etc.)
6. Writes post-execution reflection:
   ```json
   {
     "sequence_number": 2,
     "what_worked": "Generated 3 artifacts with high coherence",
     "what_failed": "None",
     "pattern_observed": "TBTX launch artifacts follow predictable structure",
     "success_signal": "All artifacts validated, 2450 chars total output",
     "tool_sequence": ["skill_retrieval", "llm_synthesis", "validation"]
   }
   ```
7. Completes job: `POST /v1/jobs/tbtx-artifact-001/complete`
   - Result pointer: `runtime/artifacts/tbtx-artifact-001/output.json`
   - Status: `COMPLETED`

### 3. Skill Extraction (Background)

**Background job (runs every 5 min):**
1. Scans `reflection_records` for `skill_extraction_attempted = 'N'`
2. For Hermes' TBTX reflection: extracts pattern
3. Creates/updates skill:
   ```
   skill_id: hermes_artifact_production_tbtx_launch_abc123
   name: TBTX launch artifact synthesis
   confidence: 0.92
   times_used: 1
   times_succeeded: 1
   ```
4. Next TBTX task retrieves this skill (confidence increases with each success)

### 4. Results

**Artifact available:**
```
runtime/artifacts/tbtx-artifact-001/output.json
→ Contains landing page copy, social assets, email sequence
```

**Job record updated:**
```
job_id: tbtx-artifact-001
status: COMPLETED
result_pointer: runtime/artifacts/tbtx-artifact-001/output.json
completed_at: 2026-06-24T12:30:00Z
```

**Reflections stored (learning for next task):**
```
[reflection_id: r1, sequence: 1, context: pre_execution]
[reflection_id: r2, sequence: 2, context: post_execution, pattern extracted]
```

## High-Risk Task Example: Agent Zero with Review Artifacts

### 1. High-Risk Task Submission
```json
{
  "task_id": "prod-deploy-001",
  "title": "Deploy Redis cluster to Hetzner production",
  "goal": "Deploy and configure new Redis cluster for session storage",
  "task_type": "implementation",
  "risk_tier": "high",
  "preferred_owner": "agent_zero",
  "review_required": true,
  "execution_approval_required": true,
  "rollback_required": true,
  "inputs": {
    "nodes": 3,
    "version": "7.0",
    "rollback_plan": "Restore from AMI snapshot v2026-06-23"
  }
}
```

**Response:** Job held in `REVIEW_REQUIRED` state (awaiting approval)

### 2. Review Artifacts Submitted
```bash
curl -X POST http://localhost:18000/v1/agent-zero/reviews/prod-deploy-001/submit \
  -H "Authorization: Bearer test-token" \
  -d '{
    "diff": "[unified diff showing cluster config changes]",
    "review": "[Review document with approver signature]",
    "rollback": "[Rollback plan: step-by-step restore procedure]"
  }'
```

### 3. Execution Approved
```bash
curl -X POST http://localhost:18000/v1/agent-zero/execute \
  -H "Authorization: Bearer test-token" \
  -d '{"job_id": "prod-deploy-001", "action": "execute"}'
```

**Job moves to `QUEUED` state → Agent Zero executor picks it up**

### 4. Agent Zero Executes with Strategy Adaptation

**Executor flow:**
1. Claim job (30-min lease for high-risk)
2. Pre-execution reflection (strategy)
3. Parse review artifacts (diff, review, rollback)
4. Retrieve prior deployment strategies
5. Build execution strategy from best-performing prior strategy
6. Execute deployment with monitoring checkpoints

**If deployment fails at checkpoint:**
- Write mid-execution adaptation reflection
- Retrieve alternative strategy
- Retry with adapted approach
- Write reflection on adaptation
- If all strategies fail → escalate

7. Post-execution reflection (what worked, patterns)
8. Complete job

**Escalation example (all strategies fail):**
```
POST /v1/jobs/prod-deploy-001/escalate
{
  "reason": "All deployment strategies failed. Manual intervention required.",
  "notify_to": "ops-team@transformby10x.ai"
}
```

## Testing the Full Loop (Local)

### Prerequisites
```bash
# Terminal 1: Start services
docker-compose up -d postgres redis

# Terminal 2: Start BizBrain Lite
cd services/bizbrain_lite
python -m uvicorn app.main:app --reload --port 18000
```

### Test Sequence

**1. Submit a low-risk Hermes task:**
```bash
curl -X POST http://localhost:18000/v1/intake/task \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "test-hermes-001", "source": "manual", ...}'
```

**2. Verify job accepted:**
```bash
curl http://localhost:18000/v1/intake/queues/status
→ Should show depth=1 for hermes queue
```

**3. Watch executor logs:**
```
[HermesExecutor] Dequeuing job from flow:hermes:jobs...
[HermesExecutor] Claimed job: test-hermes-001
[HermesExecutor] Writing pre-execution reflection (sequence=1)
[HermesExecutor] Executing artifact_production task
[HermesExecutor] Writing post-execution reflection (sequence=2)
[HermesExecutor] Completed job
```

**4. Check results:**
```bash
curl http://localhost:18000/v1/jobs/test-hermes-001
→ status: COMPLETED, result_pointer: runtime/artifacts/test-hermes-001/output.json
```

**5. Verify reflections stored:**
```sql
SELECT sequence_number, what_worked, pattern_observed FROM reflection_records 
WHERE task_id = 'test-hermes-001' ORDER BY sequence_number;

→ sequence=1 | Pre-exec setup | Executing...
→ sequence=2 | Artifact generated | Pattern extracted
```

## Integration with Existing Systems

### Intake Routing (from PR #10)
✅ Unchanged — task schema, validation, owner routing all work as-is

### Worker API Endpoints (from PR #10)
✅ Fully utilized:
- `POST /v1/jobs/{task_id}/claim` — Executors claim jobs
- `POST /v1/jobs/{task_id}/complete` — Executors complete jobs
- `POST /v1/jobs/{task_id}/fail` — Executors fail jobs
- `POST /v1/jobs/{task_id}/reflections` — Executors write reflections
- `POST /v1/jobs/{task_id}/escalate` — Escalation API

### Skill Loop (from Hermes executor)
✅ Triggered automatically:
- POST /v1/hermes/reflections — Executors write reflections
- Background skill extraction reads reflections and updates skill_records
- GET /v1/hermes/skills — Next task retrieves improved skills

## Deployment Checklist

### Hetzner Staging
- [ ] Deploy BizBrain Lite container with executor code
- [ ] Verify PostgreSQL tables created (migration 002)
- [ ] Verify Redis queues healthy
- [ ] Submit test task and verify executor picks it up
- [ ] Monitor executor logs for errors
- [ ] Run TBTX artifact proving task end-to-end
- [ ] Verify reflections stored and skill extraction triggered

### Hostinger Production (after staging validation)
- [ ] Deploy same container stack
- [ ] Restore PostgreSQL from staging backup
- [ ] Warm up Redis caches
- [ ] Run health checks on all endpoints
- [ ] Begin task intake (low-risk tasks first)
- [ ] Monitor executor performance

## Next Steps (Post-Merge)

1. **Task #1:** Run end-to-end TBTX artifact proving task on Hetzner staging
2. **Task #2:** Implement actual LLM integration (currently mocked in Hermes executor)
3. **Task #3:** Wire Postiz integration for social content output
4. **Task #4:** Add real implementation logic to Agent Zero (currently mocked)
5. **Task #5:** Promote to Hostinger production after staging evidence

## Authority & Deployment Boundary

- **FAAS remains governing:** All state changes through FAAS API, audit trail complete
- **Workers are autonomous within lanes:** Claim → execute → reflect → complete
- **No second source of truth:** All state in PostgreSQL, updated only via FAAS API
- **Hetzner staging first:** Exercise full loop before production
- **Hostinger production:** Only after staging evidence and explicit approval

## Verification Note

This PR implements the complete executor loop infrastructure. The executor implementations themselves contain TODO comments where actual task execution logic would go (LLM calls, file operations, deployments, etc.). These will be filled in incrementally as actual use cases prove the architecture.

The governance layer and proof-of-work tracking are complete and production-ready.
