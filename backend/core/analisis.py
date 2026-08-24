"""
P7 · Análisis que CRUZA datos: rotación×inmovilizado, estacionalidad decenal,
push/pull y objetivos propuestos por Ángela.

Reglas de la casa:
  - Cada número SALE de los apartados y el catálogo; nada se inventa.
  - Sin ventas cargadas (o sin validar montos) → disponible=False con motivo,
    igual que panorama() (anti-alucinación).
  - El lenguaje es de dueño de PyME: días de rotación, plata dormida,
    "stockeate antes de noviembre" — no jerga.
"""
from __future__ import annotations

import datetime

from . import esquema, ventas, cuentas as cuentas_mod
from . import fechas


# --- lecturas base -------------------------------------------------------------

def _articulos() -> list[dict]:
    from . import store
    return store.raw_actual()


def _p(monto: float, lang: str | None = None) -> str:
    """Plata para textos que van derecho al chat — delegado al formateador
    único de i18n (ES $12.345.678 / EN $12,345,678)."""
    import i18n
    return i18n.pesos(monto, lang)


def _t(key: str, lang: str | None = None, **params) -> str:
    import i18n
    return i18n.t(key, lang, **params)


def _n(x: float, lang: str | None = None) -> str:
    """Entero con separador de miles según idioma (ES 12.345 / EN 12,345)."""
    crudo = f"{x:,.0f}"
    return crudo if lang == "en" else crudo.replace(",", ".")


def _no_disponible(lang: str | None = None) -> dict | None:
    """El mismo guardián que panorama(): sin datos o sin validar → se dice."""
    if not ventas.hay_datos():
        return {"disponible": False, "motivo": _t("core.analisis.sin_ventas", lang)}
    if not ventas.montos_confirmados():
        return {"disponible": False, "motivo": _t("core.analisis.sin_validar", lang)}
    return None


def _ventas_recientes(dias: int = 365) -> list[dict]:
    """Filas de venta POR SKU (con código) de los últimos N días."""
    desde = (fechas.hoy() - datetime.timedelta(days=dias)).isoformat()
    return [f for f in esquema.filas("venta")
            if f.get("codigo") is not None and (f.get("fecha") or "") >= desde]


def _unidades_por_codigo(dias: int = 365) -> dict:
    out: dict = {}
    for f in _ventas_recientes(dias):
        out[f["codigo"]] = out.get(f["codigo"], 0.0) + float(f.get("cantidad") or 0)
    return out


# --- 1) rotación × inmovilizado -------------------------------------------------

