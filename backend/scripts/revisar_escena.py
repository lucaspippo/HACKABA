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

    choques = []
    for i, (n1, r1) in enumerate(cajas):
        for n2, r2 in cajas[i + 1:]:
            # dos nodos pegados no importan: lo que se lee mal es una ETIQUETA
            # encima de cualquier cosa.
            if not n1.startswith("etiqueta") and not n2.startswith("etiqueta"):
                continue
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
