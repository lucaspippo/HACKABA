"""
evals.py · What the engine gets right, MEASURED — not claimed.

The difference between this file and `backend/tests/` is the whole point, and
it is worth stating because a technical reader will ask:

    A TEST answers "did it break?" — green or red, and a red one stops a merge.
    An EVAL answers "how often is it right?" — a score, over a named set of
    cases, that can be compared between two runs.

The suite already had the raw material for the second one (`tests/
test_matriz_consultas.py` generates the full source x metric x grouping matrix;
`tests/test_bateria_nl.py` runs 24 phrases through the model's own route), but
it reported pass/fail. This module scores instead, and the product shows the
score.

THE THREE HONESTY RULES, and they are enforced here, not suggested:

  1. A REPORT IS A RECORDING OF A REAL RUN. Nothing in this module is computed
     when somebody opens the screen: `scripts/run_evals.py` runs the cases and
     writes a file; `/api/evals` reads that file back. A panel that recomputed
     on request could quietly show whatever today's data happened to produce
     and call it a measurement.
  2. EVERY SCORE CARRIES ITS DENOMINATOR. Each suite reports `aciertos` and
     `total`, and the screen prints "24 of 24", never a bare "100%". A bare
     percentage over an unstated set is the oldest way to lie with a number.
  3. THE RUN'S TIMESTAMP TRAVELS WITH IT. If the last run was three days ago,
     the screen says so. A quality number with no date is decoration.

AND A FOURTH, which is about us: A FAILING CASE IS REPORTED, NOT DROPPED. The
labelled set below was written by reading the frozen demo dataset. If a case
misses, either the engine is wrong or the label is wrong — both are worth
knowing, and neither is worth hiding. Nothing here is allowed to "fix" a miss
by relaxing the expectation at run time.

WHAT IS MEASURED (five suites, each with its own denominator):

    deteccion    · the labelled findings the engine must emit on the frozen
                   demo dataset, and no unexpected ones
    procedencia  · every finding the engine DID emit declares where it came
                   from: named sources, and 3+ domains if it claims to cross
    abstencion   · the cases where the right answer is "I can't" — measured as
                   a rate, because this is the one number a system that always
                   answers can never report
    consulta     · the positive half: the queries that must come back with a
                   healthy series (an engine that refuses everything would ace
                   `abstencion` alone)
    determinismo · the same call, N times, byte-identical. The claim that the
                   model never produces the number, turned into a measurement

Determinism note: this runs against the frozen demo world
(`POLPILOT_DEMO_TODAY`), so two runs on the same data are comparable. On a
tenant with live data the numbers move because the world moved, which is why
the report records `hoy` next to `generado`.
"""
from __future__ import annotations

import datetime
import json
import os
import time
from typing import Any, Callable

from . import paths

# Where a run is recorded. Per tenant, like everything else in the data dir,
# and gitignored: a run is a measurement of one moment, not repo content.
EVALS_JSON = os.path.join(paths.DATA_DIR, "evals_run.json")

# How many times `determinismo` repeats each call. Three is enough to catch a
# non-deterministic path and cheap enough to run on every build.
REPETICIONES = 3


# =============================================================================
# the labelled set
# =============================================================================
#
# Written by hand against the frozen demo dataset (`POLPILOT_DEMO_TODAY`,
# 2026-07-07), by reading the rows — not by running the engine and writing down
# whatever came out. That direction matters: a label copied from the output
# measures nothing.
#
# Only findings whose preconditions are verifiable in the data are labelled
# `obligatorio`. The rest of the engine's catalogue is reported as OBSERVED
# coverage (how many of the engine's crossings have data to exist today),
# which is information, not a grade.

FINDINGS_OBLIGATORIOS: tuple[dict, ...] = (
    {
        "id": "cruce_espacio_camara",
        "porque": "Cámara de frío 2 tiene 4 avisos de estado_deposito dentro de "
                  "los 30 días (Ramón 29/06 y 02/07, Nahuel 01/07, Tomás 06/07) "
                  "y OC-2026-0847 sigue abierta con renglones.",
        "dominios_min": 3,
        "no_estructurado": True,
    },
    {
        "id": "sobrecompra",
        "porque": "La oferta of-2026-071 (689 kg, 18%) vence el 17/07, el lote "
                  "el 15/10, y el ritmo real del código 1282 es 524,2 kg/12m: "
                  "el sobrante no da cero.",
        "dominios_min": 0,          # es card de Oportunidades, no declara dominios
        "no_estructurado": False,
    },
    {
        "id": "cruce_oferta_camara",
        "porque": "El cruce propio: la misma oferta, más los avisos de que la "
                  "cámara del proveedor está llena y su orden del 9.",
        "dominios_min": 4,
        "no_estructurado": True,
    },
)

