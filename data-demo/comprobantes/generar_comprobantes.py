# -*- coding: utf-8 -*-
"""
Comprobantes de MUESTRA del tenant demo (P10) — PNGs realistas, versionados.

Cuentan el circuito de compra real de una PyME argentina, encadenados con la
orden de compra sembrada (OC-2026-0847, en apartados.json) y con el dataset
del Litoral (proveedor, productos, costos y el cliente moroso son los REALES):

  1. remito.png   — llega el camión de Lácteos Campo Alegre. SIN precios,
                    como corresponde. Dos líneas difieren de la OC a propósito
                    (8 en vez de 10 de una manteca; otra manteca no pedida).
  2. factura.png  — Factura A por ESA entrega: precios netos derivados del
                    costo real de catálogo (costo_iva/1.21), IVA 21%, total.
  3. recibo.png   — recibo de cobranza de Almacén San Martín (el moroso real
                    de cuentas.json): $8.000.000 a cuenta.

La visión los lee DE VERDAD (nada enlatado): por eso van nítidos, con números
en formato argentino (1.234,56) y el código interno impreso en cada línea.
Correr:  python data-demo/comprobantes/generar_comprobantes.py
"""
from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.dirname(HERE)

FECHA = "07/07/2026"          # la fecha congelada del demo (POLPILOT_DEMO_TODAY)
EMISOR = "LÁCTEOS CAMPO ALEGRE S.A."
EMISOR_CUIT = "30-58732109-4"
EMISOR_DOM = "Ruta 12 km 42, Colonia Avellaneda, Entre Ríos"
CLIENTE = "DISTRIBUIDORA DEL LITORAL S.R.L."
CLIENTE_CUIT = "30-70918234-6"
CLIENTE_DOM = "Av. de los Inmigrantes 2450, Paraná, Entre Ríos"

# (codigo, cantidad, lote, vencimiento) — encadenado con la OC-2026-0847 sembrada:
# 1239 llega 8 (pedidas 10) y 1237 NO estaba en la orden.
#
# Lote y vencimiento van IMPRESOS en el remito porque es lo que trae un remito
# de lácteos de verdad, y porque es el dato que enciende el caso de
# vencimientos que ya existe: la crema (1249) entra venciendo en 21 días y el
# depósito lo sabe desde que la mercadería toca el piso, no cuando es tarde.
LINEAS = [
    (1215, 60, "L-2608-A", "2026-09-14"),
    (1211, 40, "L-2608-B", "2026-09-02"),
    (1236, 25, "L-2607-M", "2026-11-20"),
    (1239, 8, "L-2607-M", "2026-11-20"),
    (1237, 12, "L-2606-R", "2026-10-28"),
    (1249, 30, "L-2608-C", "2026-07-28"),
]

MOROSO = "ALMACÉN SAN MARTÍN"
MOROSO_CUIT = "30-65409871-2"
COBRO = 8_000_000.0


def _font(size: int, bold: bool = False):
    nombre = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(nombre, size)
    except OSError:
        return ImageFont.load_default(size)


def _ar(n: float, decimales: int = 2) -> str:
    """1234567.8 → '1.234.567,80' (formato argentino, el que la visión debe convertir)."""
    s = f"{n:,.{decimales}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def _catalogo() -> dict:
    arts = json.load(open(os.path.join(DEMO, "inventory.json"), encoding="utf-8"))["articulos"]
    return {a["codigo"]: a for a in arts}


def _lienzo(alto: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (1000, alto), "#f4f2ec")     # mesa
    d = ImageDraw.Draw(img)
    d.rectangle([30, 30, 970, alto - 30], fill="white", outline="#777", width=2)
    d.rectangle([36, 36, 964, alto - 36], outline="#bbb", width=1)  # doble filete
    return img, d


