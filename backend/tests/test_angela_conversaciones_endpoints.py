"""main.py's /api/angela + /api/angela/stream persistence side effect, and
the /api/angela/conversaciones read endpoints. No LLM call needed: these
tests run with no provider configured (the tests suite's default), which
angela.responder/stream_response already turn into a clean "unavailable"
result — see tests/test_chat_protocol.py. That is enough to prove the USER
side of the turn gets persisted even when Ángela can't answer, and lets the
suite stay network-free."""
import config
import pytest
from fastapi.testclient import TestClient

import auth
import main

client = TestClient(main.app)


def _no_provider(monkeypatch):
    for var in config.credential_vars():
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def emilio_token():
    creds = auth.cargar_o_generar_credenciales()
    return client.post("/api/login", json={"username": "emilio", "password": creds["emilio"]}).json()["token"]


@pytest.fixture
def paula_token():
    creds = auth.cargar_o_generar_credenciales()
    return client.post("/api/login", json={"username": "paula", "password": creds["paula"]}).json()["token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def test_chat_persists_the_user_side_of_the_turn(emilio_token, monkeypatch):
    _no_provider(monkeypatch)
    r = client.post("/api/angela", json={"message": "¿cuánto vendimos hoy?", "token": emilio_token})
    assert r.status_code == 200

    got = client.get("/api/angela/conversaciones", headers=_h(emilio_token),
                     params={"actor": "emilio"})
    assert got.status_code == 200
    convs = got.json()["conversations"]
    assert convs, "expected a persisted conversation for emilio"

    full = client.get(f"/api/angela/conversaciones/{convs[0]['id']}", headers=_h(emilio_token))
    assert full.status_code == 200
    messages = full.json()["messages"]
    assert any(m["role"] == "user" and m["content"] == "¿cuánto vendimos hoy?"
              for m in messages)


def test_conversations_requires_auditoria_feature(paula_token):
    r = client.get("/api/angela/conversaciones", headers=_h(paula_token))
    assert r.status_code == 403


def test_conversations_requires_auth():
    r = client.get("/api/angela/conversaciones")
    assert r.status_code == 401


def test_missing_conversation_is_404(emilio_token):
    r = client.get("/api/angela/conversaciones/no-existe", headers=_h(emilio_token))
    assert r.status_code == 404


def test_voice_channel_is_tagged_and_kept_separate(emilio_token, monkeypatch):
    _no_provider(monkeypatch)
    r = client.post("/api/angela", json={"message": "faltan ocho cajas",
                                          "token": emilio_token, "channel": "voz"})
    assert r.status_code == 200

    voice_only = client.get("/api/angela/conversaciones", headers=_h(emilio_token),
                            params={"actor": "emilio", "channel": "voz"}).json()["conversations"]
    assert voice_only
    assert all(c["channel"] == "voz" for c in voice_only)


def test_unrecognized_channel_falls_back_to_chat(emilio_token, monkeypatch):
    _no_provider(monkeypatch)
    r = client.post("/api/angela", json={"message": "algo raro",
                                          "token": emilio_token, "channel": "not-a-channel"})
    assert r.status_code == 200

    convs = client.get("/api/angela/conversaciones", headers=_h(emilio_token),
                       params={"actor": "emilio", "channel": "chat"}).json()["conversations"]
    assert any(m["content"] == "algo raro"
              for c in convs
              for m in client.get(f"/api/angela/conversaciones/{c['id']}",
                                  headers=_h(emilio_token)).json()["messages"])
