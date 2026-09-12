"""CRUD over ingested sale lines (esquema section `venta`)."""
from __future__ import annotations

from . import paging, section_records

TYPE = "venta"
FIELDS = ("fecha", "producto", "codigo", "cantidad", "precio",
          "source", "source_id", "source_status")
REQUIRED = ("producto",)
SEARCH = ("fecha", "producto", "codigo", "source")
CSV_COLUMNS = ("fecha", "producto", "codigo", "cantidad", "precio", "source")
_LIST_KW = dict(search_in=SEARCH, date_field="fecha")


def _coerce(data: dict) -> dict:
    out = dict(data)
    if "cantidad" in out and out["cantidad"] is not None:
        out["cantidad"] = float(out["cantidad"])
    if "precio" in out and out["precio"] not in (None, ""):
        out["precio"] = float(out["precio"])
    if "codigo" in out and out["codigo"] not in (None, ""):
        out["codigo"] = int(out["codigo"])
    return out


def list_page(*, q: str = "", sort: str | None = "fecha", direction: str = "desc",
              offset: int = 0, limit: int = paging.DEFAULT_LIMIT,
              source: str | None = None, date_from: str | None = None,
              date_to: str | None = None) -> dict:
    return section_records.list_page(
        TYPE, **_LIST_KW, q=q, sort=sort, direction=direction,
        offset=offset, limit=limit, source=source,
        date_from=date_from, date_to=date_to,
    )


def create(data: dict, actor: str) -> dict:
    return section_records.create(TYPE, FIELDS, REQUIRED, _coerce(data), actor, "crear_venta")


def update(id_: str, changes: dict, actor: str) -> dict:
    return section_records.update(TYPE, FIELDS, id_, _coerce(changes), actor, "editar_venta")


def delete(id_: str, actor: str) -> None:
    section_records.delete(TYPE, id_, actor, "eliminar_venta")


def export_csv(*, q: str = "", sort: str | None = "fecha", direction: str = "desc",
               source: str | None = None, date_from: str | None = None,
               date_to: str | None = None) -> str:
    return section_records.export_csv(
        TYPE, CSV_COLUMNS, **_LIST_KW, q=q, sort=sort, direction=direction,
        source=source, date_from=date_from, date_to=date_to,
    )
