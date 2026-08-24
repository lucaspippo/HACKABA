"""
P9·C5 (M9) — crear_objetivo persiste SERVER-SIDE, no solo en el localStorage
de quien lo pidió: lo ve todo el equipo, sobrevive a un navegador limpio, y
la mezcla local↔server es idempotente por id.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

import angela
import auth
import main
from core import objetivos


client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _limpio():
    if os.path.exists(objetivos.OBJETIVOS_JSON):
        os.remove(objetivos.OBJETIVOS_JSON)
    yield
    if os.path.exists(objetivos.OBJETIVOS_JSON):
        os.remove(objetivos.OBJETIVOS_JSON)
    angela._set_sesion()  # la sesión de Ángela vuelve a los defaults


@pytest.fixture()
def h():
    creds = auth.cargar_o_generar_credenciales()
    tok = client.post("/api/login", json={"username": "emilio",
                                          "password": creds["emilio"]}).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


def test_tool_crear_objetivo_persiste_en_el_server():
    angela._set_sesion(usuario="emilio", rol="Dueño")
    res, accion = angela._run_tool("crear_objetivo",
                                   {"nombre": "Bajar el inmovilizado de lácteos",
                                    "responsable": "Paula", "fecha": "este mes"})
    assert res["ok"] is True and res["id"]
    # quedó en el dominio del server, con quién lo creó
    guardados = objetivos.listar()
    assert len(guardados) == 1
    assert guardados[0]["nombre"] == "Bajar el inmovilizado de lácteos"
    assert guardados[0]["creado_por"] == "emilio"
    # la accion lleva el id del server para que el tablero no duplique
    assert accion["type"] == "crear_objetivo" and accion["id"] == res["id"]


def test_endpoints_objetivos_round_trip(h):
    assert client.get("/api/objetivos").status_code == 401  # sin token no hay tablero
    r = client.post("/api/objetivos", headers=h,
                    json={"nombre": "Contar el depósito", "responsable": "Ramón",
                          "fecha": "el lunes", "id": "oCLIENTE1"})
    assert r.status_code == 200 and r.json()["id"] == "oCLIENTE1"
    # idempotente: el mismo id no duplica
    client.post("/api/objetivos", headers=h,
                json={"nombre": "Contar el depósito", "id": "oCLIENTE1"})
    lista = client.get("/api/objetivos", headers=h).json()["objetivos"]
    assert len(lista) == 1

    r2 = client.post("/api/objetivos/oCLIENTE1/estado", headers=h,
                     json={"estado": "en_proceso"})
    assert r2.status_code == 200 and r2.json()["estado"] == "en_proceso"
    assert client.post("/api/objetivos/noexiste/estado", headers=h,
                       json={"estado": "listo"}).status_code == 404
    assert client.post("/api/objetivos/oCLIENTE1/estado", headers=h,
                       json={"estado": "cualquiera"}).status_code == 422
