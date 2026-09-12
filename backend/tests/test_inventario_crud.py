import pytest

from core import ubicaciones, proveedores, lotes, store, ordenes


@pytest.fixture(autouse=True)
def _tenant_ctx(db_tenant, monkeypatch):
    monkeypatch.setattr("core.db.tenant.current_tenant_id", lambda: db_tenant)
    yield db_tenant


def test_ubicaciones_crud():
    creada = ubicaciones.crear("Depósito Central", "emilio")
    assert creada["nombre"] == "Depósito Central"
    assert ubicaciones.listar() == [creada]

    with pytest.raises(ValueError):
        ubicaciones.crear("depósito central", "emilio")  # duplicado (case-insensitive)

    editada = ubicaciones.actualizar(creada["id"], {"nombre": "Depósito Norte"}, "emilio")
    assert editada["nombre"] == "Depósito Norte"

    ubicaciones.eliminar(creada["id"], "emilio")
    assert ubicaciones.listar() == []

    with pytest.raises(KeyError):
        ubicaciones.eliminar(creada["id"], "emilio")


def test_proveedores_crud():
    creado = proveedores.crear({"nombre": "Molinos SA", "telefono": "11-1234"}, "emilio")
    assert creado["telefono"] == "11-1234"
    assert proveedores.listar() == [creado]

    editado = proveedores.actualizar(creado["id"], {"email": "ventas@molinos.com"}, "emilio")
    assert editado["email"] == "ventas@molinos.com"
    assert editado["nombre"] == "Molinos SA"  # campos no tocados sobreviven

    proveedores.eliminar(creado["id"], "emilio")
    assert proveedores.listar() == []


def test_lotes_crud():
    creado = lotes.crear(
        {"codigo": 1, "producto": "Harina", "ubicacion": "Rack A", "lote": "L-001",
         "vencimiento": "2026-12-01", "cantidad": 50},
        "emilio",
    )
    assert creado["ubicacion"] == "Rack A"
    assert lotes.listar() == [creado]

    editado = lotes.actualizar(creado["id"], {"cantidad": 40}, "emilio")
    assert editado["cantidad"] == 40

    lotes.eliminar(creado["id"], "emilio")
    assert lotes.listar() == []


def test_lotes_requiere_producto_y_ubicacion():
    with pytest.raises(ValueError):
        lotes.crear({"ubicacion": "Rack A"}, "emilio")
    with pytest.raises(ValueError):
        lotes.crear({"producto": "Harina"}, "emilio")


@pytest.fixture(autouse=True)
def _store_cache_aislado():
    """store._cache_raw es un lru_cache GLOBAL (no por tenant): sin esto, un
    test que escribe bajo un tenant de prueba puede filtrar esos datos al
    resto de la suite, que corre bajo el tenant por defecto."""
    store._cache_raw.cache_clear()
    yield
    store._cache_raw.cache_clear()


def test_articulo_crear_recalcula_inmovilizado():
    creado = store.crear_articulo(
        {"codigo": 9001, "descripcion": "Tornillo M8", "stock": 100, "costo_iva": 12.5},
        "emilio",
    )
    assert creado["inmovilizado"] == 1250.0

    with pytest.raises(ValueError):
        store.crear_articulo({"codigo": 9001, "descripcion": "Duplicado"}, "emilio")


def test_articulo_actualizar_recalcula_inmovilizado():
    store.crear_articulo({"codigo": 9002, "descripcion": "Tuerca", "stock": 10, "costo_iva": 2}, "emilio")
    editado = store.actualizar_articulo(9002, {"stock": 20}, "emilio")
    assert editado["inmovilizado"] == 40.0

    with pytest.raises(KeyError):
        store.actualizar_articulo(424242, {"stock": 1}, "emilio")


def test_orden_compra_manual():
    orden = ordenes.crear_manual(
        proveedor="Molinos SA", ubicacion="Depósito Central", fecha="2026-08-26",
        items=[{"codigo": 1, "producto": "Harina", "cantidad": 50}], actor="emilio",
    )
    assert orden["origen"] == "manual"
    assert orden["estado"] == "borrador"
    listado = ordenes.listar()
    assert any(o["numero"] == orden["numero"] for o in listado)

    aprobada = ordenes.actualizar_estado(orden["numero"], "aprobada", "emilio")
    assert aprobada["estado"] == "aprobada"

    with pytest.raises(ValueError):
        ordenes.actualizar_estado(orden["numero"], "estado_invalido", "emilio")
    with pytest.raises(KeyError):
        ordenes.actualizar_estado("OC-9999-9999", "aprobada", "emilio")


def test_orden_compra_manual_requiere_proveedor_e_items():
    with pytest.raises(ValueError):
        ordenes.crear_manual(proveedor="", ubicacion="", fecha="", items=[{"codigo": 1}], actor="emilio")
    with pytest.raises(ValueError):
        ordenes.crear_manual(proveedor="Molinos SA", ubicacion="", fecha="", items=[], actor="emilio")
