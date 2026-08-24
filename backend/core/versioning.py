from __future__ import annotations


class VersionStore:
    """Snapshots inmutables del dato. Cada save crea una versión nueva;
    ninguna versión previa se modifica. Restore devuelve el snapshot tal cual."""

    def __init__(self, base_dir: str | None = None):
        # base_dir is unused now (Postgres, not JSON) — kept as a parameter
        # so existing call sites (core/store.py, etc.) don't need to change.
        pass

    def save(self, data: dict, motivo: str, autor: str = "sistema") -> dict:
        from core.db import versions_repo, tenant as _tenant
        tid = _tenant.current_tenant_id()
        return versions_repo.save(tid, data, reason=motivo, author=autor)

    def list(self) -> list[dict]:
        from core.db import versions_repo, tenant as _tenant
        tid = _tenant.current_tenant_id()
        return versions_repo.list_versions(tid)

    def restore(self, version_id: int) -> dict:
        from core.db import versions_repo, tenant as _tenant
        tid = _tenant.current_tenant_id()
        return versions_repo.restore(tid, version_id)
