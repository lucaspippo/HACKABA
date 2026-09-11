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
    for f in deposito.vencimientos(dias):
        cod = f.get("codigo")
        a = arts.get(cod)
        if not a:
            continue
        cant = float(f.get("cantidad") or 0)
        if cant <= 0:
            continue
        costo = float(a.get("costo_iva") or 0)
        d = int(f.get("dias_restantes") or 0)
        u12 = unidades.get(cod, 0.0)
        ritmo = u12 / 365.0
        vendible = ritmo * d
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
    }
