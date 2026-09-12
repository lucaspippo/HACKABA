"""The deploy entrypoints (deploy/migrate.py, deploy/boot.py).

These are scripts Render runs, not importable app code, so they are checked
the way their failure actually shows up: run them with a deliberately
incomplete environment and assert they refuse, loudly and non-zero, instead
of proceeding on a default.
"""
from __future__ import annotations

import os
import subprocess
import sys

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
                          text=True, cwd=REPO_ROOT, timeout=120, env=env)


def test_migrate_refuses_without_an_explicit_tenant():
    r = _run(MIGRATE, {"POLPILOT_TENANT": None})
    assert r.returncode != 0
    assert "POLPILOT_TENANT" in (r.stdout + r.stderr)


def test_migrate_refuses_a_blank_tenant():
    r = _run(MIGRATE, {"POLPILOT_TENANT": "   "})
    assert r.returncode != 0
    assert "POLPILOT_TENANT" in (r.stdout + r.stderr)
