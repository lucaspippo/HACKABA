"""
avisos_oficio.py — los avisos que cada oficio deja, como botones.

EL PROBLEMA QUE RESUELVE. «Nota — agregar información» es un campo de texto
libre que nace sin destinatario y se muere: es exactamente el objeto que el
modelo de flujo marcó como roto. Un chofer parado en la puerta de un cliente que
no está no escribe un párrafo; toca «El cliente no estaba» y sigue. La escritura
libre no desaparece — pasa a ser la última opción, detrás del micrófono, en vez
de la primera.

DE DÓNDE SALE LA LISTA. De `data-demo/avisos_por_oficio.json`, sembrada y
etiquetada. Casi todo ahí es HIPÓTESIS sobre cómo trabaja la gente y está dicho
en el archivo: PolPilot no tiene usuarios activos todavía. La única lista que no
lo es son los cuatro motivos de recepción, que ya valida `core/piso.py`.

EL OFICIO SE SACA DEL TEXTO DEL ROL, no del username. Mismo criterio que
`lib/roles.js` y que `piso.DESTINO`: una persona nueva con el mismo puesto
hereda sus avisos sin tocar código, y un tenant que nombre distinto sus puestos
se queda sin botones en vez de romperse. Las dos tablas de regex —ésta y la del
front— están pinneadas por tests contra el mismo equipo demo, que es lo que hace
que la duplicación se note el día que una de las dos se mueva.

`destino_probable` es lo que Ángela PROPONE. Se resuelve a un username real acá
o se devuelve vacío: la pantalla nunca inventa a quién le llega, y un aviso sin
destino resuelto cae en la propuesta por tipo de `piso.destinatario_sugerido`.
"""
from __future__ import annotations

import json
import os
import re

from . import paths

AVISOS_JSON = os.path.join(paths.DATA_DIR, "avisos_por_oficio.json")

# rol (TEXTO) → oficio. El orden importa: los cinco del depósito van ANTES que
# la red genérica, igual que en lib/roles.js.
OFICIOS: tuple[tuple[str, str], ...] = (
    ("deposito_encargado", r"encargad[oa].*dep[oó]sito|jefe.*dep[oó]sito"),
    ("deposito_recepcion", r"dep[oó]sito.*recepci"),
    ("deposito_conteos", r"dep[oó]sito.*conteo"),
    ("deposito_armado", r"dep[oó]sito.*armado"),
    ("deposito_ayudante", r"dep[oó]sito.*ayudante"),
    ("reparto", r"reparto|chofer"),
    ("preventa", r"preventista|vendedor"),
    ("mostrador", r"mostrador"),
    ("sucursal", r"sucursal"),
)


def oficio_de(rol: str | None) -> str | None:
    """El id del oficio de un puesto, o None si no matchea ninguno."""
    for oficio, patron in OFICIOS:
        if re.search(patron, rol or "", re.I):
            return oficio
    return None


def _seed() -> dict:
    if not os.path.exists(AVISOS_JSON):
        return {}
    try:
        with open(AVISOS_JSON, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:  # noqa: BLE001
        return {}


def _texto(a: dict, lang: str | None) -> str:
    return (a.get("texto_en") if (lang or "es") == "en" else None) or a.get("texto") or ""


def _resolver_destino(nombre: str | None) -> str | None:
    """El username real detrás de `destino_probable`, o None.

    `preventista_del_cliente` NO se puede resolver: el dataset no une un cliente
    con su preventista, y elegir uno de los dos que hay sería inventarlo. Se
    devuelve vacío y el aviso cae en la propuesta por tipo — que existe, es
    determinista, y no le miente a nadie sobre quién lo va a leer.
    """
    if not nombre:
        return None
    import auth
    return nombre if nombre in auth.USUARIOS else None


def de(rol: str | None, lang: str | None = None) -> dict:
    """Los avisos de ese puesto, listos para pintar como botones.

    Devuelve siempre la misma forma. Un oficio sin lista —administración,
    compras, el dueño— no es un error: son oficinas, escriben en vez de avisar
    desde el piso, y así está declarado en la semilla.
    """
    d = _seed()
    oficio = oficio_de(rol)
    bloque = (d.get("oficios") or {}).get(oficio or "") or {}
    avisos = []
    for a in bloque.get("avisos") or []:
        destino = _resolver_destino(a.get("destino_probable"))
        avisos.append({
            "id": a.get("id"),
            "texto": _texto(a, lang),
            "tipo": a.get("tipo"),
            "motivo": a.get("motivo"),
            "necesita": list(a.get("necesita") or []),
            "destinatario": destino,
            # Se dice cuándo NO hay regla, en vez de tapar el hueco con
            # cualquiera: es la diferencia entre "va a Celeste" y "va a alguien".
            "destino_sin_regla": destino is None,
            # false = no se puede cruzar contra ninguna tabla. Sigue valiendo
            # como mensaje, pero no alimenta ningún hallazgo, y quien lo lee
            # tiene derecho a saberlo.
            "cruza_datos": bool(a.get("cruza_datos")),
        })
    return {"oficio": oficio, "avisos": avisos,
            "sin_lista": bool(oficio) and not avisos}
