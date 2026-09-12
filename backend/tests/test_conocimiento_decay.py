import pytest
from datetime import date, timedelta

from core import conocimiento
from tests.conftest import limpiar_tabla_tenant


@pytest.fixture(autouse=True)
def limpio():
    limpiar_tabla_tenant("business_knowledge_pieces")
    yield
    limpiar_tabla_tenant("business_knowledge_pieces")


def _pieza(tipo="regla", half_life_days=None):
    return conocimiento.crear(texto="x", tipo=tipo, ambito="global", nodo="caja",
                              efecto="contexto_para_angela", half_life_days=half_life_days)


def test_decay_score_at_zero_age_equals_stored_confidence():
    p = _pieza()
    assert conocimiento.decay_score(p, today=date.fromisoformat(p["last_reinforced_at"][:10])) == pytest.approx(0.7)


def test_decay_score_halves_at_one_half_life():
    p = _pieza(half_life_days=100)
    ref = date.fromisoformat(p["last_reinforced_at"][:10])
    aged = ref + timedelta(days=100)
    assert conocimiento.decay_score(p, today=aged) == pytest.approx(0.35, abs=0.01)


def test_decay_score_uses_tipo_default_when_no_override():
    regla = _pieza(tipo="regla")  # default half-life 180
    protocolo = _pieza(tipo="protocolo")  # default half-life 365
    ref = date.fromisoformat(regla["last_reinforced_at"][:10])
    aged = ref + timedelta(days=180)
    assert conocimiento.decay_score(regla, today=aged) == pytest.approx(0.35, abs=0.01)
    assert conocimiento.decay_score(protocolo, today=aged) > 0.45  # decayed less


def test_needs_review_crosses_the_default_threshold():
    p = _pieza(half_life_days=10)
    ref = date.fromisoformat(p["last_reinforced_at"][:10])
    far = ref + timedelta(days=60)
    assert conocimiento.needs_review(p, today=far) is True
    assert conocimiento.needs_review(p, today=ref) is False


def test_freshness_buckets():
    p = _pieza(half_life_days=100)
    ref = date.fromisoformat(p["last_reinforced_at"][:10])
    assert conocimiento.freshness(p, today=ref) == "fresco"
    far = ref + timedelta(days=200)
    assert conocimiento.freshness(p, today=far) == "revisar"


def test_reinforce_resets_last_reinforced_at_and_bumps_confidence():
    p = _pieza()
    before = p["confidence"]
    out = conocimiento.reinforce(p["id"])
    assert out["confidence"] > before
    assert out["evidence_count"] == p["evidence_count"] + 1


def test_reinforce_has_diminishing_returns_and_never_exceeds_one():
    p = _pieza()
    pid = p["id"]
    last = p["confidence"]
    for _ in range(20):
        out = conocimiento.reinforce(pid)
        bump = out["confidence"] - last
        assert bump >= 0
        last = out["confidence"]
    assert last <= 1.0


def test_find_conflict_matches_same_triple_different_text():
    conocimiento.crear(texto="Tolerale 30 días", tipo="regla", ambito="cliente",
                       nodo="clientes", efecto="ajusta_umbral", entidad="Doña Elsa",
                       params={"tolerancia_dias": 30})
    conflict = conocimiento.find_conflict(
        texto="Tolerale 45 días", nodo="clientes", entidad="Doña Elsa",
        efecto="ajusta_umbral")
    assert conflict is not None
    assert conflict["params"]["tolerancia_dias"] == 30


def test_find_conflict_is_none_for_identical_text():
    conocimiento.crear(texto="Tolerale 30 días", tipo="regla", ambito="cliente",
                       nodo="clientes", efecto="ajusta_umbral", entidad="Doña Elsa")
    assert conocimiento.find_conflict(
        texto="Tolerale 30 días", nodo="clientes", entidad="Doña Elsa",
        efecto="ajusta_umbral") is None


def test_find_conflict_is_none_for_a_different_efecto():
    conocimiento.crear(texto="Tolerale 30 días", tipo="regla", ambito="cliente",
                       nodo="clientes", efecto="ajusta_umbral", entidad="Doña Elsa")
    assert conocimiento.find_conflict(
        texto="Otra regla", nodo="clientes", entidad="Doña Elsa",
        efecto="suprime_alerta") is None


def test_archive_moves_an_active_piece_out_of_aplicables():
    p = conocimiento.crear(texto="x", tipo="regla", ambito="cliente", nodo="clientes",
                           efecto="ajusta_umbral", entidad="Doña Elsa")
    conocimiento.archive(p["id"], actor="aldo")
    assert conocimiento.detalle(p["id"])["estado"] == "archivada"
    assert conocimiento.para("Doña Elsa", nodo="clientes") == []


def test_listar_excludes_archived_by_default():
    p = conocimiento.crear(texto="x", tipo="contexto", ambito="global",
                           nodo="caja", efecto="contexto_para_angela")
    conocimiento.archive(p["id"], actor="aldo")
    assert conocimiento.listar() == []
    assert len(conocimiento.listar(incluir_archivadas=True)) == 1


def test_supersede_links_the_replacement():
    old = conocimiento.crear(texto="Tolerale 30 días", tipo="regla", ambito="cliente",
                             nodo="clientes", efecto="ajusta_umbral", entidad="Doña Elsa")
    new = conocimiento.crear(texto="Tolerale 45 días", tipo="regla", ambito="cliente",
                             nodo="clientes", efecto="ajusta_umbral", entidad="Doña Elsa")
    conocimiento.supersede(old["id"], replacement_id=new["id"], actor="aldo")
    assert conocimiento.detalle(old["id"])["estado"] == "superada"
    assert conocimiento.detalle(old["id"])["superseded_by"] == new["id"]


def test_reconfirm_reinforces_and_reactivates_from_revisar():
    p = conocimiento.crear(texto="x", tipo="contexto", ambito="global",
                           nodo="caja", efecto="contexto_para_angela")
    conocimiento.set_estado(p["id"], "revisar")
    out = conocimiento.reconfirm(p["id"], actor="aldo")
    assert out["estado"] == "activo"
    assert out["evidence_count"] == p["evidence_count"] + 1
