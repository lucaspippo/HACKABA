"""Confirm-before-save for chat-proposed knowledge.

`proponer_conocimiento` used to persist a `pendiente` piece the moment the
model called it, so the owner was told his own instruction needed someone's
approval and every ignored suggestion piled up in a review queue. It now
validates and returns a payload; POST /api/conocimiento/confirm writes it.
"""
import pytest
from fastapi.testclient import TestClient

import angela
import auth
import main
from core import conocimiento, memoria
from tests.conftest import limpiar_tabla_tenant

client = TestClient(main.app)

PROPOSAL = {
    "texto": "Los martes cerramos a las 13hs por el reparto de Rosario.",
    "nodo": "deposito",
    "ambito": "categoria",
    "entidad": "reparto",
}


@pytest.fixture(autouse=True)
def limpio():
    limpiar_tabla_tenant("business_knowledge_pieces")
    limpiar_tabla_tenant("user_memory")
    yield
    limpiar_tabla_tenant("business_knowledge_pieces")
    limpiar_tabla_tenant("user_memory")


@pytest.fixture(scope="module")
def tokens():
    creds = auth.cargar_o_generar_credenciales()
    return {u: client.post("/api/login", json={"username": u, "password": creds[u]}).json()["token"]
            for u in ("emilio", "deposito", "vendedor")}


def _confirm(tok, **overrides):
    body = {**PROPOSAL, **overrides}
    return client.post("/api/conocimiento/confirm", json=body,
                       headers={"Authorization": f"Bearer {tok}"})


# --- the proposal itself persists nothing -------------------------------------

def test_validate_proposal_writes_nothing():
    conocimiento.validate_proposal(
        texto="Una regla nueva", tipo="contexto", ambito="global",
        nodo="clientes", efecto="contexto_para_angela")
    assert conocimiento.listar() == []


def test_validate_proposal_normalizes_and_returns_the_fields():
    p = conocimiento.validate_proposal(
        texto="  con espacios  ", tipo="contexto", ambito="global",
        nodo="caja", efecto="contexto_para_angela", entidad="  ")
    assert p == {"texto": "con espacios", "tipo": "contexto", "ambito": "global",
                 "nodo": "caja", "efecto": "contexto_para_angela", "entidad": None}


def test_validate_proposal_rejects_a_node_outside_the_catalog():
    with pytest.raises(conocimiento.ConocimientoInvalido):
        conocimiento.validate_proposal(
            texto="x", tipo="contexto", ambito="global", nodo="marketing",
            efecto="contexto_para_angela")


def test_validate_proposal_rejects_a_scoped_piece_with_no_entity():
    with pytest.raises(conocimiento.ConocimientoInvalido):
        conocimiento.validate_proposal(
            texto="x", tipo="contexto", ambito="cliente", nodo="clientes",
            efecto="contexto_para_angela")


def test_the_tool_returns_a_proposal_and_saves_nothing():
    angela._set_sesion(usuario="emilio", rol="dueño", features=None, idioma="es")
    result, action = angela._run_tool("proponer_conocimiento",
                                     {"texto": "Regla nueva", "nodo": "caja"})
    assert result["ok"] and result["proposal"]["texto"] == "Regla nueva"
    assert action is None
    assert conocimiento.listar() == []


# --- confirming writes, with the authority the confirmer actually has ---------

def test_owner_confirmation_lands_active(tokens):
    r = _confirm(tokens["emilio"])
    assert r.status_code == 200
    assert r.json()["state"] == "activo"
    assert conocimiento.listar()[0]["texto"] == PROPOSAL["texto"]


def test_employee_confirming_their_own_node_lands_active(tokens):
    r = _confirm(tokens["deposito"])
    assert r.json()["state"] == "activo"


def test_employee_confirming_someone_elses_node_lands_pending(tokens):
    r = _confirm(tokens["vendedor"])
    assert r.json()["state"] == "pendiente"
    assert conocimiento.listar() == []
    assert len(conocimiento.pendientes()) == 1


def test_an_employee_cannot_activate_a_global_rule(tokens):
    """visibles_para returns every global piece to everyone, so it cannot
    decide this: it would let any employee self-approve a company-wide rule."""
    r = _confirm(tokens["deposito"], ambito="global", entidad=None)
    assert r.json()["state"] == "pendiente"


def test_confirming_twice_makes_one_piece(tokens):
    first = _confirm(tokens["emilio"]).json()
    second = _confirm(tokens["emilio"]).json()
    assert second["already_existed"] is True
    assert second["piece"]["id"] == first["piece"]["id"]
    assert len(conocimiento.listar()) == 1


def test_confirm_rejects_a_bad_node(tokens):
    assert _confirm(tokens["emilio"], nodo="marketing").status_code == 400


def test_confirm_needs_a_session(tokens):
    assert client.post("/api/conocimiento/confirm", json=PROPOSAL).status_code in (401, 403)


# --- the capture setting ------------------------------------------------------

