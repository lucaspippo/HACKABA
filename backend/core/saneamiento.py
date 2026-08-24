"""
Motor de saneamiento conversacional.

Ángela no sugiere: ejecuta. Acá viven las correcciones que aplica sobre la copia
de trabajo del inventario, siempre con backup (VersionStore) y traza (AuditLog),
y siempre reversibles. El impacto se reporta en pesos.

Reglas auto-aplicables (mutación determinística y reversible):
- fantasma  → reactivar: estado anulado→activo (vuelven a ser vendibles).
- balanza   → resetear tara: valor_peso al punto medio de [cota_inf, cota_sup]
              (corrige el default 3,00 que habilita el robo de fiambre).
"""
from __future__ import annotations

from . import store, memoria
from .models import Articulo, CATEGORIA_LABEL, Categoria

CATEGORIAS_AUTO = {"fantasma", "balanza"}


def _es_fantasma(d: dict) -> bool:
    return d.get("estado") == "anulado" and (d.get("stock") or 0) > 0


def _es_balanza(d: dict) -> bool:
    a = Articulo.from_dict(d)
    return (
        a.estado == "activo" and a.venta_x_peso and a.cota_inf and a.cota_sup
        and a.valor_peso and a.cota_inf > 0 and a.cota_sup > 0 and a.valor_peso > 0
        and (a.valor_peso < a.cota_inf or a.valor_peso > a.cota_sup)
    )


def _detector(categoria: str):
    return {"fantasma": _es_fantasma, "balanza": _es_balanza}[categoria]


def _aplicar_regla(categoria: str, d: dict) -> dict:
    """Devuelve (campo, antes, despues) tras mutar el dict in-place."""
    if categoria == "fantasma":
        antes = d.get("estado")
        d["estado"] = "activo"
        return {"campo": "estado", "antes": antes, "despues": "activo"}
    if categoria == "balanza":
        antes = d.get("valor_peso")
        medio = round((d["cota_inf"] + d["cota_sup"]) / 2, 2)
        d["valor_peso"] = medio
        return {"campo": "valor_peso", "antes": antes, "despues": medio}
    raise ValueError(f"Categoría no corregible: {categoria}")


def _impacto(categoria: str, afectados: list[dict]) -> dict:
    pesos = round(sum(d.get("inmovilizado") or 0 for d in afectados), 2)
    unidades = round(sum(d.get("stock") or 0 for d in afectados), 0)
    return {"impacto_pesos": pesos, "impacto_unidades": unidades}


def proponer(categoria: str, lang: str | None = None) -> dict:
    """Preview sin mutar: qué se va a corregir, cuánto, e impacto."""
    import i18n
    if categoria not in CATEGORIAS_AUTO:
        return {
            "categoria": categoria,
            "auto": False,
            "motivo": i18n.t("core.sane.no_auto_motivo", lang),
        }
    raw = store.raw_actual()
    det = _detector(categoria)
    afectados = [d for d in raw if det(d)]

    muestra = []
    for d in afectados[:3]:
        copia = dict(d)
        cambio = _aplicar_regla(categoria, copia)
        muestra.append({"codigo": d.get("codigo"), "descripcion": d.get("descripcion"), **cambio})

    accion = i18n.t("core.sane.accion_fantasma" if categoria == "fantasma"
                    else "core.sane.accion_balanza", lang)
    return {
        "categoria": categoria,
        "label": CATEGORIA_LABEL[Categoria(categoria)],
        "auto": True,
        "cantidad": len(afectados),
        "accion": accion,
        "muestra": muestra,
        **_impacto(categoria, afectados),
    }


def aplicar(categoria: str, actor: str = "dueño") -> dict:
    """Aplica la corrección: backup → muta → guarda → audita → memoriza."""
    if categoria not in CATEGORIAS_AUTO:
        raise ValueError(f"Categoría no corregible automáticamente: {categoria}")

    raw = store.raw_actual()
    # 1) backup inmutable del estado actual completo (reversible)
    backup = store.versiones.save(
        {"articulos": raw}, motivo=f"Backup antes de sanear «{categoria}»", autor=actor
    )
    # 2) mutar
    det = _detector(categoria)
    afectados = [d for d in raw if det(d)]
    imp = _impacto(categoria, afectados)
    for d in afectados:
        _aplicar_regla(categoria, d)
    store.guardar(raw)
    # 3) audit
    store.audit.record(
        actor=actor,
        accion=f"sanear_{categoria}",
        antes={"categoria": categoria, "afectados": len(afectados)},
        despues={"version_backup": backup["id"], **imp},
    )
    # 4) memoria (riel Plan 4): el dueño aprobó corregir esta categoría
    memoria.aprobar_categoria(actor, categoria)

    corregidos = len(afectados)
    if categoria == "fantasma":
        mensaje = (f"Listo. Normalicé {corregidos} productos que el sistema tenía como "
                   f"inexistentes: vuelven a estar disponibles para vender. "
                   f"Guardé un backup por si querés revertir.")
    else:
        mensaje = (f"Listo. Corregí las {corregidos} balanzas mal calibradas "
                   f"(${int(imp['impacto_pesos']):,} en stock dejaban de cobrarse bien). "
                   f"Guardé un backup por si querés revertir.").replace(",", ".")

    return {
        "categoria": categoria,
        "corregidos": corregidos,
        "version_backup": backup["id"],
        **imp,
        "mensaje": mensaje,
    }


def aplicar_custom(categoria: str, umbral_unidades: float | None = None, actor: str = "dueño") -> dict:
    """Corrección con una regla custom del dueño. Hoy (simulado) soporta el caso
    típico de fantasma con umbral de stock: reactivar los de >= umbral, dar de baja
    (stock 0) los de menos. Sin umbral claro, cae en la corrección estándar."""
    if categoria != "fantasma" or umbral_unidades is None:
        return aplicar(categoria, actor=actor)

    raw = store.raw_actual()
    backup = store.versiones.save(
        {"articulos": raw}, motivo=f"Backup antes de corrección custom «{categoria}»", autor=actor
    )
    afectados = [d for d in raw if _es_fantasma(d)]
    reactivados = baja = 0
    for d in afectados:
        if (d.get("stock") or 0) < umbral_unidades:
            d["stock"] = 0  # dar de baja: queda anulado y sale del grupo fantasma
            baja += 1
        else:
            d["estado"] = "activo"  # reactivar
            reactivados += 1
    store.guardar(raw)
    store.audit.record(actor=actor, accion="sanear_fantasma_custom",
                       antes={"afectados": len(afectados)},
                       despues={"reactivados": reactivados, "baja": baja,
                                "umbral": umbral_unidades, "version_backup": backup["id"]})
    memoria.aprobar_categoria(actor, categoria)
    return {
        "categoria": categoria, "corregidos": len(afectados), "version_backup": backup["id"],
        "reactivados": reactivados, "baja": baja,
        "mensaje": (f"Listo. Reactivé {reactivados} productos (los que tenían {int(umbral_unidades)}+ "
                    f"unidades) y di de baja {baja} (los de menos de {int(umbral_unidades)}). "
                    f"Guardé un backup por si querés revertir."),
    }


def revertir(version_id: int, actor: str = "dueño") -> dict:
    snap = store.versiones.restore(version_id)  # KeyError si no existe
    store.guardar(snap["articulos"])
    store.audit.record(actor=actor, accion="revertir_version", despues={"version_id": version_id})
    return {"ok": True, "version_id": version_id,
            "mensaje": f"Reverti todo a la versión {version_id}. Tus datos quedaron como antes."}