def rotacion(lang: str | None = None) -> dict:
    """Cuántos días tarda en venderse el stock de cada producto, y cuánta plata
    hay parada en los que rotan lento. dias = stock / (unidades vendidas/365).

    P45·T1 — UNA SOLA "PLATA PARADA". Antes acá se llamaba `inmovilizado_total`
    a la suma de lo CLASIFICABLE (activo, con stock y con costo), mientras el
    Home y el mapa llamaban igual a la suma de TODO el catálogo. Diferían en
    $270.398 y eran, exactamente, los 3 productos fantasma: anulados que siguen
    con stock vivo. El mismo concepto mostraba dos números según la pantalla.

    Se unificó al total de TODA la mercadería, que es lo que una persona quiere
    saber cuando pregunta cuánta plata tiene parada: la del galpón, fantasmas
    incluidos — de hecho ESOS son los más parados, porque el sistema los anuló y
    nadie los puede vender. Lo que no se puede clasificar por rotación (no hay
    días de venta para un producto anulado) no desaparece: va en su propio
    estado `sin_clasificar`, así los cuatro estados suman el total exacto y el
    número reconcilia a la vista en vez de desaparecer en una resta."""
    guard = _no_disponible(lang)
    if guard:
        return guard
    unidades = _unidades_por_codigo(365)
    detalle, clasificado, dormido, atencion, sano = [], 0.0, 0.0, 0.0, 0.0
    sin_clasificar, n_sin_clasificar = 0.0, 0
    suma_dias_ponderada = 0.0
    for a in _articulos():
        stock = a.get("stock") or 0
        costo = a.get("costo_iva") or 0
        if a.get("estado") != "activo" or stock <= 0 or not costo:
            # sigue siendo plata parada: no se puede decir cada cuánto rota,
            # pero la mercadería está en el galpón igual.
            parado = a.get("inmovilizado") or 0
            if parado > 0:
                sin_clasificar += parado
                n_sin_clasificar += 1
            continue
        # el MISMO campo que suma el Home (core/store), no un producto recalculado:
        # per-ítem dan idéntico, pero sumarlos en otro orden movía sub-centavos y
        # los dos totales dejaban de ser el mismo número exacto.
        inmov = a.get("inmovilizado") or (stock * costo)
        clasificado += inmov
        u = unidades.get(a["codigo"], 0.0)
        dias = round(stock / (u / 365), 0) if u > 0 else None
        if dias is None:
            estado = "dormido"  # con stock y sin una venta en el año
        elif dias <= 35:
            estado = "sano"
        elif dias <= 60:
            estado = "atencion"
        else:
            estado = "dormido"
        if estado == "sano":
            sano += inmov
        elif estado == "atencion":
            atencion += inmov
        else:
            dormido += inmov
        if dias is not None:
            suma_dias_ponderada += dias * inmov
        detalle.append({"codigo": a["codigo"], "producto": a["descripcion"],
                        "categoria": a.get("tipo"), "inmovilizado": round(inmov, 2),
                        "dias_rotacion": dias, "unidades_12m": round(u, 1),
                        "estado": estado})
    detalle.sort(key=lambda x: x["inmovilizado"], reverse=True)
    dormidos = [x for x in detalle if x["estado"] == "dormido"][:8]
    # EL total: toda la mercadería parada. Es el mismo número que el KPI del Home
    # y el del mapa (core/store.resumen.inmovilizado_total), por construcción:
    # lo clasificable + lo que no se puede clasificar es el catálogo entero.
    total = clasificado + sin_clasificar
    return {
        "disponible": True,
        "inmovilizado_total": round(total, 2),
        # el sub-universo que SÍ se pudo medir por rotación, dicho aparte para
        # que nadie tenga que deducirlo de una resta
        "inmovilizado_clasificado": round(clasificado, 2),
        "dias_promedio": round(suma_dias_ponderada / clasificado, 0) if clasificado else None,
        "por_estado": {"sano": round(sano, 2), "atencion": round(atencion, 2),
                       "dormido": round(dormido, 2),
                       "sin_clasificar": round(sin_clasificar, 2)},
        "sin_clasificar": {"monto": round(sin_clasificar, 2), "productos": n_sin_clasificar,
                           "motivo": _t("core.analisis.sin_clasificar", lang)},
        "pct_dormido": round(dormido / total * 100, 1) if total else 0.0,
        "dormidos_top": dormidos,
        "detalle": detalle[:200],
    }


# P19·C — la plata parada en productos que tardan MÁS de N días en venderse
# (o directamente sin una venta en el año). Misma derivación que rotacion():
# dias = stock / (unidades/365). Nada nuevo se inventa: es un corte por umbral
# sobre el dato ya calculado, para las cards a pedido ("120+ días").
def plata_parada_mas_de(dias_min: int, lang: str | None = None) -> dict:
    guard = _no_disponible(lang)
    if guard:
        return guard
    dias_min = max(1, int(dias_min))
    unidades = _unidades_por_codigo(365)
    monto, cuenta, total = 0.0, 0, 0.0
    top: list[dict] = []
    for a in _articulos():
        stock = a.get("stock") or 0
        costo = a.get("costo_iva") or 0
        if a.get("estado") != "activo" or stock <= 0 or not costo:
            continue
        inmov = stock * costo
        total += inmov
        u = unidades.get(a["codigo"], 0.0)
        dias = round(stock / (u / 365), 0) if u > 0 else None
        if dias is None or dias > dias_min:
            monto += inmov
            cuenta += 1
            top.append({"producto": a["descripcion"], "inmovilizado": round(inmov, 2),
                        "dias": dias})
    top.sort(key=lambda x: x["inmovilizado"], reverse=True)
    return {"disponible": True, "dias_min": dias_min,
            "monto": round(monto, 2), "productos": cuenta,
            "pct_del_stock": round(monto / total * 100, 1) if total else 0.0,
            "top": top[:10]}


