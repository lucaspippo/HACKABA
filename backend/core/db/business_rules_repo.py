"""One row per structured business rule — core/rules.py's storage. See
migration 0048 and docs/superpowers/specs/2026-09-11-structured-business-rules-design.md."""
from __future__ import annotations

import json

from sqlalchemy import text

from core.db.engine import tenant_connection

_COLS = ("id", "description", "condition", "action", "node", "scope",
         "entity_name", "entity_type", "entity_id", "origin",
         "knowledge_piece_id", "status", "supersedes", "superseded_by",
         "version", "test_cases", "created_at")


def _to_rule(row) -> dict:
    return {
        "id": row["id"],
        "description": row["description"],
        "condition": row["condition"],
        "action": row["action"],
        "node": row["node"],
        "scope": row["scope"],
        "entity_name": row["entity_name"],
        "entity_type": row["entity_type"],
        "entity_id": row["entity_id"],
        "origin": row["origin"] or {},
        "knowledge_piece_id": row["knowledge_piece_id"],
        "status": row["status"],
        "supersedes": row["supersedes"],
        "superseded_by": row["superseded_by"],
        "version": row["version"],
        "test_cases": row["test_cases"] or [],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


def list_rules(tenant_id: str) -> list[dict]:
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(
            text(f"SELECT {', '.join(_COLS)} FROM business_rules ORDER BY created_at")
        ).mappings().all()
    return [_to_rule(r) for r in rows]


def get(tenant_id: str, rule_id: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(f"SELECT {', '.join(_COLS)} FROM business_rules WHERE id = :id"),
            {"id": rule_id},
        ).mappings().one_or_none()
    return _to_rule(row) if row else None


def create(tenant_id: str, *, id: str, description: str, condition: dict,
          action: list, node: str, scope: str, entity_name: str | None = None,
          entity_type: str | None = None, entity_id: str | None = None,
          origin: dict | None = None, knowledge_piece_id: str | None = None,
          status: str = "active", supersedes: str | None = None,
          version: int = 1, test_cases: list | None = None) -> dict:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "INSERT INTO business_rules "
                "(id, tenant_id, description, condition, action, node, scope, "
                " entity_name, entity_type, entity_id, origin, knowledge_piece_id, "
                " status, supersedes, version, test_cases) "
                "VALUES (:id, :tid, :description, :condition, :action, :node, :scope, "
                " :entity_name, :entity_type, :entity_id, :origin, :knowledge_piece_id, "
                " :status, :supersedes, :version, :test_cases) "
                f"RETURNING {', '.join(_COLS)}"
            ),
            {"id": id, "tid": tenant_id, "description": description,
             "condition": json.dumps(condition), "action": json.dumps(action),
             "node": node, "scope": scope, "entity_name": entity_name,
             "entity_type": entity_type, "entity_id": entity_id,
             "origin": json.dumps(origin or {}), "knowledge_piece_id": knowledge_piece_id,
             "status": status, "supersedes": supersedes, "version": version,
             "test_cases": json.dumps(test_cases or [])},
        ).mappings().one()
    return _to_rule(row)


def set_status(tenant_id: str, rule_id: str, status: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "UPDATE business_rules SET status = :status "
                f"WHERE id = :id RETURNING {', '.join(_COLS)}"
            ),
            {"status": status, "id": rule_id},
        ).mappings().one_or_none()
    return _to_rule(row) if row else None


def set_supersedes(tenant_id: str, rule_id: str, *, supersedes: str,
                   version: int) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "UPDATE business_rules SET supersedes = :supersedes, version = :version "
                f"WHERE id = :id RETURNING {', '.join(_COLS)}"
            ),
            {"supersedes": supersedes, "version": version, "id": rule_id},
        ).mappings().one_or_none()
    return _to_rule(row) if row else None


def set_superseded_by(tenant_id: str, rule_id: str, *, superseded_by: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "UPDATE business_rules SET status = 'superseded', superseded_by = :sup_by "
                f"WHERE id = :id RETURNING {', '.join(_COLS)}"
            ),
            {"sup_by": superseded_by, "id": rule_id},
        ).mappings().one_or_none()
    return _to_rule(row) if row else None
