"""
P21 — Consultas genéricas y SEGURAS sobre los datos ya cargados.

El claim del producto es "lo que el dueño quiera de estadística sobre SUS
datos, Ángela lo construye". Esta capa es la herramienta que lo hace posible
sin abrir la puerta a nada: NO ejecuta código ni SQL — es un contrato de
parámetros validados server-side contra whitelists. Un pedido fuera del
contrato se rechaza limpio, con motivo y con la alternativa más cercana
cuando existe (verdad literal: si el dato no existe, se dice; jamás se
interpola ni se inventa una serie).

Todo es LECTURA: ninguna ruta de este módulo muta datos.

Fuentes / métricas / agrupaciones (las whitelists son el contrato):
  ventas     · unidades | pesos | pesos_reales   · mes | trimestre | anio | categoria | producto
  inventario · inmovilizado | stock | margen_teorico | dias_rotacion · categoria | producto
  cuentas    · saldo | dias_sin_pagar            · cliente
  caja       · pesos                              · medio (la caja es EL DÍA — no hay serie histórica)

Reglas duras:
  - deflactación (pesos_reales) SOLO aplica a dinero y SOLO con el IPC cargado.
  - granularidad: las ventas están por SKU/MES → "por día" no existe y se dice.
  - tope de puntos por serie, máximo 2 series por comparación, top_n acotado.
  - composición (análisis vertical) solo sobre agrupaciones dimensionales.
"""
from __future__ import annotations

import unicodedata

from . import evolucion, macro, caja as caja_mod, cuentas as cuentas_mod

MAX_PUNTOS = 130          # 10 años mensuales entran; nada más largo tiene sentido
MAX_SERIES = 2            # la regla de charts: comparar es UNA contra UNA
TOP_MAX = 15
TOP_DEFAULT = 10

FUENTES = {"ventas", "inventario", "cuentas", "caja"}
METRICAS = {
    "ventas": {"unidades", "pesos", "pesos_reales", "participacion"},
    "inventario": {"inmovilizado", "stock", "margen_teorico", "dias_rotacion"},
    "cuentas": {"saldo", "dias_sin_pagar"},
    "caja": {"pesos"},
}
AGRUPAR = {
    "ventas": {"mes", "trimestre", "anio", "categoria", "producto"},
    "inventario": {"categoria", "producto"},
    "cuentas": {"cliente"},
    "caja": {"medio"},
}
_TEMPORALES = {"mes", "trimestre", "anio"}
# lo que la gente pide y NO existe, con su alternativa honesta
_GRANULARIDAD_INEXISTENTE = {"dia", "día", "day", "semana", "week", "dia_semana"}


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _err(motivo: str, alternativa: str | None = None, sugerencias: list | None = None,
         autocorreccion: dict | None = None) -> dict:
    """P23·A — `autocorreccion` es un error AUTOCORREGIBLE: trae los parámetros
    corregidos listos para reintentar. Ángela lo lee, reintenta UNA vez y
    entrega — jamás un menú."""
    out = {"ok": False, "motivo": motivo}
    if alternativa:
        out["alternativa"] = alternativa
    if sugerencias:
        out["sugerencias"] = sugerencias[:5]
    if autocorreccion:
        out["autocorregible"] = True
        out["reintentar_con"] = autocorreccion
    return out


# --- resolución de filtros contra lo que EXISTE -------------------------------

def _filas_ventas() -> list[dict]:
    filas, _ = evolucion.filas_ventas()
    return filas


def _categorias() -> set[str]:
    return {f["categoria"] for f in _filas_ventas()}


def _resolver_categoria(texto: str) -> str | None:
    q = _norm(texto)
    if not q:
        return None
    for c in _categorias():
        if q in _norm(c) or _norm(c) in q:
            return c
    # E3·2 — el usuario en EN puede escribir el rubro en inglés ("cold cuts"):
    # mapeo inverso desde la traducción de display a la categoría cruda (ES).
    import i18n
    for cat_es, cat_en in i18n.CATEGORIAS_EN.items():
        if q in _norm(cat_en) or _norm(cat_en) in q:
            for c in _categorias():
                if _norm(c) == cat_es:
                    return c
    return None


