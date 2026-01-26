-- Ensure column exists (safe, idempotent)
ALTER TABLE roles
  ADD COLUMN IF NOT EXISTS is_system BOOLEAN NOT NULL DEFAULT FALSE;

-- Seed minimal system roles per organization
-- Safe to run multiple times

INSERT INTO roles (org_id, name, is_system)
SELECT o.id, r.name, TRUE
FROM organizations o
CROSS JOIN (
    VALUES
      ('owner'),
      ('admin'),
      ('member')
) AS r(name)
ON CONFLICT (org_id, name) DO NOTHING;
