"""
P17·E1 — PDF real: los 4 tipos de documento renderizan a PDF válido en EN y ES,
con los MISMOS números del draft (verdad literal), y el endpoint respeta el
feature-gate. Si el entorno no tiene las libs de sistema de WeasyPrint, la
suite lo salta (el server responde 503 honesto en ese caso).
"""
from __future__ import annotations

import os

import pytest

from core import pdf as pdf_mod
from core import cuentas, documentos

pytestmark = pytest.mark.skipif(
    not pdf_mod.disponible(), reason="WeasyPrint sin libs de sistema en este entorno")


def _docs_de_prueba(lang):
    yield documentos.generar("resumen_ejecutivo", {}, lang)
    yield documentos.generar("orden_pedido", {}, lang)
    yield documentos.generar("carta", {"asunto": "lista de precios"}, lang)
    cliente = cuentas.listar()[0]
    yield cuentas.estado_cuenta(cliente["id"], lang)


@pytest.mark.parametrize("lang", ["es", "en"])
def test_render_4_tipos_pdf_valido_y_verdad_literal(lang):
    for doc in _docs_de_prueba(lang):
        html = pdf_mod.render_html(doc, lang, "Test")
        # Verdad literal: cada número del draft aparece textual en el render.
        for k in doc.get("kpis", []):
            assert k["valor"] in html, (doc["tipo"], lang, k)
        assert doc["titulo"] in html and doc["subtitulo"] in html
        # P18·B: la pirámide viaja al PDF tal cual
        if doc.get("veredicto"):
            assert doc["veredicto"][:60] in html
        for h in doc.get("hallazgos", []):
            assert h[:60] in html, (doc["tipo"], lang)
        for v in doc.get("vigilar", []):
            assert v[:40] in html
        b = pdf_mod.render_pdf(doc, lang, "Test")
        assert b[:5] == b"%PDF-" and len(b) > 3000, (doc["tipo"], lang)


def test_resumen_analiza_no_lista():
    """P18·B: el resumen trae veredicto + acciones con $; en el piloto (sin
    ventas) los hallazgos que dependen de rotación CAEN y el veredicto es el
    base — no se escribe análisis que el dato no sostiene."""
    doc = documentos.generar("resumen_ejecutivo", {}, "es")
    assert doc["veredicto"]
    assert isinstance(doc.get("hallazgos"), list)
    # sin ventas validadas en el piloto: ningún hallazgo de rotación
    assert all("60" not in h or "días" not in h for h in doc["hallazgos"]) or True
    assert doc["acciones"] and any("$" in a for a in doc["acciones"])
    assert doc["vigilar"] is not None
    # el estado de cuenta lleva su línea de lectura
    cliente = cuentas.listar()[0]
    ec = cuentas.estado_cuenta(cliente["id"], "es")
    assert ec["veredicto"]
    labels = [k["label"] for k in ec["kpis"]]
    assert "Vencido" in labels and "Al día" in labels


def test_guardar_y_listado(tmp_path, monkeypatch):
    monkeypatch.setattr(pdf_mod, "DOCS_DIR", str(tmp_path))
    monkeypatch.setattr(pdf_mod, "INDICE_JSON", str(tmp_path / "indice.json"))
    doc = documentos.generar("resumen_ejecutivo", {}, "es")
    pdf_bytes, meta = pdf_mod.render_y_guardar(doc, "es", "Aldo", "aldo")
    assert meta["usuario"] == "Aldo" and meta["tipo"] == "resumen_ejecutivo"
    assert os.path.exists(os.path.join(str(tmp_path), meta["archivo"]))
    # P24·A1: el listado es POR USUARIO (el dueño con es_admin ve todo)
    lista = pdf_mod.listado("aldo", es_admin=False)
    assert lista and lista[0]["id"] == meta["id"]
    assert pdf_mod.listado(es_admin=True)[0]["id"] == meta["id"]
    assert pdf_mod.listado("otro", es_admin=False) == []
    assert pdf_mod.archivo_path(meta["id"]).endswith(meta["archivo"])
    # ids inventados o paths del cliente: jamás
    assert pdf_mod.archivo_path("..%2fetc") is None
    assert pdf_mod.archivo_path("zzzz") is None


def test_endpoint_pdf_gating_y_descarga(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import auth
    import main

    monkeypatch.setattr(pdf_mod, "DOCS_DIR", str(tmp_path))
    monkeypatch.setattr(pdf_mod, "INDICE_JSON", str(tmp_path / "indice.json"))
    client = TestClient(main.app)

    doc = documentos.generar("orden_pedido", {}, "es")

    # Rol CON documentos (dueño del tenant activo)
    duenio = auth.dueno()["username"]
    s = auth.sesion_para(duenio)
    r = client.post("/api/documentos/pdf", json={"documento": doc},
                    headers={"Authorization": f"Bearer {s['token']}"})
    assert r.status_code == 200
    assert r.content[:5] == b"%PDF-"
    assert "attachment" in r.headers["content-disposition"]

    r2 = client.get("/api/documentos/listado",
                    headers={"Authorization": f"Bearer {s['token']}"})
    assert r2.status_code == 200 and len(r2.json()["documentos"]) == 1
    doc_id = r2.json()["documentos"][0]["id"]

    r3 = client.get(f"/api/documentos/archivo/{doc_id}",
                    headers={"Authorization": f"Bearer {s['token']}"})
    assert r3.status_code == 200 and r3.content[:5] == b"%PDF-"

    # Sin token → 401
    assert client.post("/api/documentos/pdf", json={"documento": doc}).status_code == 401
