"""
E0 · Capa del empleado de a pie — SCOPE server-side (requisito, no detalle).

Tomás (depósito) y Vanesa (mostrador) reciben `inventario` de LECTURA para que
Ángela les responda stock/negativos/precios desde el piso. Este test prueba, a
nivel HTTP y en el tenant demo, que ese acceso es EXACTAMENTE el necesario y
NADA del dueño: finanzas, auditoría, sync y sección de otro rol siguen en 403.

Corre en un subproceso con el entorno del demo (mismo patrón que
test_demo_separacion), porque tomas/vanesa sólo existen en el seed del demo.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DEMO = os.path.join(os.path.dirname(BACKEND), "data-demo")

_SNIPPET = r"""
import json
from fastapi.testclient import TestClient
import auth, main

client = TestClient(main.app)
creds = auth.cargar_o_generar_credenciales()

def _tok(u):
    return client.post("/api/login", json={"username": u, "password": creds[u]}).json()["token"]

def _code(u, method, path):
    h = {"Authorization": "Bearer " + _tok(u)}
    fn = client.get if method == "GET" else client.post
    kw = {"headers": h} if method == "GET" else {"headers": h, "json": {}}
    return fn(path, **kw).status_code

PRUEBAS = [
    ("GET", "/api/inventario"),   # las preguntas del de a pie (stock/negativos/sin-pvp)
    ("GET", "/api/deposito"),     # de Tomás sí, de Vanesa no
    ("GET", "/api/pagos"),        # del dueño (require_feature "finanzas")
    ("GET", "/api/macro"),        # del dueño (require_feature "mapa")
    ("GET", "/api/audit"),        # require_admin
    ("GET", "/api/sync/delta"),   # require_admin
    ("GET", "/api/documentos/resumen_ejecutivo"),  # documento del dueño
]
res = {u: {f"{m} {p}": _code(u, m, p) for (m, p) in PRUEBAS} for u in ("tomas", "vanesa")}
print(json.dumps(res))
"""


# El login del demo para grabar: el dueño entra y "Ve como" el empleado — el
# switch emite una sesión LEGÍTIMA del destino (P9·E). Verificamos que la sesión
# emitida para tomas/vanesa (a) sirve para lo suyo y (b) NO abre nada del dueño.
_SNIPPET_VERCOMO = r"""
import json, os
os.environ["POLPILOT_DEMO_ROLE_SWITCH"] = "1"
from fastapi.testclient import TestClient
import auth, main

client = TestClient(main.app)
creds = auth.cargar_o_generar_credenciales()
dueno = auth.dueno()["username"]
tok = client.post("/api/login", json={"username": dueno, "password": creds[dueno]}).json()["token"]
h = {"Authorization": "Bearer " + tok}

out = {}
for u in ("tomas", "vanesa"):
    r = client.post("/api/demo/ver-como", headers=h, json={"username": u})
    b = r.json() if r.status_code == 200 else {}
    t2 = b.get("token")
    def _c(path):
        return client.get(path, headers={"Authorization": "Bearer " + t2}).status_code if t2 else None
    out[u] = {"status": r.status_code, "tiene_token": bool(t2),
              "inventario": _c("/api/inventario"), "audit": _c("/api/audit")}
print(json.dumps(out))
"""


def _correr_en_demo(snippet: str = _SNIPPET) -> dict:
    env = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": DATA_DEMO,
           "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)
    r = subprocess.run([sys.executable, "-c", snippet], cwd=BACKEND, env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-1200:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_frontline_ve_lo_suyo_y_nada_del_dueno():
    res = _correr_en_demo()
    # lo que un endpoint de auth NUNCA debe devolver al rol correcto
    def ok(code):  # 200 o 4xx de negocio, pero jamás 401/403
        return code not in (401, 403)

    tomas, vanesa = res["tomas"], res["vanesa"]

    # --- lo SUYO funciona ---
    assert ok(tomas["GET /api/inventario"]), f"tomas sin inventario: {tomas}"
    assert ok(tomas["GET /api/deposito"]), f"tomas sin deposito: {tomas}"
    assert ok(vanesa["GET /api/inventario"]), f"vanesa sin inventario: {vanesa}"

    # --- NADA del dueño (ambos) ---
    for u, r in (("tomas", tomas), ("vanesa", vanesa)):
        assert r["GET /api/pagos"] == 403, f"{u} vio finanzas/pagos: {r}"
        assert r["GET /api/macro"] == 403, f"{u} vio el mapa (macro): {r}"
        assert r["GET /api/audit"] == 403, f"{u} vio auditoría: {r}"
        assert r["GET /api/sync/delta"] == 403, f"{u} vio sync: {r}"
        assert r["GET /api/documentos/resumen_ejecutivo"] == 403, f"{u} vio doc del dueño: {r}"

    # --- Vanesa (mostrador) NO entra al depósito: cada rol ve sólo su vista ---
    assert vanesa["GET /api/deposito"] == 403, f"vanesa entró al depósito: {vanesa}"


def test_ver_como_emite_sesion_legitima_y_scopeada():
    """El login para grabar: el dueño 'Ve como' Tomás/Vanesa y la sesión emitida
    es real (entra a inventario) pero sigue scopeada al empleado (auditoría 403)."""
    res = _correr_en_demo(_SNIPPET_VERCOMO)
    for u in ("tomas", "vanesa"):
        r = res[u]
        assert r["status"] == 200 and r["tiene_token"], f"ver-como {u} no emitió sesión: {r}"
        assert r["inventario"] == 200, f"la sesión de {u} no puede con inventario: {r}"
        assert r["audit"] == 403, f"la sesión de {u} abrió auditoría del dueño: {r}"
