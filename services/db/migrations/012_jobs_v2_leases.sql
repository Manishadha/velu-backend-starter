-- services/db/migrations/012_jobs_v2_leases.sql

ALTER TABLE jobs_v2
  ADD COLUMN IF NOT EXISTS claimed_by TEXT,
  ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS finished_at TIMESTAMPTZ;

-- Claim scanning index (supports queued + ordering)
CREATE INDEX IF NOT EXISTS idx_jobs_v2_claim
  ON jobs_v2 (status, priority DESC, created_at ASC);

-- Lease reclaim index (supports working + expired)
CREATE INDEX IF NOT EXISTS idx_jobs_v2_lease_reclaim
  ON jobs_v2 (status, lease_expires_at);


