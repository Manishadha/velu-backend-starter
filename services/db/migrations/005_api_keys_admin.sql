-- 005_api_keys_admin.sql
-- Hardening for org-scoped API keys (Phase 2.2)

ALTER TABLE api_keys
  ADD COLUMN IF NOT EXISTS scopes text[] NOT NULL DEFAULT '{}'::text[],
  ADD COLUMN IF NOT EXISTS last_used_at timestamptz,
  ADD COLUMN IF NOT EXISTS revoked_at timestamptz,
  ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();

-- Ensure "name" is unique per org (recommended)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_indexes
    WHERE schemaname = 'public'
      AND indexname = 'ux_api_keys_org_name'
  ) THEN
    CREATE UNIQUE INDEX ux_api_keys_org_name ON api_keys (org_id, name);
  END IF;
END$$;

-- Fast lookup by hashed_key (and only active keys)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_indexes
    WHERE schemaname = 'public'
      AND indexname = 'ix_api_keys_hashed_key_active'
  ) THEN
    CREATE INDEX ix_api_keys_hashed_key_active
      ON api_keys (hashed_key)
      WHERE revoked_at IS NULL;
  END IF;
END$$;
