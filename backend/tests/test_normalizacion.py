"""
Los dos niveles de limpieza. La frontera vive en core/normalizacion.py:
Nivel 1 = mecánico, automático, registrado y reversible. Nivel 2 = verdad
comercial, SIEMPRE con el dueño. Ante la duda → Nivel 2 (con test).
"""
from __future__ import annotations

import os

import pytest

from core import normalizacion as nz
from core import staging, store


@pytest.fixture(autouse=True)
def limpio():
    if os.path.exists(staging.STAGING_JSON):
        os.remove(staging.STAGING_JSON)
    store.resetear_actual()
    yield
    if os.path.exists(staging.STAGING_JSON):
        os.remove(staging.STAGING_JSON)
    store.resetear_actual()


# --- Nivel 1: cada transformación, con su caso a mano ---

def test_numeros_inequivocos():
    assert nz.normalizar_numero("1.234,50") == (1234.5, "separadores_es_ar")
    assert nz.normalizar_numero("$ 1.234,50")[0] == 1234.5
    assert nz.normalizar_numero("12,5") == (12.5, "coma_decimal")
    assert nz.normalizar_numero("1.234.567") == (1234567.0, "puntos_miles")
    assert nz.normalizar_numero("12.5")[0] == 12.5          # 1-2 decimales: decimal
    assert nz.normalizar_numero(1234)[0] == 1234.0          # ya numérico: tal cual
    assert nz.normalizar_numero("abc") == (None, None)      # no es un número
    assert nz.normalizar_numero("") == (None, None)


def test_numero_ambiguo_va_al_nivel_2():
    # LA regla de oro: "1.234" no se interpreta solo, jamás.
    valor, regla = nz.normalizar_numero("1.234")
    assert valor is nz.AMBIGUO and regla == "punto_tres_digitos"
    # y el parseo del staging NO inventa un valor (antes hacía float("1.234")=1.234)
    assert staging._num("1.234") is None
    assert staging._num("1.234,50") == 1234.5  # el inequívoco sí


def test_texto():
    assert nz.normalizar_texto("  MANTECA   PILON  ") == ("MANTECA PILON", ["espacios"])
    assert nz.normalizar_texto("MANTECA pilon")[0] == "MANTECA PILON"  # inconsistencia: se corrige
    assert nz.normalizar_texto("MuÃ±eca")[0] == "Muñeca"     # encoding sí; el case se respeta
    # Title Case / minúsculas NO se tocan: cambiarlos es estilo, no mecánica
    assert nz.normalizar_texto("Autoservicio García")[0] == "Autoservicio García"
    assert nz.normalizar_texto("queso cremoso")[0] == "queso cremoso"
    assert nz.normalizar_texto("YA LIMPIO") == ("YA LIMPIO", [])  # sin cambios, sin registro


def test_fecha():
    assert nz.normalizar_fecha("13/06/2026") == ("2026-06-13", "fecha_iso")
    assert nz.normalizar_fecha("2026-06-13")[1] is None  # ya ISO: no toca
    assert nz.normalizar_fecha("no es fecha")[1] is None


def test_normalizar_tabla_registra_todo_con_original():
    headers = ["Producto", "Precio", "Fecha"]
    filas = [["  QUESO   crema ", "$ 1.234,50", "13/06/2026"],
             ["MANTECA", "1.234", "2026-06-13"]]
    limpias, reg = nz.normalizar_tabla(headers, filas)
    assert limpias[0] == ["QUESO CREMA", "1234.5", "2026-06-13"]
    # todo cambio lleva el valor original (reversible)
    assert all("original" in c and "normalizado" in c for c in reg["cambios"])
    assert reg["total_cambios"] == 3 and reg["filas_afectadas"] == 1
    # el ambiguo NO se tocó: sigue como vino y está listado aparte
    assert limpias[1][1] == "1.234"
    assert reg["ambiguos"] == [{"fila": 1, "columna": "Precio", "valor": "1.234"}]
    assert "podés revertir" in nz.resumen_en_criollo(reg)


# --- Staging: nivel 1 al entrar, nivel 2 intacto ---

CSV_SUCIO = (
    "Codigo,Producto,Stock,Costo,Precio\n"
    "9001,  QUESO   nuevo  SUCIO ,10,\"$ 1.100,00\",\"1.650,50\"\n"   # texto + números es-AR
    "9002,GALLETA AMBIGUA,5,200,\"1.234\"\n"                          # precio AMBIGUO
    "9003,PRODUCTO A PERDIDA,4,900,500\n"                             # nivel 2 comercial
)


