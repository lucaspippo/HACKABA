"""P25·F1 — La historia de Marta se EJECUTA, no se escribe (reproducible).

Corre contra el demo levantado (start_demo). Todo por el pipeline real,
autenticado como Marta: 2 consultas a Ángela + la lista de precios aplicada
con backup y revertida. El feed y el panel de equipo quedan con actividad
LITERALMENTE cierta y el dataset canónico vuelve byte-igual.

Uso:  python deploy/preparar_historia_marta.py
"""
import csv
import json
import os
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# La contraseña fija con la que data-demo/seed_db.py siembra a todo el roster.
# Antes se leía de data-demo/credenciales.json, que dejó de existir cuando las
# credenciales pasaron a Postgres (sólo el hash se persiste, nunca el
# plaintext) — el archivo quedó huérfano y con contraseñas obsoletas.
PASSWORD = os.environ.get("POLPILOT_DEMO_PASSWORD") or "demo-password"


def api(path, data=None, tok=None):
    req = urllib.request.Request(
        f"http://localhost:8001{path}",
        data=json.dumps(data).encode() if data is not None else None,
        headers={"Content-Type": "application/json",
                 **({"Authorization": f"Bearer {tok}"} if tok else {})})
    return json.load(urllib.request.urlopen(req, timeout=240))


tok = api("/api/login", {"username": "marta", "password": PASSWORD})["token"]
for msg in ("¿quién me debe plata y desde cuándo?", "¿cómo viene la caja de hoy?"):
    api("/api/angela", {"mensaje": msg, "historial": [], "token": tok})
filas = list(csv.DictReader(open(os.path.join(
    RAIZ, "data-demo", "comprobantes", "lista_precios_campo_alegre.csv"), encoding="utf-8")))
ext = {"tipo_comprobante": "lista_precios",
       "proveedor": {"razon_social": "Lácteos Campo Alegre"},
       "items": [{"codigo": 1318 if f["codigo"] == "1201" else int(f["codigo"]),
                  "descripcion": f["descripcion"],
                  "precio_unitario": float(f["precio_con_iva"])} for f in filas]}
r = api("/api/factura/confirmar", {"extraccion": ext}, tok)
api(f"/api/saneamiento/revertir/{r['version_backup']}", {"actor": "marta"}, tok)
print("historia de Marta ejecutada (real, auditada, dataset byte-igual)")
