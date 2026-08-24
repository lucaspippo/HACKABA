"""
El "día del CSV": (a) los módulos dormidos despiertan con el apartado ventas,
(b) el validador de montos ataja una interpretación errada (factor 1000) ANTES
de mostrar números, (c) el dry-run no compromete nada y Evolución sigue viva.
"""
from __future__ import annotations

import datetime
import os

import pytest

from core import esquema, evolucion, staging, store, ventas

HOY = datetime.date.today()


def d(n):
    return (HOY + datetime.timedelta(days=n)).isoformat()


@pytest.fixture(autouse=True)
def limpio():
    files = [esquema.APARTADOS_JSON, staging.STAGING_JSON, ventas.VALIDACION_JSON]
    backup = {}
    for f in files:
        if os.path.exists(f):
            backup[f] = open(f, encoding="utf-8").read()
            os.remove(f)
    store.resetear_actual()
    yield
    for f in files:
        if os.path.exists(f):
            os.remove(f)
        if f in backup:
            open(f, "w", encoding="utf-8").write(backup[f])
    store.resetear_actual()


def _csv_ventas(factor=1.0):
    """Ventas sintéticas de 2 meses sobre productos REALES del catálogo, con
    precio unitario × factor (factor=1000 simula el total leído como precio)."""
    arts = [a for a in store.raw_actual()
            if (a.get("stock") or 0) > 10 and a.get("pvp") and "," not in a["descripcion"]][:3]
    assert len(arts) == 3
    filas = ["Fecha,Articulo,Cantidad,Precio"]
    for delta in (-70, -65, -40, -35, -10, -5):
        for a in arts:
            filas.append(f"{d(delta)},{a['codigo']},5,{round(a['pvp'] * factor, 2)}")
    return "\n".join(filas) + "\n", arts


def _integrar(csv_texto):
    b = staging.crear_batch("ventas_faro.csv", csv_texto)
    for o in b["observaciones"]:
        staging.resolver(b["id"], o["id"], "confirmar", {})
    return staging.integrar(b["id"])


# --- (a) el cableado: los módulos despiertan tras validar ---

def test_sin_ventas_todo_duerme_con_motivo():
    p = ventas.panorama()
    assert p["disponible"] is False and "ventas históricas" in p["motivo"]


def test_integrar_ventas_dispara_el_validador_y_bloquea_hasta_confirmar():
    csv_txt, _ = _csv_ventas()
    r = _integrar(csv_txt)
    assert "ANTES de mostrarte números" in r["mensaje"]      # la pregunta viaja al dueño
    v = ventas.validacion()
    assert v["estado"] == "pendiente" and v["total_calculado"] > 0

    p = ventas.panorama()
    assert p["disponible"] is False                          # nada de números sin confirmar
    assert "validador" in p["motivo"] or "confirme" in p["motivo"]


def test_confirmado_despierta_rotacion_margen_quiebre():
    csv_txt, arts = _csv_ventas()
    _integrar(csv_txt)
    ventas.confirmar_validacion(confirmar=True)

    p = ventas.panorama()
    assert p["disponible"] is True
    assert p["rotacion"]["disponible"] is True               # la fórmula dormida, despierta
    assert p["rotacion"]["plata_excedente"] >= 0
    assert p["margen_real"]["facturado"] > 0
    assert "quiebre" in p and isinstance(p["quiebre"]["cantidad"], int)


def test_esperado_dentro_del_20pct_confirma_solo():
    csv_txt, _ = _csv_ventas()
    _integrar(csv_txt)
    total = ventas.validacion()["total_calculado"]
    v = ventas.confirmar_validacion(esperado=total * 1.1)    # 10% de diferencia: ok
    assert v["estado"] == "confirmado"


# --- (b) el validador ataja la interpretación errada (el error de factor 1000) ---

def test_factor_1000_queda_marcado_como_sospechoso_y_bloqueado():
    csv_txt, _ = _csv_ventas(factor=1000)                    # "total" leído como precio
    _integrar(csv_txt)
    total_inflado = ventas.validacion()["total_calculado"]
    esperado_real = total_inflado / 1000                     # lo que el dueño sabe que facturó

    v = ventas.confirmar_validacion(esperado=esperado_real)
    assert v["estado"] == "sospechoso"
    assert v["diferencia_pct"] > 20
    assert "TOTAL" in v["motivo"] or "inflados" in v["motivo"]  # la pista del factor

    p = ventas.panorama()
    assert p["disponible"] is False                          # números disparatados: NO se muestran
    assert "mal interpretados" in p["motivo"]


def test_montos_en_miniatura_tambien_da_pista():
    csv_txt, _ = _csv_ventas()
    _integrar(csv_txt)
    total = ventas.validacion()["total_calculado"]
    v = ventas.confirmar_validacion(esperado=total * 1000)   # esperaba MIL veces más
    assert v["estado"] == "sospechoso" and "miniatura" in v["motivo"]


# --- (c) dry-run sin compromiso + Evolución sigue viva ---

def test_dry_run_no_persiste_nada():
    csv_txt, _ = _csv_ventas()
    r = ventas.dry_run(csv_txt)
    assert r["tipo_detectado"] == "venta" and r["filas"] == 18
    assert r["total_mes_muestra"] > 0
    assert "rotación y excedente liberable" in r["activaria"]
    # nada quedó guardado
    assert not esquema.existe("venta")
    assert staging.listar() == []
    assert ventas.validacion()["estado"] == "sin_datos"


def test_evolucion_sigue_funcionando_con_el_mismo_apartado():
    csv_txt, _ = _csv_ventas()
    _integrar(csv_txt)
    p = evolucion.panorama()
    assert p["hay_datos"] is True and len(p["serie"]) >= 2   # mismo disparador, sin romperse
