"""
Fase del negocio — el sistema define en qué momento está la empresa y, con eso,
qué mostrar. El shell se arma por rol + FASE: la personalización no es sólo "quién
sos" sino "en qué etapa estás". Hoy Horizonte está en `carga_inicial` (datos sin
sanear, sin ventas históricas). Cuando el dato avance, la fase cambia sola y se
desbloquean cosas (p. ej. Economía/Legal) — sin que nadie configure un menú.
"""
from __future__ import annotations

from . import store

def _tiene_ventas() -> bool:
    # Ventas cargadas Y montos confirmados por el dueño: recién ahí el negocio
    # está "en operación". Cargadas sin validar sigue siendo puesta a punto.
    from . import ventas
    return ventas.hay_datos() and ventas.montos_confirmados()


def datos_presentes() -> dict:
    """Qué datos REALES tiene este tenant — la fuente única que consultan los
    copys de desbloqueo (P11·B3): nada le pide al usuario un dato que ya está.
    En el demo (ventas validadas, cuentas del Litoral, WMS/TMS) da todo sí;
    en el piloto sigue diciendo qué falta, como corresponde."""
    from . import ventas, evolucion, deposito, logistica, cuentas
    return {
        "ventas": _tiene_ventas(),
        "ventas_cargadas": ventas.hay_datos(),   # cargadas aunque sin validar
        "evolucion": evolucion.hay_datos(),
        "cuentas": cuentas.hay_datos_reales(),
        "deposito": deposito.hay_datos(),
        "logistica": logistica.hay_datos(),
    }


def actual(lang: str | None = None) -> dict:
    import i18n
    libro = store.libro_triado()
    issues = libro["total_issues"]
    datos = datos_presentes()

    if not _tiene_ventas():
        return {
            "fase": "carga_inicial",
            "titulo": i18n.t("core.fase.titulo_puesta", lang),
            "foco": "saneamiento" if issues > 0 else "cargar",
            "mensaje": (
                i18n.t("core.fase.msj_saneamiento", lang, issues=issues)
                if issues > 0 else
                i18n.t("core.fase.msj_cargar", lang)
            ),
            "datos": datos,
        }

    return {
        "fase": "operacion",
        "titulo": i18n.t("core.fase.titulo_operacion", lang),
        "foco": "panel",
        "mensaje": i18n.t("core.fase.msj_operacion", lang),
        "datos": datos,
    }
