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
