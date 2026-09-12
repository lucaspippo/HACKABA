"""Provisions the dedicated database the suite runs against.

The suite must never open a connection to the database backend/.env points
the DEV server at: conftest.py deletes and reseeds the `demo` tenant's
auth_credentials at import time, so sharing one database meant a `pytest`
run silently rewrote every demo user's dev-server login password. See
tests/test_test_db_isolation.py for the regression guard.

`ensure_test_database()` derives a sibling database name (`polpilot` ->
`polpilot_test`), creates it if absent, replicates the app role's grants
into it, migrates it to head, and then repoints DATABASE_URL /
APP_DATABASE_URL at it *in os.environ* -- which is what makes the redirect
total: core.db.engine reads those two vars, and every subprocess the suite
spawns inherits them through **os.environ.

Deliberately not named test_*.py so pytest doesn't collect it.
"""
from __future__ import annotations

import os
import subprocess
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Set once per suite RUN, not per process: subprocess-spawning tests re-import
# conftest, and re-running `alembic upgrade head` for each of them would cost
# seconds apiece. Lives in os.environ so it propagates to those subprocesses.
_READY_FLAG = "_POLPILOT_TEST_DB_READY"

# The URLs actually resolved, published so a spawned subprocess re-importing
# conftest reuses them instead of deriving a second `_test` suffix.
_RESOLVED_ADMIN = "_POLPILOT_TEST_DB_ADMIN_URL"
_RESOLVED_APP = "_POLPILOT_TEST_DB_APP_URL"


def _render(url) -> str:
    """str(URL) replaces the password with '***' -- SQLAlchemy hides it by
    default, which produces a URL that parses fine and then fails to
    authenticate. Always render credentials explicitly."""
    return url.render_as_string(hide_password=False)


def _sibling_test_url(url: str, suffix: str = "_test") -> str:
    """postgresql://h/polpilot -> postgresql://h/polpilot_test (query intact)."""
    parsed = make_url(url)
    return _render(parsed.set(database=f"{parsed.database}{suffix}"))


def _maintenance_url(url: str) -> str:
    """The same server, but the always-present `postgres` database -- you
    cannot CREATE DATABASE while connected to the one being created."""
    return _render(make_url(url).set(database="postgres"))


def _create_database_if_missing(admin_url: str, test_url: str) -> None:
    nombre = make_url(test_url).database
    # CREATE DATABASE cannot run inside a transaction block.
    engine = create_engine(_maintenance_url(admin_url), isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        existe = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": nombre}
        ).scalar_one_or_none()
        if not existe:
            conn.execute(text(f'CREATE DATABASE "{nombre}"'))
    engine.dispose()


def _grant_app_role(admin_url: str, test_url: str, app_url: str) -> None:
    """Replicate docker/init-app-role.sql's grants inside the new database.

    They can't be inherited: GRANT ... ON DATABASE and ALTER DEFAULT
    PRIVILEGES ... IN SCHEMA are both per-database, and the init script only
    ever ran against the dev database. Without this the app role connects but
    every table a migration creates is unreadable to it.
    """
    app_role = make_url(app_url).username
    admin_role = make_url(admin_url).username
    nombre = make_url(test_url).database
    engine = create_engine(_maintenance_url(admin_url), isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(f'GRANT CONNECT ON DATABASE "{nombre}" TO "{app_role}"'))
    engine.dispose()

    engine = create_engine(test_url)
    with engine.begin() as conn:
        conn.execute(text(f'GRANT USAGE ON SCHEMA public TO "{app_role}"'))
        conn.execute(text(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE \"{admin_role}\" IN SCHEMA public "
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO \"{app_role}\""
        ))
        conn.execute(text(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE \"{admin_role}\" IN SCHEMA public "
            f"GRANT USAGE, SELECT ON SEQUENCES TO \"{app_role}\""
        ))
        # Tables created by an EARLIER suite run predate the default
        # privileges above, so grant on what already exists too (no-op on a
        # freshly created database).
        conn.execute(text(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES "
            f"IN SCHEMA public TO \"{app_role}\""
        ))
        conn.execute(text(
            f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO \"{app_role}\""
        ))
    engine.dispose()


def _migrate(test_admin_url: str) -> None:
    entorno = {**os.environ, "DATABASE_URL": test_admin_url}
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR, env=entorno, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "alembic upgrade head failed against the test database:\n"
            f"{proc.stdout}\n{proc.stderr}"
        )


def ensure_test_database() -> tuple[str, str]:
    """Point DATABASE_URL / APP_DATABASE_URL at a migrated test database.

    Returns the (admin, app) URLs now in effect. Idempotent across the suite
    run; safe to call from a re-imported conftest in a spawned subprocess.
    """
    # core.db.engine normally does this on import, but it is imported AFTER
    # us on purpose (see conftest.py), so the two URLs aren't in the
    # environment yet.
    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(BACKEND_DIR, ".env"))
    except ImportError:
        pass  # without python-dotenv the URLs must come from the environment

    # Already redirected by an ancestor process: reuse its URLs verbatim.
    # Re-deriving here would suffix a suffixed name (polpilot_test_test) —
    # subprocess-spawning tests inherit DATABASE_URL through **os.environ and
    # then re-import conftest, so this path is the common one, not the edge.
    ya_resuelto = os.environ.get(_RESOLVED_ADMIN)
    ya_resuelto_app = os.environ.get(_RESOLVED_APP)
    if os.environ.get(_READY_FLAG) and ya_resuelto and ya_resuelto_app:
        os.environ["DATABASE_URL"] = ya_resuelto
        os.environ["APP_DATABASE_URL"] = ya_resuelto_app
        return ya_resuelto, ya_resuelto_app

    admin_dev = os.environ["DATABASE_URL"]
    app_dev = os.environ["APP_DATABASE_URL"]

    test_admin = os.environ.get("POLPILOT_TEST_DATABASE_URL") or _sibling_test_url(admin_dev)
    test_app = os.environ.get("POLPILOT_TEST_APP_DATABASE_URL") or _sibling_test_url(app_dev)

    if make_url(test_admin).database == make_url(admin_dev).database:
        raise RuntimeError(
            "the test database resolves to the same name as the dev database "
            f"({make_url(admin_dev).database!r}) -- refusing to run the suite "
            "against the dev server's data. Set POLPILOT_TEST_DATABASE_URL."
        )

    if not os.environ.get(_READY_FLAG):
        _create_database_if_missing(admin_dev, test_admin)
        _grant_app_role(admin_dev, test_admin, test_app)
        _migrate(test_admin)
        os.environ[_READY_FLAG] = "1"

    # Last: everything downstream (core.db.engine, spawned subprocesses,
    # alembic) reads these.
    os.environ["DATABASE_URL"] = test_admin
    os.environ["APP_DATABASE_URL"] = test_app
    os.environ[_RESOLVED_ADMIN] = test_admin
    os.environ[_RESOLVED_APP] = test_app
    return test_admin, test_app
