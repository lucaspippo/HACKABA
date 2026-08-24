"""
Endurecimiento pre-deploy del DEMO público (A + B):
  (A) /api/angela sin token en el demo → 401 (no llama a Claude).
  (B) cap por IP (60/día, solo demo) sobre /api/angela y /api/factura/leer,
      leyendo la IP real detrás del proxy de Render (X-Forwarded-For).
En el PILOTO nada de esto aplica: el cap por IP es 0 y el anónimo restringido
del chat se mantiene.
"""
from __future__ import annotations

import os
import subprocess
import sys
from types import SimpleNamespace

import main


# --- lógica pura del cap por IP (tenant-agnóstica: cap explícito) --------------

def test_ip_excedido_cuenta_y_topa():
    # cap=3 → 3 permitidas, la 4ª frena; la IP queda topada
    ip = "test-A-1.1.1.1"
    assert main._ip_excedido(ip, 3) is False   # 1
    assert main._ip_excedido(ip, 3) is False   # 2
    assert main._ip_excedido(ip, 3) is False   # 3
    assert main._ip_excedido(ip, 3) is True    # 4 → frena
    assert main._ip_excedido(ip, 3) is True    # sigue topada


def test_ip_excedido_independiente_por_ip():
    a, b = "test-B-2.2.2.2", "test-B-3.3.3.3"
    assert main._ip_excedido(a, 1) is False    # A: 1ª ok
    assert main._ip_excedido(a, 1) is True     # A: topada
    assert main._ip_excedido(b, 1) is False    # B arranca de cero (independiente)


def test_ip_cap_cero_nunca_frena():
    ip = "test-C-4.4.4.4"
    for _ in range(200):
        assert main._ip_excedido(ip, 0) is False   # piloto: cap 0 → jamás frena


def test_client_ip_usa_x_forwarded_for():
    # detrás del proxy: la IP REAL es la primera de X-Forwarded-For, no el proxy
    req = SimpleNamespace(headers={"x-forwarded-for": "203.0.113.9, 10.0.0.1"},
                          client=SimpleNamespace(host="10.0.0.1"))
    assert main._client_ip(req) == "203.0.113.9"
    # sin XFF: cae a la IP directa
    req2 = SimpleNamespace(headers={}, client=SimpleNamespace(host="198.51.100.7"))
    assert main._client_ip(req2) == "198.51.100.7"


def test_cap_ip_es_cero_en_piloto():
    # la suite corre como piloto (tenant != demo) → sin cap nuevo
    assert main._es_demo() is False
    assert main._cap_ip() == 0


# --- comportamiento end-to-end del DEMO (subproceso con tenant=demo) -----------

def test_demo_sin_token_401_y_cap_por_ip():
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_demo = os.path.join(os.path.dirname(backend), "data-demo")
    env = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": data_demo,
           "POLPILOT_DEMO_TODAY": "2026-07-07", "POLPILOT_DEMO_AUTOLOGIN": "1",
           "POLPILOT_DEMO_IP_CAP": "2", "POLPILOT_DEMO_MSG_CAP": "35",
           "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)  # modo simulado: no gasta ni un token real
    code = r"""
from fastapi.testclient import TestClient
import main
c = TestClient(main.app)

# (A) sin token en el demo → 401 (NO llama a Claude)
r = c.post("/api/angela", json={"mensaje": "hola"})
assert r.status_code == 401, ("A esperaba 401, dio", r.status_code)

# token legítimo por autologin (el demo lo regala: por eso el cap por sesión
# se evade y hace falta el cap por IP)
tok = c.post("/api/demo/autologin").json()["token"]

# (B) cap por IP = 2: la 3ª llamada de la MISMA ip devuelve el mensaje de cap
xff = {"X-Forwarded-For": "9.9.9.9"}
modos = []
for _ in range(3):
    j = c.post("/api/angela", json={"mensaje": "hola", "token": tok}, headers=xff).json()
    modos.append(j.get("modo"))
assert modos[2] == "cap", ("B: la 3ª debía ser cap", modos)

# otra IP arranca de cero (no la frena la primera)
j2 = c.post("/api/angela", json={"mensaje": "hola", "token": tok},
            headers={"X-Forwarded-For": "8.8.8.8"}).json()
assert j2.get("modo") != "cap", "una IP nueva no debe estar topada"

# la UI real siempre manda token: ese camino nunca da 401 (regresión)
assert c.post("/api/angela", json={"mensaje": "hola", "token": tok},
              headers={"X-Forwarded-For": "7.7.7.7"}).status_code == 200
print("OK")
"""
    r = subprocess.run([sys.executable, "-c", code], cwd=backend, env=env,
                       capture_output=True, text=True, timeout=180)
    assert r.returncode == 0 and "OK" in r.stdout, (r.stdout[-800:], r.stderr[-800:])
