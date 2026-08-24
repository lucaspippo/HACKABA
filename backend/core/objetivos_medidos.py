"""
core/objetivos_medidos.py — P36·E4

Objetivos que Ángela MIDE SOLA contra datos que ya existen (no metas escritas a
mano por el dueño). Cada uno es un UMBRAL con:
  · valor ACTUAL   → REAL, computado en vivo del mismo endpoint que ya lo muestra
  · meta + baseline → el umbral y el punto de partida
  · historial      → SINTÉTICO (solo tenant demo, fechas ≤ fecha congelada) para
                     que la barra tenga pasado y se vea la tendencia
El progreso se CALCULA (baseline → actual → meta); nunca se hardcodea. El dueño
no carga nada: abre la app y el objetivo ya avanzó porque el `actual` es el dato
real vivo. Ver OBJETIVOS_SINTETICOS.md para el criterio de lo sintético.

Este módulo NO lee datos: recibe los `actuales` (reales) que arma el endpoint y
sólo aplica la definición + el cálculo. Así el "actual" siempre sale del mismo
lugar que el resto de la app (una sola fuente de verdad).
"""
from __future__ import annotations

# Historial SINTÉTICO: 3 puntos semanales previos (Jun 16 / 23 / 30). El 4º
# punto (la fecha congelada) lo agrega el endpoint con el valor REAL vivo.
# Definiciones: responsable = empleado REAL del demo; `fuente_lk`/`seccion` = de
# qué cruce sale; `direccion` = hacia dónde es "mejor".
DEFS = {
    "dias_cobro": {
        "responsable": "marta", "fuente_lk": "obj.f_cuentas", "seccion": "cuentas",
        "unidad": "dias", "direccion": "menor", "baseline": 29, "meta": 20,
        "hist": [("2026-06-16", 29), ("2026-06-23", 27), ("2026-06-30", 26)],
    },
    "datos_corregir": {
        "responsable": "marta", "fuente_lk": "obj.f_saneamiento", "seccion": "saneamiento",
        "unidad": "registros", "direccion": "menor", "baseline": 44, "meta": 0,
        "hist": [("2026-06-16", 44), ("2026-06-23", 34), ("2026-06-30", 26)],
    },
    "liberar_dormido": {
        # el "actual" que recibe es lo YA LIBERADO ($): baseline_dormido − dormido_vivo.
        "responsable": "celeste", "fuente_lk": "obj.f_inventario", "seccion": "inventario",
        "unidad": "pesos", "direccion": "mayor", "baseline": 0, "meta": 20_000_000,
        "baseline_dormido": 88_000_000,
        "hist": [("2026-06-16", 8_000_000), ("2026-06-23", 14_000_000), ("2026-06-30", 17_000_000)],
    },
    "pvp_margen": {
        # el "actual" es cuántos productos SIGUEN sin precio (baja hacia 0).
        "responsable": "aldo", "fuente_lk": "obj.f_margen", "seccion": "inventario",
        "unidad": "productos", "direccion": "menor", "baseline": 20, "meta": 0,
        "hist": [("2026-06-16", 20), ("2026-06-23", 15), ("2026-06-30", 11)],
    },
    "concentracion": {
        "responsable": "aldo", "fuente_lk": "obj.f_clientes", "seccion": "cuentas",
        "unidad": "pct", "direccion": "menor", "baseline": 44, "meta": 15,
        "hist": [("2026-06-16", 44), ("2026-06-23", 42), ("2026-06-30", 41)],
    },
    # P41·3.3 — dos objetivos nuevos. Mismo contrato que los 5 anteriores: el
    # `actual` es el dato REAL vivo (lo arma el endpoint desde la misma fuente
    # que ya usa la app) y baseline+historial son SINTÉTICOS del demo, con el
    # criterio de OBJETIVOS_SINTETICOS.md. No mueven ningún número canónico:
    # los leen.
    "cobrar_morosos": {
        # actual = la mora viva ($) = cuentas.alertas().impacto_pesos ($85,7M hoy).
        # Meta $20M: la mora nunca es cero en una distribuidora — el objetivo es
        # que no pase de un colchón sano, no perseguir un imposible.
        "responsable": "marta", "fuente_lk": "obj.f_mora", "seccion": "cuentas",
        "unidad": "pesos", "direccion": "menor", "baseline": 132_000_000, "meta": 20_000_000,
        "hist": [("2026-06-16", 132_000_000), ("2026-06-23", 118_400_000),
                 ("2026-06-30", 99_100_000)],
    },
    "reponer_quiebres": {
        # actual = productos con MENOS de 14 días de cobertura (el mismo umbral
        # que usa el hallazgo de quiebre inminente), sobre el detalle de rotación
        # que la app ya calcula. Meta 10: siempre hay algo por reponer.
        "responsable": "celeste", "fuente_lk": "obj.f_quiebres", "seccion": "inventario",
        "unidad": "productos", "direccion": "menor", "baseline": 58, "meta": 10,
        "hist": [("2026-06-16", 58), ("2026-06-23", 49), ("2026-06-30", 41)],
    },
}
ORDEN = ["liberar_dormido", "cobrar_morosos", "reponer_quiebres", "pvp_margen",
         "datos_corregir", "dias_cobro", "concentracion"]

