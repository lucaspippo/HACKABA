"""Postgres URL normalization (core/db/url.py) and its use in Alembic.

Managed providers hand out `postgresql://…`, which SQLAlchemy maps to the
psycopg2 dialect — and only psycopg v3 is installed (requirements.txt).
Without normalization the first query against such a URL dies with
ModuleNotFoundError, so this is the guard for that whole class of outage.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory

from core.db.url import normalize_driver

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("given", [
    "postgresql://u:p@host:5432/db",
    "postgres://u:p@host:5432/db",
    "postgresql+psycopg://u:p@host:5432/db",
])
def test_every_postgres_spelling_lands_on_psycopg(given):
    assert normalize_driver(given).startswith("postgresql+psycopg://")


def test_the_rest_of_the_url_is_untouched():
    got = normalize_driver("postgres://u:p@host:6543/db?sslmode=require")
    assert got == "postgresql+psycopg://u:p@host:6543/db?sslmode=require"


def test_an_explicit_other_driver_is_left_alone():
    # Someone who deliberately asked for a different driver gets it: this
    # normalizer exists to fix an omission, not to override a choice.
    given = "postgresql+asyncpg://u:p@host:5432/db"
    assert normalize_driver(given) == given


def test_a_non_postgres_url_is_left_alone():
    given = "sqlite:///tmp/x.db"
    assert normalize_driver(given) == given


def test_an_empty_url_is_passed_through_unchanged():
    # engine.py raises its own KeyError for a missing variable; this helper
    # must not turn that into a confusing parse error.
    assert normalize_driver("") == ""


def _sqlalchemy_url_alembic_would_use(monkeypatch: pytest.MonkeyPatch, given: str) -> str:
    """Run migrations/env.py through Alembic's own loader and report the
    `sqlalchemy.url` it lands on, exercising the real env.py module rather
    than re-checking normalize_driver() in isolation.

    Runs fully offline (as_sql=True): Alembic renders SQL without opening a
    connection, so this needs no live database and never invokes a
    migration's upgrade()/downgrade() (fn returns no revisions to run).
    """
    monkeypatch.setenv("DATABASE_URL", given)
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    # Absolute path so this does not depend on the process's cwd.
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    script = ScriptDirectory.from_config(cfg)
    with EnvironmentContext(cfg, script, fn=lambda rev, context: [], as_sql=True):
        script.run_env()
    return cfg.get_main_option("sqlalchemy.url")


@pytest.mark.parametrize("given", [
    "postgresql://u:p@host:5432/db",
    "postgres://u:p@host:5432/db",
])
def test_env_py_normalizes_database_url_before_alembic_builds_its_engine(monkeypatch, given):
    # Regression test for the bug where migrations/env.py set
    # `sqlalchemy.url` straight from os.environ["DATABASE_URL"], bypassing
    # normalize_driver entirely. Before the fix, env.py left the bare
    # `postgresql://`/`postgres://` URL untouched here, so this assertion
    # fails against the pre-fix env.py and passes once it calls
    # normalize_driver like engine.py's builders already do.
    got = _sqlalchemy_url_alembic_would_use(monkeypatch, given)
    assert got == "postgresql+psycopg://u:p@host:5432/db"
