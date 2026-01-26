-- services/db/migrations/011_jobs_v2_priority.sql
BEGIN;

ALTER TABLE jobs_v2
  ADD COLUMN IF NOT EXISTS priority integer NOT NULL DEFAULT 0;

-- Helpful index for the claim query (queued jobs ordered by priority + created_at)
CREATE INDEX IF NOT EXISTS idx_jobs_v2_claim
  ON jobs_v2 (status, priority DESC, created_at ASC);

COMMIT;
