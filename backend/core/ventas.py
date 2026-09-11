"""
Ventas — el cableado del "día del CSV".

Cuando el piloto cargue sus ventas históricas (apartado "venta", el mismo que
consume Evolución), este módulo despierta lo que dormía: rotación (excedente
liberable), margen real por producto y quiebre de stock. Sin ventas, todo
devuelve disponible=False con la explicación de siempre.

EL VALIDADOR DE MONTOS (la regla crítica): antes de mostrar CUALQUIER número
calculado de ventas, el dueño confirma el total facturado de un mes. Si lo que
él esperaba difiere >20% del calculado, casi seguro estamos interpretando mal
el monto por fila (el clásico: la columna "total" leída como precio unitario →
números x1000). En ese caso el sistema SE MARCA como sospechoso y no muestra
números disparatados en la reunión — rotación/margen/quiebre quedan bloqueados
hasta resolverlo. Evolución muestra el mismo aviso sin bloquearse (ya etiqueta
todo con fuente).

Interpretación del monto por fila: la misma y ÚNICA de evolucion._monto_fila
(cantidad×precio si hay ambos; si no, precio como total de la fila). Ambigüedad
documentada ahí; el validador existe precisamente para atraparla con el dueño.
"""
from __future__ import annotations

import datetime
import json
import os

from . import paths
from . import esquema, evolucion, normalizacion, rotacion, store
from .fechas import parse_fecha
from . import fechas

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = paths.DATA_DIR  # por-tenant: env POLPILOT_DATA_DIR o data/ (ver core/paths.py)
VALIDACION_JSON = os.path.join(DATA_DIR, "ventas_validacion.json")

UMBRAL_SOSPECHA_PCT = 20.0  # diferencia contra lo que el dueño esperaba


def filas() -> list[dict]:
    return esquema.filas("venta")


def hay_datos() -> bool:
    return bool(filas())


# --- Validador de montos -------------------------------------------------------

def _val_load() -> dict:
    try:
        return json.load(open(VALIDACION_JSON, encoding="utf-8"))
    except Exception:
        return {"estado": "sin_datos"}