# Findings the engine can emit whose preconditions depend on thresholds that
# are not obvious from reading a row (payment delays, ranking positions). They
# are not graded; their presence or absence is reported as coverage.
FINDINGS_OBSERVADOS: tuple[str, ...] = (
    "cruce_deuda_vencimiento",
    "cruce_proveedor_estrella",
    "cruce_credito_creciente",
    "cruce_queja_cliente_clave",
    "cruce_cliente_en_problemas",
)


# --- the abstention set -------------------------------------------------------
#
# Each case is a query the product MUST refuse. Refusing is not a failure mode
# here: it is the expected output, and the score is how often it happens.
#
# `motivo` says which rule should catch it, so a miss points at the rule rather
# than at "something went wrong".

CASOS_ABSTENCION: tuple[dict, ...] = (
    {"id": "granularidad_dia",
     "params": {"fuente": "ventas", "metrica": "pesos", "agrupar": "dia"},
     "porque": "Las ventas están por SKU y mes. «Por día» no existe en el dato, "
               "y la respuesta correcta es decirlo, no interpolar."},
    {"id": "granularidad_semana",
     "params": {"fuente": "ventas", "metrica": "pesos", "agrupar": "semana"},
     "porque": "Misma granularidad inexistente, otra palabra."},
    {"id": "fuente_inexistente",
     "params": {"fuente": "clima", "metrica": "pesos"},
     "porque": "Una fuente fuera de la whitelist. El contrato la rechaza con "
               "las que sí existen."},
    {"id": "metrica_ajena",
     "params": {"fuente": "inventario", "metrica": "saldo", "agrupar": "categoria"},
     "porque": "«Saldo» es de cuentas corrientes, no de inventario. Cruzar el "
               "nombre de una métrica con otra fuente es el error típico."},
    {"id": "deflactar_unidades",
     "params": {"fuente": "ventas", "metrica": "unidades", "agrupar": "mes",
                "deflactar": True},
     "porque": "Deflactar unidades no significa nada: el IPC ajusta dinero. "
               "Es la regla dura que evita un número con cara de serio."},
    {"id": "fecha_mal_formada",
     "params": {"fuente": "ventas", "metrica": "pesos", "agrupar": "mes",
                "desde": "2026"},
     "porque": "Una fecha que no es AAAA-MM. Se rechaza antes de tocar un dato."},
    {"id": "agrupar_ajeno",
     "params": {"fuente": "caja", "metrica": "pesos", "agrupar": "mes"},
     "porque": "La caja es EL DÍA: no hay serie histórica. Pedirle meses es "
               "pedirle algo que no tiene."},
)


# --- the positive half --------------------------------------------------------
#
# An engine that refused everything would score 100% on abstention. These are
# the queries that must come back with a healthy series: not empty, no None or
# NaN in the points, and the unit the caller asked for.

CASOS_CONSULTA: tuple[dict, ...] = (
    {"id": "ventas_pesos_mes",
     "params": {"fuente": "ventas", "metrica": "pesos", "agrupar": "mes"}},
    {"id": "ventas_unidades_categoria",
     "params": {"fuente": "ventas", "metrica": "unidades", "agrupar": "categoria"}},
    {"id": "inventario_inmovilizado_categoria",
     "params": {"fuente": "inventario", "metrica": "inmovilizado",
                "agrupar": "categoria"}},
    {"id": "cuentas_saldo_cliente",
     "params": {"fuente": "cuentas", "metrica": "saldo", "agrupar": "cliente"}},
    {"id": "caja_pesos_medio",
     "params": {"fuente": "caja", "metrica": "pesos", "agrupar": "medio"}},
)


# --- what must not move between two runs --------------------------------------

CASOS_DETERMINISMO: tuple[dict, ...] = (
    {"id": "cruces", "que": "Los hallazgos del motor de cruces"},
    {"id": "consulta_ventas", "que": "La serie de ventas por mes"},
    {"id": "capital", "que": "El capital inmovilizado del inventario"},
)