def _resolver_productos(texto: str, filas: list[dict]) -> tuple[set[str], list[str]]:
    """Nombres de producto cuyas palabras matchean TODAS las del pedido.
    Devuelve (nombres, sugerencias_si_vacio)."""
    palabras = [w for w in _norm(texto).split() if len(w) > 1]
    if not palabras:
        return set(), []
    nombres = {f["producto"] for f in filas}
    exactos = {n for n in nombres if all(w in _norm(n) for w in palabras)}
    if exactos:
        return exactos, []
    # sugerencias: los que matchean la mayoría de las palabras
    parciales = sorted(nombres,
                       key=lambda n: -sum(1 for w in palabras if w in _norm(n)))
    con_algo = [n for n in parciales if any(w in _norm(n) for w in palabras)]
    return set(), con_algo[:5]


def _periodo(mes: str, agrupar: str) -> str:
    """'2024-07' → '2024-07' | '2024-T3' | '2024'."""
    if agrupar == "anio":
        return mes[:4]
    if agrupar == "trimestre":
        t = (int(mes[5:7]) - 1) // 3 + 1
        return f"{mes[:4]}-T{t}"
    return mes


# --- ventas -------------------------------------------------------------------

def _serie_ventas_temporal(filas: list[dict], metrica: str, agrupar: str,
                           desde: str | None, hasta: str | None,
                           indices: dict, mes_base: str | None) -> list[dict] | dict:
    por_mes: dict[str, float] = {}
    for f in filas:
        mes = evolucion.mes_de(f.get("fecha"))
        if not mes:
            continue
        if desde and mes < desde:
            continue
        if hasta and mes > hasta:
            continue
        v = float(f.get("cantidad") or 0) if metrica == "unidades" else evolucion._monto_fila(f)
        por_mes[mes] = por_mes.get(mes, 0.0) + v
    if metrica == "pesos_reales":
        deflactados = {}
        for mes, v in por_mes.items():
            m_idx = evolucion._mes_indice_para(mes, indices)
            r = evolucion.deflactar(v, m_idx, indices, mes_base) if m_idx else None
            if r is not None:
                deflactados[mes] = r
        por_mes = deflactados
    agregado: dict[str, float] = {}
    for mes, v in por_mes.items():
        k = _periodo(mes, agrupar)
        agregado[k] = agregado.get(k, 0.0) + v
    puntos = [{"x": k, "y": round(v, 2)} for k, v in sorted(agregado.items())]
    if len(puntos) > MAX_PUNTOS:
        puntos = puntos[-MAX_PUNTOS:]
    return puntos


