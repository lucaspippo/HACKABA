"""Seeding must ASSERT the fixed demo password, not merely fill in blanks.

The bug this guards: seed_db.run() only set a credential when the user had
no row at all (`if credentials_repo.get(...) is None`). Once anything had
written a different hash for a user -- the test suite's own credential reset
did exactly this for months -- re-seeding was a silent no-op, so the tenant
was permanently stuck with a password nobody knew, and the documented
`demo-password` never worked again.

Re-seeding is the repair path, so it has to converge on the fixed password
from ANY prior state.
"""
from __future__ import annotations

import os
import subprocess
import sys

import bcrypt
from sqlalchemy import text

from core.db.engine import get_admin_engine

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DEMO = os.path.join(BACKEND, "..", "data-demo")

TENANT = "password-seed-test-tenant"


def _run_seed_db(slug: str) -> None:
    """Fresh process, for the same one-process-per-tenant reason documented in
    tests/test_seed_db.py::_run_seed_db."""
    code = (
        f"import sys; sys.path.insert(0, {DATA_DEMO!r}); "
        f"import seed_db; seed_db.run({slug!r}, name='PW Seed Test', "
        f"short_name='PWSeed', source='test')"
    )
    env = {**os.environ}
    env.pop("POLPILOT_TENANT", None)
    env.pop("POLPILOT_DATA_DIR", None)
    r = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-1500:]


def _credentials(slug: str) -> list[tuple[str, str]]:
    with get_admin_engine().begin() as conn:
        return conn.execute(text(
            "SELECT c.username, c.password_hash FROM auth_credentials c "
            "JOIN tenants t ON t.id = c.tenant_id WHERE t.slug = :slug"
        ), {"slug": slug}).fetchall()


def test_reseeding_repairs_a_drifted_password():
    """A credential written by something else must be reset by the next seed."""
    sys.path.insert(0, DATA_DEMO)
    import seed_db

    esperada = seed_db.demo_password().encode("utf-8")

    with get_admin_engine().begin() as conn:
        conn.execute(text("DELETE FROM tenants WHERE slug = :s"), {"s": TENANT})
    _run_seed_db(TENANT)

    filas = _credentials(TENANT)
    assert filas, "seeding produced no credentials at all"

    # Simulate the drift: overwrite one user's hash with a different password,
    # exactly as the test suite's credential reset used to do.
    victima = filas[0][0]
    otro = bcrypt.hashpw(b"something-else-entirely", bcrypt.gensalt()).decode()
    with get_admin_engine().begin() as conn:
        conn.execute(text(
            "UPDATE auth_credentials SET password_hash = :h "
            "WHERE username = :u AND tenant_id = "
            "(SELECT id FROM tenants WHERE slug = :s)"
        ), {"h": otro, "u": victima, "s": TENANT})

    _run_seed_db(TENANT)

    despues = dict(_credentials(TENANT))
    assert bcrypt.checkpw(esperada, despues[victima].encode("utf-8")), (
        f"re-seeding left {victima!r} on the drifted hash -- the documented "
        f"demo password still does not work for that user"
    )


def test_every_seeded_user_gets_the_fixed_password():
    sys.path.insert(0, DATA_DEMO)
    import seed_db

    esperada = seed_db.demo_password().encode("utf-8")
    _run_seed_db(TENANT)

    filas = _credentials(TENANT)
    assert filas, "seeding produced no credentials at all"
    malos = [u for u, h in filas if not bcrypt.checkpw(esperada, h.encode("utf-8"))]
    assert not malos, f"these seeded users do not accept the fixed password: {malos}"


def test_password_is_hashed_with_a_per_user_salt():
    """Real bcrypt in every environment -- and no shared-salt shortcut, so one
    leaked hash never reveals that the rest are identical."""
    _run_seed_db(TENANT)
    hashes = [h for _, h in _credentials(TENANT)]
    assert len(hashes) > 1, "need several users to compare salts"
    assert all(h.startswith("$2b$") for h in hashes), "not bcrypt"
    assert len(set(hashes)) == len(hashes), (
        "every user shares one hash -- the password was hashed once and reused"
    )