# =============================================================================
# plumbing
# =============================================================================

def _caso(cid: str, ok: bool, detalle: str, porque: str | None = None) -> dict:
    out = {"id": cid, "ok": bool(ok), "detalle": detalle}
    if porque:
        out["porque"] = porque
    return out


def _suite(sid: str, nombre: str, mide: str, casos: list[dict],
           **extra: Any) -> dict:
    """A suite always reports its denominator. `mide` is the one-line answer to
    "what question does this number answer?", shown next to the score."""
    aciertos = sum(1 for c in casos if c["ok"])
    return {
        "id": sid,
        "nombre": nombre,
        "mide": mide,
        "aciertos": aciertos,
        "total": len(casos),
        "casos": casos,
        **extra,
    }


def _canonico(valor: Any) -> str:
    """A stable serialization, so two runs can be compared byte for byte.
    `sort_keys` because dict order is not part of an answer."""
    return json.dumps(valor, sort_keys=True, ensure_ascii=False, default=str)


def _repetir(fn: Callable[[], Any]) -> tuple[bool, int]:
    """Runs `fn` REPETICIONES times; True when every run serializes identically."""
    firmas = set()
    for _ in range(REPETICIONES):
        firmas.add(_canonico(fn()))
    return len(firmas) == 1, len(firmas)


# =============================================================================
# the suites
# =============================================================================

def _hallazgos() -> list[dict]:
    """Every finding the engine emits right now: the crossings plus the
    Opportunities cards. One call, reused by two suites — recomputing it would
    make `procedencia` grade a different set than `deteccion` did."""
    from . import cruces, oportunidades_neg
    out: list[dict] = []
    try:
        out += cruces.cards("es") or []
    except Exception:  # noqa: BLE001 — a broken suite reports, never crashes
        pass
    try:
        cards = oportunidades_neg.cards("es")
        if isinstance(cards, dict):
            cards = cards.get("cards") or []
        out += cards or []
    except Exception:  # noqa: BLE001
        pass
    return out


def suite_deteccion(hallazgos: list[dict]) -> dict:
    """Did the labelled findings come out?"""
    ids = {h.get("id") for h in hallazgos}
    por_id = {h.get("id"): h for h in hallazgos}
    casos: list[dict] = []

    for esperado in FINDINGS_OBLIGATORIOS:
        hid = esperado["id"]
        card = por_id.get(hid)
        if card is None:
            casos.append(_caso(hid, False, "no se emitió", esperado["porque"]))
            continue
        # Present is not enough: it has to claim what the label says it claims.
        faltas = []
        dominios = card.get("dominios") or []
        if len(dominios) < esperado["dominios_min"]:
            faltas.append(f"declara {len(dominios)} dominios, "
                          f"esperados {esperado['dominios_min']}")
        if esperado["no_estructurado"] and not card.get("no_estructurado"):
            faltas.append("no declara haber tocado lo no estructurado")
        casos.append(_caso(
            hid, not faltas,
            "emitido" if not faltas else "emitido, pero " + "; ".join(faltas),
            esperado["porque"]))

    observados = sorted(ids & set(FINDINGS_OBSERVADOS))
    return _suite(
        "deteccion", "Detección sobre casos etiquetados",
        "de los hallazgos que este dataset obliga a encontrar, cuántos encontró",
        casos,
        # Reported, never graded: these depend on thresholds you cannot read off
        # a row, so calling their absence a miss would be inventing a standard.
        cobertura_observada={
            "emitidos": observados,
            "del_catalogo": len(FINDINGS_OBSERVADOS),
            "nota": "Cruces del motor cuyas precondiciones dependen de umbrales "
                    "(atrasos de pago, posición en el ranking). Se informa "
                    "cuántos tienen datos para existir hoy; no se puntúa.",
        },
        hallazgos_totales=len(hallazgos),
    )