def _participacion(p: dict, filas: list[dict], lang: str | None) -> dict:
    """P23·A — análisis vertical CON DENOMINADOR EXPLÍCITO: el sujeto (producto
    o categoría) como % del universo (total_negocio | una categoría padre),
    período a período. Validación dura: el sujeto tiene que ser subconjunto
    PROPIO del universo — sujeto==universo da 100% siempre y se rechaza con
    un error autocorregible (Ángela reintenta sola con universo mayor)."""
    import i18n
    agrupar = p.get("agrupar") or "mes"
    if agrupar not in _TEMPORALES:
        agrupar = "mes"
    universo_txt = _norm(p.get("universo") or "total_negocio")
    desde, hasta = p.get("desde"), p.get("hasta")

    # el universo: todo el negocio, o una categoría padre real
    if universo_txt in ("total_negocio", "total", "todo", "negocio", "whole_business",
                        "total_business", ""):
        base_universo, nombre_universo = filas, i18n.t("core.consulta.total_ventas", lang)
        universo_es_total = True
    else:
        cat_u = _resolver_categoria(universo_txt)
        if not cat_u:
            return _err(i18n.t("core.consulta.cat_inexistente", lang, texto=universo_txt),
                        sugerencias=sorted(_categorias()))
        base_universo, nombre_universo = [f for f in filas if f["categoria"] == cat_u], cat_u
        universo_es_total = False

    # el sujeto: producto o categoría, DENTRO del universo
    if p.get("producto"):
        nombres, sugerencias = _resolver_productos(p["producto"], base_universo)
        if not nombres:
            # ¿existe fuera del universo? → error claro de subconjunto
            en_todo, _ = _resolver_productos(p["producto"], filas)
            if en_todo:
                cats = sorted({f["categoria"] for f in filas if f["producto"] in en_todo})
                return _err(i18n.t("core.consulta.sujeto_fuera", lang,
                                   sujeto=p["producto"], universo=nombre_universo,
                                   donde=", ".join(cats)),
                            autocorreccion={**{k: v for k, v in p.items() if v},
                                            "universo": cats[0]})
            return _err(i18n.t("core.consulta.prod_inexistente", lang, texto=p["producto"]),
                        sugerencias=sugerencias)
        base_sujeto = [f for f in base_universo if f["producto"] in nombres]
        nombre_sujeto = (sorted(nombres)[0] if len(nombres) == 1
                         else i18n.t("core.consulta.varios_prod", lang,
                                     texto=p["producto"].upper(), n=len(nombres)))
    elif p.get("categoria"):
        cat_s = _resolver_categoria(p["categoria"])
        if not cat_s:
            return _err(i18n.t("core.consulta.cat_inexistente", lang, texto=p["categoria"]),
                        sugerencias=sorted(_categorias()))
        if not universo_es_total and _norm(cat_s) == _norm(nombre_universo):
            # sujeto == universo: 100% de sí mismo, SIEMPRE — autocorregible
            return _err(i18n.t("core.consulta.sujeto_igual_universo", lang, sujeto=cat_s),
                        autocorreccion={"fuente": "ventas", "metrica": "participacion",
                                        "categoria": cat_s, "universo": "total_negocio",
                                        "agrupar": agrupar,
                                        **({"desde": desde} if desde else {}),
                                        **({"hasta": hasta} if hasta else {})})
        base_sujeto = [f for f in base_universo if f["categoria"] == cat_s]
        if not base_sujeto and not universo_es_total:
            return _err(i18n.t("core.consulta.sujeto_fuera", lang, sujeto=cat_s,
                               universo=nombre_universo, donde="total_negocio"),
                        autocorreccion={"fuente": "ventas", "metrica": "participacion",
                                        "categoria": cat_s, "universo": "total_negocio",
                                        "agrupar": agrupar})
        nombre_sujeto = cat_s
    else:
        return _err(i18n.t("core.consulta.participacion_sin_sujeto", lang))

    # % en PESOS (mezclar unidades de rubros distintos es comparar peras con
    # camiones): monto_sujeto / monto_universo por período
    def _por_periodo(base):
        out: dict[str, float] = {}
        for f in base:
            mes = evolucion.mes_de(f.get("fecha"))
            if not mes or (desde and mes < desde) or (hasta and mes > hasta):
                continue
            k = _periodo(mes, agrupar)
            out[k] = out.get(k, 0.0) + evolucion._monto_fila(f)
        return out
    sujeto_m, universo_m = _por_periodo(base_sujeto), _por_periodo(base_universo)
    puntos = [{"x": k, "y": round(sujeto_m.get(k, 0.0) / v * 100, 2)}
              for k, v in sorted(universo_m.items()) if v > 0]
    if not puntos:
        return _err(i18n.t("core.consulta.ventana_vacia", lang))
    if len(puntos) > MAX_PUNTOS:
        puntos = puntos[-MAX_PUNTOS:]
    nombre = i18n.t("core.consulta.participacion_nombre", lang,
                    sujeto=nombre_sujeto, universo=nombre_universo)
    meses = [pt["x"] for pt in puntos]
    return {"ok": True,
            "series": [{"nombre": nombre, "puntos": puntos}],
            "meta": {"fuente": "ventas", "metrica": "participacion", "agrupar": agrupar,
                     "unidad": "%", "ventana": f"{meses[0]} → {meses[-1]}",
                     "composicion": True, "deflactado": False, "temporal": True,
                     "universo": nombre_universo}}


