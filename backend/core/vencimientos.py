"""
vencimientos.py — el vencimiento como algo que se GESTIONA, no como un campo.

Todos los ERP del rubro tienen alerta de vencimiento. Casi nadie la usa, y por
una razón simple: nadie carga la fecha. Y aun cargándola, "vence en 12 días" no
dice nada por sí solo — la pregunta real es OTRA: al ritmo al que vendés eso,
¿llegás a venderlo antes de que venza?

Ese cruce es lo que hay acá: lote (cantidad + fecha del depósito) × ritmo real
de venta (unidades de 12 meses / 365). Si el sobrante es positivo, hay plata
que se va a tirar y todavía hay tiempo de hacer algo — promoción o mandarlo a
los locales que sí lo rotan.

La captura de la fecha al ingresar mercadería vive en el circuito de
comprobantes (core/comprobantes); acá se lee lo que ya está cargado.
"""
from __future__ import annotations

from . import analisis, deposito, store
from .fechas import hoy, parse_fecha

# Ventana por defecto: lo que entra en el mes. Más allá, casi todo "no vence".
VENTANA_DIAS = 30
# Debajo de esto el sobrante es ruido de redondeo, no una decisión.
MIN_SOBRANTE_PESOS = 1.0

# What the owner decided about a lot that will not sell before it expires.
# Two ways out, and only two: a promotion, or sending it to the stores that
# do rotate it. "Aprobar" used to set React state and print a toast — the
# decision lived nowhere, a reload showed the lot again. Now it is a row.
TIPOS_GESTION = ("promocion", "locales")


def _clave(codigo, lote) -> str:
    return f"{codigo}|{lote or ''}"


def _load() -> dict:
    from core.db import blob_repo
    from core.db import tenant as _tenant
    return blob_repo.get_blob("expiry_actions", _tenant.current_tenant_id()) or {}


def _save(d: dict) -> None:
    from core.db import blob_repo
    from core.db import tenant as _tenant
    blob_repo.save_blob("expiry_actions", _tenant.current_tenant_id(), d)


def gestiones() -> dict:
    """Every lot already decided on, keyed by codigo|lote."""
    return _load()


def gestionar(codigo, lote: str | None, tipo: str, actor: str = "dueño",
              cantidad: float | None = None, nota: str | None = None) -> dict:
    """The human's yes, written down and audited. Idempotent per lot: deciding
    twice returns the first decision instead of stacking a second one."""
    if tipo not in TIPOS_GESTION:
        raise ValueError(f"tipo desconocido: {tipo!r}")
    try:
        codigo = int(codigo)
    except (TypeError, ValueError):
        raise ValueError("codigo ilegible")
    lotes = [f for f in deposito.vencimientos(365)
             if int(f.get("codigo") or 0) == codigo and (f.get("lote") or "") == (lote or "")]
    if not lotes:
        raise KeyError("lote inexistente o sin vencimiento en el año")
    f = lotes[0]
    d = _load()
    k = _clave(codigo, lote)
    if k in d:
        return {"ok": True, "ya_estaba": True, "gestion": d[k]}
    g = {"codigo": codigo, "lote": lote or "", "producto": f.get("producto"),
         "tipo": tipo, "cantidad": float(cantidad if cantidad is not None else f.get("cantidad") or 0),
         "vencimiento": f.get("vencimiento"), "actor": actor,
         "cuando": hoy().isoformat(), "nota": nota}
    d[k] = g
    _save(d)
    store.audit.record(actor=actor, accion="gestionar_vencimiento",
                       antes={"producto": g["producto"], "lote": g["lote"],
                              "vencimiento": g["vencimiento"], "gestion": None},
                       despues={"producto": g["producto"], "lote": g["lote"],
                                "tipo": tipo, "cantidad": g["cantidad"]})
    from . import analisis_cache
    analisis_cache.datos_cambiaron()
    return {"ok": True, "ya_estaba": False, "gestion": g}

def _t(key, lang=None, **p):
    import i18n
    return i18n.t(key, lang, **p)


