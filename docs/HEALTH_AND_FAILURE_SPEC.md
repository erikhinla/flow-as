# HEALTH_AND_FAILURE_SPEC

## Purpose

This document defines health checks, failure modes, and recovery procedures for FLOW Agent OS.

---

## Health Check Endpoints

### hermes-control `/health`

**Endpoint:** `GET /health`

**Response (Healthy):**
```json
{
  "status": "healthy",
  "version": "1.0",
  "timestamp": "2026-04-03T12:34:56Z",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "workers": {
      "openclaw": "ok",
      "hermes": "ok",
      "agent_zero": "ok"
    }
  },
  "queues": {
    "pending": 0,
    "queued": 2,
    "active": 1,
    "review_required": 0,
    "failed": 0,
    "dead_letter": 0,
    "escalated": 0
  },
  "metrics": {
    "jobs_completed_1h": 12,
    "jobs_failed_1h": 0,
    "reflection_extraction_lag_seconds": 5,
    "oldest_pending_job_seconds": 120
  }
}
```

**Response (Degraded):**
```json
{
  "status": "degraded",
  "timestamp": "2026-04-03T12:34:56Z",
  "checks": {
    "database": "ok",
    "redis": "error: connection refused",
    "workers": {
      "openclaw": "ok",
      "hermes": "ok",
      "agent_zero": "timeout"
    }
  },
  "alerts": [
    "Redis unreachable for 30 seconds",
    "Agent Zero worker unresponsive for 60 seconds",
    "Dead-letter queue has 2 jobs"
  ]
}
```

**Status codes:**
- `200 OK` → healthy
- `503 Service Unavailable` → degraded or unhealthy

---

## Liveness Checks

Each worker should report its own liveness.

### OpenClaw `/ping`

**Endpoint:** `GET /ping`

**Response:**
```json
{
  "status": "alive",
  "timestamp": "2026-04-03T12:34:56Z",
  "processed_tasks_1h": 25,
  "last_task": "2026-04-03T12:34:00Z",
  "validation_errors": 0
}
```

### Hermes `/ping`

**Endpoint:** `GET /ping`

**Response:**
```json
{
  "status": "alive",
  "timestamp": "2026-04-03T12:34:56Z",
  "active_jobs": 2,
  "completed_tasks_1h": 8,
  "reflection_queue_depth": 0,
  "skill_extraction_lag_seconds": 3
}
```

### Agent Zero `/ping`

**Endpoint:** `GET /ping`

**Response:**
```json
{
  "status": "alive",
  "timestamp": "2026-04-03T12:34:56Z",
  "active_jobs": 1,
  "last_task": "2026-04-03T12:33:45Z",
  "docker_socket": "ok"
}
```

---

## Critical Failure Modes

### 1. Database Unreachable

**Detection:**
- Postgres connection fails
- hermes-control cannot write job_records
- hermes-control `/health` returns 503

**Immediate:**
- Stop accepting new tasks
- Mark all `active` jobs as `blocked`
- Alert: EMAIL + Slack

**Recovery:**
```bash
# Check Postgres status
docker exec flow-postgres pg_isready

# If down, restart
docker restart flow-postgres

# Once up, hermes-control auto-recovers
# It will resume processing queued jobs
```

### 2. Redis Unreachable

**Detection:**
- Redis connection fails
- Queue operations timeout
- hermes-control `/health` shows redis: error

