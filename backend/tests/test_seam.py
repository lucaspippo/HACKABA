import pytest

import data_store as ds
from core import store, saneamiento
from tests.conftest import limpiar_tabla_tenant


@pytest.fixture(autouse=True)
def estado_limpio():
    store.resetear_actual()
    limpiar_tabla_tenant("user_memory")
    yield
    store.resetear_actual()
    limpiar_tabla_tenant("user_memory")


def test_data_store_coincide_con_original():
    # El inmovilizado sigue saliendo por el seam unificado. Los valores son los
    # del catálogo sintético (data-demo/inventory.json, seed fijo).
    r = ds.resumen()
    assert 430_000_000 < r["resumen"]["inmovilizado_total"] < 460_000_000
    assert r["alertas"]["fantasmas"]["cantidad"] == 3
    assert r["alertas"]["balanza"]["cantidad"] == 2


def test_correccion_se_refleja_en_data_store():
    saneamiento.aplicar("fantasma", actor="emilio")
    assert ds.resumen()["alertas"]["fantasmas"]["cantidad"] == 0
    assert ds.listar_grupo("fantasmas") == []


def test_correccion_balanza_se_refleja_en_data_store():
    saneamiento.aplicar("balanza", actor="emilio")
    assert ds.resumen()["alertas"]["balanza"]["cantidad"] == 0