def test_capture_off_hides_the_tool_from_the_model():
    names = [t["name"] for t in angela.tools_para(None, knowledge_capture=False)]
    assert "proponer_conocimiento" not in names
    assert "proponer_conocimiento" in [t["name"] for t in angela.tools_para(None)]


def test_capture_off_also_refuses_the_call():
    memoria.set_vista("emilio", "knowledge_capture", False)
    angela._set_sesion(usuario="emilio", rol="dueño", features=None, idioma="es")
    result, _ = angela._run_tool("proponer_conocimiento",
                                 {"texto": "Regla nueva", "nodo": "caja"})
    assert result["ok"] is False
    assert conocimiento.listar() == []


def test_capture_defaults_on_for_a_user_who_never_set_it():
    angela._set_sesion(usuario="emilio", rol="dueño", features=None, idioma="es")
    result, _ = angela._run_tool("proponer_conocimiento",
                                 {"texto": "Regla nueva", "nodo": "caja"})
    assert result["ok"] is True


# --- the context setting ------------------------------------------------------

def test_knowledge_block_carries_the_active_rules():
    conocimiento.crear(texto="A Doña Elsa tolerale 45 días.", tipo="regla",
                       ambito="cliente", nodo="clientes",
                       efecto="contexto_para_angela", entidad="Despensa Doña Elsa")
    angela._set_sesion(usuario="emilio", rol="dueño", features=None, idioma="es")
    block = angela._knowledge_block("emilio")
    assert "Doña Elsa" in block and "[clientes]" in block


def test_knowledge_block_is_empty_with_nothing_saved():
    angela._set_sesion(usuario="emilio", rol="dueño", features=None, idioma="es")
    assert angela._knowledge_block("emilio") == ""


def test_knowledge_block_skips_pending_and_paused_pieces():
    conocimiento.crear(texto="Todavía sin revisar", tipo="contexto", ambito="global",
                       nodo="caja", efecto="contexto_para_angela", estado="pendiente")
    conocimiento.crear(texto="En pausa", tipo="contexto", ambito="global",
                       nodo="caja", efecto="contexto_para_angela", estado="pausado")
    angela._set_sesion(usuario="emilio", rol="dueño", features=None, idioma="es")
    assert angela._knowledge_block("emilio") == ""


def test_knowledge_block_respects_node_scope():
    conocimiento.crear(texto="Regla de clientes", tipo="regla", ambito="cliente",
                       nodo="clientes", efecto="contexto_para_angela", entidad="Elsa")
    angela._set_sesion(usuario="deposito", rol="depósito",
                       features={"deposito", "logistica"}, idioma="es")
    assert angela._knowledge_block("deposito") == ""


def test_capture_off_covers_every_writing_tool():
    """The toggle says "save new memories": with only proponer_conocimiento
    gated, the model reached for `recordar` instead and wrote anyway."""
    names = [t["name"] for t in angela.tools_para(None, knowledge_capture=False)]
    assert not (set(names) & angela.CAPTURE_TOOLS)


def test_capture_off_refuses_recordar_too():
    memoria.set_vista("emilio", "knowledge_capture", False)
    angela._set_sesion(usuario="emilio", rol="dueño", features=None, idioma="es")
    result, _ = angela._run_tool("recordar", {"clave": "tono", "valor": "informal"})
    assert result["ok"] is False
    assert memoria.get("emilio")["preferencias"] == {}


# --- provenance: who taught it, when ------------------------------------------

def test_resumen_pieza_carries_who_taught_it():
    pieza = conocimiento.crear(
        texto="Regla con autor", tipo="contexto", ambito="global",
        nodo="caja", efecto="contexto_para_angela",
        origen={"quien": "aldo", "cuando": "2026-09-10"})
    resumen = conocimiento.resumen_pieza(pieza)
    assert resumen["quien"] == "aldo"


# --- consultar_conocimiento: read-only tool for chat and MCP ------------------

def test_consultar_conocimiento_returns_active_pieces():
    conocimiento.crear(texto="Visible", tipo="contexto", ambito="global",
                       nodo="caja", efecto="contexto_para_angela")
    angela._set_sesion(usuario="emilio", rol="dueño", features=None, idioma="es")
    result, action = angela._run_tool("consultar_conocimiento", {})
    assert action is None
    assert any(p["texto"] == "Visible" for p in result["piezas"])


def test_consultar_conocimiento_respects_role_scope():
    # ambito="categoria" (not "global"): a global piece is visible to every
    # employee by design (visibles_para), so it can't exercise node/feature
    # scoping — this needs a scoped piece, same as test_knowledge_block_respects_node_scope.
    conocimiento.crear(texto="Solo depósito", tipo="regla", ambito="categoria",
                       nodo="deposito", efecto="contexto_para_angela", entidad="depósito")
    angela._set_sesion(usuario="vendedor", rol="mostrador",
                       features={"cuentas"}, idioma="es")
    result, _ = angela._run_tool("consultar_conocimiento", {})
    assert result["piezas"] == []