**Immediate:**
- Jobs can still complete (they're in Postgres)
- Queue operations block
- Alert: EMAIL + Slack

**Recovery:**
```bash
# Check Redis status
docker exec flow-redis redis-cli ping

# If down, restart
docker restart flow-redis

# Reconciliation job will re-populate queue from Postgres
```

### 3. Worker Timeout

**Detection:**
- Worker unresponsive for > 60 seconds
- hermes-control cannot reach `/ping`
- Status changes from `active` → `escalated`

**Immediate:**
- Set job `status = escalated`
- Preserve execution context
- Alert: you (escalation notification)

**Recovery:**
```bash
# Check worker health
curl http://hermes:50090/ping

# If down, restart
docker restart hermes

# Acknowledge escalation and retry
# Set job status = queued, retry_count = 0
```

### 4. Skill Extraction Lag

**Detection:**
- Reflection records accumulate in `skill_extraction_attempted = FALSE`
- Lag > 5 minutes

**Immediate:**
- Log warning
- Skills not available for new tasks
- No escalation (background process failure)

**Recovery:**
```bash
# Manually trigger extraction
curl -X POST http://hermes-control:8080/internal/skill-extraction

# Or restart Hermes worker
docker restart hermes
```

### 5. Dead-Letter Queue Growing

**Detection:**
- `dead_letter` queue > 3 jobs
- Check `/health` response

**Immediate:**
- Alert: you
- Stop processing new tasks? Depends on cause
- Investigate root cause

**Recovery:**
```bash
# Investigate dead-letter jobs
SELECT * FROM job_records WHERE status = 'dead_letter' ORDER BY escalation_triggered_at;

# Fix root cause (e.g., API key expired, schema mismatch)

# Retry with new fix
UPDATE job_records 
SET retry_count = 0, status = 'queued' 
WHERE job_id = ?;
```

### 6. Callback Failure

**Detection:**
- Job completes but callback to hermes-control fails
- Idempotency key prevents duplicate
- Job stuck in `active` state

**Immediate:**
- Retry callback with exponential backoff
- After 3 retries, escalate

**Recovery:**
```bash
# Check hermes-control health
curl http://hermes-control:8080/health

# If down, restart
docker restart hermes-control

# Callback will auto-retry
# If callback lost, manually mark job complete
UPDATE job_records 
SET status = 'completed', updated_at = NOW() 
WHERE job_id = ? AND status = 'active';
```

---

## Monitoring Thresholds

### Alert If:

| Metric | Threshold | Action |
|--------|-----------|--------|
| Dead-letter queue | > 3 jobs | Investigate |
| Escalated queue | > 1 job | You need approval |
| Active jobs | > 10 per owner | Worker overloaded |
| Skill extraction lag | > 5 min | Restart extractor |
| Postgres slow query | > 1s | Check indexes |
| Redis memory | > 80% | Review eviction policy |
| Job timeout | > 5 min above SLA | Escalate |

---

## Retry Policy By Failure Type

### Transient Failures (auto-retry)
- Network timeout
- Database connection temporarily lost
- Worker temporarily unresponsive

Retry: exponential backoff, max 3 attempts

### Permanent Failures (dead-letter immediately)
- Schema validation failed
- Unauthorized (API key invalid)
- Task goal impossible (e.g., "classify file that doesn't exist")

Retry: manual only (requires root cause fix)

### Intermittent Failures (check first)
- Callback fails (might be idempotency issue)
- Worker slow (might recover)

Retry: once automatically, then escalate if persists

---

## Reconciliation Loop

hermes-control runs reconciliation every 5 minutes:

```python
async def reconciliation_loop():
    while True:
        # 1. Check for jobs in Redis but missing in Postgres
        redis_jobs = await redis.keys("*:jobs")
        postgres_jobs = await db.query(JobRecord).all()
        
        for redis_job in redis_jobs:
            if redis_job not in [j.job_id for j in postgres_jobs]:
                # Job orphaned in Redis, remove it
                await redis.delete(redis_job)
                log.warning(f"Removed orphaned Redis key: {redis_job}")
        
        # 2. Check for Postgres jobs stuck in 'active' for too long
        stuck_jobs = await db.query(JobRecord).filter(
            JobRecord.status == 'active',
            JobRecord.updated_at < (now() - timedelta(hours=1))
        ).all()
        
        for job in stuck_jobs:
            # Escalate if no update in 1+ hour
            job.status = 'escalated'
            job.escalation_triggered_at = now()
            await db.commit()
            await notify_escalation(job)
        
        # 3. Check for failed jobs that haven't been retried yet
        failed_jobs = await db.query(JobRecord).filter(
            JobRecord.status == 'failed',
            JobRecord.retry_count < JobRecord.max_retries
        ).all()
        
        for job in failed_jobs:
            # Re-enqueue for retry
            job.status = 'queued'
            await db.commit()
            await redis.lpush(f"{job.owner}:jobs", job.job_id)
        
        await asyncio.sleep(300)  # 5 min
```

---

## Alerting

Alert destinations:

1. **Email** → escalation_notified_to (you)
   - Dead-letter jobs
   - Escalated jobs
   - Critical failures

2. **Slack** → #ops (if configured)
   - Degraded health
   - Worker timeouts
   - High queue depth

3. **Dashboard** → Portainer UI
   - Queue status
   - Job status
   - Worker status

---

## Recovery Runbook

**If hermes-control is down:**
```bash
docker-compose logs hermes-control
docker-compose restart hermes-control
curl http://hermes-control:8080/health
```

**If Postgres is down:**
```bash
docker-compose logs flow-postgres
docker-compose restart flow-postgres
# Wait 30 seconds for recovery
curl http://hermes-control:8080/health
```

**If Redis is down:**
```bash
docker-compose logs flow-redis
docker-compose restart flow-redis
# Reconciliation will re-populate queues
```

**If all workers are down:**
```bash
docker-compose restart openclaw hermes agent_zero
# Check /health for recovery status
```

**If you're not sure:**
```bash
docker-compose ps
docker-compose logs --tail=50 hermes-control
curl http://hermes-control:8080/health | jq .
```
