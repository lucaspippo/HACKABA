import os
import subprocess
import sys

BACKEND = os.path.dirname(os.path.abspath(__file__)) + "/.."
DATA_DEMO = os.path.join(BACKEND, "..", "data-demo")


def _run_seed_db(slug: str, **kwargs) -> None:
    """seed_db.run() reads core.paths.TENANT/DATA_DIR, which — like the rest
    of this codebase's one-process-per-tenant design — are resolved once at
    first import and don't change if POLPILOT_TENANT is set later in an
    already-running process (this test's own pytest process, notably, since
    conftest.py already pinned it to "piloto" before this test runs). Real
    usage (deploy/boot.py, the CLI) always runs seed_db.py in a fresh
    process, so the test does the same — this also means it doesn't depend
    on or disturb whatever tenant conftest.py pinned for the rest of the suite.
    """
    kwargs_repr = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
    code = (
        f"import sys; sys.path.insert(0, {DATA_DEMO!r}); "
        f"import seed_db; seed_db.run({slug!r}{', ' + kwargs_repr if kwargs_repr else ''})"
    )
    env = {**os.environ}
    env.pop("POLPILOT_TENANT", None)
    env.pop("POLPILOT_DATA_DIR", None)
    r = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env=env,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr[-1500:]


def test_seed_db_creates_tenant_and_data():
    from sqlalchemy import text

    from core.db.engine import get_admin_engine

    slug = "seed-test-tenant"
    admin = get_admin_engine()
    with admin.begin() as conn:
        conn.execute(text("DELETE FROM tenants WHERE slug = :slug"), {"slug": slug})

    _run_seed_db(slug, name="Seed Test Co", short_name="SeedCo", source="test")

    with admin.begin() as conn:
        tid = conn.execute(text("SELECT id FROM tenants WHERE slug = :slug"), {"slug": slug}).scalar_one()
        n_accounts = conn.execute(text("SELECT count(*) FROM customer_accounts WHERE tenant_id = :tid"),
                                  {"tid": tid}).scalar_one()
        assert n_accounts > 0
        assert conn.execute(text("SELECT count(*) FROM inventory_working WHERE tenant_id = :tid"),
                            {"tid": tid}).scalar_one() == 1
        assert conn.execute(text("SELECT count(*) FROM caja_state WHERE tenant_id = :tid"),
                            {"tid": tid}).scalar_one() == 1

    # idempotent: running twice must not fail or duplicate
    _run_seed_db(slug, name="Seed Test Co", short_name="SeedCo", source="test")
    with admin.begin() as conn:
        n_accounts_2 = conn.execute(text("SELECT count(*) FROM customer_accounts WHERE tenant_id = :tid"),
                                    {"tid": tid}).scalar_one()
        assert n_accounts_2 == n_accounts
        conn.execute(text("DELETE FROM tenants WHERE slug = :slug"), {"slug": slug})


def test_ensure_tenant_must_run_before_postgres_backed_core_calls():
    """Root-cause regression test for a real boot-order bug: data-demo/
    generar.py calls directly into Postgres-backed core modules
    (core.staging, core.perfiles, core.comprobantes — see their
    sembrar_*() callers) partway through seeding a tenant. Those calls
    raise if the tenant has no row in `tenants` yet, which is exactly what
    happens on a genuinely fresh Postgres (a real first-ever production
    boot, or CI) if generar.py runs before the tenant row is created — a
    repeated local/Render boot masked this because the row already existed
    from an earlier run. seed_db.ensure_tenant() exists specifically to be
    called first (see deploy/boot.py's step order); this proves the
    ordering actually matters, using a throwaway tenant so it never touches
    the real "demo" tenant's data (running generar.py itself always would —
    its sembrar_*() functions hardcode POLPILOT_TENANT=demo internally)."""
    slug = f"boot-order-test-{os.urandom(4).hex()}"
    code = f'''
import sys
sys.path.insert(0, {DATA_DEMO!r})
import os
os.environ["POLPILOT_TENANT"] = {slug!r}

from core import store
try:
    store.raw_actual()
    print("BEFORE:unexpected-success")
except RuntimeError:
    print("BEFORE:expected-failure")

import seed_db
seed_db.ensure_tenant({slug!r}, name="Boot Order Test", short_name="BOT", source="test")

try:
    n = len(store.raw_actual())
    print(f"AFTER:success:{{n}}")
except Exception as e:
    print(f"AFTER:unexpected-failure:{{e}}")
'''
    env = {**os.environ}
    env.pop("POLPILOT_TENANT", None)
    env.pop("POLPILOT_DATA_DIR", None)
    try:
        r = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env=env,
                           capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr[-1500:]
        lines = r.stdout.strip().splitlines()
        assert "BEFORE:expected-failure" in lines, lines
        assert any(l.startswith("AFTER:success:") for l in lines), lines
    finally:
        from sqlalchemy import text
        from core.db.engine import get_admin_engine
        with get_admin_engine().begin() as conn:
            conn.execute(text("DELETE FROM tenants WHERE slug = :slug"), {"slug": slug})
