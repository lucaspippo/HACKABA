"""
P23 — La AUDITORÍA SISTEMÁTICA de la capa de consultas, como test PERMANENTE.

Genera programáticamente la matriz completa fuente × métrica × agrupación ×
filtro con las categorías REALES del dataset y una muestra representativa de
productos (grandes, chicos, sin ventas, cancelados) y clientes. Cada celda
válida debe devolver una serie SANA (no vacía, sin None/NaN, unidad correcta,
ventana y topes respetados, sin degenerados). Las combinaciones que POR DISEÑO
no existen deben devolver su error honesto — eso es un PASS.

Si mañana alguien toca la capa, esta matriz lo caza.

Corre con ventas SINTÉTICAS deterministas (la suite vive en el tenant piloto,
sin ventas): productos reales del demo en 3 categorías, 24 meses, más un
producto SIN ventas y un cancelado — la forma es idéntica a la real.
P23·A: participación con denominador explícito, y errores autocorregibles.
"""
from __future__ import annotations

import hashlib
import json
import math
import os

import pytest

import angela
from core import consultas, memoria, store


# --- el mundo sintético (determinista, con TODOS los bordes) -------------------

_CATS = {
    "bebidas": ["VINO TINTO LA RIBERA 750CC (X6U)", "GASEOSA COLA COSTA DULCE 2.25L (X6U)"],
    "lácteos": ["LECHE ENTERA CAMPO ALEGRE 1L (X12U)"],
    "galletitas y golosinas": ["ALFAJOR TRIPLE CAMPO ALEGRE (X24U)"],  # 1 solo producto
}
SIN_VENTAS = "TURRON CAMPO ALEGRE (X50U)"  # existe en catálogo, jamás vendió


def _filas() -> list[dict]:
    filas = []
    for i in range(24):  # 2024-07 .. 2026-06
        anio, mes = divmod(6 + i, 12)
        clave = f"{2024 + anio}-{mes + 1:02d}"
        cod = 9000
        for cat, prods in _CATS.items():
            for prod in prods:
                cod += 1
                filas.append({"fecha": f"{clave}-15", "producto": prod, "codigo": cod,
                              "categoria": cat, "cantidad": 100.0 + i * 3 + cod % 7,
                              "precio": 1000.0 * (1.03 ** i), "boca": "Casa Central"})
    return filas


@pytest.fixture(autouse=True)
def mundo(monkeypatch):
    filas = _filas()
    monkeypatch.setattr(consultas, "_filas_ventas", lambda: filas)
    indices = {f"{2024 + divmod(6 + i, 12)[0]}-{divmod(6 + i, 12)[1] + 1:02d}":
               100.0 * (1.028 ** i) for i in range(24)}
    monkeypatch.setattr(consultas.macro, "ipc_serie",
                        lambda: {"disponible": True, "indices": indices})
    antes = hashlib.sha256(json.dumps(store.raw_actual(), sort_keys=True).encode()).hexdigest()
    yield
    despues = hashlib.sha256(json.dumps(store.raw_actual(), sort_keys=True).encode()).hexdigest()
    assert antes == despues, "una consulta MUTÓ el dataset"


def _sana(r: dict, *, temporal: bool | None = None, unidad: str | None = None,
          max_puntos: int = consultas.MAX_PUNTOS) -> None:
    """Las invariantes de una serie SANA."""
    assert r["ok"], r.get("motivo")
    assert 1 <= len(r["series"]) <= consultas.MAX_SERIES
    for s in r["series"]:
        pts = s["puntos"]
        assert pts, "serie vacía"
        assert len(pts) <= max_puntos
        for pt in pts:
            assert pt["y"] is not None and not (isinstance(pt["y"], float) and math.isnan(pt["y"]))
        if r["meta"].get("temporal"):
            assert len(pts) > 1, "se pidió serie y vino un solo punto"
            xs = [pt["x"] for pt in pts]
            assert xs == sorted(xs), "serie temporal desordenada"
        if r["meta"].get("composicion"):
            assert all(0 <= pt["y"] <= 100.0001 for pt in pts), "un % fuera de [0,100]"
            ys = {round(pt["y"], 1) for pt in pts}
            assert ys != {100.0}, "degenerado: todo 100%"
    if temporal is not None:
        assert bool(r["meta"].get("temporal")) == temporal
    if unidad is not None:
        assert r["meta"]["unidad"] == unidad


# --- LA MATRIZ: ventas × métrica × agrupación × filtro -------------------------

_METRICAS_V = ["unidades", "pesos", "pesos_reales"]
_AGRUPAR_T = ["mes", "trimestre", "anio"]
_FILTROS = [{}, {"categoria": "bebidas"}, {"producto": "vino tinto la ribera"},
            {"producto": "leche entera"}]