def _ventas(p: dict, lang: str | None) -> dict:
    import i18n
    metrica = p.get("metrica") or "unidades"
    agrupar = p.get("agrupar") or "mes"
    filas = _filas_ventas()
    if not filas:
        return _err(i18n.t("core.consulta.sin_ventas", lang))

    if _norm(agrupar) in _GRANULARIDAD_INEXISTENTE:
        # el clásico "por día": el dato es SKU/mes — honesto y con alternativa
        return _err(i18n.t("core.consulta.sin_granularidad", lang), alternativa="mes")

    if metrica == "participacion":
        return _participacion(p, filas, lang)

    indices, mes_base = {}, None
    if metrica == "pesos_reales":
        ipc = macro.ipc_serie()
        if not ipc.get("disponible"):
            return _err(i18n.t("core.consulta.sin_ipc", lang), alternativa="pesos")
        indices = ipc["indices"]
        mes_base = max(indices)

    # filtros sobre lo que existe
    base = filas
    nombre_filtro = None
    if p.get("categoria"):
        cat = _resolver_categoria(p["categoria"])
        if not cat:
            return _err(i18n.t("core.consulta.cat_inexistente", lang, texto=p["categoria"]),
                        sugerencias=sorted(_categorias()))
        base = [f for f in base if f["categoria"] == cat]
        nombre_filtro = cat
    if p.get("producto"):
        nombres, sugerencias = _resolver_productos(p["producto"], base)
        if not nombres:
            return _err(i18n.t("core.consulta.prod_inexistente", lang, texto=p["producto"]),
                        sugerencias=sugerencias)
        base = [f for f in base if f["producto"] in nombres]
        nombre_filtro = (sorted(nombres)[0] if len(nombres) == 1
                         else i18n.t("core.consulta.varios_prod", lang,
                                     texto=p["producto"].upper(), n=len(nombres)))

    desde, hasta = p.get("desde"), p.get("hasta")

    if agrupar in _TEMPORALES:
        # P23·B — composición + serie temporal: lo que se quiere es PARTICIPACIÓN
        # (antes se ignoraba en silencio y volvían valores absolutos: mentira sutil)
        if p.get("composicion") and (p.get("categoria") or p.get("producto")):
            sujeto = {"categoria": p["categoria"]} if p.get("categoria") else \
                     {"producto": p["producto"]}
            return _err(i18n.t("core.consulta.composicion_temporal", lang),
                        autocorreccion={"fuente": "ventas", "metrica": "participacion",
                                        **sujeto, "universo": "total_negocio",
                                        "agrupar": agrupar,
                                        **({"desde": desde} if desde else {}),
                                        **({"hasta": hasta} if hasta else {})})
        series = [{"nombre": nombre_filtro or i18n.t("core.consulta.total_ventas", lang),
                   "puntos": _serie_ventas_temporal(base, metrica, agrupar, desde, hasta,
                                                    indices, mes_base)}]
        # la comparación: UNA serie más, mismo eje (la regla de charts)
        comp = p.get("comparar_producto") or p.get("comparar_categoria")
        if comp:
            base2 = filas
            if p.get("comparar_categoria"):
                cat2 = _resolver_categoria(comp)
                if not cat2:
                    return _err(i18n.t("core.consulta.cat_inexistente", lang, texto=comp),
                                sugerencias=sorted(_categorias()))
                base2 = [f for f in base2 if f["categoria"] == cat2]
                nombre2 = cat2
            else:
                nombres2, sug2 = _resolver_productos(comp, base2)
                if not nombres2:
                    return _err(i18n.t("core.consulta.prod_inexistente", lang, texto=comp),
                                sugerencias=sug2)
                base2 = [f for f in base2 if f["producto"] in nombres2]
                nombre2 = (sorted(nombres2)[0] if len(nombres2) == 1
                           else i18n.t("core.consulta.varios_prod", lang,
                                       texto=comp.upper(), n=len(nombres2)))
            series.append({"nombre": nombre2,
                           "puntos": _serie_ventas_temporal(base2, metrica, agrupar, desde,
                                                            hasta, indices, mes_base)})
        if all(not s["puntos"] for s in series):
            return _err(i18n.t("core.consulta.ventana_vacia", lang))
        return _ok_ventas(series, metrica, agrupar, desde, hasta, mes_base, lang,
                          composicion=False)

    # dimensional: agrupar por categoría o producto (análisis vertical, top N)
    por_dim: dict[str, float] = {}
    for f in base:
        mes = evolucion.mes_de(f.get("fecha"))
        if not mes or (desde and mes < desde) or (hasta and mes > hasta):
            continue
        v = float(f.get("cantidad") or 0) if metrica == "unidades" else evolucion._monto_fila(f)
        if metrica == "pesos_reales":
            m_idx = evolucion._mes_indice_para(mes, indices)
            r = evolucion.deflactar(v, m_idx, indices, mes_base) if m_idx else None
            if r is None:
                continue
            v = r
        k = f["categoria"] if agrupar == "categoria" else f["producto"]
        por_dim[k] = por_dim.get(k, 0.0) + v
    if not por_dim:
        return _err(i18n.t("core.consulta.ventana_vacia", lang))
    total = sum(por_dim.values())
    composicion = bool(p.get("composicion"))
    # P23·A — guard del 100% degenerado: "composición de bebidas agrupada por
    # categoría" da UNA barra al 100% (bebidas sobre sí misma). Eso no es un
    # análisis, es una tautología — error AUTOCORREGIBLE con la salida obvia.
    if composicion and len(por_dim) == 1:
        unico = next(iter(por_dim))
        return _err(i18n.t("core.consulta.sujeto_igual_universo", lang, sujeto=unico),
                    autocorreccion={"fuente": "ventas", "metrica": "participacion",
                                    ("categoria" if agrupar == "categoria" else "producto"): unico,
                                    "universo": "total_negocio", "agrupar": "mes",
                                    **({"desde": p["desde"]} if p.get("desde") else {}),
                                    **({"hasta": p["hasta"]} if p.get("hasta") else {})})
    filas_out = [{"x": k, "y": round(v / total * 100, 1) if composicion and total else round(v, 2)}
                 for k, v in por_dim.items()]
    reverso = (p.get("orden") or "desc") != "asc"
    filas_out.sort(key=lambda d: d["y"], reverse=reverso)
    top_n = min(int(p.get("top_n") or TOP_DEFAULT), TOP_MAX)
    filas_out = filas_out[:top_n]
    series = [{"nombre": nombre_filtro or i18n.t("core.consulta.total_ventas", lang),
               "puntos": filas_out}]
    return _ok_ventas(series, metrica, agrupar, desde, hasta, mes_base, lang,
                      composicion=composicion)


