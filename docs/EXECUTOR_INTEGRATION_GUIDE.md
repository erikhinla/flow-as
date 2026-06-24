# Executor Integration Guide

How the autonomous agent executors integrate with FAAS control plane.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    FAAS Control Plane                            │
│  (Intake, Routing, Job Lifecycle, Proof-of-Work Validation)     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  │  Hermes Executor │  │ OpenClaw Executor│  │ Agent Zero       │
│  │                  │  │                  │  │ Executor         │
│  │  (Artifact Prod) │  │  (Operations)    │  │ (Implementation) │
│  │                  │  │                  │  │                  │
│  │  Autonomous      │  │  Autonomous      │  │  Autonomous      │
│  │  Learning Loop   │  │  Classification  │  │  Strategy        │
│  │                  │  │                  │  │  Adaptation      │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
│           │                     │                     │
│           ├─ Claim job (lease) ─┤─ POST /v1/jobs/{id}/claim
│           ├─ Execute task ──────┤
│           ├─ Write reflection ──┤─ POST /v1/jobs/{id}/reflections
│           └─ Complete job ──────┤─ POST /v1/jobs/{id}/complete
│                                 │
│  ┌──────────────────────────────┴──────────────────────────┐
│  │                    Redis Queues                         │
│  │  flow:openclaw:jobs  flow:hermes:jobs  flow:agent_zero │
│  └───────────────────────────────────────────────────────┘
│                                                              │
│  ┌────────────────────────────────────────────────────────┐
│  │             PostgreSQL (Durable State)                 │
│  │  job_records, reflection_records, skill_records        │
│  └────────────────────────────────────────────────────────┘
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Executor Lifecycle

### Initialization (App Startup)

```python
# main.py startup
1. init_db() → Create tables
2. redis_queue_service = RedisQueueService(redis_client)
3. hermes_executor = HermesExecutor(db_factory, redis_queue_service)
4. openclaw_executor = OpenClawExecutor(db_factory, redis_queue_service)
5. agent_zero_executor = AgentZeroExecutor(db_factory, redis_queue_service)

# Each executor runs in its own asyncio task
6. asyncio.create_task(hermes_executor.run())
7. asyncio.create_task(openclaw_executor.run())
8. asyncio.create_task(agent_zero_executor.run())
```

### Main Executor Loop

```python
while True:
    job_id = await redis_queue_service.dequeue_job(owner, timeout=30)
    if not job_id:
        continue
    
    job = await db.get_job(job_id)
    
    # 1. Claim lease
    await executor.claim_job(job)
    
    # 2. Pre-execution reflection
    await executor.write_reflection(job, sequence=1, what_worked="Setup", ...)
    
    # 3. Execute
    result = await executor.execute_task(job)
    
    # 4. Handle result
    if result.success:
        await executor.write_reflection(job, sequence=2, what_worked=result.summary, ...)
        await executor.complete_job(job, result.artifact_path)
    else:
        # Try adaptation if applicable
        if result.can_retry:
            adapted = await executor.adapt_and_retry(job, result, context)
            if adapted.success:
                await executor.complete_job(job, adapted.artifact_path)
            else:
                await executor.fail_job(job, adapted.error_message)
        else:
            await executor.fail_job(job, result.error_message)
```

## Task Execution Flow

### Example: Hermes Artifact Production

