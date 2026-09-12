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

import math
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

# La tarjeta de regla de la expansion del proveedor (T_ANCHO/T_ALTO alla).
ANCHO_TARJETA, ALTO_TARJETA = 190, 92


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



# --- LINEAS QUE PASAN POR DEBAJO DE CAJAS -----------------------------------
#
# POR QUE SE AGREGO. El chequeo solo comparaba CAJA contra CAJA y daba cero
# mientras en la pantalla las lineas del producto atravesaban la tarjeta de la
# regla, pasaban por atras de «arma el reclamo» y cruzaban por detras de dos
# productos. Una linea que pasa por abajo de una caja no se lee como conexion:
# se lee como un error de dibujo. Y ninguna comparacion de rectangulos lo iba
# a encontrar nunca, porque una linea no es un rectangulo.
#
# Se reproduce la MISMA curva que dibuja el frontend (Expansion en
# EscenaReclamo.jsx), se la muestrea, y se chequea cada tramo contra cada caja.

R_EXP = 25          # radio de la forma de un nodo de expansion
RETIRO_DISCO = R_EXP + 9
T_ANCHO_F, T_ALTO_F = 190, 92     # la tarjeta de regla, en el frontend
MUESTRAS = 240


def _punto_final(desde, n, tarjeta):
    """Donde frena la linea: al borde de la forma. Misma cuenta que el JSX."""
    dx, dy = n[0] - desde[0], n[1] - desde[1]
    largo = math.hypot(dx, dy) or 1.0
    if tarjeta:
        ex, ey = T_ANCHO_F / 2 + 8, T_ALTO_F / 2 + 8
        rec = min(ex / abs(dx / largo) if abs(dx) > 0.5 else 1e9,
                  ey / abs(dy / largo) if abs(dy) > 0.5 else 1e9)
    else:
        rec = RETIRO_DISCO
    return (n[0] - dx / largo * rec, n[1] - dy / largo * rec)


def curva_expansion(desde, n, tarjeta):
    """Los puntos de la curva cuadratica, muestreada."""
    fx, fy = _punto_final(desde, n, tarjeta)
    dx, dy = n[0] - desde[0], n[1] - desde[1]
    cx = (desde[0] + fx) / 2 - dy * 0.07
    cy = (desde[1] + fy) / 2 + dx * 0.07
    pts = []
    for i in range(MUESTRAS + 1):
        t = i / MUESTRAS
        u = 1 - t
        pts.append((u * u * desde[0] + 2 * u * t * cx + t * t * fx,
                    u * u * desde[1] + 2 * u * t * cy + t * t * fy))
    return pts


def curva_arista(a, b, k):
    """La curva de una arista del caso: misma `curva()` del frontend."""
    cx, cy = punto_medio(a, b, k)
    pts = []
    for i in range(MUESTRAS + 1):
        t = i / MUESTRAS
        u = 1 - t
        pts.append((u * u * a[0] + 2 * u * t * cx + t * t * b[0],
                    u * u * a[1] + 2 * u * t * cy + t * t * b[1]))
    return pts


def _dentro(p, r):
    return r[0] <= p[0] <= r[2] and r[1] <= p[1] <= r[3]