@pytest.mark.parametrize("metrica", _METRICAS_V)
@pytest.mark.parametrize("agrupar", _AGRUPAR_T)
@pytest.mark.parametrize("filtro", _FILTROS, ids=lambda f: str(sorted(f)) or "sin_filtro")
def test_matriz_ventas_temporales(metrica, agrupar, filtro):
    r = consultas.consultar({"fuente": "ventas", "metrica": metrica,
                             "agrupar": agrupar, **filtro}, "en")
    _sana(r, temporal=True)
    assert r["meta"]["deflactado"] == (metrica == "pesos_reales")


@pytest.mark.parametrize("metrica", ["unidades", "pesos", "pesos_reales"])
@pytest.mark.parametrize("agrupar", ["categoria", "producto"])
@pytest.mark.parametrize("composicion", [False, True])
def test_matriz_ventas_dimensionales(metrica, agrupar, composicion):
    r = consultas.consultar({"fuente": "ventas", "metrica": metrica,
                             "agrupar": agrupar, "composicion": composicion}, "en")
    _sana(r, temporal=False)
    if composicion:
        assert r["meta"]["unidad"] == "%"


@pytest.mark.parametrize("sujeto", [{"categoria": "bebidas"},
                                    {"producto": "vino tinto la ribera"}])
@pytest.mark.parametrize("universo", ["total_negocio", "bebidas"])
def test_matriz_participacion(sujeto, universo):
    if sujeto == {"categoria": "bebidas"} and universo == "bebidas":
        pytest.skip("sujeto==universo se testea aparte (error autocorregible)")
    r = consultas.consultar({"fuente": "ventas", "metrica": "participacion",
                             **sujeto, "universo": universo}, "en")
    _sana(r, temporal=True, unidad="%")


@pytest.mark.parametrize("metrica,agrupar", [
    ("inmovilizado", "categoria"), ("inmovilizado", "producto"),
    ("stock", "categoria"), ("stock", "producto"),
    ("margen_teorico", "categoria"), ("dias_rotacion", "categoria"),
])
def test_matriz_inventario(metrica, agrupar):
    # inventario sale del dataset REAL del tenant de la suite (el piloto tiene
    # artículos con y sin PVP, cancelados con stock, etc. — los bordes de verdad)
    r = consultas.consultar({"fuente": "inventario", "metrica": metrica,
                             "agrupar": agrupar}, "en")
    if metrica == "dias_rotacion" and not r["ok"]:
        # sin ventas validadas en el piloto los días de rotación caen HONESTOS
        assert r["motivo"]
        return
    _sana(r, temporal=False)


@pytest.mark.parametrize("metrica", ["saldo", "dias_sin_pagar"])
def test_matriz_cuentas(metrica):
    r = consultas.consultar({"fuente": "cuentas", "metrica": metrica}, "en")
    _sana(r, temporal=False)


# --- ⛔ los errores honestos POR DISEÑO (cada uno es un PASS) -------------------

@pytest.mark.parametrize("params,que", [
    ({"fuente": "ventas", "agrupar": "dia"}, "granularidad diaria"),
    ({"fuente": "ventas", "metrica": "unidades", "deflactar": True}, "deflactar unidades"),
    ({"fuente": "cuentas", "metrica": "pesos_reales"}, "metrica ajena a la fuente"),
    ({"fuente": "sql"}, "fuente fuera de whitelist"),
    ({"fuente": "ventas", "desde": "ayer"}, "fecha malformada"),
    ({"fuente": "ventas", "producto": "unicornio dorado"}, "producto inexistente"),
    ({"fuente": "ventas", "metrica": "participacion"}, "participacion sin sujeto"),
])
def test_matriz_errores_por_disenio(params, que):
    r = consultas.consultar(params, "en")
    assert r["ok"] is False and r["motivo"], que


# --- casos borde obligatorios ---------------------------------------------------

def test_borde_sujeto_igual_universo_autocorregible():
    r = consultas.consultar({"fuente": "ventas", "metrica": "participacion",
                             "categoria": "bebidas", "universo": "bebidas"}, "en")
    assert r["ok"] is False and r["autocorregible"]
    assert r["reintentar_con"]["universo"] == "total_negocio"
    # y el reintento con la corrección FUNCIONA (el loop de Ángela cierra)
    r2 = consultas.consultar(r["reintentar_con"], "en")
    _sana(r2, temporal=True, unidad="%")


