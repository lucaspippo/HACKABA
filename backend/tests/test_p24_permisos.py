"""
P24·A — Seguridad y permisos: los documentos son POR USUARIO (server-side) y
los objetivos asignados LLEGAN al empleado y su avance vuelve al dueño.
"""
from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient

import auth
import main
from core import pdf as pdf_mod, perfiles


@pytest.fixture()
def indice_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(pdf_mod, "DOCS_DIR", str(tmp_path))
    monkeypatch.setattr(pdf_mod, "INDICE_JSON", str(tmp_path / "indice.json"))
    return tmp_path


@pytest.fixture()
def clientes():
    """emilio (dueño) + paula CON documentos habilitado (override real del dueño,
    limpiado al salir)."""
    creds = auth.cargar_o_generar_credenciales()
    c = TestClient(main.app)
    perfiles.set_feature("paula", "documentos", True, actor="emilio")
    toks = {}
    for u in ("emilio", "paula"):
        r = c.post("/api/login", json={"username": u, "password": creds[u]})
        assert r.status_code == 200
        toks[u] = r.json()["token"]
    yield c, toks
    perfiles.set_feature("paula", "documentos", False, actor="emilio")


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


# --- A1 · PDFs por usuario (las 4 combinaciones) -------------------------------

def test_pdf_por_usuario_4_combinaciones(indice_tmp, clientes):
    c, toks = clientes
    # dos documentos: uno de emilio, uno de paula (guardado por el camino real)
    m_emilio = pdf_mod.guardar({"tipo": "resumen_ejecutivo", "titulo": "Resumen de Emilio"},
                             b"%PDF-emilio", "Emilio", "es", username="emilio")
    m_rom = pdf_mod.guardar({"tipo": "orden_pedido", "titulo": "Orden de Paula"},
                            b"%PDF-paula", "Paula", "es", username="paula")

    # 1 · el dueño ve TODO (el suyo + el del equipo, con "pedido por")
    docs_emilio = c.get("/api/documentos/listado", headers=_h(toks["emilio"])).json()["documentos"]
    assert {d["id"] for d in docs_emilio} >= {m_emilio["id"], m_rom["id"]}

    # 2 · la empleada ve SOLO lo suyo
    docs_rom = c.get("/api/documentos/listado", headers=_h(toks["paula"])).json()["documentos"]
    assert {d["id"] for d in docs_rom} == {m_rom["id"]}

    # 3 · la empleada NO baja el del dueño (404: ni existe para ella)
    r = c.get(f"/api/documentos/archivo/{m_emilio['id']}", headers=_h(toks["paula"]))
    assert r.status_code == 404

    # 4 · el dueño SÍ baja el de la empleada; y cada uno el propio
    assert c.get(f"/api/documentos/archivo/{m_rom['id']}", headers=_h(toks["emilio"])).status_code == 200
    assert c.get(f"/api/documentos/archivo/{m_rom['id']}", headers=_h(toks["paula"])).status_code == 200


def test_pdf_empleado_no_ve_a_otro_empleado(indice_tmp):
    pdf_mod.guardar({"tipo": "carta", "titulo": "De vendedor"}, b"%PDF", "Vendedor",
                    "es", username="vendedor")
    assert pdf_mod.listado("paula", es_admin=False) == []
    docs = pdf_mod.listado("vendedor", es_admin=False)
    assert len(docs) == 1
    assert not pdf_mod.puede_ver(docs[0]["id"], "paula", es_admin=False)


# --- A2 · objetivos: asignar → llegar → avanzar → reflejarse -------------------

@pytest.fixture()
def objetivos_limpios():
    from core import objetivos
    backup = None
    if os.path.exists(objetivos.OBJETIVOS_JSON):
        backup = open(objetivos.OBJETIVOS_JSON, encoding="utf-8").read()
    yield
    if backup is not None:
        open(objetivos.OBJETIVOS_JSON, "w", encoding="utf-8").write(backup)
    elif os.path.exists(objetivos.OBJETIVOS_JSON):
        os.remove(objetivos.OBJETIVOS_JSON)


def test_objetivo_e2e_dueno_empleada(clientes, objetivos_limpios):
    c, toks = clientes
    # Aldo/Emilio asigna a Paula
    r = c.post("/api/objetivos", headers=_h(toks["emilio"]),
               json={"nombre": "Revisar los precios de balanza", "responsable": "Paula",
                     "fecha": "Esta semana", "id": "o-test-p24"})
    assert r.status_code == 200
    # a Paula LE LLEGA (server-side, sin depender del localStorage de nadie)
    objetivos = c.get("/api/objetivos", headers=_h(toks["paula"])).json()["objetivos"]
    mio = next(o for o in objetivos if o["id"] == "o-test-p24")
    assert mio["responsable"] == "Paula" and mio["estado"] == "pendiente"
    # Paula marca avance
    r = c.post("/api/objetivos/o-test-p24/estado", headers=_h(toks["paula"]),
               json={"estado": "en_proceso"})
    assert r.status_code == 200
    # y el dueño LO VE reflejado
    objetivos = c.get("/api/objetivos", headers=_h(toks["emilio"])).json()["objetivos"]
    assert next(o for o in objetivos if o["id"] == "o-test-p24")["estado"] == "en_proceso"
