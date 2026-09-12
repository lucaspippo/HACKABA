"""
Aprendizaje continuo — patrones que NADIE pidió calcular.

Todo lo demás en `core/` responde una pregunta que alguien ya sabía hacer
(¿quién me debe?, ¿qué se me está por acabar?). Este módulo busca lo
contrario: comportamiento que vive en los datos operativos de siempre
(pedidos, cierres de caja) pero que ningún reporte estándar de un ERP
resume, porque no es UNA cuenta — es una correlación entre dos cosas que
nadie puso a comparar.

El set (chico a propósito — se suma cuando un patrón nuevo se vuelva a
detectar en producción, nunca antes):

  1. combo_no_percibido    — dos productos que viajan juntos en el mismo
                              pedido mucho más de lo que el azar explica
  2. faltante_caja_patron  — un día de la semana donde la caja falta mucho
                              más seguido que el resto, tapado por el
                              promedio general

Misma regla que en `oportunidades_neg`: sin el soporte estadístico mínimo
(volumen, clientes distintos, tamaño del efecto) la tarjeta no existe — se
cae en silencio, nunca se fuerza a partir de dos coincidencias sueltas.
"""
from __future__ import annotations

import collections
import datetime
import itertools

# --- combos no percibidos: umbrales del cruce ---------------------------------
MIN_PEDIDOS_TOTAL = 40        # sin volumen de pedidos, la canasta no dice nada
MIN_COOCURRENCIAS = 5         # el par tiene que repetirse, no ser dos clientes sueltos
MIN_LIFT = 6.0                # cuántas veces más se ven juntos de lo que el azar predice
MIN_CLIENTES_DISTINTOS = 3    # que no sea la costumbre de un solo cliente

# --- faltantes de caja: umbrales del cruce por día de semana -------------------
MIN_CIERRES_CAJA = 20         # historial mínimo para hablar de un día "típico"
MIN_MUESTRAS_DIA = 4          # cierres de ESE día de semana, mínimo, para no opinar con 1
UMBRAL_RATIO_CAJA = 2.5       # el día señalado falta esto de veces más que el resto
UMBRAL_MIN_PESOS_CAJA = 500   # y no ser ruido de unos pesos


def _t(key: str, lang: str | None = None, **params) -> str:
    import i18n
    return i18n.t(key, lang, **params)


def _pesos(n, lang) -> str:
    import i18n
    return i18n.pesos(n or 0, lang)


def _grafico(nombre: str, puntos: list[dict], unidad: str, temporal: bool,
             ventana: str = "") -> dict:
    return {"ok": True, "series": [{"nombre": nombre, "puntos": puntos}],
            "meta": {"unidad": unidad, "temporal": temporal, "ventana": ventana,
                     "composicion": False, "deflactado": False}}


# --- 1 · combos no percibidos --------------------------------------------------

def _pares_por_lift(pedidos: list[dict]) -> list[dict]:
    """Todo par de códigos que aparece junto en el MISMO pedido más seguido de
    lo que el azar explicaría (lift = P(a∩b) / (P(a)·P(b))), con soporte real."""
    n = len(pedidos)
    prod_count: dict[int, int] = collections.Counter()
    prod_clientes: dict[int, set] = collections.defaultdict(set)
    pair_count: dict[tuple, int] = collections.Counter()
    pair_clientes: dict[tuple, set] = collections.defaultdict(set)
    nombres: dict[int, str] = {}
    for p in pedidos:
        codigos = set()
        for it in p.get("items") or []:
            cod = it.get("codigo")
            if cod is None:
                continue
            cod = int(cod)
            codigos.add(cod)
            nombres[cod] = it.get("producto")
        for cod in codigos:
            prod_count[cod] += 1
            prod_clientes[cod].add(p.get("cliente_id"))
        for a, b in itertools.combinations(sorted(codigos), 2):
            pair_count[(a, b)] += 1
            pair_clientes[(a, b)].add(p.get("cliente_id"))
    out = []
    for (a, b), cnt in pair_count.items():
        if cnt < MIN_COOCURRENCIAS or n == 0:
            continue
        clientes = pair_clientes[(a, b)]
        if len(clientes) < MIN_CLIENTES_DISTINTOS:
            continue
        lift = (cnt / n) / ((prod_count[a] / n) * (prod_count[b] / n))
        if lift < MIN_LIFT:
            continue
        out.append({"a": a, "b": b, "cnt": cnt, "lift": lift,
                    "clientes": len(clientes),
                    "prod_a": prod_count[a], "prod_b": prod_count[b]})
    out.sort(key=lambda x: (-x["lift"], -x["cnt"]))
    return out, nombres