```
1. Task Intake
   POST /v1/intake/task {
     "task_id": "artifact-123",
     "task_type": "artifact_production",
     "goal": "Generate landing page copy",
     "preferred_owner": "hermes"
   }
   → Job created in DB (status: VALIDATED)
   → Enqueued to flow:hermes:jobs

2. Hermes Executor Dequeues
   await redis.rpop("flow:hermes:jobs") → "artifact-123"
   
3. Claim Job
   POST /v1/jobs/artifact-123/claim {
     "worker_id": "hermes-executor-01",
     "owner": "hermes",
     "lease_seconds": 900
   }
   → Job status: ACTIVE
   → Lease: expires in 15 minutes

4. Pre-Execution Reflection
   POST /v1/jobs/artifact-123/reflections {
     "sequence_number": 1,
     "what_worked": "Pre-execution setup",
     "what_failed": "None",
     "pattern_observed": "Starting artifact generation"
   }

5. Get Task Context
   context = await executor.get_task_context(job)
   → Retrieves prior skills (e.g., "landing_page_patterns", confidence: 0.95)

6. Execute
   result = await executor.execute_task(job)
   → Calls LLM with goal + prior skills
   → Generates artifact
   → Validates output
   → Returns ExecutionResult(success=True, artifact_path=...)

7. Post-Execution Reflection
   POST /v1/jobs/artifact-123/reflections {
     "sequence_number": 2,
     "what_worked": "Generated coherent landing page copy",
     "what_failed": "None",
     "pattern_observed": "Landing page follows predictable structure",
     "success_signal": "All validation checks passed",
     "tool_sequence": ["skill_retrieval", "llm_synthesis", "validation"]
   }

8. Complete Job
   POST /v1/jobs/artifact-123/complete {
     "worker_id": "hermes-executor-01",
     "result_pointer": "runtime/artifacts/artifact-123/output.json",
     "needs_review": false
   }
   → Job status: COMPLETED
   → Lease released

9. Skill Extraction (Background)
   Background job runs every 5 minutes:
   → Reads reflection_records where skill_extraction_attempted='N'
   → For Hermes' reflection: extracts pattern
   → Updates skill_records with new skill + confidence
   → Marks reflection as extracted

10. Next Similar Task
    GET /v1/hermes/skills?task_type=artifact_production
    → Returns improved skills (now includes "landing_page_pattern", confidence: 0.95)
    → Execution faster and more confident
```

### Example: Agent Zero High-Risk Deployment

```
1. Task Intake (High-Risk)
   POST /v1/intake/task {
     "task_id": "deploy-prod-123",
     "task_type": "implementation",
     "risk_tier": "high",
     "review_required": true,
     "execution_approval_required": true
   }
   → Job created (status: REVIEW_REQUIRED)
   → NOT enqueued yet (waiting for review artifacts)

2. Submit Review Artifacts
   POST /v1/agent-zero/reviews/deploy-prod-123/submit {
     "diff": "[unified diff of deployment changes]",
     "review": "[Review document with signature]",
     "rollback": "[Rollback procedure]"
   }
   → Artifacts stored to disk
   → Job still in REVIEW_REQUIRED

3. Approve Execution
   POST /v1/agent-zero/execute {
     "job_id": "deploy-prod-123",
     "action": "execute"
   }
   → Validates all artifacts present
   → Job status: QUEUED
   → Enqueued to flow:agent_zero:jobs

4. Agent Zero Executor Dequeues
   await redis.rpop("flow:agent_zero:jobs") → "deploy-prod-123"

5. Claim Job (30-min lease for high-risk)
   POST /v1/jobs/deploy-prod-123/claim {
     "worker_id": "agent-zero-executor-01",
     "lease_seconds": 1800
   }

6. Pre-Execution Reflection (Strategy)
   POST /v1/jobs/deploy-prod-123/reflections {
     "sequence_number": 1,
     "what_worked": "Review artifacts validated",
     "what_failed": "None",
     "pattern_observed": "Using deployment strategy from prior successful prod-deploy-100",
     "context_type": "pre_execution"
   }

7. Get Task Context
   context = await executor.get_task_context(job)
   → Parse review artifacts (diff, rollback plan)
   → Retrieve prior deployment strategies
   → Rank by success rate

8. Execute with Strategy Adaptation
   strategy = await executor._build_strategy(job, prior_strategies)
   
   for step in strategy.execution_steps:
       result = await execute_step(step)
       if not result.success and can_retry:
           # Mid-execution adaptation
           POST /v1/jobs/deploy-prod-123/reflections {
             "sequence_number": 2,
             "what_worked": "Step 1-3 completed",
             "what_failed": f"Step 4 failed: {error}",
             "pattern_observed": "Using alternative strategy",
             "context_type": "mid_execution_adaptation"
           }
           
           # Try alternative strategy
           alt_strategy = retrieve_alternative_strategy()
           result = await execute_with_strategy(alt_strategy)
   
   if result.success:
       # Post-execution reflection
       POST /v1/jobs/deploy-prod-123/reflections {
         "sequence_number": 3,
         "what_worked": "Deployment successful; cluster up and healthy",
         "what_failed": "None",
         "pattern_observed": "Two-phase strategy more robust than single-phase",
         "success_signal": "All health checks passed"
       }
   else:
       # Escalate if all strategies fail
       POST /v1/jobs/deploy-prod-123/escalate {
         "reason": "All deployment strategies failed after 3 attempts",
         "notify_to": "ops@company.ai"
       }

9. Complete Job
   POST /v1/jobs/deploy-prod-123/complete {
     "result_pointer": "runtime/artifacts/deploy-prod-123/deployment.json",
     "needs_review": false
   }
   → Job status: COMPLETED
```

