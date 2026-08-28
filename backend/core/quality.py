from __future__ import annotations

from .models import (
    Articulo,
    Categoria,
    EstadoCalidad,
    Issue,
    CATEGORIA_ESTADO,
    PRIORIDAD,
)

UMBRAL_COSTO_VIEJO_DIAS = 365


def _issue(a: Articulo, cat: Categoria, impacto: float, detalle: str) -> Issue:
    return Issue(a.codigo, cat, CATEGORIA_ESTADO[cat], round(impacto, 2), detalle)


def clasificar(a: Articulo) -> list[Issue]:
    """Devuelve todos los problemas de calidad de un artículo (puede tener varios)."""
    issues: list[Issue] = []

    if a.estado == "anulado" and a.stock > 0:
        issues.append(_issue(a, Categoria.FANTASMA, 0.0,
                             f"Anulado con {a.stock:g} en stock"))

    if a.stock < 0:
        issues.append(_issue(a, Categoria.NEGATIVO, 0.0,
                             f"Stock negativo: {a.stock:g}"))

    if a.estado == "activo" and a.pricing_status == "needs_pricing":
        issues.append(_issue(a, Categoria.SIN_PRECIO, a.inmovilizado,
                             "Activo sin precio de venta (needs pricing)"))
    elif a.estado == "activo" and not a.pvp and a.pricing_status != "wholesale_only":
        issues.append(_issue(a, Categoria.SIN_PRECIO, a.inmovilizado,
                             "Activo sin precio de venta"))

    if (a.estado == "activo" and a.venta_x_peso and a.cota_inf and a.cota_sup
            and a.valor_peso and a.cota_inf > 0 and a.cota_sup > 0
            and a.valor_peso > 0
            and (a.valor_peso < a.cota_inf or a.valor_peso > a.cota_sup)):
        issues.append(_issue(a, Categoria.BALANZA, a.inmovilizado,
                             f"Peso {a.valor_peso:g} fuera de "
                             f"[{a.cota_inf:g}, {a.cota_sup:g}]"))

    if (a.estado == "activo" and a.antiguedad_costo_dias
            and a.antiguedad_costo_dias > UMBRAL_COSTO_VIEJO_DIAS):
        issues.append(_issue(a, Categoria.COSTO_VIEJO, a.inmovilizado,
                             f"Costo de hace {int(a.antiguedad_costo_dias)} días"))

    return issues


def estado_general(issues: list[Issue]) -> EstadoCalidad:
    """El color del registro: el peor estado entre sus issues."""
    if not issues:
        return EstadoCalidad.COMPLETO
    return max((i.estado for i in issues), key=lambda e: PRIORIDAD[e])


def libro_triado(articulos: list[Articulo], lang: str | None = None) -> dict:
    """El reemplazo de las '541 alertas': issues agrupados por categoría,
    con cantidad e impacto en $, ordenados por plata afectada.

    `lang`: idioma de los textos visibles (label / estado_label). Los IDs
    (`categoria`, `estado`) NUNCA cambian — la UI los usa para colores y filtros.
    Default None → 'es', byte-igual al histórico (CATEGORIA_LABEL)."""
    import i18n
    por_categoria: dict[str, dict] = {}
    for a in articulos:
        for issue in clasificar(a):
            grupo = por_categoria.setdefault(issue.categoria.value, {
                "categoria": issue.categoria.value,
                "label": i18n.t(f"core.calidad.{issue.categoria.value}", lang),
                "estado": issue.estado.value,
                "estado_label": i18n.t(f"core.calidad.estado_{issue.estado.value}", lang),
                "cantidad": 0,
                "impacto_pesos": 0.0,
            })
            grupo["cantidad"] += 1
            grupo["impacto_pesos"] = round(grupo["impacto_pesos"] + issue.impacto_pesos, 2)

    grupos = sorted(por_categoria.values(),
                    key=lambda g: g["impacto_pesos"], reverse=True)
    return {
        "grupos": grupos,
        "total_issues": sum(g["cantidad"] for g in grupos),
        "impacto_total": round(sum(g["impacto_pesos"] for g in grupos), 2),
    }
