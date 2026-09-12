"""mis_avisos.py — QUÉ PASÓ CON LO QUE DIJE.

La mitad que faltaba del circuito. `core/piso.py` guarda el hecho, `core/notas.py`
guarda lo que la gente contó, `core/cruces.py` los cruza y produce hallazgos —
y nada de eso volvía nunca a la persona que lo originó. `api.piso.reportes`
existía desde siempre y ninguna pantalla lo llamaba.

Sin esta vuelta, el que reporta ocho cajas rotas ve el reclamo cobrarse y no se
entera; la próxima vez lo escribe en el grupo de WhatsApp, donde por lo menos
alguien contesta. Ése es exactamente el punto donde este producto se gana o se
pierde.

QUÉ DEVUELVE, Y POR QUÉ SÓLO ESO

Tres cosas, y cada una responde una pregunta distinta que esta persona sí se
hace:

  reporte      · lo que mandé, con su estado y quién lo vio
  me_mandaron  · lo que está esperando por mí
  sirvio_para  · los hallazgos del negocio que se apoyan en algo que YO dije

La tercera es la que no existía en ningún lado. Un cruce
(`_cruce_espacio_camara`, `_cruce_queja_cliente_clave`) se arma con notas del
equipo y hoy lo ve una sola persona, en una sola pantalla de escritorio: el
dueño. Ramón avisó cuatro veces que la cámara está llena, el sistema cruzó eso
con la orden que entra el 9, y Ramón no ve la respuesta a su propia pregunta.

LO QUE NO ES: un tablero. No devuelve la decisión del dueño, ni el monto de la
cartera, ni los hallazgos de otros. Cada uno ve el tramo que le toca y el
resultado de lo que originó — nada más. Cruzar eso con "todo lo que pasa en la
empresa" sería otra pantalla de monitoreo, que es lo contrario de esto.
"""
from __future__ import annotations


def _autores_de(card: dict) -> set[str]:
    """Los usernames que aparecen como autores de las notas de un hallazgo.

    Los cruces guardan las notas que los sostienen en `datos.notas` (ver
    `cruces._nota_dict`). No se adivina por texto: si el hallazgo no declara de
    quién es la nota, no es de nadie y no se le atribuye a nadie.
    """
    datos = card.get("datos") or {}
    notas = datos.get("notas") or []
    return {n.get("autor") for n in notas if isinstance(n, dict) and n.get("autor")}


def sirvio_para(username: str, lang: str | None = None) -> list[dict]:
    """Los hallazgos que se apoyan en una nota de esta persona.

    Devuelve la versión corta —qué se encontró y qué notas suyas lo sostienen—
    y no la tarjeta entera: el drill-down con la plata del negocio es del que
    decide, no del que avisó.
    """
    from . import cruces
    out = []
    try:
        cards = cruces.cards(lang)
    except Exception:  # noqa: BLE001 — sin cruces, la pantalla igual sirve
        return []
    for c in cards:
        mias = [n for n in ((c.get("datos") or {}).get("notas") or [])
                if isinstance(n, dict) and n.get("autor") == username]
        if not mias:
            continue
        out.append({
            "id": c["id"],
            "titulo": c.get("titulo"),
            "resumen": c.get("resumen"),
            # De cuántas personas salió: "lo dijiste vos y otros dos" es lo que
            # convierte un aviso suelto en algo que se mira.
            "personas": len(_autores_de(c)),
            "mis_notas": [{"id": n.get("id"), "fecha": n.get("fecha"),
                           "canal": n.get("canal"), "texto": n.get("texto")}
                          for n in mias],
        })
    return out


# Los campos que llevan un USERNAME y se leen como una persona. El username es
# la identidad y se guarda tal cual —es la clave, y no se traduce—; el nombre
# de pantalla se resuelve acá, en el borde donde se muestra. Guardarlo sería
# duplicar un dato que ya vive en el equipo y que cambia cuando alguien se
# cambia el nombre.
_QUIENES = ("actor", "destinatario", "visto_por", "resuelto_por")


def _con_nombres(reportes: list[dict]) -> list[dict]:
    """Agrega `<campo>_nombre` a cada username. La pantalla usa ése y cae al
    username si la persona ya no está en el equipo — nunca queda vacío."""
    from . import piso
    out = []
    for r in reportes:
        extra = {f"{k}_nombre": piso._nombre(r[k]) for k in _QUIENES if r.get(k)}
        out.append({**r, **extra})
    return out


def de(username: str, lang: str | None = None) -> dict:
    """Todo lo de esta persona, en una llamada."""
    from . import piso
    mios = piso.mios(username)
    return {
        "reporte": _con_nombres(mios["reporte"]),
        "me_mandaron": _con_nombres(mios["me_mandaron"]),
        "sirvio_para": sirvio_para(username, lang),
    }