# --- 2) estacionalidad decenal ---------------------------------------------------

MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
            "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def estacionalidad(lang: str | None = None) -> dict:
    """Índice por mes calendario y categoría sobre TODA la historia: para cada
    año, cada mes se divide por el promedio de ese año (así la inflación no
    ensucia), y se promedia entre años. idx 1.5 = ese mes vende 50% más."""
    guard = _no_disponible(lang)
    if guard:
        return guard
    arts = {a["codigo"]: a.get("tipo") for a in _articulos()}
    por_cat_anio_mes: dict = {}
    for f in esquema.filas("venta"):
        cat = f.get("categoria") or arts.get(f.get("codigo"))
        fecha = f.get("fecha") or ""
        if not cat or len(fecha) < 7:
            continue
        anio, mes = fecha[:4], int(fecha[5:7])
        monto = float(f.get("cantidad") or 0) * float(f.get("precio") or 0)
        por_cat_anio_mes.setdefault(cat, {}).setdefault(anio, {}).setdefault(mes, 0.0)
        por_cat_anio_mes[cat][anio][mes] += monto

    categorias, anios_usados = {}, set()
    for cat, anios in por_cat_anio_mes.items():
        acumulado: dict = {}
        for anio, meses in anios.items():
            if len(meses) < 10:      # años incompletos no aportan índice limpio
                continue
            anios_usados.add(anio)
            promedio = sum(meses.values()) / len(meses)
            for m, v in meses.items():
                acumulado.setdefault(m, []).append(v / promedio)
        if not acumulado:
            continue
        indice = {m: round(sum(vs) / len(vs), 2) for m, vs in acumulado.items()}
        picos = sorted([m for m, v in indice.items() if v >= 1.20],
                       key=lambda m: -indice[m])
        categorias[cat] = {"indice": indice, "picos": picos,
                           "pico_max": max(indice, key=indice.get),
                           "idx_max": max(indice.values())}

    # qué pico viene en los próximos 60 días (para "stockeate antes")
    hoy = fechas.hoy()
    proximos = []
    import i18n
    for cat, d in categorias.items():
        for delta in (1, 2):
            m = (hoy.month - 1 + delta) % 12 + 1
            if m in d["picos"]:
                mes_nombre = i18n.mes_nombre(m, lang)
                proximos.append({"categoria": cat, "mes": mes_nombre,
                                 "indice": d["indice"][m],
                                 "aviso": _t("core.analisis.est_aviso", lang,
                                             mes=mes_nombre, cat=i18n.categoria(cat, lang),
                                             indice=f"{d['indice'][m]:.2f}")})
                break
    return {"disponible": True, "anios_analizados": len(anios_usados),
            "categorias": categorias, "proximos_picos": proximos}


# --- 3) push / pull --------------------------------------------------------------

