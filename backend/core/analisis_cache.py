"""
P11·B4 — Cache en memoria de los análisis caros (/api/analisis, /api/evolucion).

Antes, cada entrada a Oportunidades recomputaba TODO (rotación + estacionalidad
sobre ~10k filas de ventas + push/pull que las recalcula de nuevo): 5-8 segundos
y CPU al pedo, con YC entrando por la URL pública. Ahora:

- get_o_computar(): sirve del cache; computa solo la primera vez.
- datos_cambiaron(): EL único hook de invalidación. Lo llaman los choke points
  de persistencia (store.guardar, esquema._save, cuentas._save, ventas), no los
  endpoints: cualquier mutación —confirmar un comprobante, aplicar una
  corrección, integrar staging, validar ventas, restaurar una versión—
  invalida sola, venga por donde venga.
- precalentar(): corre al arrancar el server (lifespan) en ambos idiomas:
  la primera entrada en cámara ya es instantánea.

Solo memoria de proceso, sin archivo: los análisis son funciones puras de
(datos, idioma, fechas.hoy()), así que un hit es byte-igual a recomputar, y no
hay estado que se filtre entre tests o sobreviva stale a un redeploy. La fecha
va en la key: un server que cruza la medianoche no sirve el "hoy" de ayer.
"""
from __future__ import annotations

import threading
from typing import Callable

from . import fechas

_lock = threading.Lock()
_gen = 0                                # generación de datos: bump = invalida todo
_cache: dict[tuple, tuple] = {}         # (nombre, lang, fecha) -> (gen, valor)


def get_o_computar(nombre: str, lang: str | None, fn: Callable[[], dict]) -> dict:
    lang = lang or "es"
    key = (nombre, lang, fechas.hoy().isoformat())
    with _lock:
        hit = _cache.get(key)
        if hit and hit[0] == _gen:
            return hit[1]
        gen_al_computar = _gen
    valor = fn()                        # computar FUERA del lock (es lo caro)
    with _lock:
        if _gen == gen_al_computar:     # si nadie mutó mientras tanto, guardar
            _cache[key] = (_gen, valor)
    return valor


def datos_cambiaron() -> None:
    """El único hook: los datos del tenant cambiaron → todo el cache muere."""
    global _gen
    with _lock:
        _gen += 1
        _cache.clear()


def limpiar() -> None:
    """Alias para tests (conftest): mismo efecto que una mutación."""
    datos_cambiaron()


def precalentar() -> None:
    """Precálculo al arrancar (lifespan): ambos análisis, ambos idiomas.
    Un tenant sin ventas validadas devuelve el guard barato al instante,
    así que en el piloto esto no cuesta nada."""
    from . import evolucion as _evolucion
    from . import analisis as _analisis
    from . import grafo as _grafo
    for lang in ("es", "en"):
        get_o_computar("analisis", lang, lambda l=lang: _analisis.completo(l))
        get_o_computar("evolucion", lang, lambda l=lang: _evolucion.panorama(l))
        # el Cerebro cruza 10 años de canastas para la co-venta: ~5s la primera
        # vez. Que los pague el arranque y no el que abre la vista en la demo.
        get_o_computar("grafo", lang, lambda l=lang: _grafo.completo(l))
