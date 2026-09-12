"""One row per business-knowledge piece — core/conocimiento.py's storage,
normalized (see migration 0039; replaces the one-JSONB-blob-per-tenant
`business_knowledge` table from 0025). Every function returns/accepts the
same Spanish-keyed dict shape core/conocimiento.py's callers already
depend on; only the storage underneath is a real table."""
from __future__ import annotations

import json

from sqlalchemy import text

from core.db.engine import tenant_connection

_COLS = ("id", "texto", "texto_en", "tipo", "ambito", "entidad", "nodo",
         "efecto", "efecto_profundo", "params", "origen", "estado",
         "veces_aplicada")


def _to_piece(row) -> dict:
    return {
        "id": row["id"],
        "texto": row["texto"],
        "texto_en": row["texto_en"],
        "tipo": row["tipo"],
        "ambito": row["ambito"],
        "entidad": row["entidad"],
        "nodo": row["nodo"],
        "efecto": row["efecto"],
        "efecto_profundo": row["efecto_profundo"],
        "params": row["params"] or {},
        "origen": row["origen"] or {},
        "estado": row["estado"],
        "veces_aplicada": row["veces_aplicada"],
    }


def list_pieces(tenant_id: str) -> list[dict]:
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(
            text(f"SELECT {', '.join(_COLS)} FROM business_knowledge_pieces "
                 "ORDER BY created_at")
        ).mappings().all()
    return [_to_piece(r) for r in rows]


def get(tenant_id: str, piece_id: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(f"SELECT {', '.join(_COLS)} FROM business_knowledge_pieces "
                 "WHERE id = :id"),
            {"id": piece_id},
        ).mappings().one_or_none()
    return _to_piece(row) if row else None


def create(tenant_id: str, *, id: str, texto: str, tipo: str, ambito: str,
          nodo: str, efecto: str, entidad: str | None = None,
          texto_en: str | None = None, efecto_profundo: bool = False,
          params: dict | None = None, origen: dict | None = None,
          estado: str = "activo", veces_aplicada: int = 0) -> dict:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "INSERT INTO business_knowledge_pieces "
                "(id, tenant_id, texto, texto_en, tipo, ambito, entidad, nodo, "
                " efecto, efecto_profundo, params, origen, estado, veces_aplicada) "
                "VALUES (:id, :tid, :texto, :texto_en, :tipo, :ambito, :entidad, :nodo, "
                " :efecto, :efecto_profundo, :params, :origen, :estado, :veces_aplicada) "
                f"RETURNING {', '.join(_COLS)}"
            ),
            {"id": id, "tid": tenant_id, "texto": texto, "texto_en": texto_en,
             "tipo": tipo, "ambito": ambito, "entidad": entidad, "nodo": nodo,
             "efecto": efecto, "efecto_profundo": efecto_profundo,
             "params": json.dumps(params or {}), "origen": json.dumps(origen or {}),
             "estado": estado, "veces_aplicada": veces_aplicada},
        ).mappings().one()
    return _to_piece(row)


def set_status(tenant_id: str, piece_id: str, estado: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "UPDATE business_knowledge_pieces SET estado = :estado "
                f"WHERE id = :id RETURNING {', '.join(_COLS)}"
            ),
            {"estado": estado, "id": piece_id},
        ).mappings().one_or_none()
    return _to_piece(row) if row else None


def increment_applied(tenant_id: str, piece_id: str, n: int = 1) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "UPDATE business_knowledge_pieces "
                "SET veces_aplicada = veces_aplicada + :n "
                f"WHERE id = :id RETURNING {', '.join(_COLS)}"
            ),
            {"n": n, "id": piece_id},
        ).mappings().one_or_none()
    return _to_piece(row) if row else None


def delete(tenant_id: str, piece_id: str) -> bool:
    with tenant_connection(tenant_id) as conn:
        result = conn.execute(
            text("DELETE FROM business_knowledge_pieces WHERE id = :id"),
            {"id": piece_id},
        )
    return result.rowcount > 0


def seed_if_empty(tenant_id: str, seed: dict) -> None:
    """Bulk-loads a tenant's real, already-generated knowledge base (e.g. the
    demo tenant's data-demo/conocimiento_negocio.json) exactly once. `seed`
    is the old `{"piezas": [...]}` shape the JSON file already used."""
    piezas = (seed or {}).get("piezas") or []
    with tenant_connection(tenant_id) as conn:
        count = conn.execute(
            text("SELECT count(*) FROM business_knowledge_pieces")
        ).scalar_one()
        if count or not piezas:
            return
        for p in piezas:
            conn.execute(
                text(
                    "INSERT INTO business_knowledge_pieces "
                    "(id, tenant_id, texto, texto_en, tipo, ambito, entidad, nodo, "
                    " efecto, efecto_profundo, params, origen, estado, veces_aplicada) "
                    "VALUES (:id, :tid, :texto, :texto_en, :tipo, :ambito, :entidad, :nodo, "
                    " :efecto, :efecto_profundo, :params, :origen, :estado, :veces_aplicada) "
                    "ON CONFLICT (tenant_id, id) DO NOTHING"
                ),
                {"id": p["id"], "tid": tenant_id, "texto": p.get("texto", ""),
                 "texto_en": p.get("texto_en"), "tipo": p["tipo"], "ambito": p["ambito"],
                 "entidad": p.get("entidad"), "nodo": p["nodo"], "efecto": p["efecto"],
                 "efecto_profundo": p.get("efecto_profundo", False),
                 "params": json.dumps(p.get("params") or {}),
                 "origen": json.dumps(p.get("origen") or {}),
                 "estado": p.get("estado", "activo"),
                 "veces_aplicada": int(p.get("veces_aplicada", 0))},
            )
