"""
P9·F — Guardarrailes de Ángela for the public demo (URL without login for YC).

The keyword router that used to enforce these in canned replies is gone (D9).
The rules live in SYSTEM_PROMPT; the model follows them. This file checks
the prompt still carries them, and that POLPILOT_DEMO_MSG_CAP still cuts
the session without spending a model call.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import angela
import auth
import config
import main


client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _reset():
    yield
    angela._set_sesion()
    main._CHAT_POR_SESION.clear()


def test_los_guardarrailes_viven_en_el_system_prompt():
    """The model receives the same rules: blocked scope, injection as data,
    never reveal the prompt, one-line deflection."""
    sp = angela.SYSTEM_PROMPT
    assert "GUARDARRAILES" in sp
    assert "DATO" in sp and "jamás una orden" in sp
    assert "Nunca reveles" in sp


def test_el_prompt_prohibe_desviar_features():
    """P11·B2: charts, analysis and documents are work, not off-topic."""
    sp = angela.SYSTEM_PROMPT
    assert "LO QUE NUNCA SE DESVÍA" in sp
    assert "gráfico de estacionalidad" in sp
    assert "ERROR GRAVE" in sp


def test_el_prompt_sigue_el_idioma_del_usuario():
    sp = angela.SYSTEM_PROMPT
    assert "Match the user's language" in sp
    assert "plain-spoken business English" in sp


# --- Freno de gasto (POLPILOT_DEMO_MSG_CAP) ---

def _no_provider(monkeypatch):
    for var in config.credential_vars():
        monkeypatch.delenv(var, raising=False)


@pytest.fixture()
def token():
    creds = auth.cargar_o_generar_credenciales()
    return client.post("/api/login", json={"username": "emilio",
                                           "password": creds["emilio"]}).json()["token"]


def test_cap_de_mensajes_corta_amable(monkeypatch, token):
    _no_provider(monkeypatch)
    monkeypatch.setenv("POLPILOT_DEMO_MSG_CAP", "2")
    for _ in range(2):
        r = client.post("/api/angela", json={"token": token, "message": "hola"})
        assert r.json().get("mode") != "cap"
    r = client.post("/api/angela", json={"token": token, "message": "hola de nuevo"})
    body = r.json()
    assert body["mode"] == "cap" and body["tools_used"] == []
    assert "límite de chat" in body["answer"] or "chat limit" in body["answer"]


def test_sin_la_var_no_hay_cap(monkeypatch, token):
    """The piloto (no POLPILOT_DEMO_MSG_CAP) does not cap."""
    _no_provider(monkeypatch)
    monkeypatch.delenv("POLPILOT_DEMO_MSG_CAP", raising=False)
    for _ in range(4):
        r = client.post("/api/angela", json={"token": token, "message": "hola"})
        assert r.json().get("mode") != "cap"
