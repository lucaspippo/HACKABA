"""POST /api/admin/reset-demo — the fix: it used to only copy files back
from POLPILOT_CANONICAL_DIR, which did nothing for the Postgres-backed
domains (everything, after the JSON-to-Postgres migration — see
core/db/MIGRATING_A_MODULE.md). Now it also truncates the tenant's business
data and re-seeds it from the real on-disk dataset (core/db/reset.py +
seed_db.seed_domains()).

Runs the demo tenant in a subprocess (its own POLPILOT_DATA_DIR/
POLPILOT_CANONICAL_DIR, isolated temp copies so this never touches the
repo's committed data-demo/) — same pattern as test_kpis.py's canonical
demo tests.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

RESET_TOKEN = "test-reset-token"

_SCRIPT = """
import json
from fastapi.testclient import TestClient

import main
from core import piso, store

client = TestClient(main.app)

antes_articulos = len(store.raw_actual())

# mutate: a floor report that reset must wipe
piso.reportar("faltante", "deposito",
              {"producto": "algo", "cantidad": 1, "motivo": "roto"})
assert len(piso.listar()) == 1

r = client.post("/api/admin/reset-demo", params={"token": %(token)r})
assert r.status_code == 200, (r.status_code, r.text)

despues_articulos = len(store.raw_actual())
despues_reportes = len(piso.listar())

print(json.dumps({
    "ok": r.json()["ok"],
    "antes_articulos": antes_articulos,
    "despues_articulos": despues_articulos,
    "despues_reportes": despues_reportes,
}))
"""


def test_reset_demo_clears_postgres_mutations_and_reseeds():
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raiz = os.path.dirname(backend)
    data_demo = os.path.join(raiz, "data-demo")

    tmp = tempfile.mkdtemp(prefix="polpilot-reset-test-")
    data_dir = os.path.join(tmp, "data")
    canonical_dir = os.path.join(tmp, "canonical")
    shutil.copytree(data_demo, data_dir)
    shutil.copytree(data_demo, canonical_dir)
    try:
        env = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": data_dir,
               "POLPILOT_CANONICAL_DIR": canonical_dir, "POLPILOT_RESET_TOKEN": RESET_TOKEN,
               "POLPILOT_DEMO_TODAY": "2026-07-07", "PYTHONIOENCODING": "utf-8"}
        env.pop("ANTHROPIC_API_KEY", None)
        script = _SCRIPT % {"token": RESET_TOKEN}
        r = subprocess.run([sys.executable, "-c", script], cwd=backend, env=env,
                            capture_output=True, text=True, timeout=180)
        assert r.returncode == 0, r.stderr[-2000:]
        out = json.loads(r.stdout.strip().splitlines()[-1])
        assert out["ok"] is True
        assert out["antes_articulos"] > 0
        # inventory got wiped and re-seeded from the real dataset — same count
        assert out["despues_articulos"] == out["antes_articulos"]
        # the mutation made before reset is gone
        assert out["despues_reportes"] == 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
