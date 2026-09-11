import pytest

from core import memoria
from tests.conftest import limpiar_tabla_tenant


@pytest.fixture(autouse=True)
def limpio():
    limpiar_tabla_tenant("user_memory")
    yield
    limpiar_tabla_tenant("user_memory")


def test_get_estructura_vacia():
    m = memoria.get("emilio")
    assert set(m) >= {"preferencias", "categorias_auto", "objetivos", "datos_cargados", "recomendaciones"}


def test_set_pref_y_persistencia():
    memoria.set_pref("emilio", "ver_primero", "margen_congelados")
    assert memoria.get("emilio")["preferencias"]["ver_primero"] == "margen_congelados"


def test_compat_aprobar_categoria():
    memoria.aprobar_categoria("emilio", "balanza")
    assert "balanza" in memoria.preferencias("emilio")["categorias_auto"]


def test_dato_cargado_y_objetivo():
    memoria.marcar_dato_cargado("emilio", "ventas")
    memoria.agregar_objetivo("emilio", "Abrir 5 locales")
    m = memoria.get("emilio")
    assert "ventas" in m["datos_cargados"]
    assert "Abrir 5 locales" in m["objetivos"]


def test_recomendacion_y_resultado():
    rec = memoria.registrar_recomendacion("emilio", "Corregir balanzas")
    memoria.registrar_resultado("emilio", rec["id"], "recuperó $56M")
    r = memoria.get("emilio")["recomendaciones"][0]
    assert r["resultado"] == "recuperó $56M"