def _encabezado(d, tipo_letra: str, tipo_nombre: str, numero: str,
                emisor=EMISOR, emisor_cuit=EMISOR_CUIT, emisor_dom=EMISOR_DOM):
    d.text((60, 60), emisor, font=_font(23, True), fill="black")
    d.text((60, 100), emisor_dom, font=_font(17), fill="#333")
    d.text((60, 126), f"CUIT: {emisor_cuit}   ·   IVA RESPONSABLE INSCRIPTO",
           font=_font(17), fill="#333")
    # el recuadro con la letra del comprobante, al centro (formato AFIP de siempre)
    d.rectangle([470, 55, 530, 115], outline="black", width=3)
    d.text((500, 85), tipo_letra, font=_font(40, True), fill="black", anchor="mm")
    d.text((940, 62), tipo_nombre, font=_font(26, True), fill="black", anchor="ra")
    d.text((940, 98), f"N° {numero}", font=_font(20), fill="black", anchor="ra")
    d.text((940, 126), f"Fecha: {FECHA}", font=_font(18), fill="black", anchor="ra")
    d.line([60, 155, 940, 155], fill="#777", width=2)


def _bloque_cliente(d, y: int, extra: str | None = None) -> int:
    d.text((60, y), f"Señores: {CLIENTE}", font=_font(19, True), fill="black")
    d.text((60, y + 28), f"CUIT: {CLIENTE_CUIT}  ·  {CLIENTE_DOM}", font=_font(16), fill="#333")
    if extra:
        d.text((60, y + 54), extra, font=_font(16), fill="#333")
    fin = y + (82 if extra else 58)
    d.line([60, fin, 940, fin], fill="#bbb", width=1)
    return fin + 14


def remito():
    cat = _catalogo()
    img, d = _lienzo(700)
    _encabezado(d, "R", "REMITO", "0001-00058214")
    y = _bloque_cliente(d, 172, "Orden de compra de referencia: OC-2026-0847")
    d.text((60, y), "Cód.", font=_font(17, True), fill="black")
    d.text((150, y), "Descripción", font=_font(17, True), fill="black")
    d.text((600, y), "Lote", font=_font(17, True), fill="black")
    d.text((730, y), "Vto.", font=_font(17, True), fill="black")
    d.text((880, y), "Cantidad", font=_font(17, True), fill="black", anchor="ra")
    y += 30
    d.line([60, y - 6, 940, y - 6], fill="#777", width=1)
    for cod, cant, lote, vto in LINEAS:
        a = cat[cod]
        d.text((60, y), str(cod), font=_font(17), fill="black")
        # entra entera: una descripción cortada con "…" es basura para la visión
        # real y se ve mal en cámara. La más larga del set son 36 caracteres.
        d.text((150, y), a["descripcion"], font=_font(16), fill="black")
        d.text((600, y), lote, font=_font(16), fill="black")
        dd, mm, aa = vto.split("-")[::-1]
        d.text((730, y), f"{dd}/{mm}/{aa}", font=_font(16), fill="black")
        d.text((880, y), _ar(cant, 0), font=_font(17), fill="black", anchor="ra")
        y += 34
    d.line([60, y + 4, 940, y + 4], fill="#777", width=1)
    y += 22
    d.text((60, y), f"Bultos: {len(LINEAS)}   ·   Transporte: propio   ·   "
                    "Recibí conforme: ______________________",
           font=_font(16), fill="#333")
    d.text((60, y + 40), "Documento no válido como factura. Mercadería viaja por cuenta del comprador.",
           font=_font(14), fill="#666")
    img.save(os.path.join(HERE, "remito.png"))
    print("remito.png OK")


