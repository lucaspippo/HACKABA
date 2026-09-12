"""EL CEREBRO — que una pieza de conocimiento pausada no aparezca como si
siguiera conectada a su entidad en el mapa (grafo.construir())."""
import pytest

from core import conocimiento, grafo
from tests.conftest import limpiar_tabla_tenant


@pytest.fixture(autouse=True)
def limpio():
    limpiar_tabla_tenant("business_knowledge_pieces")
    yield
    limpiar_tabla_tenant("business_knowledge_pieces")


def test_paused_knowledge_does_not_appear_connected_on_the_map():
    # "Despensa González" is a real cliente in the piloto tenant's seed (the
    # suite's fixture data — the brief's "Despensa Doña Elsa" example is
    # demo-tenant only and has no matching node here).
    pieza = conocimiento.crear(
        texto="Regla pausada", tipo="regla", ambito="cliente",
        nodo="clientes", efecto="ajusta_umbral", entidad="Despensa González")
    conocimiento.pausar(pieza["id"])
    g = grafo.construir()
    cliente = next((n for n in g["nodos"] if n["tipo"] == "cliente"
                    and "González" in n["nombre"]), None)
    assert cliente is not None
    assert pieza["id"] not in (cliente.get("conocimiento") or [])


def test_knowledge_piece_is_a_real_node_with_an_edge_to_its_entity():
    pieza = conocimiento.crear(
        texto="Tolerale 45 días", tipo="regla", ambito="cliente",
        nodo="clientes", efecto="ajusta_umbral", entidad="Despensa González")
    g = grafo.construir()
    nid = f"conocimiento:{pieza['id']}"
    node = g["_indice"].get(nid)
    assert node is not None
    assert node["tipo"] == "conocimiento"
    cliente = next((n for n in g["nodos"] if n["tipo"] == "cliente"
                    and "González" in n["nombre"]), None)
    arista = next((a for a in g["aristas"]
                  if a["source"] == nid and a["target"] == cliente["id"]), None)
    assert arista is not None
    assert arista["rel"] == "aplica_a"


def test_a_stale_knowledge_node_is_flagged_atencion(monkeypatch):
    pieza = conocimiento.crear(
        texto="Vieja regla", tipo="regla", ambito="cliente", nodo="clientes",
        efecto="ajusta_umbral", entidad="Despensa González", half_life_days=1)
    # half_life_days=1 with "today" pushed far out decays this well past the
    # review floor regardless of the real last_reinforced_at timestamp.
    monkeypatch.setenv("POLPILOT_DEMO_TODAY", "2030-01-01")
    g = grafo.construir()
    node = g["_indice"][f"conocimiento:{pieza['id']}"]
    assert node["riesgo"] == "atencion"


def test_archived_knowledge_produces_no_node():
    pieza = conocimiento.crear(
        texto="Retirada", tipo="regla", ambito="cliente", nodo="clientes",
        efecto="ajusta_umbral", entidad="Despensa González")
    conocimiento.archive(pieza["id"], actor="aldo")
    g = grafo.construir()
    assert f"conocimiento:{pieza['id']}" not in g["_indice"]


def test_caminos_can_seed_from_a_knowledge_piece():
    pieza = conocimiento.crear(
        texto="Tolerale 45 días", tipo="regla", ambito="cliente", nodo="clientes",
        efecto="ajusta_umbral", entidad="Despensa González")
    g = grafo.construir()
    card = {"id": "x", "titulo": "x", "tipo": "x",
            "conocimiento_aplicado": [conocimiento.resumen_pieza(pieza)]}
    caminos = grafo.caminos(g, [card])
    assert caminos
    assert f"conocimiento:{pieza['id']}" in caminos[0]["semillas"]
