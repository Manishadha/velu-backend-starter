-- 010_projects_slug.sql

ALTER TABLE projects
  ADD COLUMN IF NOT EXISTS slug TEXT;

-- If it's unique per org (recommended)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
     WHERE schemaname='public' AND indexname='projects_org_slug_key'
  ) THEN
    CREATE UNIQUE INDEX projects_org_slug_key ON projects(org_id, slug);
  END IF;
END$$;