def suite_procedencia(hallazgos: list[dict]) -> dict:
    """Does every finding say where it came from?

    This is the suite that grades US, not the dataset: it runs over whatever
    the engine emitted, so it cannot be gamed by a label.
    """
    casos: list[dict] = []
    for h in hallazgos:
        hid = h.get("id") or "?"
        faltas = []
        if not (h.get("fuentes") or []):
            faltas.append("no declara fuentes")
        if h.get("cruce"):
            dominios = h.get("dominios") or []
            if len(dominios) < 3:
                faltas.append(f"se declara cruce con {len(dominios)} dominios "
                              "(un cruce toca 3 o más)")
        drill = h.get("drill") or {}
        insight = h.get("insight") or {}
        if not (drill.get("porque") or insight.get("evidence")):
            faltas.append("no expone el porqué")
        casos.append(_caso(hid, not faltas,
                           "declara fuente y porqué" if not faltas
                           else "; ".join(faltas)))
    return _suite(
        "procedencia", "Procedencia declarada",
        "de los hallazgos que emitió, cuántos declaran de dónde salieron",
        casos)


def suite_abstencion() -> dict:
    """How often does it say "I can't" when it can't?

    The suite nobody else reports, because a system that always answers has no
    number to put here.
    """
    from . import consultas
    casos: list[dict] = []
    for caso in CASOS_ABSTENCION:
        try:
            r = consultas.consultar(dict(caso["params"]), "es")
        except Exception as e:  # noqa: BLE001
            # An exception is NOT an abstention. Blowing up is a different
            # failure from saying "I can't", and scoring them the same would
            # hide the worse one.
            casos.append(_caso(caso["id"], False,
                               f"excepción en vez de respuesta honesta: "
                               f"{e.__class__.__name__}", caso["porque"]))
            continue
        nego = isinstance(r, dict) and r.get("ok") is False and bool(r.get("motivo"))
        detalle = (f"se negó: {r.get('motivo')}" if nego
                   else "contestó algo en vez de negarse")
        casos.append(_caso(caso["id"], nego, detalle, caso["porque"]))
    return _suite(
        "abstencion", "Abstención correcta",
        "de las preguntas que no se pueden contestar con estos datos, "
        "cuántas veces dijo que no sabe",
        casos)


def _serie_sana(r: dict) -> str | None:
    """None when the answer is healthy; otherwise what is wrong with it."""
    if not isinstance(r, dict):
        return "la respuesta no es un objeto"
    if r.get("ok") is False:
        return f"se negó: {r.get('motivo')}"
    series = r.get("series") or []
    if not series:
        return "sin series"
    for s in series:
        puntos = s.get("puntos") or []
        if not puntos:
            return "una serie vino vacía"
        for p in puntos:
            if not isinstance(p, dict):
                return "un punto no es un objeto"
            # `y` is the value in every series this layer emits (see
            # consultas._serie_ventas_temporal); `v` is tolerated so a future
            # shape does not silently score as healthy.
            v = p.get("y", p.get("v"))
            if v is None:
                return "un punto vino en None"
            if isinstance(v, float) and v != v:   # NaN
                return "un punto vino en NaN"
    return None


def suite_consulta() -> dict:
    """The positive half: the queries that must come back with a real series."""
    from . import consultas
    casos: list[dict] = []
    for caso in CASOS_CONSULTA:
        try:
            r = consultas.consultar(dict(caso["params"]), "es")
        except Exception as e:  # noqa: BLE001
            casos.append(_caso(caso["id"], False,
                               f"excepción: {e.__class__.__name__}"))
            continue
        problema = _serie_sana(r)
        casos.append(_caso(caso["id"], problema is None,
                           problema or f"{len(r.get('series') or [])} serie/s sana/s"))
    return _suite(
        "consulta", "Consultas que deben contestarse",
        "de las preguntas que sí tienen respuesta, cuántas volvieron con una "
        "serie sana",
        casos)


def suite_determinismo() -> dict:
    """The same call, three times, byte-identical.

    This is the claim of the house — the model narrates, the code computes —
    turned into something a stranger can check.
    """
    from . import analisis, consultas, cruces
    fns: dict[str, Callable[[], Any]] = {
        "cruces": lambda: cruces.cards("es"),
        "consulta_ventas": lambda: consultas.consultar(
            {"fuente": "ventas", "metrica": "pesos", "agrupar": "mes"}, "es"),
        "capital": lambda: analisis.rotacion(),
    }
    por_id = {c["id"]: c for c in CASOS_DETERMINISMO}
    casos: list[dict] = []
    for cid, fn in fns.items():
        que = por_id.get(cid, {}).get("que", cid)
        try:
            igual, distintas = _repetir(fn)
        except Exception as e:  # noqa: BLE001
            casos.append(_caso(cid, False, f"excepción: {e.__class__.__name__}", que))
            continue
        casos.append(_caso(
            cid, igual,
            f"{REPETICIONES} corridas idénticas" if igual
            else f"{distintas} resultados distintos en {REPETICIONES} corridas",
            que))
    return _suite(
        "determinismo", "Determinismo",
        f"de las consultas repetidas {REPETICIONES} veces, cuántas dieron "
        "exactamente lo mismo",
        casos)