def en_riesgo(dias: int = VENTANA_DIAS, lang: str | None = None) -> dict:
    """Lotes que vencen dentro de la ventana Y que al ritmo actual no se
    alcanzan a vender. Cada uno con cuánto sobra y cuánta plata es."""
    if not deposito.hay_datos():
        return {"disponible": False, "motivo": _t("core.venc.sin_deposito", lang)}
    dias = max(1, min(int(dias or VENTANA_DIAS), 365))
    h = hoy()
    arts = {a.get("codigo"): a for a in store.raw_actual()}
    unidades = analisis._unidades_por_codigo(365)

    items, total_riesgo, sin_ritmo = [], 0.0, 0
    decididos = _load()
    gestionados = []
    # FEFO — LA DEMANDA DE UN PRODUCTO ES UNA SOLA Y SE REPARTE ENTRE SUS LOTES.
    #
    # `ritmo` es del PRODUCTO, no del lote. Dársela entera a cada lote era
    # prometerle las mismas ventas a dos lotes a la vez: con dos lotes del
    # mismo producto venciendo en la misma ventana, el segundo parecía que se
    # vendía solo y desaparecía del listado. La plata en riesgo salía a la
    # mitad, y en silencio (ver PRODUCT.md, The Counting Rule: la unidad de
    # esta cuenta es el PRODUCTO, no la fila del depósito).
    #
    # El reparto es el orden real del depósito: primero vence, primero sale.
    # Cada lote sólo puede vender la demanda que no se llevaron los que vencen
    # antes que él. `deposito.vencimientos` ya viene ordenado por urgencia; se
    # reordena igual para no depender en silencio de eso, con el lote como
    # desempate para que dos que vencen el mismo día repartan siempre igual.
    #
    # Un lote YA DECIDIDO (promoción, locales) también consume demanda: la
    # mercadería sigue existiendo y se sigue vendiendo. Sacarlo del reparto le
    # regalaría esas ventas al siguiente y volvería a bajar el riesgo.
    asignado: dict = {}
    filas = sorted(deposito.vencimientos(dias),
                   key=lambda x: (int(x.get("dias_restantes") or 0),
                                  str(x.get("lote") or "")))
    for f in filas:
        cod = f.get("codigo")
        a = arts.get(cod)
        if not a:
            continue
        cant = float(f.get("cantidad") or 0)
        d = int(f.get("dias_restantes") or 0)
        u12 = unidades.get(cod, 0.0)
        ritmo = u12 / 365.0
        vendible = min(max(cant, 0.0), max(0.0, ritmo * d - asignado.get(cod, 0.0)))
        asignado[cod] = asignado.get(cod, 0.0) + vendible

        g = decididos.get(_clave(cod, f.get("lote")))
        if g:
            # Decided: out of the list, but not out of sight — the card says
            # what was decided, by whom, so the same lot is not decided twice.
            gestionados.append({**g, "dias_restantes": d})
            continue
        if cant <= 0:
            continue
        costo = float(a.get("costo_iva") or 0)
        sobrante = cant - vendible
        if u12 <= 0:
            sin_ritmo += 1
        if sobrante <= 0:
            continue  # llega a venderse: no es un problema, no se alarma
        plata = round(sobrante * costo, 2)
        if plata < MIN_SOBRANTE_PESOS:
            continue
        total_riesgo += plata
        items.append({
            "codigo": cod, "producto": f.get("producto") or a.get("descripcion"),
            "lote": f.get("lote"), "ubicacion": f.get("ubicacion"),
            "vencimiento": f.get("vencimiento"), "dias_restantes": d,
            "cantidad": round(cant, 1),
            "por_peso": bool(a.get("venta_x_peso")),
            "ritmo_mes": round(ritmo * 30.44, 1),
            "vendible_antes": round(vendible, 1),
            "sobrante": round(sobrante, 1),
            "plata_en_riesgo": plata,
            "sin_venta_12m": u12 <= 0,
        })
    items.sort(key=lambda x: (x["dias_restantes"], -x["plata_en_riesgo"]))

    vencidos = deposito.vencidos()
    perdido = 0.0
    for f in vencidos:
        a = arts.get(f.get("codigo"))
        if a:
            perdido += float(f.get("cantidad") or 0) * float(a.get("costo_iva") or 0)

    return {
        "disponible": True,
        "hoy": h.isoformat(),
        "ventana_dias": dias,
        "items": items,
        "total_en_riesgo": round(total_riesgo, 2),
        "lotes_en_riesgo": len(items),
        "sin_ritmo": sin_ritmo,
        "vencidos": len(vencidos),
        "vencidos_pesos": round(perdido, 2),
        "por_vencer_total": len(deposito.vencimientos(dias)),
        "gestionados": gestionados,
    }


def propuesta(lang: str | None = None, dias: int = VENTANA_DIAS) -> dict | None:
    """La acción que Ángela propone sobre el lote más urgente: promoción o
    mandarlo a los locales. Propone, no ejecuta — espera el OK del dueño."""
    r = en_riesgo(dias, lang)
    if not r.get("disponible") or not r["items"]:
        return None
    peor = r["items"][0]
    # La cantidad se dice como se pide: los kilos con su decimal, las unidades
    # enteras ("192 unidades", nunca "192,4 unidades").
    if peor["por_peso"]:
        cantidad = f"{peor['sobrante']:g} kg"
    else:
        cantidad = _t("core.venc.n_unidades", lang, n=round(peor["sobrante"]))
    return {
        "tipo": "promocion_vencimiento",
        "titulo": _t("core.venc.prop_t", lang, producto=peor["producto"]),
        "detalle": _t("core.venc.prop_d", lang, sobrante=cantidad,
                      producto=peor["producto"], dias=peor["dias_restantes"]),
        "codigo": peor["codigo"], "producto": peor["producto"],
        "cantidad": peor["sobrante"],
        # What "Aprobar" persists (Ángela's suggestion) and the other way out
        # the owner can pick instead — both are real decisions, one click each.
        "lote": peor.get("lote"),
        "gestion": "promocion",
        "alternativa": {"gestion": "locales",
                        "label": _t("core.venc.alt_locales", lang)},
    }
