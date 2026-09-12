"""proponer_conocimiento — el tool de chat que deja una propuesta de
conocimiento del negocio "pendiente" (core/conocimiento.py's staging state),
open a CUALQUIER usuario. Ver tests/test_conocimiento.py para el modelo y la
capa REST de aprobar/rechazar; acá solo la vía de entrada por chat."""
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
    assert result["pendiente"] is True
    assert accion is None
    pieza = result["pieza"]
    assert pieza["estado"] == "pendiente"
    assert pieza["origen"]["quien"] == "vendedor"
    # tipo/efecto NUNCA los elige el modelo — quedan fijos, inertes hasta
    # que alguien los confirme (mismo principio que pattern_feedback.learn()).
    assert pieza["tipo"] == "contexto"
    assert pieza["efecto"] == "contexto_para_angela"
    # y no tiene efecto todavía: no aparece entre las aplicables
    assert conocimiento.aplicables(nodo="clientes") == []


def test_sin_entidad_queda_global(db_tenant, monkeypatch):
    from core.db import tenant as tenant_module
    monkeypatch.setattr(tenant_module, "current_tenant_id", lambda: db_tenant)
    angela._set_sesion(usuario="paula", rol="Administración")
    result, _ = angela._run_tool("proponer_conocimiento", {
        "texto": "Los viernes no se piden reposiciones al proveedor grande.",
        "nodo": "proveedores",
    })
    assert result["pieza"]["ambito"] == "global"


def test_nodo_invalido_no_rompe_devuelve_motivo(db_tenant, monkeypatch):
    from core.db import tenant as tenant_module
    monkeypatch.setattr(tenant_module, "current_tenant_id", lambda: db_tenant)
    angela._set_sesion(usuario="emilio", rol="Dueño")
    result, _ = angela._run_tool("proponer_conocimiento", {
        "texto": "x", "nodo": "no_existe",
    })
    assert result["ok"] is False and "motivo" in result


def test_propuesta_audita_quien_la_hizo(db_tenant, monkeypatch):
    from core.db import tenant as tenant_module
    monkeypatch.setattr(tenant_module, "current_tenant_id", lambda: db_tenant)
    angela._set_sesion(usuario="deposito", rol="Depósito")
    angela._run_tool("proponer_conocimiento", {
        "texto": "La balanza 3 pesa 50g de más.", "nodo": "deposito",
    })
    from core.audit import AuditLog
    eventos = AuditLog(None).list()
    ev = next(e for e in eventos if e["accion"] == "proponer_conocimiento")
    assert ev["actor"] == "deposito"
