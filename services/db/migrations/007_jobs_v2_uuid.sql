-- 007_jobs_v2_uuid.sql
-- Ensure jobs_v2 uses UUID ids (tests assume uuid: "... WHERE id = %s::uuid").

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
DECLARE
  id_type text;
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='public' AND table_name='jobs_v2'
  ) THEN
    SELECT data_type
      INTO id_type
      FROM information_schema.columns
     WHERE table_schema='public'
       AND table_name='jobs_v2'
       AND column_name='id'
     LIMIT 1;

    -- If old schema uses bigint, rebuild to uuid.
    IF id_type = 'bigint' THEN
      EXECUTE 'ALTER TABLE jobs_v2 RENAME TO jobs_v2__old';

      EXECUTE $q$
        CREATE TABLE jobs_v2 (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          legacy_id bigint UNIQUE,
          org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
          project_id uuid REFERENCES projects(id) ON DELETE SET NULL,
          task text NOT NULL,
          status text NOT NULL DEFAULT 'queued',
          payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          result jsonb,
          error jsonb,
          priority integer NOT NULL DEFAULT 0,
          attempts integer NOT NULL DEFAULT 0,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          actor_type text NOT NULL DEFAULT 'api_key',
          actor_id text
        );
      $q$;

      -- Copy rows (keep old numeric id in legacy_id)
      EXECUTE $q$
        INSERT INTO jobs_v2 (
          legacy_id, org_id, project_id, task, status, payload,
          result, error, priority, attempts, created_at, updated_at,
          actor_type, actor_id
        )
        SELECT
          id, org_id, project_id, task, status, payload,
          result, error, priority, attempts, created_at, updated_at,
          COALESCE(actor_type, 'api_key'), actor_id
        FROM jobs_v2__old;
      $q$;

      EXECUTE 'DROP TABLE jobs_v2__old CASCADE';
    END IF;
  ELSE
    -- Fresh DB: create correct schema
    EXECUTE $q$
      CREATE TABLE jobs_v2 (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        project_id uuid REFERENCES projects(id) ON DELETE SET NULL,
        task text NOT NULL,
        status text NOT NULL DEFAULT 'queued',
        payload jsonb NOT NULL DEFAULT '{}'::jsonb,
        result jsonb,
        error jsonb,
        priority integer NOT NULL DEFAULT 0,
        attempts integer NOT NULL DEFAULT 0,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        actor_type text NOT NULL DEFAULT 'api_key',
        actor_id text
      );
    $q$;
  END IF;

  -- Ensure columns/defaults even if table existed with uuid already
  EXECUTE 'ALTER TABLE jobs_v2 ADD COLUMN IF NOT EXISTS actor_type text';
  EXECUTE 'ALTER TABLE jobs_v2 ADD COLUMN IF NOT EXISTS actor_id text';
  EXECUTE 'ALTER TABLE jobs_v2 ALTER COLUMN actor_type SET DEFAULT ''api_key''';
  EXECUTE 'ALTER TABLE jobs_v2 ALTER COLUMN actor_type SET NOT NULL';

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname='public' AND indexname='ix_jobs_v2_org_created_at'
  ) THEN
    EXECUTE 'CREATE INDEX ix_jobs_v2_org_created_at ON jobs_v2 (org_id, created_at DESC)';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname='public' AND indexname='ix_jobs_v2_project'
  ) THEN
    EXECUTE 'CREATE INDEX ix_jobs_v2_project ON jobs_v2 (project_id)';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname='public' AND indexname='ix_jobs_v2_status'
  ) THEN
    EXECUTE 'CREATE INDEX ix_jobs_v2_status ON jobs_v2 (status)';
  END IF;
END $$;
