-- FAAS governed worker contract: apply on Hetzner staging before proving run.
-- If historic jobs already duplicate a task_id, stop and reconcile them deliberately.

ALTER TABLE job_records ADD COLUMN IF NOT EXISTS review_required BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE job_records ADD COLUMN IF NOT EXISTS execution_approval_required BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE job_records ADD COLUMN IF NOT EXISTS attempt_number INTEGER NOT NULL DEFAULT 0;
ALTER TABLE job_records ADD COLUMN IF NOT EXISTS claimed_by VARCHAR(100);
ALTER TABLE job_records ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMP;
ALTER TABLE job_records ALTER COLUMN task_id TYPE VARCHAR(100);
ALTER TABLE job_records ALTER COLUMN job_id TYPE VARCHAR(100);
ALTER TABLE job_records ALTER COLUMN task_type TYPE VARCHAR(40);

DO $$
BEGIN
  IF EXISTS (
    SELECT task_id FROM job_records GROUP BY task_id HAVING COUNT(*) > 1
  ) THEN
    RAISE EXCEPTION 'Duplicate job_records.task_id values found; reconcile before applying FAAS idempotency constraint';
  END IF;
END $$;
CREATE UNIQUE INDEX IF NOT EXISTS idx_job_records_task_id_unique ON job_records (task_id);

ALTER TABLE reflection_records ADD COLUMN IF NOT EXISTS sequence_number INTEGER NOT NULL DEFAULT 1;
ALTER TABLE reflection_records ALTER COLUMN task_id TYPE VARCHAR(100);
ALTER TABLE reflection_records ALTER COLUMN job_id TYPE VARCHAR(100);

WITH ordered AS (
  SELECT reflection_id, ROW_NUMBER() OVER (
    PARTITION BY task_id ORDER BY created_at, reflection_id
  ) AS new_sequence
  FROM reflection_records
)
UPDATE reflection_records AS reflections
SET sequence_number = ordered.new_sequence
FROM ordered
WHERE reflections.reflection_id = ordered.reflection_id;

CREATE UNIQUE INDEX IF NOT EXISTS uq_reflection_task_sequence ON reflection_records (task_id, sequence_number);
