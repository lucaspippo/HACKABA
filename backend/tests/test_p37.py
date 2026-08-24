"""
P37 — INCIDENTE DE PRIVACIDAD: el nombre/logo/datos del PILOTO (Horizonte)
jamás pueden estar en lo que se empaqueta o sirve bajo el tenant demo (el link
público de YC). Estos tests fallan si vuelven a colarse — en el código fuente
del frontend O en el build servido (frontend/dist).

No se testea el bare "piloto": el repo se llama "polpilot-demo"
(falso positivo). Se usan marcas FUERTES del piloto: su razón social, el asset
del logo, y datos reales (empleados/inventario) que estaban hardcodeados.
"""
import glob
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_FRONT = os.path.normpath(os.path.join(_HERE, "..", "..", "frontend"))

MARCADORES = [
    "Supermercados Horizonte",   # razón social del tenant piloto
    "piloto.png", "piloto.jpg", "piloto.jpeg",  # asset del logo del piloto
    "Emilio", "Paula", "Osvaldo",  # personas del seed del piloto
]


def _archivos(base, exts):
    out = []
    if not os.path.isdir(base):
        return out
    for root, _, files in os.walk(base):
        if "node_modules" in root:
            continue
        for f in files:
            if f.endswith(exts):
                out.append(os.path.join(root, f))
    return out


def test_asset_del_piloto_no_empaquetado():
    """El logo del piloto no puede estar en public/ ni en el build servido."""
    assert not glob.glob(os.path.join(_FRONT, "public", "logos", "piloto.*")), \
        "el logo del piloto sigue en frontend/public/logos"
    assert not glob.glob(os.path.join(_FRONT, "dist", "logos", "piloto.*")), \
        "el logo del piloto sigue en el build (frontend/dist/logos)"


def test_nombre_y_datos_del_piloto_no_en_el_frontend():
    """Ni el código fuente ni el bundle servido nombran al piloto ni traen sus
    datos. Cubre src (lo que se compila) y dist (lo que se sirve, si hay build)."""
    fuentes = _archivos(os.path.join(_FRONT, "src"), (".js", ".jsx", ".json", ".html"))
    fuentes += _archivos(os.path.join(_FRONT, "dist"), (".js", ".html", ".css"))
    hits = []
    for path in fuentes:
        try:
            txt = open(path, encoding="utf-8").read()
        except Exception:
            continue
        for m in MARCADORES:
            if m in txt:
                hits.append((os.path.relpath(path, _FRONT), m))
    assert not hits, f"marcadores del piloto en lo que se empaqueta/sirve: {hits}"
