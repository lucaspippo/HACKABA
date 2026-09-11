"""
Evolución — comparar peras con peras: el negocio en el tiempo, ajustado por IPC.

En Argentina comparar facturación nominal entre meses es mentirse: todo "sube".
Este motor lleva cualquier monto histórico a PESOS DE HOY (monto × índice_hoy /
índice_del_mes, IPC nivel general INDEC) y responde las comparaciones que
importan: interanual, acumulado del año (YTD) y la serie mensual real vs nominal.
SIEMPRE ambos valores, etiquetados sin ambigüedad.

Datos: el apartado "venta" (esquema.filas("venta")) — el MISMO CSV de ventas
históricas que despierta rotación/margen/quiebre. Hoy no está cargado: la
sección vive en modo "esperando datos" y despierta sola cuando entre.

Demo interna: con POLPILOT_DEMO_EVOLUCION=1 el motor usa un dataset sintético
de 24 meses (determinista, con estacionalidad e inflación argenta). Nunca se
persiste ni se mezcla con datos del piloto; la respuesta viaja marcada demo=True.

Las funciones de cálculo son puras (reciben filas e índices): testeables sin
red y sin tocar la UI.
"""
from __future__ import annotations

import datetime
from . import fechas
import os

from . import esquema, macro

# Caída interanual REAL que dispara la alerta descriptiva (en %).
UMBRAL_CAIDA_REAL = 10.0


# --- utilitarios puros --------------------------------------------------------

def mes_de(fecha) -> str | None:
    """'2026-06-15' / '15/06/2026' → '2026-06'. None si no se entiende."""
    from .fechas import parse_fecha
    f = parse_fecha(fecha)
    return f.strftime("%Y-%m") if f else None


def _monto_fila(f: dict) -> float:
    """El monto de una fila de venta. DECISIÓN: si hay cantidad y precio, es
    cantidad × precio (precio unitario); si sólo hay precio, se toma como el
    importe de la fila (exports que traen 'total'). Documentado en el reporte."""
    cantidad = f.get("cantidad") or 0
    precio = f.get("precio")
    if precio is None:
        return 0.0
    return float(cantidad) * float(precio) if cantidad else float(precio)


def agregados_mensuales(filas: list[dict]) -> dict[str, float]:
    """mes 'YYYY-MM' → facturación nominal del mes."""
    out: dict[str, float] = {}
    for f in filas:
        mes = mes_de(f.get("fecha"))
        if mes:
            out[mes] = out.get(mes, 0.0) + _monto_fila(f)
    return {m: round(v, 2) for m, v in out.items()}


def deflactar(monto: float, mes_origen: str, indices: dict[str, float],
              mes_base: str) -> float | None:
    """monto de mes_origen expresado en pesos de mes_base. None si falta índice
    (nunca inventamos un deflactor)."""
    io, ib = indices.get(mes_origen), indices.get(mes_base)
    if not io or not ib:
        return None
    return round(monto * ib / io, 2)


def _mes_indice_para(mes: str, indices: dict[str, float]) -> str | None:
    """El índice del mes, o el último anterior disponible (el INDEC publica con
    ~1 mes de rezago: junio se deflacta con mayo y se etiqueta así)."""
    if mes in indices:
        return mes
    previos = [m for m in indices if m < mes]
    return max(previos) if previos else None


