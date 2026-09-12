"""
odoo_demo.py · The Odoo connector's SAMPLE transport, for the public demo.

The real connector (conectores.ConectorOdoo + core/odoo_ingest.py) is
production code: XML-RPC against the client's own Odoo, credentials encrypted
at rest. The public demo has no Odoo to point it at, so the Connectors
section showed Odoo as "pendiente" and the whole sync/review/ingest pipeline
— half the product's story — stayed invisible.

This module is the demo's answer, built on the same discipline as
core/extraccion.py's canonical sample documents:

  · EXPLICIT, NEVER A FALLBACK. The sample transport only exists after the
    owner clicks "Conectar Odoo de muestra" (which writes a marker in the
    tenant's DATA_DIR). A configured REAL connection always wins; a failed
    real connection still fails loudly. Nothing here catches an error to
    substitute canned data — that category of fallback was removed from this
    product on purpose and stays removed.
  · ONLY THE TRANSPORT IS CANNED. What the pulls return comes from
    data-demo/odoo_muestra.json (generated deterministically from the demo
    dataset itself by data-demo/generar_odoo_muestra.py). Everything after
    the pull — linking, upserts, staging batches, review, integration,
    audit — is the real pipeline, byte for byte.
  · COHERENT WITH THE DATASET. The sample's products, suppliers and orders
    are the Litoral catalog's own rows (values identical, so the first sync
    is a pure LINK + provenance stamp), plus a handful of genuinely new rows
    that exercise the staging/review flow without polluting the catalog.

Availability is gated by the sample file existing in DATA_DIR (only the demo
dataset ships it) and the HTTP endpoint is additionally gated to the demo
tenant, same belt-and-braces as /api/admin/reset-demo.
"""
from __future__ import annotations

import datetime
import json
import os

from . import esquema, store
from .paths import DATA_DIR

MUESTRA_JSON = os.path.join(DATA_DIR, "odoo_muestra.json")
# Runtime state, never versioned (gitignored like the rest of the live demo
# state): its existence IS the "connected to the sample" switch, and it also
# records exactly what activar() linked so desactivar() can undo precisely.
MARKER_JSON = os.path.join(DATA_DIR, "odoo_demo_conectado.json")


def disponible() -> bool:
    """Whether this tenant ships a sample at all (only the demo dataset does)."""
    return os.path.exists(MUESTRA_JSON)


def activo() -> bool:
    return disponible() and os.path.exists(MARKER_JSON)


def payloads() -> dict:
    with open(MUESTRA_JSON, encoding="utf-8") as fh:
        return json.load(fh)


def _marker() -> dict:
    try:
        with open(MARKER_JSON, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def estado() -> dict:
    m = _marker()
    return {
        "disponible": disponible(),
        "activo": activo(),
        "activado": m.get("activado"),
        "actor": m.get("actor"),
    }


def _vincular_productos(vinculos: list[dict], actor: str) -> int:
    """Stamp provenance (source/source_id/sku) on the catalog rows the sample
    maps to existing products. Values are untouched: the sample carries the
    dataset's own numbers, so this is linkage, not data change. Goes through
    store.guardar + the audit log like every other catalog write."""
    raw = store.raw_actual()
    por_codigo = {d.get("codigo"): d for d in raw}
    linked = 0
    antes, despues = [], []
    for v in vinculos:
        d = por_codigo.get(v["codigo"])
        if not d or d.get("source") == "odoo":
            continue
        antes.append({"codigo": d.get("codigo"), "source": d.get("source"),
                      "source_id": d.get("source_id")})
        d["source"] = "odoo"
        d["source_id"] = str(v["source_id"])
        if v.get("sku") and not d.get("sku"):
            d["sku"] = v["sku"]
        despues.append({"codigo": d.get("codigo"), "source": "odoo",
                        "source_id": d["source_id"]})
        linked += 1
    if linked:
        store.guardar(raw)
        store.audit.record(actor, "vincular_articulos_odoo_muestra",
                           {"articulos": antes}, {"articulos": despues})
    return linked


def _vincular_proveedores(vinculos: list[dict], actor: str) -> int:
    from . import proveedores as proveedores_mod
    from .audit import AuditLog
    filas = esquema.filas(proveedores_mod._TIPO)
    por_nombre = { (f.get("nombre") or "").strip().lower(): f for f in filas }
    linked, nombres = 0, []
    for v in vinculos:
        f = por_nombre.get((v["nombre"] or "").strip().lower())
        if not f or f.get("source") == "odoo":
            continue
        f["source"] = "odoo"
        f["source_id"] = str(v["source_id"])
        nombres.append(v["nombre"])
        linked += 1
    if linked:
        esquema.reemplazar_filas(proveedores_mod._TIPO, filas)
        AuditLog().record(actor, "vincular_proveedores_odoo_muestra", None,
                          {"proveedores": nombres})
    return linked


def _desvincular(actor: str) -> dict:
    """Undo exactly what activar() linked (recorded in the marker), so
    disconnecting the sample leaves the catalog as it was."""
    m = _marker()
    from . import proveedores as proveedores_mod
    from .audit import AuditLog
    n_prod = 0
    codigos = set(m.get("productos_vinculados") or [])
    if codigos:
        raw = store.raw_actual()
        for d in raw:
            if d.get("codigo") in codigos and d.get("source") == "odoo":
                d.pop("source", None)
                d.pop("source_id", None)
                n_prod += 1
        if n_prod:
            store.guardar(raw)
    n_prov = 0
    nombres = {x.strip().lower() for x in (m.get("proveedores_vinculados") or [])}
    if nombres:
        filas = esquema.filas(proveedores_mod._TIPO)
        for f in filas:
            if ((f.get("nombre") or "").strip().lower() in nombres
                    and f.get("source") == "odoo"):
                f.pop("source", None)
                f.pop("source_id", None)
                n_prov += 1
        if n_prov:
            esquema.reemplazar_filas(proveedores_mod._TIPO, filas)
    if n_prod or n_prov:
        AuditLog().record(actor, "desvincular_odoo_muestra", None,
                          {"productos": n_prod, "proveedores": n_prov})
    return {"productos": n_prod, "proveedores": n_prov}


def activar(actor: str) -> dict:
    """Link the mapped catalog/supplier rows and flip the sample transport on.

    Raises on a tenant with no sample — the caller decides how that surfaces
    (the endpoint 404s before ever getting here on a non-demo tenant)."""
    if not disponible():
        raise ValueError("This tenant ships no Odoo sample (odoo_muestra.json).")
    data = payloads()
    vinculos = data.get("vinculos") or {}
    n_prod = _vincular_productos(vinculos.get("productos") or [], actor)
    n_prov = _vincular_proveedores(vinculos.get("proveedores") or [], actor)
    marker = {
        "activado": datetime.datetime.now().isoformat(timespec="seconds"),
        "actor": actor,
        "productos_vinculados": [v["codigo"] for v in
                                 (vinculos.get("productos") or [])],
        "proveedores_vinculados": [v["nombre"] for v in
                                   (vinculos.get("proveedores") or [])],
    }
    with open(MARKER_JSON, "w", encoding="utf-8") as fh:
        json.dump(marker, fh, ensure_ascii=False, indent=1)
    from . import analisis_cache
    analisis_cache.datos_cambiaron()
    return {"productos_vinculados": n_prod, "proveedores_vinculados": n_prov}


def desactivar(actor: str) -> dict:
    out = _desvincular(actor)
    try:
        os.remove(MARKER_JSON)
    except OSError:
        pass
    from . import analisis_cache
    analisis_cache.datos_cambiaron()
    return out
