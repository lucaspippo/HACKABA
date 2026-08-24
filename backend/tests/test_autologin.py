"""
P11·B8 — Entrada directa sin login para el link de YC (POLPILOT_DEMO_AUTOLOGIN).

Con el flag: POST /api/demo/autologin mintea la sesión del DUEÑO (mismo riel
que ver-como). Sin el flag / en el piloto: el endpoint NO EXISTE (404) — un
visitante del piloto real jamás entra sin credenciales.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import auth
import main


client = TestClient(main.app)


def test_piloto_sin_flag_no_existe(monkeypatch):
    """El test explícito que pide el prompt: en el piloto este flag NO existe."""
    monkeypatch.delenv("POLPILOT_DEMO_AUTOLOGIN", raising=False)
    assert client.post("/api/demo/autologin").status_code == 404


def test_flag_apagado_tambien_404(monkeypatch):
    monkeypatch.setenv("POLPILOT_DEMO_AUTOLOGIN", "0")
    assert client.post("/api/demo/autologin").status_code == 404


def test_con_flag_entra_como_el_dueno(monkeypatch):
    monkeypatch.setenv("POLPILOT_DEMO_AUTOLOGIN", "1")
    r = client.post("/api/demo/autologin")
    assert r.status_code == 200
    s = r.json()
    assert s["token"] and s["usuario"]["username"] == auth.dueno()["username"]
    assert s["usuario"]["es_admin"] is True
    # la sesión minteada es LEGÍTIMA: /api/me la reconoce
    me = client.get(f"/api/me?token={s['token']}")
    assert me.status_code == 200 and me.json()["username"] == s["usuario"]["username"]


def test_health_expone_el_flag(monkeypatch):
    monkeypatch.setenv("POLPILOT_DEMO_AUTOLOGIN", "1")
    assert client.get("/api/health").json()["autologin"] is True
    monkeypatch.delenv("POLPILOT_DEMO_AUTOLOGIN", raising=False)
    assert client.get("/api/health").json()["autologin"] is False


def test_login_normal_sigue_existiendo(monkeypatch):
    """Detrás del autologin, el login de siempre no cambia (logout → login)."""
    monkeypatch.setenv("POLPILOT_DEMO_AUTOLOGIN", "1")
    creds = auth.cargar_o_generar_credenciales()
    r = client.post("/api/login", json={"username": "emilio", "password": creds["emilio"]})
    assert r.status_code == 200 and r.json()["token"]
