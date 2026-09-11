import os

import pytest

from core import store, saneamiento, memoria


@pytest.fixture(autouse=True)
def estado_limpio():
    store.resetear_actual()
    if os.path.exists(memoria.MEMORIA_JSON):
        os.remove(memoria.MEMORIA_JSON)
    yield
    store.resetear_actual()
    if os.path.exists(memoria.MEMORIA_JSON):
        os.remove(memoria.MEMORIA_JSON)


def test_panorama_estructura():
    p = store.panorama()
    assert p["resumen"]["inmovilizado_total"] > 0
    assert set(p["alertas"]) == {"fantasmas", "negativos", "sin_pvp", "balanza", "costo_viejo"}
    assert len(p["top_inmovilizado"]) <= 25
    assert "grupos" in p


def test_panorama_refleja_correccion_balanza():
    antes = store.panorama()["alertas"]["balanza"]["cantidad"]
    assert antes > 0
    saneamiento.aplicar("balanza", actor="emilio")
    assert store.panorama()["alertas"]["balanza"]["cantidad"] == 0


def test_panorama_refleja_correccion_fantasma():
    saneamiento.aplicar("fantasma", actor="emilio")
    assert store.panorama()["alertas"]["fantasmas"]["cantidad"] == 0