# El umbral de cobertura que define "por quebrar" — el MISMO que
# oportunidades_neg.COBERTURA_QUIEBRE_DIAS, para que el objetivo y el hallazgo
# no cuenten cosas distintas.
COBERTURA_QUIEBRE_DIAS = 14


def _progreso(baseline, actual, meta, direccion):
    rango = abs(baseline - meta) or 1
    avance = (baseline - actual) if direccion == "menor" else (actual - baseline)
    return max(0.0, min(1.0, avance / rango))


def _estado(d, actual, progreso):
    """avanza | estancado | cumplido. Estancado = el último tramo (vs el punto
    sintético más reciente) casi no se movió (o retrocedió)."""
    if progreso >= 0.999:
        return "cumplido"
    prev = d["hist"][-1][1]
    rango = abs(d["baseline"] - d["meta"]) or 1
    mejora = (prev - actual) if d["direccion"] == "menor" else (actual - prev)
    if mejora < 0.02 * rango:
        return "estancado"
    return "avanza"


def construir(actuales: dict, hoy_iso: str) -> list[dict]:
    """`actuales` = {id: valor REAL vivo} (ya normalizado por el endpoint, en las
    mismas unidades que baseline/meta). Devuelve los objetivos con progreso,
    estado e historial (los 3 puntos sintéticos + el actual real de hoy)."""
    out = []
    for oid in ORDEN:
        d = DEFS[oid]
        if oid not in actuales or actuales[oid] is None:
            continue
        actual = actuales[oid]
        prog = _progreso(d["baseline"], actual, d["meta"], d["direccion"])
        serie = [{"fecha": f, "valor": v} for f, v in d["hist"]]
        serie.append({"fecha": hoy_iso, "valor": actual})
        out.append({
            "id": oid, "responsable": d["responsable"], "fuente_lk": d["fuente_lk"],
            "seccion": d["seccion"], "unidad": d["unidad"], "direccion": d["direccion"],
            "baseline": d["baseline"], "meta": d["meta"], "actual": actual,
            "progreso": round(prog, 3), "estado": _estado(d, actual, prog),
            "historial": serie,
        })
    return out


def resumen(objs: list[dict]) -> dict:
    """Para la cabecera del panel: activos, cuántos avanzaron esta semana, y cuál
    está más cerca de cumplirse."""
    activos = [o for o in objs if o["estado"] != "cumplido"]
    avanzaron = [o for o in objs if o["estado"] == "avanza"]
    mas_cerca = max(objs, key=lambda o: o["progreso"], default=None)
    return {
        "activos": len(activos),
        "avanzaron": len(avanzaron),
        "mas_cerca": mas_cerca["id"] if mas_cerca else None,
        "mas_cerca_pct": round(mas_cerca["progreso"] * 100) if mas_cerca else 0,
    }
