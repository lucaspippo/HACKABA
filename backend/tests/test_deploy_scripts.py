"""The deploy entrypoints (deploy/migrate.py, deploy/boot.py).

These are scripts Render runs, not importable app code, so they are checked
the way their failure actually shows up: run them with a deliberately
incomplete environment and assert they refuse, loudly and non-zero, instead
of proceeding on a default.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIGRATE = os.path.join(REPO_ROOT, "deploy", "migrate.py")


def _run(script: str, env_overrides: dict[str, str | None]):
    env = dict(os.environ)
    for k, v in env_overrides.items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    return subprocess.run([sys.executable, script], capture_output=True,
                          text=True, cwd=REPO_ROOT, timeout=90, env=env)


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


def _boot_with_sentinel_data_dir(seed_flag: str | None):
    """Runs boot.py against a throwaway data dir whose generar.py and seed_db
    only record that they were called. Returns the set of markers written.

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

    overrides = {"POLPILOT_TENANT": "piloto", "POLPILOT_DATA_DIR": data_dir,
                 "POLPILOT_CANONICAL_DIR": None, "POLPILOT_SEED_ON_BOOT": seed_flag}
    try:
        _run(BOOT, overrides)
    except subprocess.TimeoutExpired:
        pass  # got as far as serving; the markers are what we assert on
    if not os.path.exists(marker):
        return set()
    with open(marker, encoding="utf-8") as fh:
        return {json.loads(line) for line in fh if line.strip()}


def test_a_productive_shape_never_regenerates_the_dataset():
    markers = _boot_with_sentinel_data_dir(seed_flag=None)
    assert "generar" not in markers, "generar.py ran without the flag — data loss"
    assert "run" not in markers, "seed_db.run ran without the flag — data loss"
    # The tenant row is still ensured: needed to serve, not only to seed.
    assert "ensure_tenant" in markers


def test_the_demo_shape_does_regenerate_the_dataset():
    # The positive control — without it the test above would also pass if the
    # seed path were deleted outright rather than gated.
    markers = _boot_with_sentinel_data_dir(seed_flag="1")
    assert {"generar", "run", "ensure_tenant"} <= markers
