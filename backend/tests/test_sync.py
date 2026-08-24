import csv
import io

import pytest

from core import sync, conectores, saneamiento, store


@pytest.fixture(autouse=True)
def limpio():
    store.resetear_actual()
    yield
    store.resetear_actual()


def test_sin_cambios_no_hay_delta():
    assert sync.deltas() == []
    exp = sync.generar_delta_export("generico")
    assert exp["registros"] == 0


def test_delta_solo_los_corregidos():
    # Corrijo las balanzas → solo esas deben aparecer en el delta.
    saneamiento.aplicar("balanza")
    ds = sync.deltas()
    assert len(ds) > 0
    total_articulos = len(store.raw_actual())
    assert len(ds) < total_articulos  # NUNCA toda la base
    # cada delta trae el código (ID) y los campos que cambiaron
    assert all("codigo" in d and d["cambios"] for d in ds)


def test_export_csv_tiene_id_y_solo_cambios():
    saneamiento.aplicar("balanza")
    exp = sync.generar_delta_export("faro")
    filas = list(csv.reader(io.StringIO(exp["csv"])))
    assert filas[0][0] == "CODIGO"  # ID primero, para UPDATE
    assert len(filas) - 1 == exp["registros"]


def test_idempotencia_mismo_delta_dos_veces():
    saneamiento.aplicar("balanza")
    a = sync.generar_delta_export("generico")["csv"]
    b = sync.generar_delta_export("generico")["csv"]
    assert a == b  # determinístico


def test_conflict_resolution_por_campo():
    assert sync.quien_gana("pvp") == "polpilot"     # precios → nosotros
    assert sync.quien_gana("stock") == "faro"      # stock vivo → Faro
    assert sync.quien_gana("cuit") == "faro"       # fiscal → Faro


def test_conectores_mcp_es_slot_vacio():
    nombres = {c["nombre"]: c for c in conectores.disponibles()}
    assert nombres["csv"]["estado"] == "activo"
    assert nombres["mcp"]["estado"] == "pendiente"
    with pytest.raises(NotImplementedError):
        conectores.ConectorMCP().pull_data()
