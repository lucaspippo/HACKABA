from __future__ import annotations

import json

from sqlalchemy import text

from core.db.engine import tenant_connection

_COLS = ("username, nombre, rol, es_admin, interno, telefono, color, "
         "superficies, descripcion, descripcion_en, features, ingreso, "
         "puesto, activo")

# Fields the caller may set on create()/update(). `username`/`tenant_id` are
# never touched here — the PK is set once at create() and never renamed.
_SETTABLE = ("nombre", "rol", "es_admin", "interno", "telefono", "color",
             "superficies", "descripcion", "descripcion_en", "features",
             "ingreso", "puesto")

_JSONB_FIELDS = {"superficies", "features", "puesto"}


def _to_usuario(row) -> dict:
    return {
        "username": row["username"],
        "nombre": row["nombre"],
        "rol": row["rol"],
        "es_admin": row["es_admin"],
        "interno": row["interno"],
        "telefono": row["telefono"],
        "color": row["color"],
        "superficies": row["superficies"],
        "descripcion": row["descripcion"],
        "descripcion_en": row["descripcion_en"],
        "features": row["features"],
        "ingreso": row["ingreso"].isoformat() if row["ingreso"] else None,
        "puesto": row["puesto"],
        "activo": row["activo"],
    }


def list_all(tenant_id: str, include_inactive: bool = False) -> list[dict]:
    query = f"SELECT {_COLS} FROM users"
    if not include_inactive:
        query += " WHERE activo = true"
    query += " ORDER BY created_at"
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(text(query)).mappings().all()
    return [_to_usuario(r) for r in rows]


def get(tenant_id: str, username: str, include_inactive: bool = True) -> dict | None:
    query = f"SELECT {_COLS} FROM users WHERE username = :u"
    if not include_inactive:
        query += " AND activo = true"
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(text(query), {"u": username}).mappings().first()
    return _to_usuario(row) if row else None


def create(tenant_id: str, usuario: dict) -> None:
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "INSERT INTO users "
                "(tenant_id, username, nombre, rol, es_admin, interno, telefono, "
                "color, superficies, descripcion, descripcion_en, features, "
                "ingreso, puesto) "
                "VALUES (:tid, :username, :nombre, :rol, :es_admin, :interno, "
                ":telefono, :color, :superficies, :descripcion, :descripcion_en, "
                ":features, :ingreso, :puesto)"
            ),
            {
                "tid": tenant_id,
                "username": usuario["username"],
                "nombre": usuario["nombre"],
                "rol": usuario["rol"],
                "es_admin": bool(usuario.get("es_admin", False)),
                "interno": bool(usuario.get("interno", False)),
                "telefono": usuario.get("telefono"),
                "color": usuario.get("color"),
                "superficies": json.dumps(usuario.get("superficies") or []),
                "descripcion": usuario.get("descripcion"),
                "descripcion_en": usuario.get("descripcion_en"),
                "features": json.dumps(usuario.get("features") or []),
                "ingreso": usuario.get("ingreso"),
                "puesto": json.dumps(usuario["puesto"]) if usuario.get("puesto") else None,
            },
        )


def update(tenant_id: str, username: str, cambios: dict) -> dict | None:
    """Partial update — only keys present in `cambios` (from _SETTABLE) are
    touched. Returns the updated row, or None if the user doesn't exist."""
    campos = {k: v for k, v in cambios.items() if k in _SETTABLE}
    if not campos:
        return get(tenant_id, username)
    sets = ", ".join(f"{k} = :{k}" for k in campos)
    params = {k: (json.dumps(v) if k in _JSONB_FIELDS and v is not None else v)
              for k, v in campos.items()}
    params["u"] = username
    with tenant_connection(tenant_id) as conn:
        conn.execute(text(f"UPDATE users SET {sets} WHERE username = :u"), params)
    return get(tenant_id, username)


def set_active(tenant_id: str, username: str, activo: bool) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text("UPDATE users SET activo = :activo WHERE username = :u"),
            {"activo": activo, "u": username},
        )
    return get(tenant_id, username)
