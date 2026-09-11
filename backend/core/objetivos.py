"""
Objetivos del equipo — persistencia SERVER-SIDE (P9·C5, M9).

Antes, `crear_objetivo` de Ángela vivía solo en el localStorage de quien lo
pedía: el resto del equipo no lo veía y un navegador limpio lo borraba. Ahora
el objetivo se persiste acá (JSON por tenant, como recordatorios) y el tablero
de todos lo sincroniza. El id puede venir del cliente (uid del tablero) para
que la mezcla local↔server sea idempotente, sin duplicados.
"""
from __future__ import annotations

import secrets

ESTADOS = ("pendiente", "en_proceso", "listo")


def crear(nombre: str, responsable: str | None = None, fecha: str | None = None,
          creado_por: str | None = None, oid: str | None = None) -> dict:
    from core.db import team_goals_repo, tenant as _tenant
    tid = _tenant.current_tenant_id()
    if oid:
        ya = team_goals_repo.get(tid, oid)
        if ya:
            return ya  # idempotente: el cliente reintenta sin duplicar
    o = {
        "id": oid or "ob" + secrets.token_hex(3),
        "nombre": (nombre or "").strip(),
        "responsable": responsable or "Sin asignar",
        "fecha": fecha or "sin fecha",
        "estado": "pendiente",
        "creado_por": creado_por or "dueño",
    }
    team_goals_repo.create(tid, o)
    return team_goals_repo.get(tid, o["id"])


def listar() -> list[dict]:
    from core.db import team_goals_repo, tenant as _tenant
    return team_goals_repo.list_goals(_tenant.current_tenant_id())


def cambiar_estado(oid: str, estado: str) -> dict:
    if estado not in ESTADOS:
        raise ValueError(f"estado inválido: {estado}")
    from core.db import team_goals_repo, tenant as _tenant
    tid = _tenant.current_tenant_id()
    o = team_goals_repo.get(tid, oid)
    if not o:
        raise KeyError("objetivo inexistente")
    team_goals_repo.update_status(tid, oid, estado)
    o["estado"] = estado
    return o