def _cruzan(p, q, a, b):
    """Se cortan los segmentos pq y ab?"""
    def lado(o, x, y):
        return (x[0] - o[0]) * (y[1] - o[1]) - (x[1] - o[1]) * (y[0] - o[0])
    d1, d2 = lado(a, b, p), lado(a, b, q)
    d3, d4 = lado(p, q, a), lado(p, q, b)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def toca_rect(pts, r, margen=3):
    """Pasa la polilinea por adentro (o al ras) del rectangulo?"""
    x0, y0, x1, y1 = r[0] - margen, r[1] - margen, r[2] + margen, r[3] + margen
    lados = (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
             ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0)))
    caja = (x0, y0, x1, y1)
    for i in range(len(pts) - 1):
        p, q = pts[i], pts[i + 1]
        if _dentro(p, caja) or _dentro(q, caja):
            return True
        for a, b in lados:
            if _cruzan(p, q, a, b):
                return True
    return False


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
    lineas = []          # (nombre, puntos, cual_expansion, id_del_destino)
    cajas_exp = {}       # cual -> [(nombre, rect, id_nodo)]
    for cual, exp in (esc.get("expansiones") or {}).items():
        desde = nodos.get(exp.get("desde") or cual)
        tarjeta = exp.get("forma") == "tarjeta"
        for gr in exp.get("grupos", []):
            r_rel = rect(gr["x"], gr["y"], len(gr["rel"]) * 6.0 + 16, 20)
            cajas.append((f"rel:{cual}:«{gr['rel']}»", r_rel))
            cajas_exp.setdefault(cual, []).append(
                (f"etiqueta «{gr['rel']}»", r_rel, None))
            tarjeta = exp.get("forma") == "tarjeta"
            for m in gr["nodos"]:
                if tarjeta:
                    # una tarjeta de regla: el texto va ADENTRO, asi que la
                    # caja es la tarjeta y no depende del largo del nombre.
                    # +11 de alto por la etiqueta «la que usé» de la usada,
                    # que cuelga por fuera del borde de arriba.
                    extra = 22 if m.get("usada") else 0
                    r = rect(m["x"], m["y"] - extra / 2,
                             ANCHO_TARJETA, ALTO_TARJETA + extra)
                else:
                    # centrado en la forma, que esta arriba del nombre
                    r = rect(m["x"], m["y"] + 12, ANCHO_CHIP(m["nombre"]),
                             ALTO_NODO_EXP)
                nom = f"chip:{cual}|{gr['rel']}:{m['nombre'][:24]}"
                cajas.append((nom, r))
                cajas_exp.setdefault(cual, []).append((nom, r, m["id"]))
                if desde:
                    lineas.append((
                        f"linea {cual} -> {m['nombre'][:28]}",
                        curva_expansion((desde["x"], desde["y"]),
                                        (m["x"], m["y"]), tarjeta),
                        cual, m["id"]))

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

    # --- LINEAS CONTRA CAJAS -------------------------------------------
    #
    # Cada linea de expansion contra: los nodos del caso, las etiquetas de sus
    # aristas, y los nodos y etiquetas de SU PROPIA expansion (las de la otra
    # nunca coexisten). Se saltea el nodo de DESTINO de la linea —llegar hasta
    # el es su trabajo— y el nodo del que SALE, por lo mismo.
    cajas_caso = [(n, r) for n, r in cajas
                  if n.startswith("nodo:") or n.startswith("etiqueta:")]
    exps = esc.get("expansiones") or {}
    cruces = []
    for nombre, pts, cual, destino in lineas:
        origen = "nodo:" + (exps.get(cual, {}).get("desde") or cual)
        for n2, r2 in cajas_caso:
            if n2 == origen:
                continue
            if toca_rect(pts, r2):
                cruces.append((nombre, n2))
        for n2, r2, nid in cajas_exp.get(cual, []):
            if nid == destino:
                continue
            if toca_rect(pts, r2):
                cruces.append((nombre, n2))

    if not choques and not cruces:
        print(f"[escena] {len(cajas)} cajas, {len(lineas)} lineas, "
              f"0 choques, 0 cruces")
        raise SystemExit(0)
    if choques:
        print(f"[escena] {len(choques)} CHOQUE(S) de caja:")
        for n1, n2 in choques:
            print("  " + n1 + chr(10) + "    pisa " + n2)
    if cruces:
        print(f"[escena] {len(cruces)} LINEA(S) por debajo de una caja:")
        for n1, n2 in cruces:
            print("  " + n1 + chr(10) + "    cruza " + n2)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
