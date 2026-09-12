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