def _val_save(d: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(d, open(VALIDACION_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    # P11·B4: validar/desvalidar ventas prende o apaga TODOS los análisis.
    from . import analisis_cache
    analisis_cache.datos_cambiaron()


def _ultimo_mes_completo() -> tuple[str | None, float]:
    """El último mes con datos (evitando el corriente, que suele estar a medias)."""
    agg = evolucion.agregados_mensuales(filas())
    if not agg:
        return None, 0.0
    mes_corriente = fechas.hoy().strftime("%Y-%m")
    completos = [m for m in agg if m < mes_corriente]
    mes = max(completos) if completos else max(agg)
    return mes, agg[mes]


def iniciar_validacion(lang: str | None = None) -> dict:
    """Se llama al integrar un batch de ventas: arma la pregunta para el dueño.
    Hasta que confirme, los números de ventas no se muestran."""
    import i18n
    mes, total = _ultimo_mes_completo()
    if not mes:
        return {"estado": "sin_datos"}
    v = {
        "estado": "pendiente",
        "mes": mes,
        "total_calculado": round(total, 2),
        "pregunta": i18n.t("core.ventas.pregunta", lang, mes=mes,
                           total=i18n.pesos(total, lang)),
    }
    _val_save(v)
    return v


def validacion(lang: str | None = None) -> dict:
    """El estado actual del validador (recalcula la pregunta si hay datos nuevos)."""
    v = _val_load()
    if hay_datos() and v.get("estado") == "sin_datos":
        return iniciar_validacion(lang)
    if not hay_datos():
        return {"estado": "sin_datos"}
    return v


def confirmar_validacion(esperado: float | None = None, confirmar: bool = False,
                         actor: str = "dueño", lang: str | None = None) -> dict:
    """El dueño responde. confirmar=True → los números se liberan. Con 'esperado':
    si difiere >20% del calculado → SOSPECHOSO (probable error de interpretación
    del monto por fila) y todo queda bloqueado, marcado, sin números en pantalla."""
    import i18n
    v = _val_load()
    if v.get("estado") in ("sin_datos",):
        raise ValueError(i18n.t("core.ventas.nada_para_validar", lang))
    total = v.get("total_calculado") or 0
    if confirmar:
        v.update({"estado": "confirmado", "confirmado_por": actor})
    elif esperado is not None and esperado > 0:
        dif_pct = abs(total - esperado) / esperado * 100
        if dif_pct <= UMBRAL_SOSPECHA_PCT:
            v.update({"estado": "confirmado", "esperado": esperado,
                      "diferencia_pct": round(dif_pct, 1), "confirmado_por": actor})
        else:
            factor = (total / esperado) if esperado else 0
            pista = ""
            if factor > 5:
                pista = i18n.t("core.ventas.pista_inflados", lang)
            elif factor < 0.2 and factor > 0:
                pista = i18n.t("core.ventas.pista_miniatura", lang)
            v.update({"estado": "sospechoso", "esperado": esperado,
                      "diferencia_pct": round(dif_pct, 1), "factor": round(factor, 2),
                      "motivo": i18n.t("core.ventas.dif_motivo", lang,
                                       pct=round(dif_pct), pista=pista)})
    else:
        raise ValueError(i18n.t("core.ventas.esperado_o_confirma", lang))
    _val_save(v)
    store.audit.record(actor=actor, accion="validacion_montos_ventas",
                       despues={"estado": v["estado"], "mes": v.get("mes"),
                                "diferencia_pct": v.get("diferencia_pct")})
    return v


def montos_confirmados() -> bool:
    return _val_load().get("estado") == "confirmado"


# --- Agregados que despiertan los módulos --------------------------------------

def _rango_dias() -> int:
    fechas = [f for f in (parse_fecha(x.get("fecha")) for x in filas()) if f]
    if not fechas:
        return 0
    return max((max(fechas) - min(fechas)).days, 1)


def ventas_por_codigo() -> dict:
    """Unidades vendidas por código de producto en todo el período cargado."""
    out: dict = {}
    for f in filas():
        cod = f.get("codigo")
        if cod is None:
            continue
        out[cod] = out.get(cod, 0.0) + float(f.get("cantidad") or 0)
    return out


def panorama(lang: str | None = None) -> dict:
    """Lo que consume la API: rotación + margen real + quiebre, TODOS detrás del
    validador de montos. Sin ventas o sin confirmar → disponible=False con motivo."""
    import i18n
    if not hay_datos():
        return {"disponible": False,
                "motivo": i18n.t("core.ventas.motivo_sin_ventas", lang),
                "validacion": {"estado": "sin_datos"}}
    v = validacion(lang)
    if v.get("estado") != "confirmado":
        return {"disponible": False,
                "motivo": i18n.t("core.ventas.motivo_sospechoso"
                                 if v.get("estado") == "sospechoso"
                                 else "core.ventas.motivo_sin_confirmar", lang),
                "validacion": v}

    arts = store.raw_actual()
    vpc = ventas_por_codigo()
    dias = _rango_dias()

    # Rotación / excedente (la fórmula que dormía en rotacion.py, ahora cableada).
    rot = rotacion.analizar(arts, ventas_por_codigo=vpc, dias_periodo=dias)

    # Quiebre: activos con demanda que se quedan sin stock antes de la reposición.
    quiebre = []
    for a in arts:
        if a.get("estado") != "activo":
            continue
        vendidas = vpc.get(a.get("codigo"), 0)
        if vendidas <= 0:
            continue
        m = rotacion.metricas_articulo(a.get("stock") or 0, a.get("costo_iva") or 0,
                                       vendidas, dias)
        if m["demanda_diaria"] > 0:
            dias_cobertura = (a.get("stock") or 0) / m["demanda_diaria"]
            if dias_cobertura < rotacion.DIAS_REPOSICION_DEFAULT:
                quiebre.append({"codigo": a.get("codigo"), "descripcion": a.get("descripcion"),
                                "stock": a.get("stock"), "dias_cobertura": round(dias_cobertura, 1),
                                "demanda_diaria": m["demanda_diaria"]})
    quiebre.sort(key=lambda x: x["dias_cobertura"])

    # Margen real: lo facturado vs el costo ACTUAL de lo vendido (aprox documentada:
    # no tenemos costo histórico por fila; cuando venga en el CSV real, se afina).
    costo_por_cod = {a.get("codigo"): a.get("costo_iva") or 0 for a in arts}
    facturado, costo_vendido = 0.0, 0.0
    for f in filas():
        monto = evolucion._monto_fila(f)
        facturado += monto
        costo_vendido += float(f.get("cantidad") or 0) * costo_por_cod.get(f.get("codigo"), 0)
    margen_real = (round((facturado - costo_vendido) / facturado * 100, 1)
                   if facturado else None)

    return {
        "disponible": True, "validacion": v, "dias_periodo": dias,
        "rotacion": rot,
        "quiebre": {"cantidad": len(quiebre), "items": quiebre[:20]},
        "margen_real": {"facturado": round(facturado, 2),
                        "costo_vendido": round(costo_vendido, 2),
                        "margen_pct": margen_real,
                        "nota": i18n.t("core.ventas.nota_margen", lang)},
    }


# --- Dry-run: probar un CSV sin comprometer nada --------------------------------

def dry_run(csv_texto: str) -> dict:
    """Carga un CSV de ventas EN MEMORIA: qué se detecta, qué activaría y el total
    del mes de muestra para el validador. No persiste nada, no toca el staging."""
    from . import staging  # import perezoso: staging ya importa medio mundo
    import csv as _csv
    import io as _io
    rows = list(_csv.reader(_io.StringIO(csv_texto)))
    if not rows:
        raise ValueError("El archivo está vacío.")
    headers = [str(c) for c in rows[0]]
    deteccion = esquema.detectar_tipo(headers)
    cuerpo = [r for r in rows[1:] if any(r)]
    cuerpo, norm = normalizacion.normalizar_tabla(headers, cuerpo)
    tipo, mapeo, filas_c, observaciones = staging._coerce_y_analizar(
        deteccion["tipo"], headers, cuerpo, norm["ambiguos"])
    agg = evolucion.agregados_mensuales(filas_c) if tipo == "venta" else {}
    mes = max(agg) if agg else None
    return {
        "dry_run": True, "tipo_detectado": tipo, "filas": len(filas_c),
        "observaciones": [{"tipo": o["tipo"], "items": o["items"]} for o in observaciones],
        "mes_muestra": mes,
        "total_mes_muestra": round(agg[mes], 2) if mes else None,
        "activaria": (["rotación y excedente liberable", "margen real por producto",
                       "alertas de quiebre de stock", "Evolución (comparación por IPC)"]
                      if tipo == "venta" else []),
        "nota": "Nada quedó guardado: es una prueba. La carga real pasa por la zona de revisión.",
    }