def factura():
    cat = _catalogo()
    img, d = _lienzo(760)
    _encabezado(d, "A", "FACTURA", "0001-00091352")
    y = _bloque_cliente(d, 172, "Condición de venta: Cuenta corriente 30 días  ·  "
                                "Remito de referencia: 0001-00058214")
    d.text((60, y), "Cód.", font=_font(16, True), fill="black")
    d.text((145, y), "Descripción", font=_font(16, True), fill="black")
    d.text((640, y), "Cant.", font=_font(16, True), fill="black", anchor="ra")
    d.text((780, y), "P. unitario", font=_font(16, True), fill="black", anchor="ra")
    d.text((930, y), "Subtotal", font=_font(16, True), fill="black", anchor="ra")
    y += 28
    d.line([60, y - 6, 940, y - 6], fill="#777", width=1)
    neto = 0.0
    for cod, cant, _lote, _vto in LINEAS:  # la factura no lleva lote: solo plata
        a = cat[cod]
        precio = round(a["costo_iva"] / 1.21, 2)
        sub = round(precio * cant, 2)
        neto = round(neto + sub, 2)
        d.text((60, y), str(cod), font=_font(15), fill="black")
        d.text((145, y), a["descripcion"], font=_font(15), fill="black")
        d.text((640, y), _ar(cant, 0), font=_font(15), fill="black", anchor="ra")
        d.text((780, y), _ar(precio), font=_font(15), fill="black", anchor="ra")
        d.text((930, y), _ar(sub), font=_font(15), fill="black", anchor="ra")
        y += 32
    iva = round(neto * 0.21, 2)
    total = round(neto + iva, 2)
    d.line([560, y + 4, 940, y + 4], fill="#777", width=1)
    y += 18
    for etiqueta, monto, negrita in (("Neto gravado", neto, False),
                                     ("IVA 21%", iva, False),
                                     ("TOTAL", total, True)):
        d.text((640, y), etiqueta, font=_font(18, negrita), fill="black", anchor="ra")
        d.text((930, y), f"$ {_ar(monto)}", font=_font(18, negrita), fill="black", anchor="ra")
        y += 30
    d.text((60, y + 12), "CAE N°: 76284519032478  ·  Vto. CAE: 17/07/2026",
           font=_font(14), fill="#666")
    img.save(os.path.join(HERE, "factura.png"))
    print(f"factura.png OK (neto {_ar(neto)} · IVA {_ar(iva)} · total {_ar(total)})")


def recibo():
    img, d = _lienzo(640)
    # lo emite la DISTRIBUIDORA (cobra), el que paga es el cliente moroso
    _encabezado(d, "X", "RECIBO", "0001-00003412",
                emisor=CLIENTE, emisor_cuit=CLIENTE_CUIT, emisor_dom=CLIENTE_DOM)
    y = 180
    d.text((60, y), f"Recibimos de: {MOROSO}", font=_font(20, True), fill="black")
    d.text((60, y + 32), f"CUIT: {MOROSO_CUIT}", font=_font(16), fill="#333")
    y += 76
    d.text((60, y), "La suma de: PESOS OCHO MILLONES con 00/100",
           font=_font(18), fill="black")
    y += 40
    d.text((60, y), "En concepto de: pago a cuenta de facturas vencidas de cuenta corriente",
           font=_font(17), fill="black")
    y += 40
    d.text((60, y), "Medio de pago: transferencia bancaria  ·  Banco Entre Ríos",
           font=_font(16), fill="#333")
    y += 60
    d.rectangle([560, y, 940, y + 64], outline="black", width=2)
    d.text((575, y + 32), "TOTAL", font=_font(20, True), fill="black", anchor="lm")
    d.text((925, y + 32), f"$ {_ar(COBRO)}", font=_font(22, True), fill="black", anchor="rm")
    y += 100
    d.text((60, y), "Firma y aclaración: ______________________     Documento no fiscal.",
           font=_font(15), fill="#666")
    img.save(os.path.join(HERE, "recibo.png"))
    print("recibo.png OK")


# --- La extracción CANÓNICA de cada muestra -----------------------------------
# El mismo script que dibuja la imagen escribe lo que esa imagen dice. Así no
# pueden divergir: si mañana cambia una cantidad del remito, cambia el PNG y
# cambia el JSON en la misma corrida.
#
# Para qué sirve: core/extraccion.py hashea la imagen que sube el usuario y, si
# es una de estas muestras, devuelve ESTO sin llamar a la visión. El demo de YC
# deja de depender de que haya red y API key en la sala. Cualquier otra foto
# sigue yendo a la visión real, que es la que importa para el producto.

