from fastapi.testclient import TestClient

import auth
import main

client = TestClient(main.app)


def _token():
    creds = auth.cargar_o_generar_credenciales()
    return client.post("/api/login", json={"username": "emilio", "password": creds["emilio"]}).json()["token"]


def _h():
    return {"Authorization": f"Bearer {_token()}"}


def test_sales_endpoint_crud_and_pagination():
    h = _h()
    created = client.post("/api/sales", headers=h, json={
        "fecha": "2026-07-01", "producto": "Harina API", "cantidad": 2, "precio": 10,
    })
    assert created.status_code == 200
    sid = created.json()["id"]

    listed = client.get("/api/sales?q=harina+api&limit=20", headers=h)
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] >= 1
    assert body["items"][0]["id"] == sid
    assert "has_more" in body

    csv = client.get("/api/sales/export.csv?q=harina+api", headers=h)
    assert csv.status_code == 200
    assert "text/csv" in csv.headers["content-type"]
    assert b"Harina API" in csv.content

    deleted = client.post(f"/api/sales/{sid}/eliminar", headers=h, json={})
    assert deleted.status_code == 200
    assert client.get("/api/sales?q=harina+api", headers=h).json()["total"] == 0


def test_receipts_endpoint_create_and_list():
    h = _h()
    created = client.post("/api/receipts", headers=h, json={
        "fecha": "2026-07-02", "producto": "Aceite API", "proveedor": "Molinos",
        "cantidad": 5, "deposito": "WH",
    })
    assert created.status_code == 200
    rid = created.json()["id"]
    listed = client.get("/api/receipts?q=aceite+api", headers=h)
    assert listed.json()["total"] >= 1
    client.post(f"/api/receipts/{rid}/eliminar", headers=h, json={})


def test_productos_endpoint_paginates_and_deletes():
    h = _h()
    created = client.post("/api/articulos", headers=h, json={
        "codigo": 9201, "descripcion": "Producto API", "stock": 1, "costo_iva": 5,
    })
    assert created.status_code == 200
    page = client.get("/api/productos?q=producto+api&limit=10", headers=h)
    assert page.status_code == 200
    assert page.json()["total"] == 1
    gone = client.post("/api/articulos/9201/eliminar", headers=h, json={})
    assert gone.status_code == 200
    assert client.get("/api/productos?q=producto+api", headers=h).json()["total"] == 0


def test_movimientos_endpoint_lists_lots():
    h = _h()
    created = client.post("/api/lotes", headers=h, json={
        "producto": "Harina mov", "ubicacion": "Rack Z", "cantidad": 4,
    })
    assert created.status_code == 200
    lid = created.json()["id"]
    page = client.get("/api/movimientos?q=rack+z", headers=h)
    assert page.status_code == 200
    assert page.json()["total"] >= 1
    csv = client.get("/api/movimientos/export.csv?q=rack+z", headers=h)
    assert csv.status_code == 200
    assert b"Harina mov" in csv.content
    client.post(f"/api/lotes/{lid}/eliminar", headers=h, json={})


def test_movimientos_endpoint_filters_discrepancies():
    h = _h()
    gap = client.post("/api/lotes", headers=h, json={
        "producto": "Harina disc", "ubicacion": "Rack D", "cantidad": 50,
        "counted_qty": 40,
    })
    assert gap.status_code == 200
    lid = gap.json()["id"]
    page = client.get("/api/movimientos?discrepancia=1&q=harina+disc", headers=h)
    assert page.status_code == 200
    assert page.json()["total"] == 1
    assert page.json()["items"][0]["diferencia"] == -10
    client.post(f"/api/lotes/{lid}/eliminar", headers=h, json={})


def test_conciliacion_endpoint_lists_and_accepts():
    h = _h()
    created = client.post("/api/articulos", headers=h, json={
        "codigo": 9301, "descripcion": "Harina conc API", "stock": 50,
        "costo_iva": 10, "pvp": 20,
    })
    assert created.status_code == 200
    lot = client.post("/api/lotes", headers=h, json={
        "codigo": 9301, "producto": "Harina conc API", "ubicacion": "Rack C",
        "cantidad": 50, "counted_qty": 40,
    })
    assert lot.status_code == 200
    lid = lot.json()["id"]

    listed = client.get("/api/conciliacion", headers=h)
    assert listed.status_code == 200
    body = listed.json()
    ids = {d["id"] for d in body["diferencias"]}
    assert lid in ids
    item = next(d for d in body["diferencias"] if d["id"] == lid)
    assert item["diferencia"] == -10
    assert item["hipotesis"]["clase"]

    accepted = client.post(f"/api/conciliacion/{lid}/aceptar", headers=h, json={})
    assert accepted.status_code == 200
    assert accepted.json()["cantidad"] == 40

    after = client.get("/api/conciliacion", headers=h).json()
    assert lid not in {d["id"] for d in after["diferencias"]}

    client.post(f"/api/lotes/{lid}/eliminar", headers=h, json={})
    client.post("/api/articulos/9301/eliminar", headers=h, json={})
