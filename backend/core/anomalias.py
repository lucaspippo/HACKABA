"""
Anomalías de negocio sobre los datos EXISTENTES (no sólo los nuevos del staging).

Las mismas que detecta la zona de revisión, pero corriendo sobre el inventario que
ya está cargado: precio a pérdida, posibles duplicados, stock anormalmente alto.
Aparecen en "Datos a corregir" con el mismo flujo: regla en lote + preview + backup.
"""
from __future__ import annotations

import unicodedata

from . import store, pricing

OUTLIER_STOCK = 10000


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _perdida(raw):
    # Consciente de unidad: para un producto por peso compara $/kg vs $/kg, para
    # uno normal $/u vs $/u. Nunca cruza unidades. Ver core/pricing.py.
    return [d for d in raw if pricing.es_a_perdida(d)]


def _outliers(raw):
    return [d for d in raw if (d.get("stock") or 0) > OUTLIER_STOCK]


def _duplicados(raw):
    grupos = {}
    for d in raw:
        grupos.setdefault(_norm(d.get("descripcion")), []).append(d)
    return [d for k, items in grupos.items() if k and len(items) > 1 for d in items]


def analizar_existentes() -> list[dict]:
    raw = store.raw_actual()
    out = []

    perdida = _perdida(raw)
    if perdida:
        loss = round(sum((d["costo_iva"] - d["pvp"]) * (d.get("stock") or 0) for d in perdida), 2)
        out.append({
            "tipo": "precio_perdida", "titulo": "Precios que figuran por debajo del costo",
            "descripcion": f"{len(perdida)} productos figuran con el costo más alto que el precio de venta. "
                           f"Casi siempre es un error de carga (costo con IVA contra precio sin IVA, o un "
                           f"precio viejo). Conviene revisarlo con Ángela, no ponerle un margen a ciegas.",
            "items": len(perdida), "impacto_pesos": loss,
            "codigos": [d.get("codigo") for d in perdida],
        })

    dups = _duplicados(raw)
    if dups:
        out.append({
            "tipo": "duplicado", "titulo": "Posibles duplicados",
            "descripcion": f"{len(dups)} productos comparten nombre con otro (códigos distintos). "
                           f"Conviene revisarlos para no contar stock dos veces.",
            "items": len(dups), "impacto_pesos": round(sum(d.get("inmovilizado") or 0 for d in dups), 2),
            "codigos": [d.get("codigo") for d in dups],
        })

    outs = _outliers(raw)
    if outs:
        out.append({
            "tipo": "stock_outlier", "titulo": "Stock anormalmente alto",
            "descripcion": f"{len(outs)} productos tienen más de {OUTLIER_STOCK:,} unidades. "
                           f"¿Es correcto o hay un error de tipeo?".replace(",", "."),
            "items": len(outs), "impacto_pesos": round(sum((d.get("stock") or 0) * (d.get("costo_iva") or 0) for d in outs), 2),
            "codigos": [d.get("codigo") for d in outs],
        })

    out.sort(key=lambda g: g["impacto_pesos"], reverse=True)
    return out


def aplicar(tipo: str, accion: str, params: dict | None = None, actor: str = "dueño") -> dict:
    """Aplica una corrección de anomalía en lote sobre los datos existentes, con backup."""
    params = params or {}
    if tipo != "precio_perdida" or accion != "set_margen":
        raise ValueError("Esa anomalía no se corrige automáticamente; revisala en el inventario.")
    raw = store.raw_actual()
    backup = store.versiones.save({"articulos": raw}, motivo="Backup antes de corregir precios a pérdida", autor=actor)
    margen = params.get("margen", 30)
    afectados = _perdida(raw)
    for d in afectados:
        d["pvp"] = round(d["costo_iva"] * (1 + margen / 100), 2)
    store.guardar(raw)
    store.audit.record(actor=actor, accion="corregir_precio_perdida",
                       antes={"afectados": len(afectados)}, despues={"margen": margen, "version_backup": backup["id"]})
    return {"corregidos": len(afectados), "version_backup": backup["id"],
            "mensaje": f"Listo. Le puse un margen del {margen}% a {len(afectados)} productos que vendías "
                       f"por debajo del costo. Guardé un backup por si querés revertir."}
