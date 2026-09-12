"""Confirm-before-save for chat-proposed knowledge.

`proponer_conocimiento` used to persist a `pendiente` piece the moment the
model called it, so the owner was told his own instruction needed someone's
approval and every ignored suggestion piled up in a review queue. It now
validates and returns a payload; POST /api/conocimiento/confirm writes it.
"""
from datetime import date

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


def test_admin_edit_keeps_the_piece_active():
    pieza = conocimiento.crear(texto="Original", tipo="contexto", ambito="global",
                               nodo="caja", efecto="contexto_para_angela",
                               origen={"quien": "aldo", "cuando": "2026-09-10"})
    out = conocimiento.edit_piece(pieza["id"], actor="aldo", is_admin=True,
                                  texto="Editado por el admin")
    assert out["texto"] == "Editado por el admin"
    assert out["estado"] == "activo"


def test_author_non_admin_edit_re_enters_staging():
    pieza = conocimiento.crear(texto="Original", tipo="contexto", ambito="global",
                               nodo="caja", efecto="contexto_para_angela",
                               origen={"quien": "vendedor", "cuando": "2026-09-10"})
    out = conocimiento.edit_piece(pieza["id"], actor="vendedor", is_admin=False,
                                  texto="Editado por el autor")
    assert out["texto"] == "Editado por el autor"
    assert out["estado"] == "pendiente"


def test_edit_validates_like_crear():
    pieza = conocimiento.crear(texto="Original", tipo="contexto", ambito="global",
                               nodo="caja", efecto="contexto_para_angela")
    with pytest.raises(conocimiento.ConocimientoInvalido):
        conocimiento.edit_piece(pieza["id"], actor="aldo", is_admin=True, tipo="no-existe")


def test_edit_returns_none_for_a_missing_piece():
    assert conocimiento.edit_piece("no-existe", actor="aldo", is_admin=True, texto="x") is None


def test_edit_endpoint_needs_admin_or_author(tokens):
    pieza = conocimiento.crear(texto="Original", tipo="contexto", ambito="global",
                               nodo="caja", efecto="contexto_para_angela",
                               origen={"quien": "deposito", "cuando": "2026-09-10"})
    # vendedor is neither admin nor the author "deposito"
    r = client.post(f"/api/conocimiento/{pieza['id']}/editar",
                    json={"texto": "intento ajeno"},
                    headers={"Authorization": f"Bearer {tokens['vendedor']}"})
    assert r.status_code == 403
    # deposito IS the author
    r = client.post(f"/api/conocimiento/{pieza['id']}/editar",
                    json={"texto": "editado por su autor"},
                    headers={"Authorization": f"Bearer {tokens['deposito']}"})
    assert r.status_code == 200
    assert r.json()["pieza"]["texto"] == "editado por su autor"


def test_edit_endpoint_404s_on_a_missing_piece(tokens):
    r = client.post("/api/conocimiento/no-existe/editar", json={"texto": "x"},
                    headers={"Authorization": f"Bearer {tokens['emilio']}"})
    assert r.status_code == 404


def test_archive_endpoint_needs_admin_or_author(tokens):
    pieza = conocimiento.crear(texto="x", tipo="contexto", ambito="global",
                               nodo="caja", efecto="contexto_para_angela",
                               origen={"quien": "aldo", "cuando": "2026-09-10"})
    r = client.post(f"/api/conocimiento/{pieza['id']}/archivar", json={},
                    headers={"Authorization": f"Bearer {tokens['vendedor']}"})
    assert r.status_code == 403
    r = client.post(f"/api/conocimiento/{pieza['id']}/archivar", json={},
                    headers={"Authorization": f"Bearer {tokens['emilio']}"})
    assert r.status_code == 200
    assert r.json()["pieza"]["estado"] == "archivada"


def test_reconfirmar_endpoint(tokens):
    pieza = conocimiento.crear(texto="x", tipo="contexto", ambito="global",
                               nodo="caja", efecto="contexto_para_angela")
    conocimiento.set_estado(pieza["id"], "revisar")
    r = client.post(f"/api/conocimiento/{pieza['id']}/reconfirmar", json=None,
                    headers={"Authorization": f"Bearer {tokens['emilio']}"})
    assert r.status_code == 200
    assert r.json()["pieza"]["estado"] == "activo"


def test_resumen_pieza_includes_the_replacement_text():
    old = conocimiento.crear(texto="Vieja", tipo="regla", ambito="global",
                             nodo="caja", efecto="contexto_para_angela")
    new = conocimiento.crear(texto="Nueva", tipo="regla", ambito="global",
                             nodo="caja", efecto="contexto_para_angela")
    conocimiento.supersede(old["id"], replacement_id=new["id"], actor="aldo")
    resumen = conocimiento.resumen_pieza(conocimiento.detalle(old["id"]))
    assert resumen["superseded_by_texto"] == "Nueva"


def test_create_endpoint_blocks_a_conflicting_rule(tokens):
    conocimiento.crear(texto="Tolerale 30 días", tipo="regla", ambito="cliente",
                       nodo="clientes", efecto="ajusta_umbral", entidad="Doña Elsa")
    r = client.post("/api/conocimiento", json={
        "texto": "Tolerale 45 días", "tipo": "regla", "ambito": "cliente",
        "nodo": "clientes", "efecto": "ajusta_umbral", "entidad": "Doña Elsa"},
        headers={"Authorization": f"Bearer {tokens['emilio']}"})
    assert r.status_code == 409


def test_age_days_counts_from_origen_cuando():
    pieza = conocimiento.crear(texto="x", tipo="contexto", ambito="global",
                               nodo="caja", efecto="contexto_para_angela",
                               origen={"quien": "aldo", "cuando": "2026-08-01"})
    assert conocimiento.age_days(pieza, today=date(2026, 9, 10)) == 40


def test_age_days_is_none_without_origen():
    pieza = conocimiento.crear(texto="x", tipo="contexto", ambito="global",
                               nodo="caja", efecto="contexto_para_angela")
    assert conocimiento.age_days(pieza) is None


def test_the_tool_can_propose_a_real_effect():
    angela._set_sesion(usuario="emilio", rol="dueño", features=None, idioma="es")
    result, _ = angela._run_tool("proponer_conocimiento", {
        "texto": "Suprimí la alerta de balanza 2, desvía menos de 1%",
        "nodo": "deposito", "efecto_sugerido": "suprime_alerta",
        "tipo_sugerido": "excepcion"})
    assert result["proposal"]["efecto"] == "suprime_alerta"
    assert result["proposal"]["tipo"] == "excepcion"


def test_confirming_just_context_still_forces_narrative_effect(tokens):
    r = client.post("/api/conocimiento/confirm", json={
        "texto": "Suprimí la alerta de balanza 2", "nodo": "deposito",
        "tipo": "contexto", "efecto": "contexto_para_angela"},  # client explicitly chose "just remember"
        headers={"Authorization": f"Bearer {tokens['emilio']}"})
    assert r.json()["piece"]["efecto"] == "contexto_para_angela"


def test_confirming_apply_the_rule_passes_the_real_effect_through(tokens):
    r = client.post("/api/conocimiento/confirm", json={
        "texto": "Suprimí la alerta de balanza 2", "nodo": "deposito",
        "tipo": "excepcion", "efecto": "suprime_alerta"},  # client explicitly chose "also apply"
        headers={"Authorization": f"Bearer {tokens['emilio']}"})
    assert r.json()["piece"]["efecto"] == "suprime_alerta"
