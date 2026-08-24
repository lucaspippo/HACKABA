"""
autonomia.py · CUÁNTO puede hacer Ángela sola. Lo decide el dueño, no nosotros.

El producto arranca en el extremo desconfiado: Ángela propone TODO y nadie
ejecuta nada sensible sin un sí. Está bien para el primer día y es insostenible
para el mes tres — un dueño al que le piden veinte OK por semana aprende a
apretar sin leer, y una aprobación que no se lee es peor que no pedirla.

Así que la autonomía se GRADÚA, y el que la gradúa es él:

  pide_ok  · Ángela propone de a una y espera. El default de fábrica.
  agrupa   · lo rutinario y reversible se junta en UNA aprobación en vez de
             ocho. Sigue habiendo un sí humano — hay menos interrupciones.

QUÉ NO SE GRADÚA, y por qué está escrito acá y no en un comentario suelto:
plata, stock y permisos quedan clavados en `pide_ok`. No hay setting que los
mueva. Un recordatorio de cobranza que sale solo es un cliente enojado que el
dueño no vio venir; un permiso que se otorga solo es un agujero. La confianza se
gana en lo reversible, no en lo que duele.

LO QUE ÁNGELA YA HACE SOLA (y conviene que el dueño lo sepa): la normalización
nivel 1 al entrar un archivo — mayúsculas, espacios, separadores de miles. No
toca significado comercial, queda con respaldo y se revierte con un click. Es el
único caso, está auditado como `normalizacion_nivel1` con actor `sistema`, y se
muestra en el panel como lo que es: el ejemplo de hasta dónde llega hoy.

Determinismo: acá no hay criterio de IA. Es una preferencia guardada, auditada
y leída por la interfaz para decidir CÓMO presenta las propuestas. Ángela no la
escribe ni la interpreta.
"""
from __future__ import annotations

import json
import os

from . import paths

AUTONOMIA_JSON = os.path.join(paths.DATA_DIR, "autonomia.json")

NIVELES = ("pide_ok", "agrupa")

# clase → hasta dónde puede llegar. `tope` None = clavada en el default.
# Las clases son las MISMAS de core/auditoria.py: un solo vocabulario para
# "qué toca esta acción" en todo el producto.
POLITICA = {
    "plata":    {"default": "pide_ok", "tope": None},
    "stock":    {"default": "pide_ok", "tope": None},
    "permisos": {"default": "pide_ok", "tope": None},
    "datos":    {"default": "pide_ok", "tope": "agrupa"},
}


def _load() -> dict:
    try:
        with open(AUTONOMIA_JSON, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _save(d: dict) -> None:
    os.makedirs(paths.DATA_DIR, exist_ok=True)
    with open(AUTONOMIA_JSON, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def nivel_de(clase: str) -> str:
    """El nivel vigente de una clase. Una clase clavada devuelve su default
    aunque el archivo diga otra cosa: el candado manda sobre el JSON."""
    pol = POLITICA.get(clase)
    if not pol:
        return "pide_ok"
    if pol["tope"] is None:
        return pol["default"]
    guardado = _load().get(clase)
    return guardado if guardado in NIVELES else pol["default"]


def estado(lang: str | None = None) -> dict:
    """El panel entero: qué puede hacer Ángela sola hoy, clase por clase."""
    import i18n
    filas = []
    for clase, pol in POLITICA.items():
        nivel = nivel_de(clase)
        filas.append({
            "clase": clase,
            "label": i18n.t(f"autonomia.clase_{clase}", lang),
            "nivel": nivel,
            "nivel_label": i18n.t(f"autonomia.nivel_{nivel}", lang),
            "graduable": pol["tope"] is not None,
            "tope": pol["tope"],
            # el porqué del candado, en una línea: sin esto un candado es
            # arbitrariedad; con esto es una promesa del producto.
            "motivo": (None if pol["tope"] else i18n.t(f"autonomia.candado_{clase}", lang)),
        })
    return {
        "clases": filas,
        "niveles": [{"id": n, "label": i18n.t(f"autonomia.nivel_{n}", lang),
                     "detalle": i18n.t(f"autonomia.nivel_{n}_det", lang)} for n in NIVELES],
        # lo único que hoy corre sin preguntar, dicho de frente
        "ya_hace_sola": {
            "accion": "normalizacion_nivel1",
            "texto": i18n.t("autonomia.ya_hace_sola", lang),
        },
        "proximo_paso": i18n.t("autonomia.proximo_paso", lang),
    }


def set_nivel(clase: str, nivel: str, actor: str) -> dict:
    """El dueño mueve la perilla. Queda auditado como cualquier otra decisión:
    "le di más autonomía a Ángela" es exactamente el tipo de cambio que después
    hay que poder rastrear."""
    from . import store
    pol = POLITICA.get(clase)
    if not pol:
        raise ValueError(f"clase desconocida: {clase!r}")
    if nivel not in NIVELES:
        raise ValueError(f"nivel desconocido: {nivel!r}")
    if pol["tope"] is None:
        raise ValueError("esa clase no se gradúa")
    antes = nivel_de(clase)
    d = _load()
    d[clase] = nivel
    _save(d)
    store.audit.record(actor=actor, accion="cambiar_autonomia_angela",
                       antes={"clase": clase, "nivel": antes},
                       despues={"clase": clase, "nivel": nivel})
    return {"ok": True, "clase": clase, "nivel": nivel}
