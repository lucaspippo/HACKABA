"""Filter, sort, and slice row lists for paginated CRUD endpoints."""
from __future__ import annotations

import csv
import io

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_LIMIT
    return max(1, min(int(limit), MAX_LIMIT))


def _haystack(row: dict, fields: tuple[str, ...]) -> str:
    if fields:
        values = [row.get(f) for f in fields]
    else:
        values = row.values()
    return " ".join("" if v is None else str(v) for v in values).lower()


def _sort_key(row: dict, field: str):
    value = row.get(field)
    if value is None or value == "":
        return (1, "")
    if isinstance(value, (int, float)):
        return (0, value)
    try:
        return (0, float(value))
    except (TypeError, ValueError):
        return (0, str(value).lower())


def collect_facets(rows: list[dict], fields: tuple[str, ...] | list[str]) -> dict:
    """Unique non-empty values per field, sorted, for filter dropdowns."""
    out: dict[str, list] = {}
    for field in fields:
        seen: list[str] = []
        used: set[str] = set()
        for row in rows:
            value = row.get(field)
            if value in (None, ""):
                continue
            key = str(value)
            if key not in used:
                used.add(key)
                seen.append(key)
        seen.sort(key=str.lower)
        out[field] = seen
    return out


def filter_sort(
    rows: list[dict],
    *,
    q: str = "",
    search_in: tuple[str, ...] = (),
    sort: str | None = None,
    direction: str = "asc",
    equals: dict | None = None,
    empty: tuple[str, ...] | list[str] | None = None,
    date_field: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """Filter and sort without slicing — used by both pagination and CSV export."""
    filtered = list(rows)
    if equals:
        for key, expected in equals.items():
            if expected in (None, "", "all"):
                continue
            filtered = [r for r in filtered if r.get(key) == expected]
    if empty:
        for key in empty:
            filtered = [r for r in filtered if r.get(key) in (None, "")]
    if date_field and (date_from or date_to):
        lo = date_from or ""
        hi = date_to or "\uffff"
        filtered = [
            r for r in filtered
            if lo <= str(r.get(date_field) or "") <= hi
        ]
    needle = (q or "").strip().lower()
    if needle:
        filtered = [r for r in filtered if needle in _haystack(r, search_in)]
    if sort:
        reverse = (direction or "asc").lower() == "desc"
        filtered.sort(key=lambda r: _sort_key(r, sort), reverse=reverse)
    return filtered


def page_rows(
    rows: list[dict],
    *,
    q: str = "",
    search_in: tuple[str, ...] = (),
    sort: str | None = None,
    direction: str = "asc",
    offset: int = 0,
    limit: int = DEFAULT_LIMIT,
    equals: dict | None = None,
    empty: tuple[str, ...] | list[str] | None = None,
    date_field: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Return `{items, total, offset, limit, has_more}` after filter/sort/slice."""
    filtered = filter_sort(
        rows, q=q, search_in=search_in, sort=sort, direction=direction,
        equals=equals, empty=empty, date_field=date_field,
        date_from=date_from, date_to=date_to,
    )
    total = len(filtered)
    offset = max(0, int(offset or 0))
    limit = clamp_limit(limit)
    items = filtered[offset:offset + limit]
    return {
        "items": items,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(items) < total,
    }


def rows_to_csv(rows: list[dict], columns: tuple[str, ...] | list[str]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(list(columns))
    for row in rows:
        writer.writerow(["" if row.get(c) is None else row.get(c) for c in columns])
    return buf.getvalue()
