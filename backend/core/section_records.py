"""Generic create/update/delete + paginated list over an esquema section."""
from __future__ import annotations

import uuid

from . import esquema, paging
from .audit import AuditLog

_audit = AuditLog()


def ensure_ids(tipo: str) -> list[dict]:
    rows = esquema.filas(tipo)
    changed = False
    for row in rows:
        if not row.get("id"):
            row["id"] = uuid.uuid4().hex[:10]
            changed = True
    if changed:
        esquema.reemplazar_filas(tipo, rows)
    return rows


def match_source(rows: list[dict], source: str | None) -> list[dict]:
    if not source or source == "all":
        return rows
    if source == "odoo":
        return [r for r in rows if r.get("source") == "odoo"]
    if source == "manual":
        return [r for r in rows if r.get("source") == "manual"]
    if source == "csv":
        return [r for r in rows if r.get("source") not in ("odoo", "manual")]
    return [r for r in rows if r.get("source") == source]


def list_page(
    tipo: str,
    *,
    search_in: tuple[str, ...],
    date_field: str | None = None,
    q: str = "",
    sort: str | None = None,
    direction: str = "asc",
    offset: int = 0,
    limit: int = paging.DEFAULT_LIMIT,
    source: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    equals: dict | None = None,
    empty: tuple[str, ...] | list[str] | None = None,
    facet_fields: tuple[str, ...] | list[str] = (),
) -> dict:
    rows = match_source(ensure_ids(tipo), source)
    result = paging.page_rows(
        rows, q=q, search_in=search_in, sort=sort, direction=direction,
        offset=offset, limit=limit, equals=equals, empty=empty,
        date_field=date_field, date_from=date_from, date_to=date_to,
    )
    if facet_fields:
        result["facets"] = paging.collect_facets(rows, facet_fields)
    return result


def matching_rows(
    tipo: str,
    *,
    search_in: tuple[str, ...],
    date_field: str | None = None,
    q: str = "",
    sort: str | None = None,
    direction: str = "asc",
    source: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    equals: dict | None = None,
    empty: tuple[str, ...] | list[str] | None = None,
) -> list[dict]:
    rows = match_source(ensure_ids(tipo), source)
    return paging.filter_sort(
        rows, q=q, search_in=search_in, sort=sort, direction=direction,
        equals=equals, empty=empty, date_field=date_field,
        date_from=date_from, date_to=date_to,
    )


def create(tipo: str, fields: tuple[str, ...], required: tuple[str, ...],
           data: dict, actor: str, action: str) -> dict:
    for field in required:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError(f"{field}_requerido")
    rows = ensure_ids(tipo)
    row = {"id": uuid.uuid4().hex[:10]}
    for field in fields:
        if field in data:
            row[field] = data[field]
    if not row.get("source"):
        row["source"] = "manual"
    rows.append(row)
    esquema.reemplazar_filas(tipo, rows)
    _audit.record(actor, action, None, row)
    return row


def update(tipo: str, fields: tuple[str, ...], id_: str, changes: dict,
           actor: str, action: str) -> dict:
    rows = ensure_ids(tipo)
    for row in rows:
        if row.get("id") == id_:
            before = dict(row)
            row.update({k: v for k, v in changes.items() if k in fields and k != "id"})
            esquema.reemplazar_filas(tipo, rows)
            _audit.record(actor, action, before, row)
            return row
    raise KeyError(id_)


def delete(tipo: str, id_: str, actor: str, action: str) -> None:
    rows = ensure_ids(tipo)
    remaining = [r for r in rows if r.get("id") != id_]
    if len(remaining) == len(rows):
        raise KeyError(id_)
    deleted = next(r for r in rows if r.get("id") == id_)
    esquema.reemplazar_filas(tipo, remaining)
    _audit.record(actor, action, deleted, None)


def export_csv(tipo: str, columns: tuple[str, ...], **kwargs) -> str:
    rows = matching_rows(tipo, **kwargs)
    return paging.rows_to_csv(rows, columns)
