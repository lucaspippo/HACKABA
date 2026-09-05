"""proponer_conocimiento — the chat tool that OFFERS to remember a piece of
business knowledge, open to ANY user. It persists nothing: the payload rides
back on the tool result, the chip asks, and POST /api/conocimiento/confirm
writes it (see tests/test_conocimiento_confirmar.py). See
tests/test_conocimiento.py for the model and the REST layer's approve/reject;
this file covers only the chat entry point."""
from __future__ import annotations

import pytest

import angela
from core import conocimiento
from tests.conftest import limpiar_tabla_tenant


@pytest.fixture(autouse=True)
def limpio():
    limpiar_tabla_tenant("business_knowledge_pieces")
    usuario, rol = angela._usuario_actual(), angela._rol_actual()
    yield
    angela._set_sesion(usuario=usuario, rol=rol)
    limpiar_tabla_tenant("business_knowledge_pieces")


def test_cualquier_usuario_puede_proponer(db_tenant, monkeypatch):
    from core.db import tenant as tenant_module
    monkeypatch.setattr(tenant_module, "current_tenant_id", lambda: db_tenant)
    angela._set_sesion(usuario="vendedor", rol="Ventas y cobranzas")
    result, accion = angela._run_tool("proponer_conocimiento", {
        "texto": "El vendedor dijo que Doña Elsa siempre paga en fecha.",
        "nodo": "clientes", "entidad": "Despensa Doña Elsa",
    })
    assert result["ok"] is True
    assert accion is None
    propuesta = result["proposal"]
    assert propuesta["ambito"] == "cliente" or propuesta["ambito"] == "categoria"
    # tipo/efecto are NEVER chosen by the model — they stay fixed.
    assert propuesta["tipo"] == "contexto"
    assert propuesta["efecto"] == "contexto_para_angela"
    # and nothing was written: not as a piece, not even as a pending one
    assert conocimiento.listar() == []
    assert conocimiento.pendientes() == []
    assert conocimiento.aplicables(nodo="clientes") == []


def test_sin_entidad_queda_global(db_tenant, monkeypatch):
    from core.db import tenant as tenant_module
    monkeypatch.setattr(tenant_module, "current_tenant_id", lambda: db_tenant)
    angela._set_sesion(usuario="paula", rol="Administración")
    result, _ = angela._run_tool("proponer_conocimiento", {
        "texto": "Los viernes no se piden reposiciones al proveedor grande.",
        "nodo": "proveedores",
    })
    assert result["proposal"]["ambito"] == "global"


def test_nodo_invalido_no_rompe_devuelve_motivo(db_tenant, monkeypatch):
    from core.db import tenant as tenant_module
    monkeypatch.setattr(tenant_module, "current_tenant_id", lambda: db_tenant)
    angela._set_sesion(usuario="emilio", rol="Dueño")
    result, _ = angela._run_tool("proponer_conocimiento", {
        "texto": "x", "nodo": "no_existe",
    })
    assert result["ok"] is False and "motivo" in result


def test_proponer_no_deja_rastro_de_auditoria(db_tenant, monkeypatch):
    """Nothing happened yet, so nothing is audited. The audit entry belongs to
    the confirmation, which is the act with an effect."""
    from core.db import tenant as tenant_module
    monkeypatch.setattr(tenant_module, "current_tenant_id", lambda: db_tenant)
    from core.audit import AuditLog
    antes = len([e for e in AuditLog(None).list() if e["accion"] == "proponer_conocimiento"])
    angela._set_sesion(usuario="deposito", rol="Depósito")
    angela._run_tool("proponer_conocimiento", {
        "texto": "La balanza 3 pesa 50g de más.", "nodo": "deposito",
    })
    despues = len([e for e in AuditLog(None).list() if e["accion"] == "proponer_conocimiento"])
    assert despues == antes


def test_repropone_lo_ya_guardado_avisando_que_ya_esta(db_tenant, monkeypatch):
    from core.db import tenant as tenant_module
    monkeypatch.setattr(tenant_module, "current_tenant_id", lambda: db_tenant)
    pieza = conocimiento.crear(
        texto="La balanza 3 pesa 50g de más.", tipo="contexto", ambito="global",
        nodo="deposito", efecto="contexto_para_angela")
    angela._set_sesion(usuario="deposito", rol="Depósito")
    result, _ = angela._run_tool("proponer_conocimiento", {
        "texto": "La balanza 3 pesa 50g de más.", "nodo": "deposito",
    })
    assert result["already_saved"] == pieza["id"]
