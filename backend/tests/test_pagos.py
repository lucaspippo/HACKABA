"""
P16: pagos y liquidez (core/pagos.py + /api/pagos).

El módulo lee finanzas.json del DATA_DIR del tenant. Sin archivo (piloto)
todo devuelve vacío honesto: la UI muestra su placeholder, jamás un cero
inventado. Con datos, los totales salen YA calculados por el core (regla B12).
"""
from __future__ import annotations

import datetime

import pytest

from core import pagos
from core.fechas import hoy
from tests.conftest import limpiar_tabla_tenant


@pytest.fixture(autouse=True)
def sin_residuos():
    """Aísla finance_data: cada test arranca sin fila para el tenant activo."""
    limpiar_tabla_tenant("finance_data")
    yield
    limpiar_tabla_tenant("finance_data")


def _d(n: int) -> str:
    return (hoy() + datetime.timedelta(days=n)).isoformat()


def _sembrar():
    from core.db import blob_repo
    from core.db import tenant as _tenant
    blob_repo.save_blob("finance_data", _tenant.current_tenant_id(), {
        "pagos_proveedores": [
            {"proveedor": "Alimentos del Paraná SA", "numero": "FC-A-00001",
             "emision": _d(-28), "vencimiento": _d(2), "monto": 5_000_000, "estado": "pendiente"},
            {"proveedor": "Lácteos Campo Alegre", "numero": "FC-A-00002",
             "emision": _d(-34), "vencimiento": _d(-4), "monto": 1_200_000, "estado": "pendiente"},
            {"proveedor": "Golosinas Costa Dulce SRL", "numero": "FC-A-00003",
             "emision": _d(-10), "vencimiento": _d(20), "monto": 3_000_000, "estado": "pendiente"},
        ],
        "tarjeta_cuotas": [
            {"venta_semana": _d(-7), "plan": "2 cuotas", "acredita": _d(5), "monto": 800_000},
            {"venta_semana": _d(-14), "plan": "3 cuotas", "acredita": _d(45), "monto": 300_000},
        ],
        "cheques": [
            {"cliente": "Supermercado El Puente", "numero": "31234567", "banco": "Banco Nación",
             "recibido": _d(-3), "cobro": _d(10), "monto": 4_000_000},
        ],
    })


def test_sin_archivo_todo_vacio_y_honesto():
    assert pagos.hay_datos() is False
    assert pagos.pagos_por_vencer() == []
    assert pagos.pagos_vencidos() == []
    assert pagos.tarjeta_por_acreditar() == []
    assert pagos.cheques_en_cartera() == []
    r = pagos.resumen()
    assert r["hay_datos"] is False and r["por_pagar_total"] == 0


def test_lecturas_con_datos():
    _sembrar()
    assert pagos.hay_datos() is True
    # vence en 2 días → por vencer; vencida hace 4 → vencidos
    assert [p["numero"] for p in pagos.pagos_por_vencer(7)] == ["FC-A-00001"]
    assert [p["numero"] for p in pagos.pagos_vencidos()] == ["FC-A-00002"]
    assert pagos.pagos_vencidos()[0]["dias_vencido"] == 4
    # la cuota a 45 días queda fuera de la ventana de 30
    assert [c["monto"] for c in pagos.tarjeta_por_acreditar(30)] == [800_000]
    ch = pagos.cheques_en_cartera()
    assert len(ch) == 1 and ch[0]["dias_para_cobro"] == 10


def test_resumen_totales_precalculados():
    _sembrar()
    r = pagos.resumen()
    assert r["por_pagar_total"] == 9_200_000     # las 3 pendientes
    assert r["por_pagar_semana"] == 5_000_000    # solo la que vence en 2 días
    assert r["pagos_vencidos"] == 1 and r["vencidos_total"] == 1_200_000
    assert r["tarjeta_7dias"] == 800_000
    assert r["cheques_cartera"] == 1 and r["cheques_total"] == 4_000_000


def test_endpoint_gateado_por_finanzas():
    from fastapi.testclient import TestClient
    import auth
    import main
    client = TestClient(main.app)
    creds = auth.cargar_o_generar_credenciales()
    # emilio (dueño) tiene finanzas; vendedor no → 403 (mismo patrón que test_authz)
    tok = client.post("/api/login", json={"username": "emilio", "password": creds["emilio"]}).json()["token"]
    r = client.get("/api/pagos", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert set(r.json()) == {"resumen", "pagos_por_vencer", "pagos_vencidos",
                             "tarjeta_por_acreditar", "cheques", "proyeccion"}
    tok2 = client.post("/api/login", json={"username": "vendedor", "password": creds["vendedor"]}).json()["token"]
    assert client.get("/api/pagos", headers={"Authorization": f"Bearer {tok2}"}).status_code == 403
