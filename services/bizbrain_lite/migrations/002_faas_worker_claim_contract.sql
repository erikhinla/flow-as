-- FAAS governed worker contract: apply on Hetzner staging before proving run.
-- Safe to re-run on a database that already has these columns/indexes.

ALTER TABLE job_records ADD COLUMN IF NOT EXISTS review_required BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE job_records ADD COLUMN IF NOT EXISTS execution_approval_required BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE job_records ADD COLUMN IF NOT EXISTS attempt_number INTEGER NOT NULL DEFAULT 0;
ALTER TABLE job_records ADD COLUMN IF NOT EXISTS claimed_by VARCHAR(100);
ALTER TABLE job_records ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMP;
ALTER TABLE job_records ALTER COLUMN task_id TYPE VARCHAR(100);
ALTER TABLE job_records ALTER COLUMN job_id TYPE VARCHAR(100);
ALTER TABLE job_records ALTER COLUMN task_type TYPE VARCHAR(40);
CREATE UNIQUE INDEX IF NOT EXISTS idx_job_records_task_id_unique ON job_records (task_id);

ALTER TABLE reflection_records ADD COLUMN IF NOT EXISTS sequence_number INTEGER NOT NULL DEFAULT 1;
ALTER TABLE reflection_records ALTER COLUMN task_id TYPE VARCHAR(100);
ALTER TABLE reflection_records ALTER COLUMN job_id TYPE VARCHAR(100);
CREATE UNIQUE INDEX IF NOT EXISTS uq_reflection_task_sequence ON reflection_records (task_id, sequence_number);