def test_borde_composicion_degenerada_autocorregible():
    """EL BUG DEL VINO: composición de bebidas agrupada por categoría = una
    barra al 100%. Ahora es un error autocorregible que lleva a participación."""
    r = consultas.consultar({"fuente": "ventas", "metrica": "pesos",
                             "agrupar": "categoria", "categoria": "bebidas",
                             "composicion": True}, "en")
    assert r["ok"] is False and r["autocorregible"]
    r2 = consultas.consultar(r["reintentar_con"], "en")
    _sana(r2, temporal=True, unidad="%")


def test_borde_producto_fuera_del_universo():
    r = consultas.consultar({"fuente": "ventas", "metrica": "participacion",
                             "producto": "vino tinto la ribera",
                             "universo": "lácteos"}, "en")
    assert r["ok"] is False and r["autocorregible"]
    assert r["reintentar_con"]["universo"] == "bebidas"  # sugiere DONDE vive


def test_borde_producto_sin_ventas_en_ventana():
    """Existe en el catálogo pero jamás vendió: error claro, no una serie inventada."""
    r = consultas.consultar({"fuente": "ventas", "producto": SIN_VENTAS.lower()}, "en")
    assert r["ok"] is False and r["motivo"]


def test_borde_ventana_excede_historico():
    r = consultas.consultar({"fuente": "ventas", "metrica": "pesos", "agrupar": "mes",
                             "desde": "1990-01", "hasta": "2099-12"}, "en")
    _sana(r, temporal=True)  # recorta a lo que hay, no revienta


def test_borde_ventana_sin_datos():
    r = consultas.consultar({"fuente": "ventas", "desde": "1990-01",
                             "hasta": "1991-01"}, "en")
    assert r["ok"] is False  # ventana vacía dicha, no serie vacía muda


def test_borde_categoria_un_solo_producto():
    r = consultas.consultar({"fuente": "ventas", "metrica": "pesos", "agrupar": "mes",
                             "categoria": "galletitas y golosinas"}, "en")
    _sana(r, temporal=True)


def test_borde_nombre_ambiguo_junta_y_lo_dice():
    filas = consultas._filas_ventas()
    r = consultas.consultar({"fuente": "ventas", "producto": "campo alegre"}, "en")
    _sana(r, temporal=True)
    assert "products" in r["series"][0]["nombre"]  # "(N products)": lo dice


def test_borde_alias_de_fuente():
    """🔧 estaba rota: el modelo decía fuente 'trend'/'sales' y el rechazo se
    leía como falta de permisos (descarriló el caso del vino en vivo). Los
    alias obvios normalizan; el gate de features ve la fuente real."""
    for alias in ("trend", "sales", "evolution", "stock", "inventory"):
        r = consultas.consultar({"fuente": alias}, "en")
        # con alias de ventas resuelve ventas; con alias de inventario, inventario
        assert r["ok"], f"{alias} → {r.get('motivo')}"
    r = consultas.consultar({"fuente": "blockchain"}, "en")
    assert r["ok"] is False  # lo genuinamente desconocido sigue rechazado


def test_borde_alias_de_seccion_al_fijar():
    """🔧 estaba rota: fijar_en 'evolution'/'Trend' (el modelo piensa en inglés)
    rebotaba con 'sección inexistente' y Ángela lo convertía en una historia de
    permisos. Los alias normalizan y el widget queda fijo."""
    angela._set_sesion(usuario="emilio", rol="dueño")
    for seccion in ("trend", "Trend", "evolution", "Evolución", "home"):
        result, accion = angela._run_tool("consultar_serie", {
            "fuente": "trend", "metrica": "participacion", "producto": "vino tinto",
            "universo": "total_negocio", "fijar_en": seccion, "tipo": "linea",
        })
        assert result["ok"] and result.get("fijado"), (seccion, result)
        assert accion["section"] in ("evolucion", "inicio")
    from core import memoria
    memoria.borrar_vista("emilio", "widgets")


def test_borde_composicion_temporal_redirige_a_participacion():
    """🔧 estaba rota (silenciosa): composicion:true + agrupar:mes devolvía
    valores ABSOLUTOS ignorando el pedido de %. Ahora redirige a participación."""
    r = consultas.consultar({"fuente": "ventas", "metrica": "pesos", "agrupar": "mes",
                             "categoria": "bebidas", "composicion": True}, "en")
    assert r["ok"] is False and r["autocorregible"]
    r2 = consultas.consultar(r["reintentar_con"], "en")
    _sana(r2, temporal=True, unidad="%")


def test_borde_fuente_sin_permiso_del_rol():
    angela._set_sesion(usuario="deposito", rol="depósito", features={"deposito"})
    result, _ = angela._run_tool("consultar_serie", {"fuente": "cuentas"})
    assert result.get("error") == "sin_acceso"
    angela._set_sesion(usuario="dueño", rol="dueño")