def comparar(filas: list[dict], indices: dict[str, float],
             hoy: datetime.date | None = None, lang: str | None = None) -> dict:
    """Las tres respuestas del motor: serie mensual, interanual y YTD.
    Puro: recibe filas e índices, no toca red ni disco."""
    import i18n
    hoy = hoy or fechas.hoy()
    nominal = agregados_mensuales(filas)
    if not nominal:
        return {"hay_datos": False}

    mes_base = max(indices) if indices else None
    etiqueta_base = (i18n.t("core.evolucion.etiqueta_base", lang, mes_base=mes_base)
                     if mes_base else i18n.t("core.evolucion.sin_indice", lang))

    def real(monto, mes):
        if not mes_base:
            return None
        m_idx = _mes_indice_para(mes, indices)
        return deflactar(monto, m_idx, indices, mes_base) if m_idx else None

    serie = [{"mes": m, "nominal": v, "real": real(v, m)}
             for m, v in sorted(nominal.items())]

    # Interanual: el último mes con datos vs el mismo mes del año anterior.
    ultimo = max(nominal)
    hace_un_anio = f"{int(ultimo[:4]) - 1}{ultimo[4:]}"
    interanual = None
    if hace_un_anio in nominal:
        act_r, ant_r = real(nominal[ultimo], ultimo), real(nominal[hace_un_anio], hace_un_anio)
        interanual = {
            "mes": ultimo, "mes_anterior": hace_un_anio,
            "nominal_actual": nominal[ultimo], "nominal_anterior": nominal[hace_un_anio],
            "real_actual": act_r, "real_anterior": ant_r,
            "variacion_nominal_pct": round((nominal[ultimo] / nominal[hace_un_anio] - 1) * 100, 1),
            "variacion_real_pct": (round((act_r / ant_r - 1) * 100, 1)
                                   if act_r and ant_r else None),
        }

    # YTD: enero..último mes con datos del año, vs los mismos meses del anterior.
    anio = ultimo[:4]
    meses_ytd = [m for m in nominal if m[:4] == anio and m <= ultimo]
    meses_prev = [f"{int(anio) - 1}{m[4:]}" for m in meses_ytd]
    ytd = None
    if all(m in nominal for m in meses_prev) and meses_ytd:
        nom_act = sum(nominal[m] for m in meses_ytd)
        nom_ant = sum(nominal[m] for m in meses_prev)
        real_act = [real(nominal[m], m) for m in meses_ytd]
        real_ant = [real(nominal[m], m) for m in meses_prev]
        completo = all(v is not None for v in real_act + real_ant)
        ytd = {
            "anio": anio, "meses": len(meses_ytd),
            "nominal_actual": round(nom_act, 2), "nominal_anterior": round(nom_ant, 2),
            "real_actual": round(sum(real_act), 2) if completo else None,
            "real_anterior": round(sum(real_ant), 2) if completo else None,
            "variacion_nominal_pct": round((nom_act / nom_ant - 1) * 100, 1) if nom_ant else None,
            "variacion_real_pct": (round((sum(real_act) / sum(real_ant) - 1) * 100, 1)
                                   if completo and sum(real_ant) else None),
        }

    return {"hay_datos": True, "mes_base": mes_base, "etiqueta_base": etiqueta_base,
            "serie": serie, "interanual": interanual, "ytd": ytd}


def alertas_de(resultado: dict, lang: str | None = None) -> list[dict]:
    """Alertas DESCRIPTIVAS (el dato, no el consejo). Sólo con datos reales."""
    import i18n
    out = []
    inter = (resultado or {}).get("interanual")
    if inter and inter.get("variacion_real_pct") is not None \
            and inter["variacion_real_pct"] <= -UMBRAL_CAIDA_REAL:
        out.append({
            "tipo": "caida_real_interanual",
            "titulo": i18n.t("core.evolucion.alerta_caida_titulo", lang),
            "detalle": i18n.t("core.evolucion.alerta_caida_detalle", lang,
                              mes=inter["mes"],
                              caida=abs(inter["variacion_real_pct"]),
                              mes_anterior=inter["mes_anterior"],
                              nominal=f"{inter['variacion_nominal_pct']:+}"),
        })
    return out


# --- datos: apartado real o demo sintética ------------------------------------

def modo_demo() -> bool:
    return os.environ.get("POLPILOT_DEMO_EVOLUCION", "") == "1"


