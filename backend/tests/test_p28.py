"""
P28 — "El mapa de tu negocio": el backend mínimo que lo sostiene.

El mapa NO inventa números: compone en el cliente los MISMOS endpoints
cacheados que ya usan las secciones (inventario, cuentas, pagos, depósito,
oportunidades, calidad). Lo único nuevo del server: la feature "mapa" del
dueño y GET /api/macro (IPC/dólar reales para el nodo Contexto económico).
"""
from __future__ import annotations

from fastapi.testclient import TestClient

import auth
import main

client = TestClient(main.app)


def _token(username: str) -> dict:
    creds = auth.cargar_o_generar_credenciales()
    tok = client.post("/api/login", json={"username": username,
                                          "password": creds[username]}).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


def test_mapa_es_feature_del_dueno():
    from core import perfiles
    assert "mapa" in perfiles.features_efectivas("emilio")
    # y NO de un rol operativo: el mapa es la vista del dueño
    assert "mapa" not in perfiles.features_efectivas("paula")


def test_modulo_mapa_tiene_label_bilingue():
    import i18n
    labels_es = auth.modulos_labels("es")
    labels_en = auth.modulos_labels("en")
    assert labels_es["mapa"] == "El mapa de tu negocio"
    assert labels_en["mapa"] == "Your Business Map"
    assert i18n.t("modulo.mapa", "es") != i18n.t("modulo.mapa", "en")


def test_api_macro_gated_y_honesto():
    # sin la feature → 403 (paula no tiene mapa)
    r = client.get("/api/macro", headers=_token("paula"))
    assert r.status_code == 403
    # el dueño sí; cada indicador declara disponible=True/False — nunca inventa
    r = client.get("/api/macro", headers=_token("emilio"))
    assert r.status_code == 200
    body = r.json()
    for k in ("inflacion", "dolar"):
        assert k in body
        assert "disponible" in body[k]
