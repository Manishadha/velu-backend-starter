-- PostgreSQL example RLS policies (adjust if you use SQLite locally)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS tenant (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app_user (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  email text UNIQUE NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS membership (
  tenant_id uuid REFERENCES tenant(id) ON DELETE CASCADE,
  user_id uuid REFERENCES app_user(id) ON DELETE CASCADE,
  role text NOT NULL DEFAULT 'user',
  PRIMARY KEY (tenant_id, user_id)
);

CREATE TABLE IF NOT EXISTS note (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
  owner_id uuid NOT NULL REFERENCES app_user(id) ON DELETE SET NULL,
  title text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE note ENABLE ROW LEVEL SECURITY;

CREATE POLICY note_isolated_per_tenant
ON note
USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
