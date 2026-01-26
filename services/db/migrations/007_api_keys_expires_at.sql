ALTER TABLE api_keys
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at
ON api_keys (expires_at);

CREATE INDEX IF NOT EXISTS ix_api_keys_hashed_key_active_expires
ON api_keys (hashed_key)
WHERE revoked_at IS NULL;
