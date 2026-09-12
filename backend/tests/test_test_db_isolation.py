"""The suite must run against a dedicated test database, never the one the
developer's backend/.env points the dev server at.

Regression guard for a real bug: tests/conftest.py deletes and reseeds the
`demo` tenant's rows in auth_credentials at import time (with
DEMO_TEST_PASSWORD). While the suite shared the dev server's database, merely
collecting tests silently rewrote every demo user's login password, so nobody
could log into the dev server afterwards -- the stored bcrypt hash no longer
matched the seeded fixed password, and the plaintext was never recorded
anywhere.

Isolating the suite's database is what makes that class of bug impossible: a
run that never opens a connection to the dev database cannot corrupt it.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text

from core.db.engine import get_admin_engine

from .conftest import DEMO_TEST_PASSWORD

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _dev_database_url() -> str | None:
    """The admin URL backend/.env declares for the DEV server, read straight
    off disk -- conftest overwrites os.environ["DATABASE_URL"] with the test
    URL, so the environment can't tell us what the dev server uses."""
    try:
        from dotenv import dotenv_values
    except ImportError:
        return None
    valores = dotenv_values(os.path.join(REPO_ROOT, "backend", ".env"))
    return valores.get("DATABASE_URL")


def _database_name(url: str) -> str:
    return url.rsplit("/", 1)[-1].split("?")[0]


def test_suite_connects_to_a_dedicated_test_database():
    """The engine every repo/test goes through must not be the dev database."""
    dev_url = _dev_database_url()
    if not dev_url:
        pytest.skip("backend/.env declares no DATABASE_URL to compare against")

    with get_admin_engine().begin() as conn:
        en_uso = conn.execute(text("SELECT current_database()")).scalar_one()

    assert en_uso != _database_name(dev_url), (
        f"the suite is connected to {en_uso!r}, the same database "
        f"backend/.env points the dev server at -- conftest's credential "
        f"reset will clobber the dev server's demo logins"
    )


def test_dev_database_demo_credentials_are_untouched_by_the_suite():
    """The dev database's demo passwords must never be the suite's password."""
    dev_url = _dev_database_url()
    if not dev_url:
        pytest.skip("backend/.env declares no DATABASE_URL to inspect")

    import bcrypt

    try:
        engine = create_engine(dev_url)
        with engine.begin() as conn:
            filas = conn.execute(text(
                "SELECT c.username, c.password_hash FROM auth_credentials c "
                "JOIN tenants t ON t.id = c.tenant_id WHERE t.slug = 'demo'"
            )).fetchall()
    except Exception as e:  # dev DB absent on CI / a fresh clone
        pytest.skip(f"dev database not reachable ({type(e).__name__})")

    if not filas:
        pytest.skip("dev database has no seeded demo credentials to check")

    clobbered = [
        usuario for usuario, hash_guardado in filas
        if bcrypt.checkpw(DEMO_TEST_PASSWORD.encode("utf-8"), hash_guardado.encode("utf-8"))
    ]
    assert not clobbered, (
        f"the suite overwrote the dev database's demo password for "
        f"{clobbered} -- those users can no longer log into the dev server"
    )
