import pytest

from core import conocimiento, insight
from tests.conftest import limpiar_tabla_tenant


@pytest.fixture(autouse=True)
def limpio():
    limpiar_tabla_tenant("business_knowledge_pieces")
    yield
    limpiar_tabla_tenant("business_knowledge_pieces")


def _pieza(**over):
    base = dict(texto="Tolerale 45 días", tipo="regla", ambito="cliente",
               nodo="clientes", efecto="ajusta_umbral", entidad="Doña Elsa")
    base.update(over)
    return conocimiento.crear(**base)


def test_knowledge_evidence_has_the_right_shape():
    p = _pieza()
    ev = insight.knowledge(p)
    assert ev["kind"] == "knowledge"
    assert ev["id"] == p["id"]
    assert ev["label"] == p["texto"]
    assert ev["weight"] == "supporting"
    assert ev["origen"] == p["origen"]
    assert ev["freshness"] in ("fresco", "atencion", "revisar")
    assert isinstance(ev["needs_review"], bool)


def test_knowledge_evidence_rejects_a_bad_weight():
    p = _pieza()
    with pytest.raises(ValueError):
        insight.knowledge(p, weight="load-bearing")


def test_knowledge_evidence_reflects_current_decay_not_build_time_decay():
    """freshness()/needs_review() are read from conocimiento at the moment
    knowledge() is called — this test just confirms the wiring calls
    through, the decay MATH itself is tested in test_conocimiento_decay.py."""
    p = _pieza()
    ev = insight.knowledge(p)
    assert ev["freshness"] == conocimiento.freshness(p)
