"""The deploy entrypoints (deploy/migrate.py, deploy/boot.py).

These are scripts Render runs, not importable app code, so they are checked
the way their failure actually shows up: run them with a deliberately
incomplete environment and assert they refuse, loudly and non-zero, instead
of proceeding on a default.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIGRATE = os.path.join(REPO_ROOT, "deploy", "migrate.py")


def _run(script: str, env_overrides: dict[str, str | None], out_path: str | None = None):
    """Runs a deploy script. With `out_path` the child's output goes to a FILE
    instead of a pipe — see _boot_with_sentinel_data_dir for why that matters."""
    env = dict(os.environ)
    for k, v in env_overrides.items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    if out_path is None:
        return subprocess.run([sys.executable, script], capture_output=True,
                              text=True, cwd=REPO_ROOT, timeout=90, env=env)
    with open(out_path, "w", encoding="utf-8", errors="replace") as fh:
        return subprocess.run([sys.executable, script], stdout=fh,
                              stderr=subprocess.STDOUT, cwd=REPO_ROOT,
                              timeout=90, env=env)


def test_migrate_refuses_without_an_explicit_tenant():
    r = _run(MIGRATE, {"POLPILOT_TENANT": None})
    assert r.returncode != 0
    assert "POLPILOT_TENANT" in (r.stdout + r.stderr)


def test_migrate_refuses_a_blank_tenant():
    r = _run(MIGRATE, {"POLPILOT_TENANT": "   "})
    assert r.returncode != 0
    assert "POLPILOT_TENANT" in (r.stdout + r.stderr)


BOOT = os.path.join(REPO_ROOT, "deploy", "boot.py")


def test_boot_refuses_without_an_explicit_tenant():
    r = _run(BOOT, {"POLPILOT_TENANT": None})
    assert r.returncode != 0
    assert "POLPILOT_TENANT" in (r.stdout + r.stderr)


def test_boot_no_longer_runs_alembic():
    # Migrations belong to deploy/migrate.py (the preDeployCommand) so that a
    # failed migration fails the deploy instead of taking the service down.
    # Forbid the INVOCATION, not the word: boot.py's docstring is expected to
    # explain where migrations went, and naming alembic in prose is correct.
    source = open(BOOT, encoding="utf-8").read()
    assert '"alembic"' not in source, "no alembic argv may remain"
    assert "'alembic'" not in source, "no alembic argv may remain"


def test_boot_seeding_is_gated_on_the_flag():
    # generar.py rewrites the whole dataset: on a productive tenant that is
    # data loss, so the seed path must be reachable only via the flag.
    source = open(BOOT, encoding="utf-8").read()
    assert "seed_on_boot" in source
    # Naming the flag in a log line is good; re-reading it here is not — the
    # default must live in deploy_guard alone, or the two can disagree.
    assert 'environ.get("POLPILOT_SEED_ON_BOOT"' not in source
    assert "environ['POLPILOT_SEED_ON_BOOT'" not in source


# Fails on the first connect, immediately: `.invalid` is reserved by RFC 2606
# and can never resolve, so there is no port to wait on (a closed local port
# does NOT fail fast here — the connection just hangs). Pointing the child at
# this makes boot.py's step 5 take its "Postgres unreadable" hard exit, so the
# run can never reach step 7 (`exec uvicorn`). See _boot_with_sentinel_data_dir.
_UNREACHABLE_DB = "postgresql+psycopg://nobody:nobody@polpilot-no-such-host.invalid:5432/nope"
# uvicorn's CLI rejects a non-integer --port before it opens any socket, so
# even a run that legitimately gets past step 5 leaves nothing listening.
_UNBINDABLE_PORT = "not-a-port"


def _sentinel_data_dir() -> tuple[str, str]:
    """A throwaway data dir whose generar.py and seed_db only record that they
    were called. Returns (data_dir, marker_path).

    boot.py inserts DATA_DIR at the front of sys.path and imports seed_db from
    it, so the sentinel dir must provide that module too — otherwise the run
    dies on the import before ever reaching the gate under test."""
    data_dir = tempfile.mkdtemp(prefix="polpilot-bootgate-")
    marker = os.path.join(data_dir, "markers.jsonl")

    def _sentinel(name: str) -> str:
        return (
            "import json\n"
            f"open({marker!r}, 'a', encoding='utf-8').write(json.dumps({name!r}) + '\\n')\n"
        )

    with open(os.path.join(data_dir, "generar.py"), "w", encoding="utf-8") as fh:
        fh.write(_sentinel("generar"))
    with open(os.path.join(data_dir, "seed_db.py"), "w", encoding="utf-8") as fh:
        fh.write(
            "import json\n"
            f"_M = {marker!r}\n"
            "def _mark(w):\n"
            "    open(_M, 'a', encoding='utf-8').write(json.dumps(w) + '\\n')\n"
            "def ensure_tenant(tenant):\n"
            "    _mark('ensure_tenant')\n"
            "def run(tenant):\n"
            "    _mark('run')\n"
        )
    return data_dir, marker


def _markers(marker: str) -> set[str]:
    if not os.path.exists(marker):
        return set()
    with open(marker, encoding="utf-8") as fh:
        return {json.loads(line) for line in fh if line.strip()}


def _boot_with_sentinel_data_dir(seed_flag: str | None, *, tenant: str = "piloto",
                                 reachable_db: bool = False,
                                 canonical: str | None = None):
    """Runs boot.py against a sentinel data dir. Returns
    (returncode, markers, output).

    Two things here exist to keep the child from OUTLIVING the test, and both
    matter: boot.py ends in os.execvp, which on Windows spawns a NEW process
    and exits the old one. A timeout would then kill an already-dead pid while
    the exec'd uvicorn kept running, holding the inherited stdout pipe open —
    communicate() blocked on an EOF that never came (the suite hung for
    ~25 min) and left a uvicorn listening on port 8000 against the TEST
    database, which local dev also uses.

      · Output goes to a FILE, never a pipe, so no surviving child can block
        the parent.
      · The child is steered away from step 7. By default APP/DATABASE_URL are
        unreachable, so step 5 hard-exits; every marker asserted on here is
        written before step 5. A test that must get PAST step 5 passes
        reachable_db=True and relies on _UNBINDABLE_PORT instead."""
    data_dir, marker = _sentinel_data_dir()
    # Outside data_dir: step 6 copies that directory, and a file the parent
    # still holds open would join the copy.
    out_path = data_dir + ".out"
    overrides: dict[str, str | None] = {
        "POLPILOT_TENANT": tenant,
        "POLPILOT_DATA_DIR": data_dir,
        "POLPILOT_CANONICAL_DIR": canonical,
        "POLPILOT_SEED_ON_BOOT": seed_flag,
        "PORT": _UNBINDABLE_PORT,
    }
    if not reachable_db:
        overrides["DATABASE_URL"] = _UNREACHABLE_DB
        overrides["APP_DATABASE_URL"] = _UNREACHABLE_DB
    r = _run(BOOT, overrides, out_path=out_path)
    with open(out_path, encoding="utf-8", errors="replace") as fh:
        return r.returncode, _markers(marker), fh.read()


def test_a_productive_shape_never_regenerates_the_dataset():
    code, markers, _out = _boot_with_sentinel_data_dir(seed_flag=None)
    assert "generar" not in markers, "generar.py ran without the flag — data loss"
    assert "run" not in markers, "seed_db.run ran without the flag — data loss"
    # The tenant row is still ensured: needed to serve, not only to seed.
    assert "ensure_tenant" in markers
    # The unreachable database stopped the run at step 5, before `exec uvicorn`.
    assert code != 0


def test_the_demo_shape_does_regenerate_the_dataset():
    # The positive control — without it the test above would also pass if the
    # seed path were deleted outright rather than gated.
    code, markers, _out = _boot_with_sentinel_data_dir(seed_flag="1")
    assert {"generar", "run", "ensure_tenant"} <= markers
    assert code != 0


def test_an_unreadable_postgres_is_still_a_hard_failure():
    # The other half of the step-5 split: a missing/refused database is a real
    # misconfiguration and must never be served through.
    code, _markers_, out = _boot_with_sentinel_data_dir(seed_flag=None)
    assert code != 0
    assert "[boot][X]" in out and "Postgres unreadable" in out


def test_an_empty_productive_tenant_still_comes_up():
    """The chicken-and-egg step 5 used to create: seeding is off by default on
    a productive tenant, so its first deploy has an empty (but perfectly
    readable) database. The old unconditional `assert n > 0` exited 1, the
    healthcheck never passed, Render never published — and there was no way to
    load the data, because loading it goes through the app that would not
    start. An empty tenant must warn and serve."""
    from sqlalchemy import text

    from core.db.engine import get_admin_engine

    slug = f"test-boot-{uuid.uuid4().hex[:8]}"
    engine = get_admin_engine()
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO tenants (slug, name, short_name, source) "
            "VALUES (:slug, 'Boot Test Tenant', 'Boot Test', 'test')"
        ), {"slug": slug})
    canonical = tempfile.mkdtemp(prefix="polpilot-bootcanon-")
    os.rmdir(canonical)  # step 6 copies onto a path that must not exist yet
    try:
        code, markers, out = _boot_with_sentinel_data_dir(
            seed_flag=None, tenant=slug, reachable_db=True, canonical=canonical)
        assert "[boot][X]" not in out, out[-2000:]
        assert "has no inventory in Postgres yet" in out, out[-2000:]
        assert "ensure_tenant" in markers
        # Step 6 only runs once step 5 has let the boot through, so the
        # canonical copy existing is the proof it did.
        assert os.path.isdir(canonical), out[-2000:]
        # `code` is deliberately NOT asserted on: this run does reach step 7,
        # and os.execvp on Windows spawns a new process and exits this one
        # with 0 whatever the exec'd command then does. What keeps that
        # process from surviving the test is _UNBINDABLE_PORT — uvicorn's CLI
        # rejects a non-integer --port before it opens any socket.
        assert code == 0
    finally:
        shutil.rmtree(canonical, ignore_errors=True)
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM tenants WHERE slug = :slug"), {"slug": slug})
