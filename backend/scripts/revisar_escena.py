"""
revisar_escena.py — ¿alguna etiqueta de la escena pisa a un nodo o a otra?

POR QUE EXISTE. Las posiciones de `core/escena.py` se deciden a mano, y a mano
se equivoca uno: «se envia por mail» quedo tapado por la tarjeta verde DOS
veces, y las dos veces lo encontro el usuario mirando la pantalla, no nosotros.
El problema es que el solapamiento depende de cosas que no se ven leyendo el
codigo — la curva de la arista mueve el punto medio, y la caja del envio cambia
de ancho segun cuanto texto traiga la regla.

Asi que se calcula. Este script reproduce la MISMA aritmetica que el frontend
(`curva()` en EscenaReclamo.jsx) y compara cada rectangulo contra todos los
demas. No es un test de la suite: es una herramienta para correr cuando se
mueve algo de la escena.

    python scripts/revisar_escena.py

Sale 0 si no hay choques; 1 y la lista si los hay.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Las medidas de cada forma, tomadas de EscenaReclamo.jsx. Si alla cambia un
# tamanio, cambia aca: son dos archivos que tienen que decir lo mismo, y esa es
# justamente la razon por la que conviene poder correr esto.
CAJAS = {
    "persona":  (96, 122),    # disco de 76 + el nombre y el rol debajo
    "nota":     (172, 150),   # post-it + la linea del autor
    "producto": (116, 116),   # disco r=58
    "proveedor": (92, 118),   # rombo r=36 + nombre
    "regla":    (170, 80),
    "orden":    (86, 116),
    "envio":    (250, 104),   # ancho AUTO: se mide el real en el navegador
}

ANCHO_CHAR = 6.4    # lo que mide un caracter en la pildora, a 12px
PAD_PILDORA = 18
ALTO_PILDORA = 22


def ANCHO_CHIP(nombre: str) -> float:
    """Lo que mide un nodo de la expansion: la forma o el nombre, el que sea
    mas ancho. El nombre va DEBAJO, asi que manda el texto."""
    return max(64.0, len(nombre) * 5.3 + 14)


# Alto de un nodo de expansion: la forma (~52) + el nombre debajo (~16) + aire.
ALTO_NODO_EXP = 76


def punto_medio(a, b, k):
    """La misma formula que `curva()` en el frontend."""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    dx, dy = b[0] - a[0], b[1] - a[1]
    return mx - dy * k * 0.5, my + dx * k * 0.5


def rect(cx, cy, w, h):
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def chocan(r1, r2, margen=4):
    return not (r1[2] + margen < r2[0] or r2[2] + margen < r1[0]
                or r1[3] + margen < r2[1] or r2[3] + margen < r1[1])


def main() -> None:
    os.environ.setdefault("POLPILOT_TENANT", "demo")
    from core import escena

    esc = escena.reclamo("es")
    if not esc.get("disponible"):
        print("[escena] no disponible (falta el caso sembrado)")
        raise SystemExit(0)

    nodos = {n["id"]: n for n in esc["nodos"]}
    cajas = []
    for n in esc["nodos"]:
        w, h = CAJAS.get(n["tipo"], (80, 80))
        cajas.append((f"nodo:{n['id']}", rect(n["x"], n["y"], w, h)))

    for a in esc["aristas"]:
        de, hacia = nodos[a["de"]], nodos[a["a"]]
        cx, cy = punto_medio((de["x"], de["y"]), (hacia["x"], hacia["y"]),
                             a.get("curva") or 0)
        cx += a.get("dx") or 0
        cy += a.get("dy") or 0
        w = len(a["etiqueta"]) * ANCHO_CHAR + PAD_PILDORA
        cajas.append((f"etiqueta:«{a['etiqueta']}»", rect(cx, cy, w, ALTO_PILDORA)))

    # LA EXPANSION ENTERA: los chips Y las etiquetas de cada racimo.
    #
    # La version anterior solo metia los nodos y por eso daba 0 choques con la
    # pantalla visiblemente pisada: lo que se solapaba eran las ETIQUETAS de
    # las relaciones contra los chips de al lado. Una etiqueta que no se chequea
    # es una etiqueta que se va a pisar.
    # CADA expansion se chequea POR SEPARADO contra la escena: nunca se abren
    # dos a la vez, asi que que dos expansiones se pisen entre si no importa.
    for cual, exp in (esc.get("expansiones") or {}).items():
        for gr in exp.get("grupos", []):
            cajas.append((f"rel:{cual}:«{gr['rel']}»",
                          rect(gr["x"], gr["y"], len(gr["rel"]) * 6.0 + 16, 20)))
            for m in gr["nodos"]:
                # centrado en la forma, que esta arriba del nombre
                cajas.append((f"chip:{cual}|{gr['rel']}:{m['nombre'][:24]}",
                              rect(m["x"], m["y"] + 12, ANCHO_CHIP(m["nombre"]),
                                   ALTO_NODO_EXP)))

    # LA PILDORA DE LA PISTA. Vive abajo a la izquierda, fuera del grupo que se
    # transforma, asi que no se achica con la escena: en coordenadas del lienzo
    # base ocupa siempre el mismo lugar y cualquier expansion que llegue ahi la
    # pisa. Paso: el racimo del proveedor le caia encima.
    # La pildora de la pista YA NO se chequea: dejo de vivir adentro del SVG y
    # pasó a ser HTML posicionado contra el panel (ver EscenaReclamo.jsx). No
    # comparte sistema de coordenadas con nada de esto, asi que no puede chocar.

    choques = []
    for i, (n1, r1) in enumerate(cajas):
        for n2, r2 in cajas[i + 1:]:
            # dos nodos pegados no importan: lo que se lee mal es una ETIQUETA
            # encima de cualquier cosa.
            de_exp = lambda x: x.startswith("chip:") or x.startswith("rel:")
            hay_texto = (n1.startswith("etiqueta") or n2.startswith("etiqueta")
                         or de_exp(n1) or de_exp(n2))
            if not hay_texto:
                continue
            # dos chips del MISMO racimo se apilan a proposito: estan pegadas
            # una debajo de la otra y eso se lee bien. Lo que no puede pasar es
            # que se pisen entre racimos, con una etiqueta, o con la escena.
            cual = lambda x: x.split(":")[1].split("|")[0] if ":" in x else ""
            if (de_exp(n1) and de_exp(n2)) and cual(n1) != cual(n2):
                continue     # expansiones distintas: nunca coexisten
            if (n1.startswith("chip:") and n2.startswith("chip:")
                    and n1.split(":", 1)[1].split(":")[0] == n2.split(":", 1)[1].split(":")[0]):
                continue     # mismo racimo: apilado a proposito
            if chocan(r1, r2):
                choques.append((n1, n2))

    if not choques:
        print(f"[escena] {len(cajas)} cajas, 0 choques")
        raise SystemExit(0)
    print(f"[escena] {len(choques)} CHOQUE(S):")
    for n1, n2 in choques:
        print(f"  {n1}\n    pisa {n2}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
