import pytest

from core import anomalias, store


@pytest.fixture(autouse=True)
def limpio():
    # El catálogo sintético viene sin precios a pérdida (el generador lo dejó
    # sano en esa dimensión), así que el detector se prueba sembrando dos
    # artículos rotos sobre la copia de trabajo — nunca sobre el seed.
    store.resetear_actual()
    raw = store.raw_actual()
    raw += [
        {"codigo": 990001, "descripcion": "QUESO DE PRUEBA A PERDIDA",
         "estado": "activo", "stock": 10, "costo_iva": 200, "pvp": 100,
         "inmovilizado": 2000},
        {"codigo": 990002, "descripcion": "FIDEOS DE PRUEBA A PERDIDA",
         "estado": "activo", "stock": 4, "costo_iva": 500, "pvp": 480,
         "inmovilizado": 2000},
    ]
    store.guardar(raw)
    yield
    store.resetear_actual()


def test_detecta_precio_perdida_en_existentes():
    tipos = {a["tipo"] for a in anomalias.analizar_existentes()}
    assert "precio_perdida" in tipos


def test_ordenadas_por_impacto():
    impactos = [a["impacto_pesos"] for a in anomalias.analizar_existentes()]
    assert impactos == sorted(impactos, reverse=True)


def test_aplicar_precio_perdida_corrige():
    antes = [a for a in anomalias.analizar_existentes() if a["tipo"] == "precio_perdida"][0]["items"]
    assert antes > 0
    res = anomalias.aplicar("precio_perdida", "set_margen", {"margen": 30})
    assert res["corregidos"] == antes
    # tras corregir, ya no hay productos a pérdida
    tipos = {a["tipo"] for a in anomalias.analizar_existentes()}
    assert "precio_perdida" not in tipos


def test_aplicar_no_corregible_da_error():
    with pytest.raises(ValueError):
        anomalias.aplicar("duplicado", "ver", {})
