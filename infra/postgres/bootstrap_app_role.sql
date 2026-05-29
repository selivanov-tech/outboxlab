-- Cluster-level role used by tests + (optionally) prod runtime to exercise
-- and benefit from RLS as a non-superuser.
--
-- WHY here and not inside an Alembic migration:
--   * roles are cluster-scoped, not database-scoped; running CREATE ROLE
--     from a migration assumes CREATEROLE/superuser on the migration
--     connection and would collide if the same cluster ever hosts a
--     second OutboxLab DB.
--   * prod (Neon) provides a pre-configured app role for the runtime
--     connection — this file is for dev (compose init) + CI (workflow
--     step). Prod should never need to run it.
--
-- Mounted into the dev postgres image at
-- /docker-entrypoint-initdb.d/01-bootstrap-app-role.sql via compose, and
-- piped through psql in the GitHub Actions CI workflow.
--
-- Idempotent so re-runs on CI retries are harmless. Re-runs in dev are
-- a no-op anyway — the entrypoint scripts only execute once, on an
-- empty data dir.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'outboxlab_app') THEN
    CREATE ROLE outboxlab_app NOLOGIN;
  END IF;
END$$;

GRANT USAGE ON SCHEMA public TO outboxlab_app;

-- ALTER DEFAULT PRIVILEGES catches future tables (the migration creates
-- them right after this file runs). Existing tables get covered by an
-- explicit GRANT in case the file is ever re-run after migration.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO outboxlab_app;

GRANT SELECT, INSERT, UPDATE, DELETE
  ON ALL TABLES IN SCHEMA public TO outboxlab_app;