def _card_combo_no_percibido(lang) -> dict | None:
    from . import ventas_cliente
    pedidos = ventas_cliente.todos_los_pedidos()
    if len(pedidos) < MIN_PEDIDOS_TOTAL:
        return None
    pares, nombres = _pares_por_lift(pedidos)
    if not pares:
        return None
    top = pares[0]
    # El ancla es el menos frecuente de los dos: "cuando aparece ESTE, el otro
    # casi siempre lo acompaña" cuenta una historia; al revés, no.
    if top["prod_a"] <= top["prod_b"]:
        ancla, pareja, n_ancla = top["a"], top["b"], top["prod_a"]
    else:
        ancla, pareja, n_ancla = top["b"], top["a"], top["prod_b"]
    nombre_a, nombre_b = nombres[ancla], nombres[pareja]

    monto_conjunto = 0.0
    montos_pareja: list[float] = []
    con_ambos = 0
    faltantes: list[dict] = []
    con_pareja: list[dict] = []
    for p in pedidos:
        por_codigo = {int(it["codigo"]): it for it in (p.get("items") or [])
                      if it.get("codigo") is not None}
        if ancla not in por_codigo:
            continue
        if pareja in por_codigo:
            con_ambos += 1
            monto_conjunto += float(por_codigo[ancla].get("monto") or 0)
            monto_conjunto += float(por_codigo[pareja].get("monto") or 0)
            montos_pareja.append(float(por_codigo[pareja].get("monto") or 0))
            con_pareja.append({"nombre": p.get("cliente"),
                               "monto": round(float(por_codigo[pareja].get("monto") or 0), 2),
                               "detalle": _t("core.pat.combo_i_conjunto", lang,
                                             fecha=p.get("fecha"))})
        else:
            faltantes.append({"nombre": p.get("cliente"), "fecha": p.get("fecha"),
                              "detalle": _t("core.pat.combo_i_falta", lang,
                                            a=nombre_a, fecha=p.get("fecha"), b=nombre_b)})
    attach_pct = round(con_ambos / n_ancla * 100) if n_ancla else 0
    hay_hueco = bool(faltantes) and montos_pareja
    if hay_hueco:
        monto = round(len(faltantes) * (sum(montos_pareja) / len(montos_pareja)), 2)
        monto_label = _t("core.pat.combo_monto_label_potencial", lang)
        resumen = _t("core.pat.combo_r_falta", lang, pct=attach_pct, a=nombre_a,
                     b=nombre_b, n=len(faltantes))
        q2 = _t("core.pat.combo_q2_falta", lang, n=len(faltantes))
        involucrados = [{"nombre": f["nombre"], "monto": None, "detalle": f["detalle"]}
                        for f in faltantes[:6]]
    else:
        monto = round(monto_conjunto, 2)
        monto_label = _t("core.pat.combo_monto_label_conjunto", lang)
        resumen = _t("core.pat.combo_r_conjunto", lang, pct=attach_pct, a=nombre_a, b=nombre_b)
        q2 = _t("core.pat.combo_q2_conjunto", lang)
        involucrados = con_pareja[:6]
    if monto <= 0:
        return None
    grafico = _grafico(
        _t("core.pat.combo_g", lang, a=nombre_a),
        [{"x": _t("core.pat.combo_g_con", lang, b=nombre_b), "y": con_ambos},
         {"x": _t("core.pat.combo_g_sin", lang, b=nombre_b), "y": len(faltantes)}],
        "#", False)
    return {
        "id": "combo_no_percibido", "tipo": "vender",
        "titulo": _t("core.pat.combo_t", lang, a=nombre_a, b=nombre_b),
        "monto": monto, "monto_label": monto_label,
        "datos": {"producto_ancla": nombre_a, "producto_pareja": nombre_b,
                  "attach_pct": attach_pct, "coocurrencias": con_ambos,
                  "pedidos_sin_pareja": len(faltantes), "clientes": top["clientes"],
                  "lift": round(top["lift"], 2)},
        "resumen": resumen,
        "accion_chat": _t("core.pat.combo_chat", lang, a=nombre_a, b=nombre_b),
        "navegar": "cuentas",
        "fuentes": [_t("core.opn.f_cuentas", lang)],
        "drill": {
            "porque": [
                _t("core.pat.combo_q1", lang, n=n_ancla, clientes=top["clientes"],
                   a=nombre_a, b=nombre_b, pct=attach_pct),
                q2,
            ],
            "grafico": grafico,
            "involucrados": involucrados,
            "supuestos": [_t("core.pat.combo_s1", lang)],
        },
    }