def _ok_ventas(series, metrica, agrupar, desde, hasta, mes_base, lang, composicion) -> dict:
    import i18n
    unidad = ("%" if composicion else
              i18n.t("core.consulta.u_unidades", lang) if metrica == "unidades" else
              i18n.t("core.consulta.u_pesos_reales", lang, base=mes_base)
              if metrica == "pesos_reales" else "$")
    meses = sorted({pt["x"] for s in series for pt in s["puntos"]})
    ventana = f"{meses[0]} → {meses[-1]}" if meses and agrupar in _TEMPORALES else \
              (f"{desde or '2016-07'} → {hasta or 'hoy'}")
    return {"ok": True, "series": series,
            "meta": {"fuente": "ventas", "metrica": metrica, "agrupar": agrupar,
                     "unidad": unidad, "ventana": ventana, "composicion": composicion,
                     "deflactado": metrica == "pesos_reales", "base_ipc": mes_base,
                     "temporal": agrupar in _TEMPORALES}}


# --- inventario ---------------------------------------------------------------

def _inventario(p: dict, lang: str | None) -> dict:
    import i18n
    from . import analisis, store
    metrica = p.get("metrica") or "inmovilizado"
    agrupar = p.get("agrupar") or "categoria"
    arts = [a for a in store.raw_actual() if a.get("estado") == "activo"]
    if p.get("categoria"):
        cat = _resolver_categoria(p["categoria"])
        if not cat:
            return _err(i18n.t("core.consulta.cat_inexistente", lang, texto=p["categoria"]),
                        sugerencias=sorted(_categorias()))
        arts = [a for a in arts if _norm(a.get("tipo")) == _norm(cat)]
    if p.get("producto"):
        palabras = [w for w in _norm(p["producto"]).split() if len(w) > 1]
        arts = [a for a in arts if all(w in _norm(a.get("descripcion")) for w in palabras)]
        if not arts:
            return _err(i18n.t("core.consulta.prod_inexistente", lang, texto=p["producto"]))

    unidades = analisis._unidades_por_codigo(365) if metrica == "dias_rotacion" else {}

    grupos: dict[str, dict] = {}
    for a in arts:
        k = (a.get("tipo") or "?") if agrupar == "categoria" else a.get("descripcion")
        g = grupos.setdefault(k, {"inmovilizado": 0.0, "stock": 0.0,
                                  "margen_num": 0.0, "margen_den": 0.0,
                                  "dias_num": 0.0, "dias_den": 0.0})
        stock = max(a.get("stock") or 0, 0)
        costo = a.get("costo_iva") or 0
        inmov = stock * costo
        g["inmovilizado"] += inmov
        g["stock"] += stock
        pvp = a.get("pvp")
        if pvp and costo and pvp > 0:
            g["margen_num"] += (pvp - costo) / pvp * inmov
            g["margen_den"] += inmov
        if metrica == "dias_rotacion":
            u = unidades.get(a.get("codigo"), 0.0)
            if u > 0 and stock > 0:
                dias = stock / (u / 365)
                g["dias_num"] += dias * inmov
                g["dias_den"] += inmov

    filas_out = []
    for k, g in grupos.items():
        if metrica == "inmovilizado":
            y = round(g["inmovilizado"], 2)
        elif metrica == "stock":
            y = round(g["stock"], 0)
        elif metrica == "margen_teorico":
            if not g["margen_den"]:
                continue  # sin precios no hay margen: el grupo cae, no se inventa
            y = round(g["margen_num"] / g["margen_den"] * 100, 1)
        else:  # dias_rotacion
            if not g["dias_den"]:
                continue
            y = round(g["dias_num"] / g["dias_den"], 0)
    # composición solo tiene sentido en $ o stock
        filas_out.append({"x": k, "y": y})
    if not filas_out:
        return _err(i18n.t("core.consulta.sin_datos_metrica", lang))
    composicion = bool(p.get("composicion")) and metrica in ("inmovilizado", "stock")
    if composicion:
        total = sum(f["y"] for f in filas_out)
        filas_out = [{"x": f["x"], "y": round(f["y"] / total * 100, 1)} for f in filas_out]
    reverso = (p.get("orden") or "desc") != "asc"
    filas_out.sort(key=lambda d: d["y"], reverse=reverso)
    top_n = min(int(p.get("top_n") or TOP_DEFAULT), TOP_MAX)
    filas_out = filas_out[:top_n]
    unidad = ("%" if composicion or metrica == "margen_teorico" else
              i18n.t("core.consulta.u_dias", lang) if metrica == "dias_rotacion" else
              i18n.t("core.consulta.u_unidades", lang) if metrica == "stock" else "$")
    return {"ok": True,
            "series": [{"nombre": i18n.t(f"core.consulta.m_{metrica}", lang),
                        "puntos": filas_out}],
            "meta": {"fuente": "inventario", "metrica": metrica, "agrupar": agrupar,
                     "unidad": unidad, "ventana": i18n.t("core.consulta.hoy", lang),
                     "composicion": composicion, "deflactado": False, "temporal": False}}


