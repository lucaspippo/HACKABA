"""
Importador asistido — Ángela mapea las columnas de cualquier export.

El dueño suelta un Excel/CSV y el sistema infiere a qué campo canónico
corresponde cada columna (por nombre de header), reporta el mapeo para que lo
confirme, y deja lo que no pudo mapear a la vista. Hoy el mapeo es heurístico
(sinónimos); el hook de IA se enciende cuando haya ANTHROPIC_API_KEY.

# TODO IA: si hay API key, pedirle a Claude el mapeo de headers ambiguos.
# TODO: validación final del formato con un export REAL de Horizonte (spec §15).
"""
from __future__ import annotations

import csv
import io
import os
import unicodedata

import openpyxl

# Campos canónicos por destino (ver spec §9).
DESTINOS = {
    "venta_historica": ["fecha", "boca", "articulo", "cantidad", "kilos", "precio", "costo", "es_venta_a_sucursal_propia"],
    "cuenta_corriente": ["cliente", "saldo", "plazo", "vencimiento"],
    "producto": ["codigo", "descripcion", "stock", "costo", "pvp", "venta_x_peso"],
    "deposito": ["codigo", "producto", "ubicacion", "lote", "vencimiento", "cantidad"],
    "logistica": ["pedido", "cliente", "direccion", "estado", "fecha_prevista", "transporte"],
}

# Sinónimos de header por campo (normalizados: minúsculas, sin acentos).
SINONIMOS = {
    "codigo": ["codigo", "cod", "sku", "id"],
    "descripcion": ["descripcion", "producto", "nombre", "detalle", "articulo"],
    "pvp": ["pvp", "precio de venta", "precio venta", "precio publico", "venta", "precio"],
    "fecha": ["fecha", "dia", "date", "emision"],
    "boca": ["boca", "local", "sucursal", "punto de venta", "pdv", "deposito"],
    "articulo": ["articulo", "producto", "descripcion", "item", "codigo", "sku"],
    "cantidad": ["cantidad", "cant", "unidades", "qty", "bultos"],
    "kilos": ["kilos", "kg", "peso", "kgs"],
    "precio": ["precio", "pvp", "venta", "importe", "total", "monto"],
    "costo": ["costo", "cost", "costo unitario"],
    "es_venta_a_sucursal_propia": ["sucursal propia", "interna", "es sucursal", "propia"],
    "cliente": ["cliente", "razon social", "nombre", "cuit"],
    "saldo": ["saldo", "deuda", "debe", "balance"],
    "plazo": ["plazo", "dias", "condicion"],
    "vencimiento": ["vencimiento", "vence", "due"],
    "producto": ["producto", "descripcion", "articulo", "detalle", "nombre"],
    "ubicacion": ["ubicacion", "pasillo", "estanteria", "rack", "sector", "camara", "posicion"],
    "lote": ["lote", "partida", "batch"],
    "pedido": ["pedido", "nro pedido", "orden", "remito", "comprobante"],
    "direccion": ["direccion", "domicilio", "destino"],
    "estado": ["estado", "status", "situacion"],
    "fecha_prevista": ["fecha prevista", "fecha entrega", "prevista", "fecha"],
    "transporte": ["transporte", "camion", "chofer", "vehiculo", "flete"],
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def inferir_mapeo(headers: list[str], destino: str = "venta_historica") -> dict:
    """Devuelve {campo_canonico: header_original|None} y los headers sin usar."""
    campos = DESTINOS.get(destino, [])
    headers_norm = [(h, _norm(h)) for h in headers]
    usados = set()
    mapeo = {}
    for campo in campos:
        encontrado = None
        for syn in SINONIMOS.get(campo, [campo]):
            for orig, hn in headers_norm:
                if orig in usados:
                    continue
                if syn == hn or syn in hn or hn in syn:
                    encontrado = orig
                    break
            if encontrado:
                break
        if encontrado:
            usados.add(encontrado)
        mapeo[campo] = encontrado
    sin_mapear = [h for h, _ in headers_norm if h not in usados]
    return {"destino": destino, "mapeo": mapeo, "sin_mapear": sin_mapear}


def _leer(path: str) -> tuple[list[str], list[list]]:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        rows = [[c for c in r] for r in ws.iter_rows(values_only=True)]
        wb.close()
    else:  # csv
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = [r for r in csv.reader(f)]
    headers = [str(c) if c is not None else "" for c in (rows[0] if rows else [])]
    return headers, rows[1:]


def previsualizar_filas(headers: list[str], filas: list[list], destino: str, n: int = 3) -> dict:
    info = inferir_mapeo(headers, destino)
    ejemplo = [dict(zip(headers, fila)) for fila in filas[:n]]
    info["filas_ejemplo"] = ejemplo
    info["total_filas"] = len(filas)
    info["mapeados"] = sum(1 for v in info["mapeo"].values() if v)
    return info


def previsualizar(path: str, destino: str = "venta_historica") -> dict:
    headers, filas = _leer(path)
    return previsualizar_filas(headers, filas, destino)


def previsualizar_csv(texto: str, destino: str = "venta_historica") -> dict:
    """Igual que previsualizar pero desde el contenido CSV (lo manda el frontend)."""
    rows = list(csv.reader(io.StringIO(texto)))
    headers = [str(c) for c in (rows[0] if rows else [])]
    return previsualizar_filas(headers, rows[1:], destino)
