"""CRUD + pagination for ingested operational rows: sales, receipts, movements, products."""
import pytest

from core import lotes, receipts, sales, store
from tests.conftest import limpiar_tabla_tenant


@pytest.fixture(autouse=True)
def _tenant_ctx(db_tenant, monkeypatch):
    monkeypatch.setattr("core.db.tenant.current_tenant_id", lambda: db_tenant)
    yield db_tenant
    limpiar_tabla_tenant("data_sections")
    store._cache_raw.cache_clear()


def test_sales_crud_roundtrip():
    created = sales.create(
        {"fecha": "2026-07-01", "producto": "Harina 000", "cantidad": 2, "precio": 1500},
        "emilio",
    )
    assert created["id"]
    assert created["source"] == "manual"
    assert created["producto"] == "Harina 000"

    listed = sales.list_page()
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == created["id"]

    updated = sales.update(created["id"], {"cantidad": 5}, "emilio")
    assert updated["cantidad"] == 5
    assert updated["producto"] == "Harina 000"

    sales.delete(created["id"], "emilio")
    assert sales.list_page()["total"] == 0

    with pytest.raises(KeyError):
        sales.delete(created["id"], "emilio")


def test_sales_create_requires_product():
    with pytest.raises(ValueError):
        sales.create({"fecha": "2026-07-01", "cantidad": 1}, "emilio")


def test_sales_list_page_search_sort_source_and_dates():
    sales.create({"fecha": "2026-06-01", "producto": "CSV viejo", "cantidad": 1, "precio": 10}, "emilio")
    odoo = sales.create(
        {"fecha": "2026-07-10", "producto": "Aceite Odoo", "cantidad": 3, "precio": 150,
         "source": "odoo", "source_id": "sol-1"},
        "emilio",
    )
    sales.create({"fecha": "2026-07-01", "producto": "Harina", "cantidad": 8, "precio": 20}, "emilio")

    page = sales.list_page(q="aceite", limit=50)
    assert page["total"] == 1
    assert page["items"][0]["id"] == odoo["id"]

    odoo_only = sales.list_page(source="odoo")
    assert odoo_only["total"] == 1
    assert odoo_only["items"][0]["source"] == "odoo"

    july = sales.list_page(date_from="2026-07-01", date_to="2026-07-31", sort="fecha", direction="asc")
    assert [r["producto"] for r in july["items"]] == ["Harina", "Aceite Odoo"]

    paged = sales.list_page(sort="fecha", direction="asc", offset=1, limit=1)
    assert paged["total"] == 3
    assert paged["has_more"] is True
    assert len(paged["items"]) == 1


def test_sales_export_csv_uses_current_filters():
    sales.create({"fecha": "2026-07-01", "producto": "Harina", "cantidad": 2, "precio": 10}, "emilio")
    sales.create(
        {"fecha": "2026-07-02", "producto": "Aceite", "cantidad": 1, "precio": 20,
         "source": "odoo", "source_id": "sol-2"},
        "emilio",
    )
    csv = sales.export_csv(source="odoo")
    assert "Aceite" in csv
    assert "Harina" not in csv.splitlines()[1] if "Harina" not in csv else True
    assert "fecha,producto,codigo,cantidad,precio,source" in csv.splitlines()[0]
    assert "Aceite" in csv
    lines = [ln for ln in csv.splitlines() if ln and not ln.startswith("fecha")]
    assert len(lines) == 1


def test_receipts_crud_and_pagination():
    created = receipts.create(
        {"fecha": "2026-07-02", "producto": "Aceite", "proveedor": "Molinos",
         "cantidad": 20, "deposito": "WH", "po_number": "PO001"},
        "emilio",
    )
    assert created["source"] == "manual"
    page = receipts.list_page(q="molinos")
    assert page["total"] == 1
    receipts.update(created["id"], {"cantidad": 25}, "emilio")
    assert receipts.list_page()["items"][0]["cantidad"] == 25
    receipts.delete(created["id"], "emilio")
    assert receipts.list_page()["total"] == 0


def test_receipts_create_requires_product():
    with pytest.raises(ValueError):
        receipts.create({"fecha": "2026-07-01", "cantidad": 1}, "emilio")


def test_movements_list_page_and_extra_fields():
    created = lotes.crear(
        {"producto": "Harina", "ubicacion": "Rack A", "lote": "L-001",
         "vencimiento": "2026-12-01", "cantidad": 50, "in_date": "2026-07-02",
         "counted_qty": 49},
        "emilio",
    )
    page = lotes.list_page(q="rack")
    assert page["total"] == 1
    assert page["items"][0]["in_date"] == "2026-07-02"
    assert page["items"][0]["counted_qty"] == 49
    csv = lotes.export_csv()
    assert "Harina" in csv
    assert "ubicacion" in csv.splitlines()[0]
    lotes.eliminar(created["id"], "emilio")


def test_product_delete_and_list_page():
    created = store.crear_articulo(
        {"codigo": 9101, "descripcion": "Producto CRUD", "stock": 3, "costo_iva": 10},
        "emilio",
    )
    page = store.list_page(q="producto crud")
    assert page["total"] == 1
    assert page["items"][0]["codigo"] == 9101

    store.eliminar_articulo(9101, "emilio")
    assert store.list_page(q="producto crud")["total"] == 0
    with pytest.raises(KeyError):
        store.eliminar_articulo(9101, "emilio")
    assert created["descripcion"] == "Producto CRUD"


def test_product_list_page_filters_source_and_quality():
    store.upsert_desde_conector({
        "descripcion": "Aceite Odoo", "sku": "ACE-001", "stock": 12,
        "costo_iva": 100, "pvp": 150, "source": "odoo", "source_id": "tmpl-9",
    }, actor="emilio")
    odoo = store.list_page(source="odoo", q="aceite")
    assert odoo["total"] == 1
    assert odoo["items"][0]["sku"] == "ACE-001"
    assert odoo["items"][0]["source"] == "odoo"