def _sha256(ruta: str) -> str:
    import hashlib
    with open(ruta, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _extraccion_remito() -> dict:
    cat = _catalogo()
    return {
        "es_comprobante": True, "legible": True, "tipo_comprobante": "remito",
        "proveedor": {"razon_social": EMISOR, "cuit": EMISOR_CUIT},
        "numero": "0001-00058214",
        "fecha": "-".join(FECHA.split("/")[::-1]),
        # el texto TAL CUAL sale impreso: es lo que reparsea core/validacion con
        # locale argentino fijo. La muestra ejercita el mismo camino que la foto.
        "fecha_texto": FECHA,
        "orden_compra_referencia": "OC-2026-0847",
        "items": [{"codigo": cod, "descripcion": cat[cod]["descripcion"],
                   "cantidad": float(cant), "lote": lote, "vencimiento": vto,
                   "vencimiento_texto": "/".join(vto.split("-")[::-1]),
                   "precio_unitario": None, "subtotal": None, "confianza": "leido"}
                  for cod, cant, lote, vto in LINEAS],
        "subtotal": None, "iva": None, "total": None,
        "campos_dudosos": [], "campos_ilegibles": [],
    }


def _extraccion_factura() -> dict:
    cat = _catalogo()
    items, neto = [], 0.0
    for cod, cant, _l, _v in LINEAS:
        precio = round(cat[cod]["costo_iva"] / 1.21, 2)
        sub = round(precio * cant, 2)
        neto = round(neto + sub, 2)
        items.append({"codigo": cod, "descripcion": cat[cod]["descripcion"],
                      "cantidad": float(cant), "precio_unitario": precio,
                      "subtotal": sub, "confianza": "leido"})
    iva = round(neto * 0.21, 2)
    return {
        "es_comprobante": True, "legible": True, "tipo_comprobante": "factura",
        "proveedor": {"razon_social": EMISOR, "cuit": EMISOR_CUIT},
        "numero": "0001-00091352",
        "fecha": "-".join(FECHA.split("/")[::-1]),
        "fecha_texto": FECHA,
        "condicion": "Cuenta corriente 30 días",
        "items": items, "subtotal": neto, "iva": iva,
        "total": round(neto + iva, 2),
        "campos_dudosos": [], "campos_ilegibles": [],
    }


def _extraccion_recibo() -> dict:
    return {
        "es_comprobante": True, "legible": True, "tipo_comprobante": "recibo",
        "cliente": {"razon_social": MOROSO},
        "proveedor": {"razon_social": CLIENTE, "cuit": CLIENTE_CUIT},
        "numero": "0001-00003412",
        "fecha": "-".join(FECHA.split("/")[::-1]),
        "fecha_texto": FECHA,
        "items": [], "total": COBRO,
        "campos_dudosos": [], "campos_ilegibles": [],
    }


def extracciones():
    salida = {"_nota": "Lo que dice cada muestra, escrito por el MISMO script que "
                       "dibuja la imagen (no pueden divergir). core/extraccion.py "
                       "lo sirve por hash cuando la foto subida ES una muestra; "
                       "cualquier otra imagen va a la visión real.",
              "muestras": {}}
    for mid, fn in (("remito", _extraccion_remito), ("factura", _extraccion_factura),
                    ("recibo", _extraccion_recibo)):
        ruta = os.path.join(HERE, f"{mid}.png")
        if not os.path.exists(ruta):
            continue
        salida["muestras"][mid] = {"sha256": _sha256(ruta), "extraccion": fn()}
    destino = os.path.join(HERE, "extracciones.json")
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    print(f"extracciones.json OK ({len(salida['muestras'])} muestras)")


if __name__ == "__main__":
    remito()
    factura()
    recibo()
    extracciones()   # último: hashea los PNG recién escritos