def _ventas_demo(hoy: datetime.date | None = None) -> list[dict]:
    """24 meses sintéticos, deterministas, con estacionalidad e inflación
    argenta (~2.6%/mes nominal vs IPC ~3%: leve caída real, dispara la alerta
    demo). SOLO para tests y demo interna con flag: no se persiste jamás."""
    hoy = hoy or fechas.hoy()
    # arranca 24 meses atrás, termina el mes pasado (el corriente está incompleto)
    estacion = {1: 0.85, 2: 0.88, 3: 1.0, 4: 1.0, 5: 1.02, 6: 1.05,
                7: 1.08, 8: 1.0, 9: 0.98, 10: 1.02, 11: 1.05, 12: 1.35}
    filas = []
    base = 90_000_000.0
    anio, mes = hoy.year, hoy.month - 1 or 12
    if hoy.month == 1:
        anio -= 1
    # generamos hacia atrás y revertimos: nominal crece 2.6% por mes
    meses = []
    a, m = anio, mes
    for _ in range(24):
        meses.append((a, m))
        m -= 1
        if m == 0:
            a, m = a - 1, 12
    meses.reverse()
    nivel = base
    for (a, m) in meses:
        monto_mes = nivel * estacion[m]
        # El último mes viene flojo a propósito: la demo muestra también la
        # alerta descriptiva de caída real interanual, no sólo el gráfico.
        if (a, m) == meses[-1]:
            monto_mes *= 0.78
        # dos filas por mes para que la agregación trabaje de verdad
        filas.append({"fecha": f"{a:04d}-{m:02d}-10", "producto": "DEMO mostrador",
                      "codigo": None, "cantidad": 1, "precio": round(monto_mes * 0.6, 2)})
        filas.append({"fecha": f"{a:04d}-{m:02d}-25", "producto": "DEMO reparto",
                      "codigo": None, "cantidad": 1, "precio": round(monto_mes * 0.4, 2)})
        nivel *= 1.026
    return filas


def filas_ventas() -> tuple[list[dict], bool]:
    """(filas, es_demo). El apartado real SIEMPRE gana sobre la demo."""
    reales = esquema.filas("venta")
    if reales:
        return reales, False
    if modo_demo():
        return _ventas_demo(), True
    return [], False


def hay_datos() -> bool:
    return bool(esquema.filas("venta"))


def composicion_categorias(filas: list[dict], meses_atras: int = 24) -> list[dict]:
    """P25·C — el análisis vertical como serie: cada categoría como % de la
    facturación, mes a mes (pesos nominales: la participación es un cociente,
    la inflación se cancela). Para el área apilada de Evolución."""
    por_mes: dict[str, dict[str, float]] = {}
    for f in filas:
        mes = mes_de(f.get("fecha"))
        if not mes:
            continue
        cat = f.get("categoria") or "?"
        d = por_mes.setdefault(mes, {})
        d[cat] = d.get(cat, 0.0) + _monto_fila(f)
    out = []
    for mes in sorted(por_mes)[-meses_atras:]:
        total = sum(por_mes[mes].values())
        fila = {"mes": mes}
        for cat, v in por_mes[mes].items():
            fila[cat] = round(v / total * 100, 1) if total else 0
        out.append(fila)
    return out


def panorama(lang: str | None = None) -> dict:
    """Lo que consume la API y Ángela: datos + índice + comparaciones + alertas."""
    import i18n
    filas, es_demo = filas_ventas()
    serie_ipc = macro.ipc_serie()
    hay_indice = bool(serie_ipc.get("disponible"))
    if not filas:
        return {
            "hay_datos": False, "demo": False, "hay_indice": hay_indice,
            "mensaje": i18n.t("core.evolucion.sin_datos", lang),
        }
    indices = serie_ipc.get("indices", {}) if hay_indice else {}
    r = comparar(filas, indices, lang=lang)
    # Las alertas se calculan igual en demo (la respuesta ya viaja marcada demo=True
    # y la UI la etiqueta); con datos reales son las alertas de negocio de verdad.
    r.update({"demo": es_demo, "hay_indice": hay_indice, "alertas": alertas_de(r, lang),
              # P25·C — el análisis vertical como serie, para el área apilada
              "composicion": composicion_categorias(filas, 24)})
    if not hay_indice:
        r["aviso_indice"] = i18n.t("core.evolucion.aviso_indice", lang)
    return r