# --- cuentas corrientes -------------------------------------------------------

def _cuentas(p: dict, lang: str | None) -> dict:
    import i18n
    metrica = p.get("metrica") or "saldo"
    clientes = cuentas_mod.listar()
    if p.get("cliente"):
        q = _norm(p["cliente"])
        clientes = [c for c in clientes if q in _norm(c["nombre"])]
        if not clientes:
            return _err(i18n.t("core.consulta.cliente_inexistente", lang, texto=p["cliente"]))
    filas_out = [{"x": c["nombre"], "y": c.get(metrica) or 0} for c in clientes]
    reverso = (p.get("orden") or "desc") != "asc"
    filas_out.sort(key=lambda d: d["y"], reverse=reverso)
    top_n = min(int(p.get("top_n") or TOP_DEFAULT), TOP_MAX)
    filas_out = filas_out[:top_n]
    unidad = "$" if metrica == "saldo" else i18n.t("core.consulta.u_dias", lang)
    return {"ok": True,
            "series": [{"nombre": i18n.t(f"core.consulta.m_{metrica}", lang),
                        "puntos": filas_out}],
            "meta": {"fuente": "cuentas", "metrica": metrica, "agrupar": "cliente",
                     "unidad": unidad, "ventana": i18n.t("core.consulta.hoy", lang),
                     "composicion": False, "deflactado": False, "temporal": False}}


