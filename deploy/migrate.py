"""Render's preDeployCommand: bring the schema to head before any instance
of the new version starts.

Why this is not in boot.py any more: when Alembic ran inside the container,
a failed migration exited the process, the healthcheck failed, and the
service went DOWN. As a pre-deploy step the deploy fails and the previously
running instance keeps serving — the failure stops being an outage.

It is also what keeps migrations single-writer if the service is ever split
into several (see D2 in the design doc): a pre-deploy step runs once per
deploy, while N booting containers would race.

Not here yet, deliberately: creating the restricted NOBYPASSRLS role that
APP_DATABASE_URL connects as. On Supabase that role already exists
(docker/init-app-role.sql is its local equivalent). A managed Render Postgres
has no docker-entrypoint-initdb.d hook, so when the database moves (D12),
this is the file that role bootstrap belongs in.
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BACKEND = os.path.join(ROOT, "backend")

sys.path.insert(0, BACKEND)
import deploy_guard  # noqa: E402  (needs BACKEND on the path first)


def main() -> None:
    tenant = deploy_guard.require_tenant()
    print(f"[migrate] tenant={tenant}", flush=True)

    r = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True, text=True, cwd=BACKEND, timeout=300,
    )
    if r.returncode != 0:
        print(r.stdout[-1500:] + r.stderr[-1500:], flush=True)
        print("[migrate][X] alembic upgrade head failed — the deploy stops "
              "here and the running instance keeps serving", flush=True)
        raise SystemExit(1)
    print("[migrate] schema at head", flush=True)


if __name__ == "__main__":
    main()
