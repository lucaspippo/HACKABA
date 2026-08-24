import os

import pytest

from core import cuentas, caja


@pytest.fixture(autouse=True)
def limpio():
    for f in (cuentas.CUENTAS_JSON, caja.CAJA_JSON):
        if os.path.exists(f):
            os.remove(f)
    yield
    for f in (cuentas.CUENTAS_JSON, caja.CAJA_JSON):
        if os.path.exists(f):
            os.remove(f)


# --- Plan 6: cuentas corrientes ---

def test_deudores_ordenados_por_monto():
    l = cuentas.listar()
    assert l[0]["nombre"] == "Almacén Don Pérez"
    assert l[0]["saldo"] == 30_000_000
    saldos = [c["saldo"] for c in l]
    assert saldos == sorted(saldos, reverse=True)


def test_morosos_y_score():
    perez = cuentas.get("perez")
    assert perez["en_mora"] is True  # 45 > 30
    assert cuentas.get("laesquina")["en_mora"] is False  # 12 < 30
    assert cuentas.get("elcerdito")["score"] == "riesgoso"  # 60 > 15*1.5


def test_scoring_venta():
    s = cuentas.scoring_venta("La Esquina")
    assert s["conocido"] is True and s["autoriza"] is True
    assert cuentas.scoring_venta("Cliente Nuevo XYZ")["conocido"] is False


def test_scoring_supera_limite_pide_autorizacion():
    s = cuentas.scoring_venta("El Cerdito", monto=5_000_000)
    assert s["autoriza"] is False


def test_mensaje_cobro_y_alertas():
    mc = cuentas.mensaje_cobro("perez")
    assert "Horizonte" in mc["mensaje"]
    a = cuentas.alertas()
    assert a["cantidad"] == len(cuentas.morosos()) and a["impacto_pesos"] > 0


# --- Plan 7: caja ---

def test_caja_totales():
    e = caja.estado()
    assert e["totales"]["total"] == 50_000 + 145_000 + 92_000 + 68_000 - 40_000


def test_caja_cierre_con_diferencia_alerta():
    r = caja.cerrar(declarado=300_000)  # total real 315.000 → diferencia -15.000
    assert r["diferencia"] == -15_000
    assert r["nota_angela"] is not None


def test_caja_cierre_sin_declarar():
    r = caja.cerrar()
    assert r["diferencia"] == 0
    assert r["total"] == 315_000
