"""
data_store.py · Capa de acceso a datos de PolPilot
==================================================
Expone consultas tipo "SQL-lite" sobre el inventario. Estas funciones alimentan
los endpoints REST y las tools de Ángela.

Desde el Plan 3, la fuente de verdad es el NÚCLEO (`core.store`): este módulo
delega en `core.store.panorama()`, que recomputa todo desde la copia de trabajo.
Así una corrección del saneamiento se refleja en TODO el sistema (no sólo en
/api/calidad). El seam quedó unificado.
"""

from __future__ import annotations

import json
import os
import unicodedata

from core import store as core_store

HERE = os.path.dirname(os.path.abspath(__file__))

# Etiquetas legibles de cada grupo de problemas (para la UI y para Ángela).
# El ES es la fuente histórica; la versión por idioma sale de i18n
# (grupo_label / grupos_disponibles). Los KEYS del dict son IDs: no se traducen.
GRUPOS_LABEL = {
    "fantasmas": "Productos fantasma (anulados con stock vivo)",
    "negativos": "Stock negativo (el sistema miente)",
    "sin_pvp": "Sin precio de venta cargado",
    "balanza": "Balanza con peso teórico fuera de rango",
    "costo_viejo": "Costo desactualizado (más de 1 año)",
}


def grupo_label(grupo: str, lang: str | None = None) -> str:
    """La etiqueta visible de un grupo en el idioma pedido (default 'es',
    byte-igual a GRUPOS_LABEL)."""
    import i18n
    return i18n.t(f"core.grupo.{grupo}", lang) if grupo in GRUPOS_LABEL else grupo