def push_pull(lang: str | None = None) -> dict:
    """Qué empujar (push: margen alto que rota lento o temporada por venir) y
    qué dejar que la demanda traccione sola (pull: rota rápido — reponer y no
    tocar). Fundado en rotación + margen + estacionalidad, no en opinión."""
    guard = _no_disponible(lang)
    if guard:
        return guard
    rot = rotacion(lang)
    est = estacionalidad(lang)
    arts = {a["codigo"]: a for a in _articulos()}
    hoy = fechas.hoy()
    meses_prox = [(hoy.month - 1 + d) % 12 + 1 for d in (1, 2)]

    pull, push = [], []
    for x in rot["detalle"]:
        a = arts.get(x["codigo"])
        if not a or not a.get("pvp") or not a.get("costo_iva"):
            continue
        margen_pct = (a["pvp"] - a["costo_iva"]) / a["costo_iva"] * 100
        cat_idx = est["categorias"].get(x["categoria"], {}).get("indice", {})
        temporada = max((cat_idx.get(m, 1.0) for m in meses_prox), default=1.0)
        if x["dias_rotacion"] is not None and x["dias_rotacion"] <= 20:
            pull.append({**x, "margen_pct": round(margen_pct, 1),
                         "motivo": _t("core.analisis.pp_pull_motivo", lang,
                                      dias=f"{x['dias_rotacion']:.0f}")})
        elif margen_pct >= 22 and (x["dias_rotacion"] is None or x["dias_rotacion"] > 40):
            extra = (_t("core.analisis.pp_push_temporada", lang, temporada=f"{temporada:.2f}")
                     if temporada >= 1.15 else "")
            push.append({**x, "margen_pct": round(margen_pct, 1), "temporada_prox": temporada,
                         "motivo": _t("core.analisis.pp_push_margen", lang,
                                      margen=f"{margen_pct:.0f}", extra=extra)})
        elif temporada >= 1.25 and margen_pct >= 18:
            push.append({**x, "margen_pct": round(margen_pct, 1), "temporada_prox": temporada,
                         "motivo": _t("core.analisis.pp_push_estacional", lang,
                                      temporada=f"{temporada:.2f}")})
    pull.sort(key=lambda x: x["unidades_12m"], reverse=True)
    push.sort(key=lambda x: (x.get("temporada_prox", 1), x["margen_pct"]), reverse=True)
    return {"disponible": True, "pull": pull[:6], "push": push[:6]}


# --- 4) objetivos propuestos ------------------------------------------------------

def objetivos(lang: str | None = None) -> dict:
    """Objetivos con números que salen de TODO lo que Ángela ve. Propuestas,
    no órdenes: el dueño adopta las que quiere."""
    import i18n
    guard = _no_disponible(lang)
    if guard:
        return guard
    out = []
    # 1) morosos a cobrar (cuentas corrientes)
    try:
        al = cuentas_mod.alertas()
        if al.get("cantidad"):
            out.append({"id": "cobrar_morosos",
                        "titulo": _t("core.analisis.obj_morosos_titulo", lang, n=al["cantidad"]),
                        "detalle": _t("core.analisis.obj_morosos_detalle", lang,
                                      monto=_p(al["impacto_pesos"], lang)),
                        "monto": al["impacto_pesos"]})
    except Exception:
        pass
    # 2) plata dormida a liquidar
    rot = rotacion(lang)
    if rot.get("disponible") and rot["por_estado"]["dormido"] > 0:
        dormido = rot["por_estado"]["dormido"]
        top = rot["dormidos_top"][0] if rot["dormidos_top"] else None
        top_txt = (_t("core.analisis.obj_dormido_top", lang, producto=top["producto"],
                      monto=_p(top["inmovilizado"], lang)) if top else "")
        out.append({"id": "liquidar_dormido",
                    "titulo": _t("core.analisis.obj_dormido_titulo", lang,
                                 monto=_p(dormido, lang)),
                    "detalle": _t("core.analisis.obj_dormido_detalle", lang, top=top_txt),
                    "monto": dormido})
    # 3) ganarle al pico estacional que viene
    est = estacionalidad(lang)
    if est.get("disponible") and est["proximos_picos"]:
        p = est["proximos_picos"][0]
        out.append({"id": "pico_estacional",
                    "titulo": _t("core.analisis.obj_pico_titulo", lang,
                                 categoria=i18n.categoria(p["categoria"], lang), mes=p["mes"]),
                    "detalle": _t("core.analisis.obj_pico_detalle", lang, aviso=p["aviso"]),
                    "monto": None})
    # 4) sostener el crecimiento real (por volumen, no por inflación)
    u12 = sum(_unidades_por_codigo(365).values())
    u12_prev = sum(_unidades_por_codigo(730).values()) - u12
    if u12_prev > 0:
        crec = (u12 / u12_prev - 1) * 100
        cierre = _t("core.analisis.obj_crec_bien" if crec >= 0
                    else "core.analisis.obj_crec_mal", lang)
        out.append({"id": "crecimiento",
                    "titulo": _t("core.analisis.obj_crec_titulo", lang, crec=f"{crec:+.1f}"),
                    "detalle": _t("core.analisis.obj_crec_detalle", lang,
                                  u12=_n(u12, lang), u12_prev=_n(u12_prev, lang),
                                  cierre=cierre),
                    "monto": None})
    return {"disponible": True, "objetivos": out}


