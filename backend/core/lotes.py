"""
lotes.py — CRUD real sobre los lotes del depósito. Los lotes YA viven en el
apartado "deposito" (core/deposito.py los lee para vencimientos/vencidos/
discrepancias) — este módulo no crea un almacenamiento paralelo, sólo agrega
las operaciones de escritura que faltaban (crear/editar/borrar un lote) sobre
esas mismas filas, así deposito.py y vencimientos.py ven los cambios sin
tocarlos: siguen leyendo el mismo apartado de siempre.
"""
from __future__ import annotations

import uuid

from . import esquema, paging, section_records
from .audit import AuditLog

_audit = AuditLog(esquema.DATA_DIR)
_TIPO = "deposito"
_CAMPOS = ("codigo", "producto", "ubicacion", "lote", "vencimiento", "cantidad",
           "in_date", "counted_qty", "source", "source_id")
SEARCH = ("producto", "ubicacion", "lote", "codigo", "source")
CSV_COLUMNS = ("producto", "codigo", "ubicacion", "lote", "vencimiento",
               "cantidad", "counted_qty", "diferencia", "in_date", "source")
QTY_EPS = 0.01


def _con_ids(filas: list[dict]) -> tuple[list[dict], bool]:
    """Las filas semilla (data-demo/apartados.json) no traen `id`: se lo
    asignamos la primera vez que se listan y quedan estables de ahí en más."""
    cambio = False
    for f in filas:
        if not f.get("id"):
            f["id"] = uuid.uuid4().hex[:10]
            cambio = True
    return filas, cambio


def listar() -> list[dict]:
    filas, cambio = _con_ids(esquema.filas(_TIPO))
    if cambio:
        esquema.reemplazar_filas(_TIPO, filas)
    return filas


def crear(datos: dict, actor: str) -> dict:
    if not (datos.get("producto") or datos.get("codigo")):
        raise ValueError("producto_requerido")
    if not datos.get("ubicacion"):
        raise ValueError("ubicacion_requerida")
    filas = listar()
    fila = {"id": uuid.uuid4().hex[:10], **{c: datos.get(c) for c in _CAMPOS}}
    if not fila.get("source"):
        fila["source"] = "manual"
    filas.append(fila)
    esquema.reemplazar_filas(_TIPO, filas)
    _audit.record(actor, "crear_lote", None, fila)
    return fila


def actualizar(id_: str, cambios: dict, actor: str) -> dict:
    filas = listar()
    for f in filas:
        if f["id"] == id_:
            antes = dict(f)
            f.update({k: v for k, v in cambios.items() if k in _CAMPOS})
            esquema.reemplazar_filas(_TIPO, filas)
            _audit.record(actor, "editar_lote", antes, f)
            return f
    raise KeyError(id_)


def eliminar(id_: str, actor: str) -> None:
    filas = listar()
    quedan = [f for f in filas if f["id"] != id_]
    if len(quedan) == len(filas):
        raise KeyError(id_)
    borrado = next(f for f in filas if f["id"] == id_)
    esquema.reemplazar_filas(_TIPO, quedan)
    _audit.record(actor, "eliminar_lote", borrado, None)


def _enriquecer(row: dict) -> dict:
    """Add the counted-vs-system gap so the grid can filter and sort it."""
    out = dict(row)
    counted = out.get("counted_qty")
    if counted is None or counted == "":
        out["diferencia"] = None
        out["tiene_discrepancia"] = False
        return out
    try:
        diff = round(float(counted) - float(out.get("cantidad") or 0), 2)
    except (TypeError, ValueError):
        out["diferencia"] = None
        out["tiene_discrepancia"] = False
        return out
    out["diferencia"] = diff
    out["tiene_discrepancia"] = abs(diff) > QTY_EPS
    return out


def _rows(*, q: str = "", sort: str | None = "producto", direction: str = "asc",
          source: str | None = None, discrepancia: bool = False) -> list[dict]:
    rows = [_enriquecer(r) for r in listar()]
    rows = section_records.match_source(rows, source)
    if discrepancia:
        rows = [r for r in rows if r.get("tiene_discrepancia")]
    return paging.filter_sort(
        rows, q=q, search_in=SEARCH, sort=sort, direction=direction)


def list_page(*, q: str = "", sort: str | None = "producto", direction: str = "asc",
              offset: int = 0, limit: int = paging.DEFAULT_LIMIT,
              source: str | None = None, discrepancia: bool = False) -> dict:
    rows = _rows(q=q, sort=sort, direction=direction, source=source,
                 discrepancia=discrepancia)
    return paging.page_rows(rows, offset=offset, limit=limit)


def export_csv(*, q: str = "", sort: str | None = "producto", direction: str = "asc",
               source: str | None = None, discrepancia: bool = False) -> str:
    rows = _rows(q=q, sort=sort, direction=direction, source=source,
                 discrepancia=discrepancia)
    return paging.rows_to_csv(rows, CSV_COLUMNS)
