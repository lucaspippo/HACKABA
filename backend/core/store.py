from __future__ import annotations

import datetime
import json
import os
import statistics
from functools import lru_cache

from .audit import AuditLog
from .models import Articulo
from .versioning import VersionStore
from . import paths
from . import quality
from . import pricing

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = paths.DATA_DIR  # por-tenant: env POLPILOT_DATA_DIR o data/ (ver core/paths.py)
# ORIGINAL catalog, immutable on disk (generar.py produces it) — the seed the
# Postgres working copy (inventory_working, see core/db/inventory_repo.py)
# starts from the first time a tenant is touched, and the one
# resetear_actual() reverts to. Same role data-demo/cuentas.json plays for
# core/cuentas.py — see core/db/MIGRATING_A_MODULE.md.
INVENTORY_JSON = os.path.join(DATA_DIR, "inventory.json")

versiones = VersionStore(DATA_DIR)
audit = AuditLog(DATA_DIR)


def _load_seed() -> list[dict]:
    with open(INVENTORY_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return data["articulos"]


@lru_cache(maxsize=1)
def _cache_raw() -> tuple:
    """Raw article list (dicts), from the Postgres working copy — seeded
    once from INVENTORY_JSON if the tenant has no row yet."""
    from core.db import inventory_repo
    from core.db import tenant as _tenant
    tid = _tenant.current_tenant_id()
    articulos = inventory_repo.get_articles(tid)
    if articulos is None:
        articulos = _load_seed()
        inventory_repo.save_articles(tid, articulos)
    # tuple para que sea hasheable bajo lru_cache; se reconvierte a list al leer.
    return tuple(json.dumps(d) for d in articulos)


def raw_actual() -> list[dict]:
    return [json.loads(s) for s in _cache_raw()]


def articulos() -> list[Articulo]:
    return [Articulo.from_dict(d) for d in raw_actual()]


_panorama_cache: dict | None = None


def guardar(raw: list[dict]) -> None:
    """Persiste la copia de trabajo y refresca los caches."""
    global _panorama_cache
    from core.db import inventory_repo
    from core.db import tenant as _tenant
    inventory_repo.save_articles(_tenant.current_tenant_id(), raw)
    _cache_raw.cache_clear()
    _panorama_cache = None
    from . import analisis_cache
    analisis_cache.datos_cambiaron()


_CAMPOS_ARTICULO = ("descripcion", "estado", "tipo", "proveedor", "um",
                     "venta_x_peso", "cota_inf", "cota_sup", "valor_peso",
                     "stock", "costo_iva", "pvp")


def _recalcular_inmovilizado(d: dict) -> None:
    """`inmovilizado` no se deriva al leer (queda guardado en la fila, como lo
    dejó generar.py) — cualquier escritura manual de stock/costo tiene que
    recalcularlo ella misma o el número queda mintiendo silenciosamente."""
    d["inmovilizado"] = round((d.get("stock") or 0) * (d.get("costo_iva") or 0), 2)


def crear_articulo(datos: dict, actor: str) -> dict:
    """Alta manual de un producto (no viene de un CSV ni de una foto)."""
    codigo = datos.get("codigo")
    if not codigo:
        raise ValueError("codigo_requerido")
    if not datos.get("descripcion"):
        raise ValueError("descripcion_requerida")
    raw = raw_actual()
    if any(d.get("codigo") == codigo for d in raw):
        raise ValueError("codigo_duplicado")
    nuevo = {"codigo": codigo, "estado": "activo", **{k: datos.get(k) for k in _CAMPOS_ARTICULO}}
    nuevo["descripcion"] = datos["descripcion"]
    _recalcular_inmovilizado(nuevo)
    raw.append(nuevo)
    guardar(raw)
    audit.record(actor, "crear_articulo", None,
                  {"codigo": codigo, "descripcion": nuevo["descripcion"]})
    return nuevo


def actualizar_articulo(codigo: int, cambios: dict, actor: str) -> dict:
    """Edición manual de campos existentes (precio, costo, categoría,
    proveedor...) — distinto del saneamiento automático, que sólo corrige las
    dos categorías auto-aplicables (fantasma, balanza)."""
    raw = raw_actual()
    for d in raw:
        if d.get("codigo") == codigo:
            antes = dict(d)
            d.update({k: v for k, v in cambios.items() if k in _CAMPOS_ARTICULO})
            if "stock" in cambios or "costo_iva" in cambios:
                _recalcular_inmovilizado(d)
            guardar(raw)
            audit.record(actor, "editar_articulo", antes, d)
            return d
    raise KeyError(codigo)


def eliminar_articulo(codigo: int, actor: str) -> None:
    raw = raw_actual()
    quedan = [d for d in raw if d.get("codigo") != codigo]
    if len(quedan) == len(raw):
        raise KeyError(codigo)
    borrado = next(d for d in raw if d.get("codigo") == codigo)
    guardar(quedan)
    audit.record(actor, "eliminar_articulo", borrado, None)


def buscar_por_source(source: str, source_id: str) -> dict | None:
    return next((d for d in raw_actual()
                 if d.get("source") == source and d.get("source_id") == source_id), None)


def upsert_desde_conector(fila: dict, actor: str) -> dict:
    """Create-or-update a product coming from an external connector (e.g.
    Odoo), as opposed to crear_articulo/actualizar_articulo (the dueño's
    manual edits): it resolves the internal codigo automatically and accepts
    the provenance fields (source, source_id, sku). Used both for the
    auto-upsert of already-linked products (core/odoo_ingest.py) and when
    integrating a Staging batch of new products."""
    raw = raw_actual()
    existente = next((d for d in raw if d.get("source") == fila["source"]
                       and d.get("source_id") == fila["source_id"]), None)
    if existente:
        antes = dict(existente)
        for campo in ("descripcion", "sku", "stock", "costo_iva", "pvp",
                      "free_qty", "incoming_qty", "outgoing_qty", "estado",
                      "pricing_status", "precio_lista", "moneda", "precios_pricelist"):
            if campo in fila:
                existente[campo] = fila[campo]
        _recalcular_inmovilizado(existente)
        guardar(raw)
        audit.record(actor, "actualizar_articulo_conector", antes, existente)
        return existente
    siguiente = max([d.get("codigo", 0) for d in raw] + [0]) + 1
    nuevo = {
        "codigo": siguiente, "descripcion": fila["descripcion"],
        "estado": fila.get("estado") or "activo",
        "stock": fila.get("stock") or 0, "costo_iva": fila.get("costo_iva"),
        "pvp": fila.get("pvp"), "venta_x_peso": False,
        "sku": fila.get("sku"), "source": fila["source"], "source_id": fila["source_id"],
        "free_qty": fila.get("free_qty"),
        "incoming_qty": fila.get("incoming_qty"),
        "outgoing_qty": fila.get("outgoing_qty"),
        "pricing_status": fila.get("pricing_status"),
        "precio_lista": fila.get("precio_lista"),
        "moneda": fila.get("moneda"),
        "precios_pricelist": fila.get("precios_pricelist") or [],
    }
    _recalcular_inmovilizado(nuevo)
    raw.append(nuevo)
    guardar(raw)
    audit.record(actor, "crear_articulo_conector", None, nuevo)
    return nuevo


def resetear_actual() -> None:
    """Descarta las correcciones y vuelve al inventory.json original."""
    global _panorama_cache
    from core.db import inventory_repo
    from core.db import tenant as _tenant
    inventory_repo.save_articles(_tenant.current_tenant_id(), _load_seed())
    _cache_raw.cache_clear()
    _panorama_cache = None
    from . import analisis_cache
    analisis_cache.datos_cambiaron()


def libro_triado(lang: str | None = None) -> dict:
    return quality.libro_triado(articulos(), lang)


def reload() -> None:
    global _panorama_cache
    _cache_raw.cache_clear()
    _panorama_cache = None
    from . import analisis_cache
    analisis_cache.datos_cambiaron()
    _cache_raw()


# ---------------------------------------------------------------------------
# Panorama: el payload completo (resumen + alertas + top + grupos) recomputado
# desde la copia de trabajo. Es la fuente única que unifica el seam: cuando el
# saneamiento corrige algo, todo el sistema lo refleja (no sólo /api/calidad).
# ---------------------------------------------------------------------------

def _stat(grupo: list[dict]) -> dict:
    return {
        "cantidad": len(grupo),
        "impacto_pesos": round(sum(d.get("inmovilizado") or 0 for d in grupo), 2),
        "unidades": round(sum(d.get("stock") or 0 for d in grupo), 0),
    }


def _compute_panorama() -> dict:
    raw = raw_actual()
    grupos = {k: [] for k in ("fantasmas", "negativos", "sin_pvp", "balanza", "costo_viejo")}
    plural = {
        "fantasma": "fantasmas", "negativo": "negativos", "sin_precio": "sin_pvp",
        "balanza": "balanza", "costo_viejo": "costo_viejo",
    }
    for d in raw:
        for issue in quality.clasificar(Articulo.from_dict(d)):
            grupos[plural[issue.categoria.value]].append(d)

    activos = [d for d in raw if d.get("estado", "activo") != "anulado"]
    anulados = [d for d in raw if d.get("estado") == "anulado"]
    con_stock_pos = [d for d in raw if (d.get("stock") or 0) > 0]
    inmovilizado_total = round(sum(d.get("inmovilizado") or 0 for d in raw), 2)
    antig = [d["antiguedad_costo_dias"] for d in activos if d.get("antiguedad_costo_dias") is not None]

    # Orden de cada grupo (igual que data_store): por unidades o por plata.
    grupos["fantasmas"].sort(key=lambda d: d.get("stock") or 0, reverse=True)
    grupos["negativos"].sort(key=lambda d: d.get("stock") or 0)
    for k in ("sin_pvp", "balanza", "costo_viejo"):
        grupos[k].sort(key=lambda d: d.get("inmovilizado") or 0, reverse=True)

    # P38·A — "Datos a corregir" cuenta REGISTROS, no incidencias: un producto
    # con dos problemas es un producto a corregir, no dos. Este número es la
    # fuente única del badge del sidebar, del filtro de la tabla de stock y del
    # contador del Inicio — antes cada pantalla lo sumaba a mano y el costo
    # viejo quedaba afuera del badge pero adentro de la sección.
    a_corregir = len({d.get("codigo") for k in
                      ("fantasmas", "negativos", "sin_pvp", "balanza", "costo_viejo")
                      for d in grupos[k]})

    problemas = sum(len(grupos[k]) for k in ("fantasmas", "negativos", "sin_pvp", "balanza"))
    if problemas > 300:
        salud = {"nivel": "requiere_accion", "label": "Requiere acción urgente"}
    elif problemas > 100:
        salud = {"nivel": "atencion", "label": "Atención requerida"}
    else:
        salud = {"nivel": "en_orden", "label": "En orden"}

    top = sorted(con_stock_pos, key=lambda d: d.get("inmovilizado") or 0, reverse=True)[:25]
    negativos_stat = _stat(grupos["negativos"])

    return {
        "meta": {
            "empresa": paths.EMPRESA,   # por tenant: piloto o demo (ver core/paths.py)
            "fuente": paths.FUENTE,
            "generado": datetime.datetime.now().isoformat(timespec="seconds"),
            "total_articulos": len(raw),
        },
        "resumen": {
            "inmovilizado_total": inmovilizado_total,
            "total_articulos": len(raw),
            "activos": len(activos),
            "anulados": len(anulados),
            "con_costo": len([d for d in activos if d.get("costo_iva")]),
            "stock_positivo": len(con_stock_pos),
            "stock_cero": len([d for d in raw if (d.get("stock") or 0) == 0]),
            "stock_negativo": len(grupos["negativos"]),
            "unidades_stock_positivo": round(sum(d.get("stock") or 0 for d in con_stock_pos), 0),
            "antiguedad_mediana_costo_dias": round(statistics.median(antig), 0) if antig else None,
            "a_corregir": a_corregir,
            "salud": salud,
        },
        "alertas": {
            "fantasmas": _stat(grupos["fantasmas"]),
            "negativos": negativos_stat,
            "sin_pvp": _stat(grupos["sin_pvp"]),
            "balanza": _stat(grupos["balanza"]),
            "costo_viejo": _stat(grupos["costo_viejo"]),
        },
        "top_inmovilizado": top,
        "grupos": grupos,
        "articulos": raw,
    }


def panorama() -> dict:
    """Payload completo recomputado desde la copia de trabajo (cacheado)."""
    global _panorama_cache
    if _panorama_cache is None:
        _panorama_cache = _compute_panorama()
    return _panorama_cache


# Prioridad para elegir el "estado de calidad" principal de un artículo (peor primero).
_ESTADO_PRIORIDAD = ["negativo", "fantasma", "balanza", "sin_precio", "costo_viejo"]


def articulos_con_estado() -> list[dict]:
    """Todos los artículos con su estado de calidad principal, para la tabla
    'ver todo' del inventario. estado_calidad ∈ {ok, fantasma, negativo,
    sin_precio, balanza, costo_viejo}."""
    out = []
    for d in raw_actual():
        cats = {i.categoria.value for i in quality.clasificar(Articulo.from_dict(d))}
        estado_cal = next((c for c in _ESTADO_PRIORIDAD if c in cats), "ok")
        out.append({
            "codigo": d.get("codigo"),
            "descripcion": d.get("descripcion"),
            "estado": d.get("estado", "activo"),
            "stock": d.get("stock") or 0,
            "costo_iva": d.get("costo_iva"),
            "pvp": d.get("pvp"),
            "inmovilizado": d.get("inmovilizado") or 0,
            "estado_calidad": estado_cal,
            # Pricing consciente de unidad: la tabla distingue balanza ($/kg) de unidad.
            "unidad_pricing": pricing.unidad(d),
            "label_precio": pricing.label_precio(d),
            "margen_pct": pricing.margen_pct(d),
            "margen_venta_pct": pricing.margen_sobre_venta_pct(d),
            "margen_pesos": pricing.margen_pesos(d),
            # P38·G — un pesable son tres cosas: kilos, PIEZAS y el precio de
            # una pieza. La tabla de stock las muestra juntas donde aplica.
            "peso_por_unidad": pricing.peso_por_unidad(d),
            "unidades": pricing.unidades_de(d),
            "precio_por_unidad": pricing.precio_por_unidad(d),
            "source": d.get("source"),
            "source_id": d.get("source_id"),
            "sku": d.get("sku"),
            "tipo": d.get("tipo"),
            "proveedor": d.get("proveedor"),
            "free_qty": d.get("free_qty"),
            "incoming_qty": d.get("incoming_qty"),
            "outgoing_qty": d.get("outgoing_qty"),
            "pricing_status": d.get("pricing_status"),
            "precio_lista": d.get("precio_lista"),
            "moneda": d.get("moneda"),
        })
    return out


_PRODUCT_SEARCH = ("descripcion", "codigo", "sku", "source", "tipo", "proveedor")
_PRODUCT_CSV = ("codigo", "sku", "descripcion", "stock", "costo_iva", "pvp",
                "margen_venta_pct", "margen_pesos",
                "estado", "estado_calidad", "source")


def _filtered_articles(*, q: str = "", sort: str | None = "descripcion",
                       direction: str = "asc", source: str | None = None,
                       filtro: str | None = None, err: str | None = None) -> list[dict]:
    from . import paging, section_records
    rows = articulos_con_estado()
    if filtro == "ok":
        rows = [r for r in rows if r.get("estado_calidad") == "ok"]
    elif filtro == "balanza":
        rows = [r for r in rows if r.get("unidad_pricing") == "kg"]
    elif filtro == "a_corregir":
        rows = [r for r in rows if r.get("estado_calidad") != "ok"]
        if err and err != "todos":
            rows = [r for r in rows if r.get("estado_calidad") == err]
    rows = section_records.match_source(rows, source)
    return paging.filter_sort(
        rows, q=q, search_in=_PRODUCT_SEARCH, sort=sort, direction=direction)


def list_page(*, q: str = "", sort: str | None = "descripcion", direction: str = "asc",
              offset: int = 0, limit: int = 50, source: str | None = None,
              filtro: str | None = None, err: str | None = None) -> dict:
    from . import paging
    rows = _filtered_articles(q=q, sort=sort, direction=direction, source=source,
                              filtro=filtro, err=err)
    return paging.page_rows(rows, offset=offset, limit=limit)


def export_csv(*, q: str = "", sort: str | None = "descripcion", direction: str = "asc",
               source: str | None = None, filtro: str | None = None,
               err: str | None = None) -> str:
    from . import paging
    rows = _filtered_articles(q=q, sort=sort, direction=direction, source=source,
                              filtro=filtro, err=err)
    return paging.rows_to_csv(rows, _PRODUCT_CSV)


def articulos_balanza() -> list[dict]:
    """Productos que se venden por peso (venta_x_peso). Su propia categoría: kg y $/kg."""
    out = []
    for d in raw_actual():
        if not d.get("venta_x_peso"):
            continue
        out.append({
            "codigo": d.get("codigo"),
            "descripcion": d.get("descripcion"),
            "estado": d.get("estado", "activo"),
            "stock": d.get("stock") or 0,       # interpretado en kg
            "costo_iva": d.get("costo_iva"),
            "pvp": d.get("pvp"),                # interpretado en $/kg
            "valor_peso": d.get("valor_peso"),
            "cota_inf": d.get("cota_inf"),
            "cota_sup": d.get("cota_sup"),
            "inmovilizado": d.get("inmovilizado") or 0,
            # P38·G — las tres lecturas del pesable, juntas
            "peso_por_unidad": pricing.peso_por_unidad(d),
            "unidades": pricing.unidades_de(d),
            "precio_por_unidad": pricing.precio_por_unidad(d),
        })
    return out
