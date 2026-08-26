from __future__ import annotations

from sqlalchemy import text

from core.db.engine import tenant_connection, to_local_iso

_COLS = "id, name, owner, target_date, status, created_by, created_at"


def _to_goal(row) -> dict:
    return {
        "id": row["id"],
        "nombre": row["name"],
        "responsable": row["owner"],
        "fecha": row["target_date"],
        "estado": row["status"],
        "creado_por": row["created_by"],
        "creado": to_local_iso(row["created_at"]),
    }


def list_goals(tenant_id: str) -> list[dict]:
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(
            text(f"SELECT {_COLS} FROM team_goals ORDER BY created_at DESC")
        ).mappings().all()
    return [_to_goal(r) for r in rows]


def get(tenant_id: str, goal_id: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(f"SELECT {_COLS} FROM team_goals WHERE id = :id"),
            {"id": goal_id},
        ).mappings().first()
    return _to_goal(row) if row else None


def create(tenant_id: str, goal: dict) -> None:
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "INSERT INTO team_goals (tenant_id, id, name, owner, target_date, status, created_by) "
                "VALUES (:tid, :id, :name, :owner, :target_date, :status, :created_by)"
            ),
            {
                "tid": tenant_id,
                "id": goal["id"],
                "name": goal["nombre"],
                "owner": goal["responsable"],
                "target_date": goal["fecha"],
                "status": goal["estado"],
                "created_by": goal["creado_por"],
            },
        )


def update_status(tenant_id: str, goal_id: str, status: str) -> None:
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text("UPDATE team_goals SET status = :status WHERE id = :id"),
            {"status": status, "id": goal_id},
        )
