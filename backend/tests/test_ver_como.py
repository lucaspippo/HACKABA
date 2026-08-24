"""
P9·E — "View as / Ver como": SOLO tenant demo, detrás de un feature flag.

En el piloto (sin POLPILOT_DEMO_ROLE_SWITCH) el endpoint directamente NO
EXISTE (404): un empleado real de Horizonte jamás puede verse como el dueño.
Con el flag, el switch emite una sesión LEGÍTIMA del usuario destino y exige
una sesión ya válida.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import auth
import main


client = TestClient(main.app)


@pytest.fixture()
def h():
    creds = auth.cargar_o_generar_credenciales()
    tok = client.post("/api/login", json={"username": "emilio",
                                          "password": creds["emilio"]}).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


def test_en_el_piloto_el_endpoint_no_existe(h, monkeypatch):
    """El test EXPLÍCITO que pide el prompt: sin flag → 404, ni con sesión
    válida de dueño."""
    monkeypatch.delenv("POLPILOT_DEMO_ROLE_SWITCH", raising=False)
    r = client.post("/api/demo/ver-como", headers=h, json={"username": "paula"})
    assert r.status_code == 404
    # y el health NO lo publicita
    assert client.get("/api/health").json()["role_switch"] is False


def test_con_flag_emite_sesion_legitima_del_destino(h, monkeypatch):
    monkeypatch.setenv("POLPILOT_DEMO_ROLE_SWITCH", "1")
    r = client.post("/api/demo/ver-como", headers=h, json={"username": "paula"})
    assert r.status_code == 200
    s = r.json()
    assert s["usuario"]["username"] == "paula"
    # la sesión emitida es real: el token identifica al usuario destino
    yo = client.get(f"/api/me?token={s['token']}")
    assert yo.status_code == 200 and yo.json()["username"] == "paula"


def test_sin_sesion_valida_no_hay_switch(monkeypatch):
    monkeypatch.setenv("POLPILOT_DEMO_ROLE_SWITCH", "1")
    r = client.post("/api/demo/ver-como", json={"username": "paula"})
    assert r.status_code == 401


def test_no_se_puede_mirar_como_un_usuario_interno(h, monkeypatch):
    monkeypatch.setenv("POLPILOT_DEMO_ROLE_SWITCH", "1")
    r = client.post("/api/demo/ver-como", headers=h, json={"username": "polpilot"})
    assert r.status_code == 404
    r2 = client.post("/api/demo/ver-como", headers=h, json={"username": "noexiste"})
    assert r2.status_code == 404


def test_equipo_nombres_trae_superficies(h):
    """P11·B9: el selector "View as" de desktop filtra por superficies — el
    endpoint las expone para TODOS (Objetivos/Equipo siguen viendo el equipo
    completo; el filtro es del selector, no de la lista)."""
    r = client.get("/api/equipo/nombres", headers=h).json()
    assert all("superficies" in p for p in r["equipo"])
    # el piloto declara sus superficies en el seed: emilio es desktop+mobile
    emilio = next(p for p in r["equipo"] if p["username"] == "emilio")
    assert "desktop" in emilio["superficies"]