def test_staging_nivel1_registra_y_es_visible():
    r = staging.crear_batch("sucio.csv", CSV_SUCIO)
    n = r["normalizaciones"]
    assert n and n["total_cambios"] >= 3   # espacios+mayúsculas, costo, precio
    assert "Normalicé sola" in n["resumen"]
    # quedó en el AuditLog con actor sistema
    ev = [e for e in store.audit.list() if e["accion"] == "normalizacion_nivel1"]
    assert ev and ev[-1]["actor"] == "sistema"
    # y el valor quedó BIEN puesto en la fila (mismo significado, prolijo)
    b = staging._find(staging._load(), r["id"])
    assert b["filas"][0]["descripcion"] == "QUESO NUEVO SUCIO"  # mayoría mayúscula: se unifica
    assert b["filas"][0]["pvp"] == 1650.5 and b["filas"][0]["costo_iva"] == 1100.0


def test_staging_ambiguo_cae_al_nivel_2_y_no_inventa():
    r = staging.crear_batch("sucio.csv", CSV_SUCIO)
    tipos = {o["tipo"] for o in r["observaciones"]}
    assert "numero_ambiguo" in tipos
    b = staging._find(staging._load(), r["id"])
    assert b["filas"][1]["pvp"] is None    # sin valor: NO 1.234 inventado
    # y no se duplica como "sin precio" (tiene precio, espera interpretación)
    obs_sp = next((o for o in r["observaciones"] if o["tipo"] == "sin_precio"), None)
    assert obs_sp is None or 1 not in obs_sp["indices"]


def test_resolver_ambiguo_como_miles_y_como_decimal():
    r = staging.crear_batch("sucio.csv", CSV_SUCIO)
    staging.resolver(r["id"], "numero_ambiguo", "interpretar_miles", {})
    b = staging._find(staging._load(), r["id"])
    assert b["filas"][1]["pvp"] == 1234.0  # la decisión del dueño, explícita

    staging.descartar(r["id"])
    r = staging.crear_batch("sucio2.csv", CSV_SUCIO)
    staging.resolver(r["id"], "numero_ambiguo", "interpretar_decimal", {})
    b = staging._find(staging._load(), r["id"])
    assert b["filas"][1]["pvp"] == 1.234


def test_revertir_normalizacion_vuelve_al_crudo():
    r = staging.crear_batch("sucio.csv", CSV_SUCIO)
    r2 = staging.revertir_normalizacion(r["id"])
    assert r2["normalizaciones"] is None
    b = staging._find(staging._load(), r["id"])
    # el texto volvió a como vino (sin prolijar)
    assert b["filas"][0]["descripcion"] == "QUESO   nuevo  SUCIO"
    assert b["crudo"] is None
    ev = [e for e in store.audit.list() if e["accion"] == "revertir_normalizacion_nivel1"]
    assert ev


def test_nivel_2_comercial_intacto_nada_se_aplica_solo():
    r = staging.crear_batch("sucio.csv", CSV_SUCIO)
    # el precio a pérdida sigue siendo card que espera al dueño
    perdida = next(o for o in r["observaciones"] if o["tipo"] == "precio_perdida")
    assert perdida["resuelta"] is False
    b = staging._find(staging._load(), r["id"])
    # el valor comercial NO fue alterado por el nivel 1: sigue 500 < 900
    assert b["filas"][2]["pvp"] == 500.0 and b["filas"][2]["costo_iva"] == 900.0


def test_csv_limpio_no_genera_ruido():
    limpio_csv = "Codigo,Producto,Stock,Costo,Precio\n9010,PRODUCTO LIMPIO,10,100,150\n"
    r = staging.crear_batch("limpio.csv", limpio_csv)
    assert r["normalizaciones"] is None  # nada que informar, nada guardado de más


# --- Ángela (router): consultar y revertir con ok ---

def test_angela_consulta_y_revierte_con_confirmacion():
    import angela
    angela._set_sesion(features=None)
    staging.crear_batch("sucio.csv", CSV_SUCIO)
    r = angela._fallback("¿qué normalizaste del archivo?")
    assert "Normalicé sola" in r["respuesta"]

    r = angela._fallback("revertí la normalización")
    assert r["opciones"]  # propone, no aplica
    b = staging.listar()[-1]
    assert b["normalizaciones"] is not None  # sigue intacta

    r = angela._fallback("confirmá: revertí la normalización")
    assert "deshice" in r["respuesta"]
    assert staging.listar()[-1]["normalizaciones"] is None
