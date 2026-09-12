from core import imported, esquema, store
from tests.conftest import limpiar_tabla_tenant


def setup_function():
    limpiar_tabla_tenant("data_sections")
    store.resetear_actual()


def teardown_function():
    limpiar_tabla_tenant("data_sections")
    store.resetear_actual()


def test_overview_includes_catalog_even_without_sections():
    result = imported.overview()
    assert result["summary"]["products"] > 0
    assert result["summary"]["sales"] == 0
    assert result["summary"]["receipts"] == 0
    assert result["summary"]["movements"] == 0
    assert result["sales"] == []
    product = result["products"][0]
    assert "description" in product
    assert "_key" in product


def test_overview_projects_odoo_provenance():
    store.upsert_desde_conector({
        "descripcion": "Aceite Odoo",
        "sku": "ACE-001",
        "stock": 12,
        "costo_iva": 100,
        "pvp": 150,
        "free_qty": 10,
        "incoming_qty": 2,
        "outgoing_qty": 0,
        "source": "odoo",
        "source_id": "tmpl-9",
    }, actor="emilio")
    esquema.reemplazar_filas("venta", [
        {"fecha": "2026-07-01", "producto": "Aceite Odoo", "codigo": 1,
         "cantidad": 3, "precio": 150, "source": "odoo", "source_id": "sol-1"},
        {"fecha": "2026-06-01", "producto": "CSV viejo", "codigo": 2,
         "cantidad": 1, "precio": 10},
    ])
    esquema.reemplazar_filas("recepciones", [
        {"fecha": "2026-07-02", "producto": "Aceite Odoo", "codigo": 1,
         "proveedor": "Molinos", "cantidad": 20, "deposito": "WH",
         "origen": "WH/IN", "po_number": "PO001",
         "source": "odoo", "source_id": "sm-1"},
    ])
    esquema.reemplazar_filas("deposito", [
        {"producto": "Aceite Odoo", "codigo": 1, "ubicacion": "Stock",
         "lote": "L1", "vencimiento": "2027-01-01", "cantidad": 12,
         "in_date": "2026-07-02", "counted_qty": 11,
         "source": "odoo", "source_id": "q-1"},
    ])

    result = imported.overview()
    assert result["summary"]["sales"] == 2
    assert result["summary"]["receipts"] == 1
    assert result["summary"]["movements"] == 1
    assert result["summary"]["odoo"]["sales"] == 1
    assert result["summary"]["odoo"]["receipts"] == 1
    assert result["summary"]["odoo"]["movements"] == 1
    assert result["summary"]["odoo"]["products"] >= 1
    assert result["sales"][0]["date"] == "2026-07-01"
    oil = next(p for p in result["products"] if p.get("source_id") == "tmpl-9")
    assert oil["sku"] == "ACE-001"
    assert oil["description"] == "Aceite Odoo"
    assert oil["free_qty"] == 10
    assert result["movements"][0]["counted_qty"] == 11
    assert result["receipts"][0]["po_number"] == "PO001"
    assert result["receipts"][0]["vendor"] == "Molinos"