def kpis(lang: str | None = None) -> dict:
    """Los KPIs del dueño (P18) — TODO derivado de datos ya cargados, cada uno
    presente SOLO si su dato existe. Una sola fuente de verdad: Trend, el chat
    y el resumen ejecutivo citan estos mismos números.

    Decisiones documentadas:
    - margen_teorico: (PVP − costo_iva) / PVP, ponderado por CAPITAL inmovilizado
      (stock × costo), sobre activos con ambos datos. Es margen de LISTA a
      precios de hoy, no margen realizado sobre ventas históricas.
    - cobro_dias: promedio de `promedio_pago_dias` por cliente (comportamiento
      que el dominio ya usa para scoring), ponderado por saldo adeudado.
    """
    out: dict = {}
    # 1) Crecimiento real en VOLUMEN: unidades 12M vs 12M previos (el mismo
    #    cálculo del objetivo "crecimiento" — la inflación no lo ensucia).
    if not _no_disponible(lang):
        u12 = sum(_unidades_por_codigo(365).values())
        u12_prev = sum(_unidades_por_codigo(730).values()) - u12
        if u12 > 0 and u12_prev > 0:
            out["crecimiento_pct"] = round((u12 / u12_prev - 1) * 100, 1)
        # 2) Rotación + 3) plata dormida (ya calculadas)
        rot = rotacion(lang)
        if rot.get("disponible") and rot.get("dias_promedio") is not None:
            out["rotacion_dias"] = round(rot["dias_promedio"])
            out["dormido"] = {"monto": rot["por_estado"]["dormido"], "pct": rot["pct_dormido"]}

    # 4) Margen teórico a precios de hoy (no depende de ventas). Guard de
    #    COBERTURA: si menos del 80% de los activos tiene PVP y costo, el
    #    agregado no es defendible (catálogos con precios rotos/sin cargar
    #    lo dominarían) → el KPI CAE, no se maquilla.
    activos = [a for a in _articulos() if a.get("estado") != "anulado"]
    con_ambos = [a for a in activos if a.get("pvp") and a.get("costo_iva")]
    sin_pvp = len([a for a in activos if not a.get("pvp")])
    if activos and len(con_ambos) / len(activos) >= 0.8:
        pesos = [(max(a.get("stock") or 0, 0) * a["costo_iva"],
                  (a["pvp"] - a["costo_iva"]) / a["pvp"]) for a in con_ambos]
        total_cap = sum(c for c, _ in pesos)
        if total_cap > 0:
            out["margen_teorico"] = {
                "pct": round(sum(c * m for c, m in pesos) / total_cap * 100, 1),
                "sin_pvp": sin_pvp,
            }

    # 5) Días hasta cobrar (comportamiento por cliente, ponderado por saldo)
    from . import cuentas as cuentas_mod
    con_saldo = [c for c in cuentas_mod.listar()
                 if (c.get("saldo") or 0) > 0 and c.get("promedio_pago_dias")]
    tot_saldo = sum(c["saldo"] for c in con_saldo)
    if tot_saldo > 0:
        out["cobro_dias"] = round(sum(c["saldo"] * c["promedio_pago_dias"]
                                      for c in con_saldo) / tot_saldo)
    return out


def completo(lang: str | None = None) -> dict:
    """Todo junto para la API: un solo viaje."""
    guard = _no_disponible(lang)
    if guard:
        return guard
    return {"disponible": True, "rotacion": rotacion(lang), "estacionalidad": estacionalidad(lang),
            "push_pull": push_pull(lang), "objetivos": objetivos(lang)["objetivos"],
            "kpis": kpis(lang)}