# =============================================================================
# the run
# =============================================================================

class EvalsApagados(RuntimeError):
    """Raised when something tries to RUN the suites without asking for it."""


# THE HARD LOCK — evals never run by accident.
#
# Running the suites is expensive (every finding recomputed, three times over
# for the determinism suite) and, in a live demo, expense is latency: the one
# thing a 2m30s pitch cannot afford is a screen thinking. So running is
# opt-in through an environment variable, and the default is OFF.
#
# This is a belt on top of braces. The structure already made it safe — only
# `scripts/run_evals.py` calls `correr()`, and `/api/evals` reads a file — but
# structure is a promise about today's call graph. A future import, a well-
# meant "let's refresh it on open", or a scheduled job would each be one line
# away from spending twenty seconds mid-demo. This makes that line fail loudly
# instead of silently working.
#
# To run them on purpose:  POLPILOT_EVALS=1 py backend/scripts/run_evals.py
FLAG_EVALS = "POLPILOT_EVALS"


def habilitados() -> bool:
    return os.environ.get(FLAG_EVALS, "").strip() in ("1", "true", "yes", "si", "sí")


def correr() -> dict:
    """Runs every suite and returns the report. Does not persist — `guardar`
    does, so a caller can run without writing (a dry run before a demo).

    Refuses to run unless POLPILOT_EVALS is set. See the lock above.
    """
    if not habilitados():
        raise EvalsApagados(
            "Los evals están apagados. Correrlos es caro y en una demo eso es "
            f"latencia. Para correrlos a propósito: {FLAG_EVALS}=1 "
            "py backend/scripts/run_evals.py"
        )
    from .fechas import hoy
    arranque = time.time()
    hallazgos = _hallazgos()
    suites = [
        suite_deteccion(hallazgos),
        suite_procedencia(hallazgos),
        suite_abstencion(),
        suite_consulta(),
        suite_determinismo(),
    ]
    aciertos = sum(s["aciertos"] for s in suites)
    total = sum(s["total"] for s in suites)
    return {
        "generado": datetime.datetime.now().replace(microsecond=0).isoformat(),
        "duracion_s": round(time.time() - arranque, 2),
        "hoy": hoy().isoformat(),
        "tenant": paths.TENANT,
        "empresa": paths.EMPRESA,
        # Said out loud in the payload, not only in a doc: whoever reads this
        # report over the API knows what it was measured against.
        "dataset": "sintético, determinista, semilla fija (data-demo/generar.py)",
        "suites": suites,
        "resumen": {"aciertos": aciertos, "total": total},
    }


def guardar(reporte: dict, destino: str | None = None) -> str:
    destino = destino or EVALS_JSON
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=1)
    return destino


def ultimo() -> dict:
    """The last recorded run, or an honest empty state.

    NEVER computes. A screen that says "97%" because it just recalculated on
    open is not reporting a measurement, it is performing one and calling it
    history — and the difference is the whole reason this file exists.
    """
    try:
        with open(EVALS_JSON, encoding="utf-8") as f:
            reporte = json.load(f)
    except FileNotFoundError:
        return {"disponible": False,
                "motivo": "todavía no corrió ningún eval en esta instancia",
                "como": "python -m scripts.run_evals"}
    except Exception as e:  # noqa: BLE001
        return {"disponible": False,
                "motivo": f"el archivo del último eval no se pudo leer ({e.__class__.__name__})",
                "como": "python -m scripts.run_evals"}
    reporte["disponible"] = True
    reporte["antiguedad_dias"] = _antiguedad(reporte.get("generado"))
    return reporte


def _antiguedad(generado: str | None) -> int | None:
    """Days since the run. The screen prints it, so an old number reads old."""
    if not generado:
        return None
    try:
        cuando = datetime.datetime.fromisoformat(generado)
    except ValueError:
        return None
    return max(0, (datetime.datetime.now() - cuando).days)
