# POSTGRES_STATE_SPEC

## Purpose

This document specifies the durable state tables required for FLOW Agent OS.

All runtime state lives in Postgres, indexed by UUID keys, and queryable by status, owner, and task type.

Redis serves as the hot-state layer (queues), but Postgres is the source of truth.

---

## Table: job_records

Tracks every job execution.

```sql
CREATE TABLE job_records (
  job_id UUID PRIMARY KEY,
  task_id UUID NOT NULL,
  owner VARCHAR(20) NOT NULL,  -- openclaw, hermes, agent_zero
  status VARCHAR(20) NOT NULL, -- pending, active, completed, failed, dead_letter, etc.
  task_type VARCHAR(20) NOT NULL,
  risk_tier VARCHAR(10) NOT NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  result_pointer TEXT,
  review_pointer TEXT,
  rollback_pointer TEXT,
  retry_count INTEGER DEFAULT 0,
  max_retries INTEGER DEFAULT 3,
  error_message TEXT,
  escalation_triggered_at TIMESTAMP,
  escalation_notified_to VARCHAR(255),
  INDEX idx_status (status),
  INDEX idx_owner (owner),
  INDEX idx_task_type (task_type),
  INDEX idx_created_at (created_at)
);
```

**Query examples:**
```sql
-- All active jobs for an owner
SELECT * FROM job_records WHERE owner = 'hermes' AND status = 'active';

-- Dead-letter jobs needing escalation
SELECT * FROM job_records WHERE status = 'dead_letter' AND escalation_triggered_at IS NULL;

-- Jobs by type and status
SELECT * FROM job_records WHERE task_type = 'skill_extraction' AND status = 'completed';
```

---

## Table: reflection_records

Captures post-execution reflections for skill extraction.

```sql
CREATE TABLE reflection_records (
  reflection_id UUID PRIMARY KEY,
  task_id UUID NOT NULL,
  job_id UUID NOT NULL,
  owner VARCHAR(20) NOT NULL,
  what_worked TEXT NOT NULL,
  what_failed TEXT NOT NULL,
  pattern_observed TEXT,
  context_type VARCHAR(100),
  tool_sequence TEXT[], -- array of tool names
  success_signal TEXT,
  failure_signal TEXT,
  sensitivity_level VARCHAR(20) DEFAULT 'internal',
  created_at TIMESTAMP NOT NULL,
  skill_extraction_attempted BOOLEAN DEFAULT FALSE,
  skills_extracted UUID[],
  INDEX idx_owner (owner),
  INDEX idx_task_id (task_id),
  INDEX idx_job_id (job_id),
  INDEX idx_created_at (created_at),
  INDEX idx_context_type (context_type),
  FOREIGN KEY (job_id) REFERENCES job_records(job_id)
);
```

**Query examples:**
```sql
-- Reflections ready for skill extraction
SELECT * FROM reflection_records 
WHERE skill_extraction_attempted = FALSE 
ORDER BY created_at DESC;

-- Reflections for a specific context
SELECT * FROM reflection_records 
WHERE context_type = 'intake_form' AND sensitivity_level != 'redacted';
```

---

## Table: skill_records

Reusable execution patterns indexed by task type and context.

```sql
CREATE TABLE skill_records (
  skill_id UUID PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  task_type VARCHAR(20) NOT NULL,
  context_type VARCHAR(100),
  pattern TEXT NOT NULL,
  tool_sequence TEXT[],
  success_signal TEXT,
  failure_signal TEXT,
  confidence FLOAT DEFAULT 0.5,
  times_used INTEGER DEFAULT 0,
  times_succeeded INTEGER DEFAULT 0,
  times_failed INTEGER DEFAULT 0,
  last_used_at TIMESTAMP,
  last_succeeded_at TIMESTAMP,
  source_reflection_id UUID NOT NULL,
  status VARCHAR(20) DEFAULT 'active',
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP,
  version INTEGER DEFAULT 1,
  INDEX idx_task_type (task_type),
  INDEX idx_context_type (context_type),
  INDEX idx_status (status),
  INDEX idx_confidence (confidence DESC),
  FOREIGN KEY (source_reflection_id) REFERENCES reflection_records(reflection_id)
);
```

**Query examples:**
```sql
-- Skills for a task type, sorted by confidence
SELECT * FROM skill_records 
WHERE task_type = 'rewrite' 
  AND status = 'active' 
ORDER BY confidence DESC;

-- Skills for a specific context
SELECT * FROM skill_records 
WHERE context_type = 'blog_post' 
  AND status IN ('active', 'low_confidence');

-- Retrieve top 3 skills for a new task
SELECT * FROM skill_records 
WHERE task_type = 'markdown_generation' 
  AND context_type = 'intake_form'
  AND status = 'active'
ORDER BY confidence DESC 
LIMIT 3;
```

---

## Table: task_envelopes (optional, for reference)

Can optionally store task envelopes in Postgres for audit and query purposes.

```sql
CREATE TABLE task_envelopes (
  task_id UUID PRIMARY KEY,
  title VARCHAR(200) NOT NULL,
  goal TEXT NOT NULL,
  task_type VARCHAR(20) NOT NULL,
  risk_tier VARCHAR(10) NOT NULL,
  preferred_owner VARCHAR(20) NOT NULL,
  source VARCHAR(20) NOT NULL,
  inputs JSONB,
  output_required TEXT,
  review_required BOOLEAN DEFAULT FALSE,
  rollback_required BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL,
  created_by VARCHAR(255),
  INDEX idx_task_type (task_type),
  INDEX idx_risk_tier (risk_tier),
  INDEX idx_created_at (created_at)
);
```

---

## Indexes and Performance

**Critical indexes:**
- `job_records.status` — frequent queries for active/failed jobs
- `job_records.owner` — owner-specific dashboards
- `skill_records.task_type` + `confidence` — skill retrieval on new tasks
- `reflection_records.skill_extraction_attempted` — extraction queue

**Retention policy:**
- `job_records`: Archive after 90 days, keep 5 years for audit
- `reflection_records`: Keep indefinitely (skill source of truth)
- `skill_records`: Keep indefinitely, retire low-confidence after 1 year

---

## Connection Pool

Recommend:
- Min pool size: 5 connections
- Max pool size: 20 connections
- Idle timeout: 30s
- Retry on connection loss: enabled

Use async/await patterns (asyncpg in Python, or equivalent) to avoid blocking.

---

## Migrations

Use Alembic (SQLAlchemy) or equivalent for schema management.

All migrations are versioned and committed to git.
Rollback scripts are tested before production deployment.

---

## Monitoring

Track:
- Query performance (slow query log)
- Connection pool saturation
- Table sizes (especially reflection_records growth)
- Index usage

Alert if:
- Dead-letter queue > 10 jobs
- Reflection_records → skill_records extraction lag > 1 hour
- Postgres connection pool exhausted