# --- caja (el día corriente: no hay serie histórica y se dice) ----------------

def _caja(p: dict, lang: str | None) -> dict:
    import i18n
    e = caja_mod.estado()
    por_medio = (e.get("totales") or {}).get("por_medio") or {}
    if not por_medio:
        return _err(i18n.t("core.consulta.caja_vacia", lang))
    filas_out = [{"x": m, "y": round(v, 2)} for m, v in por_medio.items()]
    filas_out.sort(key=lambda d: d["y"], reverse=True)
    return {"ok": True,
            "series": [{"nombre": i18n.t("core.consulta.caja_hoy", lang), "puntos": filas_out}],
            "meta": {"fuente": "caja", "metrica": "pesos", "agrupar": "medio",
                     "unidad": "$", "ventana": e.get("fecha") or "",
                     "composicion": False, "deflactado": False, "temporal": False,
                     "nota": i18n.t("core.consulta.caja_nota", lang)}}


# --- entrada única ------------------------------------------------------------

# P23·B — el modelo dice "trend", "sales" o "stock" con toda naturalidad: los
# alias obvios se normalizan acá en vez de rebotar (el rebote se leía como un
# problema de permisos y descarrilaba la conversación).
FUENTE_ALIAS = {
    "venta": "ventas", "sales": "ventas", "trend": "ventas", "evolucion": "ventas",
    "evolution": "ventas", "facturacion": "ventas", "revenue": "ventas",
    "stock": "inventario", "inventory": "inventario", "articulos": "inventario",
    "productos": "inventario", "products": "inventario",
    "accounts": "cuentas", "clientes": "cuentas", "customers": "cuentas",
    "receivables": "cuentas", "cash": "caja", "register": "caja",
}


def consultar(p: dict, lang: str | None = None) -> dict:
    """El contrato completo: valida contra whitelists y despacha. Nunca muta."""
    import i18n
    p = dict(p or {})
    fuente = _norm(p.get("fuente") or "ventas")
    fuente = FUENTE_ALIAS.get(fuente, fuente)
    p["fuente"] = fuente
    if fuente not in FUENTES:
        return _err(i18n.t("core.consulta.fuente_desconocida", lang, texto=fuente),
                    sugerencias=sorted(FUENTES))
    metrica = _norm(p.get("metrica") or "")
    agrupar = _norm(p.get("agrupar") or "")
    if metrica and metrica not in METRICAS[fuente]:
        return _err(i18n.t("core.consulta.metrica_invalida", lang,
                           metrica=metrica, fuente=fuente),
                    sugerencias=sorted(METRICAS[fuente]))
    if agrupar and agrupar not in AGRUPAR[fuente] and agrupar not in _GRANULARIDAD_INEXISTENTE:
        return _err(i18n.t("core.consulta.agrupar_invalido", lang,
                           agrupar=agrupar, fuente=fuente),
                    sugerencias=sorted(AGRUPAR[fuente]))
    # regla dura: deflactar unidades no existe
    if metrica == "unidades" and p.get("deflactar"):
        return _err(i18n.t("core.consulta.deflactar_unidades", lang))
    for campo in ("desde", "hasta"):
        v = p.get(campo)
        if v and not (isinstance(v, str) and len(v) == 7 and v[4] == "-"):
            return _err(i18n.t("core.consulta.fecha_invalida", lang, campo=campo))
    if metrica:
        p["metrica"] = metrica
    if agrupar:
        p["agrupar"] = agrupar
    if fuente == "ventas":
        return _ventas(p, lang)
    if fuente == "inventario":
        return _inventario(p, lang)
    if fuente == "cuentas":
        return _cuentas(p, lang)
    return _caja(p, lang)