# --- 2 · faltantes de caja con patrón por día de semana -------------------------

def _card_faltante_caja_patron(lang) -> dict | None:
    import i18n
    from . import caja
    hist = [h for h in (caja.historial() or []) if h.get("total")]
    if len(hist) < MIN_CIERRES_CAJA:
        return None
    por_dia: dict[int, list[tuple[str, float]]] = collections.defaultdict(list)
    for h in hist:
        try:
            wd = datetime.date.fromisoformat(h["fecha"]).weekday()
        except (KeyError, ValueError, TypeError):
            continue
        por_dia[wd].append((h["fecha"], float(h.get("diferencia") or 0)))
    candidatos = []
    for wd, muestras in por_dia.items():
        if len(muestras) < MIN_MUESTRAS_DIA:
            continue
        resto = [d for wd2, ms in por_dia.items() if wd2 != wd for _, d in ms]
        if not resto:
            continue
        difs = [d for _, d in muestras]
        falt_dia = sum(-d for d in difs if d < 0) / len(difs)
        falt_resto = sum(-d for d in resto if d < 0) / len(resto)
        candidatos.append((wd, falt_dia, falt_resto, muestras, resto))
    if not candidatos:
        return None
    wd, falt_dia, falt_resto, muestras, resto = max(candidatos, key=lambda c: c[1])
    if falt_dia < UMBRAL_MIN_PESOS_CAJA:
        return None
    if falt_resto > 0 and falt_dia < falt_resto * UMBRAL_RATIO_CAJA:
        return None

    difs = [d for _, d in muestras]
    faltantes = [(f, d) for f, d in muestras if d < 0]
    pct = round(len(faltantes) / len(difs) * 100)
    pct_resto = round(sum(1 for d in resto if d < 0) / len(resto) * 100)
    total = round(sum(-d for d in difs if d < 0), 2)
    dia = i18n.dia_semana_nombre(wd, lang)
    grafico = _grafico(_t("core.pat.caja_g", lang),
                       [{"x": f, "y": round(-d, 2) or 0.0} for f, d in sorted(muestras)],
                       "$", True)
    return {
        "id": "faltante_caja_patron", "tipo": "revisar",
        "titulo": _t("core.pat.caja_t", lang, dia=dia),
        "monto": total,
        "datos": {"dia_semana": wd, "dia_nombre": dia, "pct_faltante": pct,
                  "pct_faltante_resto": pct_resto, "cierres_analizados": len(difs),
                  "total_faltante": total},
        "resumen": _t("core.pat.caja_r", lang, pct=pct, dia=dia, pct_resto=pct_resto,
                      total=_pesos(total, lang), n=len(difs)),
        "accion_chat": _t("core.pat.caja_chat", lang, dia=dia),
        "navegar": "caja",
        "fuentes": [_t("core.prio.f_caja", lang)],
        "drill": {
            "porque": [
                _t("core.pat.caja_q1", lang, n=len(difs), faltan=len(faltantes),
                   dia=dia, pct=pct, pct_resto=pct_resto),
                _t("core.pat.caja_q2", lang, total=_pesos(total, lang), dia=dia),
            ],
            "grafico": grafico,
            "involucrados": [{"nombre": f, "monto": round(-d, 2),
                              "detalle": _t("core.pat.caja_i", lang, fecha=f,
                                            monto=_pesos(-d, lang))}
                             for f, d in sorted(faltantes, key=lambda x: x[1])[:6]],
            "supuestos": [_t("core.pat.caja_s1", lang)],
        },
    }


# --- el set --------------------------------------------------------------------

NATURALEZA = {
    "combo_no_percibido": "accionable",
    "faltante_caja_patron": "riesgo",
}

DOMINIO = {
    "combo_no_percibido": ("cuentas", "oportunidades"),
    "faltante_caja_patron": ("caja",),
}

_SET = (_card_combo_no_percibido, _card_faltante_caja_patron)


def cards(lang: str | None = None) -> list[dict]:
    out = []
    for fn in _SET:
        try:
            c = fn(lang)
        except Exception:  # noqa: BLE001 — un patrón roto no tira la sección
            c = None
        if c:
            c["naturaleza"] = NATURALEZA.get(c["id"], "accionable")
            out.append(c)
    out.sort(key=lambda c: -(c.get("monto") or 0))
    return out
