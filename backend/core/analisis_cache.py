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
        # EL MAPA Y LAS PRIORIDADES TAMBIÉN. Medido: en frío el mapa tardaba
        # 5,2 s y prioridades 14,7 s — y son las dos primeras pantallas del
        # guion. Que las pague el arranque es la diferencia entre entrar y
        # esperar quince segundos con el proyector encendido.
        try:
            # la escena del reclamo: es la primera pantalla del demo y la
            # transición desde el mapa tiene que ser instantánea
            from . import escena as _escena
            get_o_computar("escena_reclamo", lang, lambda l=lang: _escena.reclamo(l))
        except Exception:  # noqa: BLE001
            pass
        try:
            from . import mapa_operacion as _mapa
            get_o_computar("mapa_operacion", lang, lambda l=lang: _mapa.mapa(l))
        except Exception:  # noqa: BLE001 — el precalc nunca rompe el arranque
            pass
        try:
            # `inbox` ya cachea su parte cara bajo la llave "prioridades" y
            # recorta por rol en cada request. Se la llama a ella y no a
            # `_compose` para no tener dos caminos que llenen la misma llave.
            from . import priorities as _prio
            _prio.inbox(lang, None)
        except Exception:  # noqa: BLE001
            pass
        # LO QUE USA ÁNGELA CUANDO LE PREGUNTAN DE VERDAD.
        # Medido con un proceso ya precalentado, el tiempo que tardaba cada
        # herramienta EN CALIENTE: consultar_cruces 2,0 s · capital_recuperable
        # 1,4 s · consultar_evolucion 0,98 s · cuentas_corrientes 0,81 s ·
        # consultar_deposito 0,70 s. Eran segundos de reloj que no los ponía el
        # modelo: los poníamos nosotros recomputando en la tool lo que la
        # pantalla equivalente ya leía del cache. Las tools ahora pasan por
        # estas mismas llaves (ver angela._run_tool) y acá se llenan al
        # arrancar, así la PRIMERA pregunta del jurado ya las encuentra hechas.
        for llave, hacer in (
            ("cruces", lambda l=lang: __import__(
                "core.cruces", fromlist=["cards"]).cards(l)),
            ("oportunidades", lambda l=lang: __import__(
                "core.oportunidades_neg", fromlist=["cards"]).cards(l)),
            ("cuentas_panorama", lambda: _panorama_cuentas()),
            ("deposito_resumen", lambda: _resumen_deposito()),
        ):
            try:
                get_o_computar(llave, lang, hacer)
            except Exception:  # noqa: BLE001 — el precalc nunca rompe el arranque
                pass


def _panorama_cuentas() -> dict:
    """El mismo compuesto que arma la tool `cuentas_corrientes` sin cliente."""
    from . import cuentas
    return {"totales": cuentas.totales(), "clientes": cuentas.listar(),
            "morosos": cuentas.morosos(), "alertas": cuentas.alertas()}


def _resumen_deposito() -> dict:
    from . import deposito
    return deposito.resumen()