def _strip(s: str) -> str:
    """Normaliza para búsqueda: minúsculas, sin acentos."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def _load() -> dict:
    """Payload completo desde el núcleo de verdad (refleja correcciones)."""
    return core_store.panorama()


def reload_data() -> None:
    core_store.reload()


# ----------------------------------------------------------------------------
# Consultas de alto nivel (usadas por REST y por las tools de Ángela)
# ----------------------------------------------------------------------------

def resumen(lang: str | None = None) -> dict:
    d = _load()
    res = d["resumen"]
    salud = res.get("salud") or {}
    if salud.get("nivel"):
        # El label de salud sale del catálogo por nivel (el nivel es el ID y no
        # cambia). Copias frescas: el panorama del núcleo está cacheado y no se muta.
        import i18n
        res = dict(res)
        res["salud"] = {**salud, "label": i18n.t(f"core.salud.{salud['nivel']}", lang)}
    return {"meta": d["meta"], "resumen": res, "alertas": d["alertas"]}


def meta() -> dict:
    return _load()["meta"]


def top_inmovilizado(n: int = 10) -> list[dict]:
    return _load()["top_inmovilizado"][: max(1, min(n, 50))]


def listar_grupo(grupo: str, limit: int | None = None) -> list[dict]:
    grupos = _load()["grupos"]
    if grupo not in grupos:
        return []
    items = grupos[grupo]
    if grupo == "fantasmas":
        # Mercadería real sin costo: lo relevante es cuántas unidades fantasma hay.
        items = sorted(items, key=lambda r: r.get("stock", 0), reverse=True)
    elif grupo == "negativos":
        # El quiebre de integridad más grave es el más negativo.
        items = sorted(items, key=lambda r: r.get("stock", 0))
    else:
        items = sorted(items, key=lambda r: r.get("inmovilizado", 0), reverse=True)
    return items[:limit] if limit else items


def buscar_productos(texto: str, limit: int = 25) -> list[dict]:
    """Busca artículos cuyo nombre contenga el texto (sin acentos, case-insensitive).
    Enriquecido con la unidad de pricing para que Ángela distinga $/kg de $/u."""
    from core import pricing
    q = _strip(texto)
    if not q:
        return []
    hits = [r for r in _load()["articulos"] if q in _strip(r["descripcion"])]
    hits.sort(key=lambda r: r.get("inmovilizado", 0), reverse=True)
    return [pricing.enriquecer(r) for r in hits[:limit]]


def plata_en(texto: str) -> dict:
    """
    Responde '¿cuánta plata tengo en X?'. Suma el inmovilizado de todos los
    artículos cuyo nombre matchea el texto. Devuelve el total y el desglose.
    """
    hits = buscar_productos(texto, limit=200)
    total = round(sum(r["inmovilizado"] for r in hits), 2)
    unidades = round(sum(r["stock"] for r in hits if r["stock"] > 0), 0)
    desglose = [
        {
            "codigo": r["codigo"],
            "descripcion": r["descripcion"],
            "stock": r["stock"],
            "costo_iva": r["costo_iva"],
            "inmovilizado": r["inmovilizado"],
        }
        for r in hits
        if r["inmovilizado"] > 0
    ][:15]
    return {
        "consulta": texto,
        "coincidencias": len(hits),
        "inmovilizado_total": total,
        "unidades": unidades,
        "desglose": desglose,
    }


def grupos_disponibles(lang: str | None = None) -> dict:
    return {g: grupo_label(g, lang) for g in GRUPOS_LABEL}


# ----------------------------------------------------------------------------
# Oportunidades: la otra cara de las alertas. Plata que se puede capturar.
# Hoy salen de los datos internos; las que cruzan contexto externo
# (economía/precios/legal) quedan como placeholders hasta cargar ese feed.
# ----------------------------------------------------------------------------

def _impacto_grupo(grupo: str) -> float:
    return round(sum(r.get("inmovilizado", 0) for r in _load()["grupos"].get(grupo, [])), 2)


def oportunidades(lang: str | None = None) -> dict:
    """Los textos salen del catálogo i18n (ES verbatim al histórico); los IDs y
    grupos son keys internas y no se traducen."""
    import i18n
    _t = lambda k, **p: i18n.t(k, lang, **p)
    al = _load()["alertas"]
    concretas = [
        {
            "id": "sin_pvp",
            "titulo": _t("core.oport.sin_pvp_titulo"),
            "descripcion": _t("core.oport.sin_pvp_desc", n=al["sin_pvp"]["cantidad"]),
            "impacto_pesos": _impacto_grupo("sin_pvp"),
            "impacto_label": _t("core.oport.sin_pvp_impacto"),
            "accion": _t("core.oport.sin_pvp_accion"),
            "grupo": "sin_pvp",
            "estado": "nueva",
        },
        {
            "id": "balanza",
            "titulo": _t("core.oport.balanza_titulo"),
            "descripcion": _t("core.oport.balanza_desc", n=al["balanza"]["cantidad"]),
            "impacto_pesos": _impacto_grupo("balanza"),
            "impacto_label": _t("core.oport.balanza_impacto"),
            "accion": _t("core.oport.balanza_accion"),
            "grupo": "balanza",
            "estado": "nueva",
        },
    ]

    # Placeholders con diseño real: aparecen cuando FALTA su dato — P11·B3:
    # una tarjeta que pide un dato ya cargado es una mentira de UI.
    from core import fase as _fase_mod
    _datos = _fase_mod.datos_presentes()
    _hay_contexto = bool(contexto_texto_para_prompt(1))
    pendientes = [
        {
            "id": "ventana_compra",
            "titulo": _t("core.oport.ventana_titulo"),
            "descripcion": _t("core.oport.ventana_desc"),
            "falta": _t("core.oport.ventana_falta"),
            "estado": "pendiente_datos",
        },
        {
            "id": "rotacion",
            "titulo": _t("core.oport.rotacion_titulo"),
            "descripcion": _t("core.oport.rotacion_desc"),
            "falta": _t("core.oport.rotacion_falta"),
            "estado": "pendiente_datos",
        },
        {
            "id": "credito",
            "titulo": _t("core.oport.credito_titulo"),
            "descripcion": _t("core.oport.credito_desc"),
            "falta": _t("core.oport.credito_falta"),
            "estado": "pendiente_datos",
        },
    ]
    pendientes = [p for p in pendientes
                  if not (p["id"] == "rotacion" and _datos["ventas"])
                  and not (p["id"] in ("ventana_compra", "credito") and _hay_contexto)]

    return {
        "concretas": sorted(concretas, key=lambda o: o["impacto_pesos"], reverse=True),
        "pendientes": pendientes,
    }


# ----------------------------------------------------------------------------
# Contexto externo cargado a mano (TXT de economía/legal/precios).
# Hasta conectar APIs, alimenta a Ángela para generar oportunidades reales.
# ----------------------------------------------------------------------------

from core import paths as _paths
CONTEXTO_JSON = os.path.join(_paths.DATA_DIR, "contexto.json")


def _contexto_load() -> list[dict]:
    if not os.path.exists(CONTEXTO_JSON):
        return []
    try:
        with open(CONTEXTO_JSON, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def contexto_listar() -> list[dict]:
    # Devuelve metadata sin el cuerpo completo (para la UI).
    return [
        {k: v for k, v in c.items() if k != "texto"} | {"chars": len(c.get("texto", ""))}
        for c in _contexto_load()
    ]


def contexto_agregar(nombre: str, tipo: str, texto: str) -> dict:
    import datetime as _dt

    items = _contexto_load()
    entry = {
        "id": f"ctx-{len(items) + 1}",
        "nombre": nombre,
        "tipo": tipo,
        "cargado": _dt.datetime.now().isoformat(timespec="seconds"),
        "texto": texto,
    }
    items.append(entry)
    with open(CONTEXTO_JSON, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    return {k: v for k, v in entry.items() if k != "texto"} | {"chars": len(texto)}


def contexto_texto_para_prompt(max_chars: int = 4000) -> str:
    """Concatena el contexto cargado para inyectarlo en el system prompt de Ángela."""
    items = _contexto_load()
    if not items:
        return ""
    partes = []
    for c in items:
        partes.append(f"[{c['tipo']} · {c['nombre']}]\n{c['texto']}")
    blob = "\n\n".join(partes)
    return blob[:max_chars]
