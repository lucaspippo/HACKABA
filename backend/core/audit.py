from __future__ import annotations

import json
import os


def _seed_inicial() -> list[dict]:
    """El historial REAL del tenant si existe en disco (p.ej. data-demo/
    audit.json, regenerado por data-demo/generar.py en cada boot), usado
    SOLO para la siembra inicial en Postgres (una vez por tenant). Sin
    archivo, no hay nada que sembrar — un tenant nuevo empieza con el
    registro vacío (es append-only, no tiene fallback tipo _SEED)."""
    from core import paths
    archivo = os.path.join(paths.DATA_DIR, "audit.json")
    if not os.path.exists(archivo):
        return []
    try:
        return json.load(open(archivo, encoding="utf-8"))
    except Exception:
        return []


class AuditLog:
    """Registro append-only de toda acción sobre los datos: quién, qué,
    antes y después. Es la trazabilidad que sostiene la confianza."""

    def __init__(self, base_dir: str | None = None):
        # base_dir ya no se usa (Postgres, no JSON) — se mantiene el parámetro
        # para no romper los call sites existentes (core/store.py, etc.).
        pass

    def record(self, actor: str, accion: str, antes=None, despues=None) -> dict:
        from core.db import audit_repo, tenant as _tenant
        tid = _tenant.current_tenant_id()
        audit_repo.seed_if_empty(tid, _seed_inicial())
        return audit_repo.record(tid, actor=actor, action=accion, before=antes, after=despues)

    def list(self) -> list[dict]:
        from core.db import audit_repo, tenant as _tenant
        tid = _tenant.current_tenant_id()
        audit_repo.seed_if_empty(tid, _seed_inicial())
        return audit_repo.list_events(tid)