## Key Integration Points

### 1. Queue Consumption
- **Where:** Redis keys `flow:{owner}:jobs`
- **How:** Executor calls `redis.rpop(queue_name, timeout=30)`
- **Result:** Job ID returned or None after timeout

### 2. Job Claiming
- **Endpoint:** `POST /v1/jobs/{task_id}/claim`
- **Payload:** `{worker_id, owner, lease_seconds}`
- **Result:** Job status becomes ACTIVE, lease set
- **Why:** Prevents multiple workers from executing same job

### 3. Reflection Writing
- **Endpoint:** `POST /v1/jobs/{task_id}/reflections`
- **Windows:** Pre (seq=1), Mid (seq=2+), Post (seq=final)
- **Idempotency:** Sequence number ensures no duplicates
- **Triggers:** Background skill extraction on completion

### 4. Job Completion
- **Endpoint:** `POST /v1/jobs/{task_id}/complete`
- **Payload:** `{worker_id, result_pointer, needs_review}`
- **Result:** Job status becomes COMPLETED or REVIEW_REQUIRED
- **Idempotency:** Re-submitting same result_pointer returns success

### 5. Error Handling
- **Endpoint:** `POST /v1/jobs/{task_id}/fail`
- **Payload:** `{worker_id, error_message}`
- **Result:** Job status becomes FAILED
- **Retry:** Depends on job.retry_count < job.max_retries

### 6. Escalation
- **Endpoint:** `POST /v1/jobs/{task_id}/escalate`
- **Payload:** `{worker_id, reason, notify_to}`
- **Result:** Job status becomes ESCALATED, notification sent
- **Trigger:** Exhausted retries or human-required decision

## Performance Considerations

### Queue Polling
```python
# Each executor uses blocking pop with timeout
await redis.brpop(f"flow:{owner}:jobs", timeout=30)
# - If job available: pops and processes immediately
# - If no job: blocks for up to 30 seconds (no busy-wait)
# - Wakes up on new job or timeout
```

### Concurrent Execution
```python
# Each executor runs in its own asyncio task
asyncio.create_task(hermes_executor.run())
asyncio.create_task(openclaw_executor.run())
asyncio.create_task(agent_zero_executor.run())

# Can be scaled to multiple instances per owner:
# task1 = asyncio.create_task(HermesExecutor(...).run())
# task2 = asyncio.create_task(HermesExecutor(...).run())
# task3 = asyncio.create_task(HermesExecutor(...).run())
# → 3 Hermes instances, each processing jobs independently
```

### Lease Management
```python
# Prevents stuck jobs:
# - Job claimed with 15-min lease
# - If worker crashes before completing: lease expires
# - Next worker can claim the same job after lease expiration
# - Result: no permanent stuck jobs

# High-risk tasks get longer leases:
# - Hermes: 900s (15 min)
# - OpenClaw: 900s (15 min)
# - Agent Zero: 1800s (30 min)
```

## Troubleshooting

### Jobs not being processed
```
1. Check executor is running
   → grep "Executor started" logs

2. Check Redis queue has jobs
   → redis-cli LLEN flow:hermes:jobs

3. Check job record exists
   → SELECT * FROM job_records WHERE job_id = 'xxx'

4. Check for lease conflicts
   → SELECT * FROM job_records WHERE claimed_by IS NOT NULL AND lease_expires_at > NOW()

5. Check executor logs for errors
   → grep "ERROR" logs | grep executor
```

### Reflections not written
```
1. Check API token in executor config
   → Executor must send Authorization: Bearer token

2. Check reflection endpoint is accessible
   → curl -X POST http://localhost:18000/v1/jobs/test-id/reflections

3. Check sequence numbers are unique
   → SELECT * FROM reflection_records WHERE task_id = 'xxx' ORDER BY sequence_number

4. Check executor logs for reflection write errors
   → grep "reflection" logs
```

### Skill extraction not triggered
```
1. Check skill extraction background job is running
   → grep "Skill extraction" logs

2. Check reflection has pattern_observed
   → SELECT pattern_observed FROM reflection_records WHERE task_id = 'xxx'

3. Check skill_extraction_attempted flag
   → SELECT skill_extraction_attempted FROM reflection_records WHERE task_id = 'xxx'

4. Check skill_records table for new entries
   → SELECT * FROM skill_records WHERE source_reflection_id = 'xxx'
```
