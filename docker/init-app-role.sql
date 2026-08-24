-- Runs once, at first container init (postgres image convention:
-- docker-entrypoint-initdb.d/*.sql executes before anything else, before any
-- app table exists). Creates the role the application actually connects as.
--
-- Why this exists: POSTGRES_USER (polpilot) is the cluster's bootstrap
-- superuser. Superusers bypass Row-Level Security unconditionally, even on
-- tables with FORCE ROW LEVEL SECURITY — so the app must never connect as
-- polpilot for tenant-scoped queries, or RLS silently does nothing.
-- polpilot_app has no such bypass, and ALTER DEFAULT PRIVILEGES means every
-- table any future migration creates (as polpilot) is automatically
-- readable/writable by polpilot_app — no per-migration re-granting needed.

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'polpilot_app') THEN
    CREATE ROLE polpilot_app LOGIN PASSWORD 'polpilot_app'
      NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
  END IF;
END
$$;

GRANT CONNECT ON DATABASE polpilot TO polpilot_app;
GRANT USAGE ON SCHEMA public TO polpilot_app;

ALTER DEFAULT PRIVILEGES FOR ROLE polpilot IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO polpilot_app;
ALTER DEFAULT PRIVILEGES FOR ROLE polpilot IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO polpilot_app;
