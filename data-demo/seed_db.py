"""
Seeds (or resets) a tenant's row plus its auth credentials and cuentas data
into Postgres. Ports data-demo/generar.py's role for the domains migrated so
far (cuentas only, so far — as more core/*.py modules move off JSON, see
backend/core/db/MIGRATING_A_MODULE.md, their seed data joins this script).

Must run as a fresh process per tenant, never called for a second tenant
from within an already-running one: core.paths.TENANT/DATA_DIR are resolved
once at first import (same one-process-per-tenant assumption the rest of the
codebase makes — see the plan's Global Constraints) and won't retarget just
because POLPILOT_TENANT changes later in that same process.

Usage: python seed_db.py [tenant_slug]   (default: demo)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import text  # noqa: E402

from core.db.engine import get_admin_engine  # noqa: E402


def run(tenant_slug: str = "demo", *, name: str | None = None,
        short_name: str | None = None, source: str | None = None) -> None:
    admin = get_admin_engine()
    with admin.begin() as conn:
        tid = conn.execute(
            text("SELECT id FROM tenants WHERE slug = :slug"), {"slug": tenant_slug}
        ).scalar_one_or_none()
        if tid is None:
            tid = conn.execute(
                text(
                    "INSERT INTO tenants (slug, name, short_name, source) "
                    "VALUES (:slug, :name, :short_name, :source) RETURNING id"
                ),
                {
                    "slug": tenant_slug,
                    "name": name or "Distribuidora del Litoral",
                    "short_name": short_name or "Distribuidora del Litoral",
                    "source": source or "ERP de la distribuidora - nucleo de verdad PolPilot (DEMO)",
                },
            ).scalar_one()
    tid = str(tid)

    os.environ["POLPILOT_TENANT"] = tenant_slug
    from core.db import credentials_repo

    if tenant_slug == "demo":
        import usuarios_demo
        roster = usuarios_demo.USUARIOS
    else:
        import auth
        roster = auth.USUARIOS

    for username in roster:
        if credentials_repo.get(tid, username) is None:
            import bcrypt
            credentials_repo.set(tid, username, bcrypt.hashpw(b"demo-password", bcrypt.gensalt()).decode())

    # Triggers the customer_accounts/account_movements seed — core.cuentas.
    # _load() already knows to read this tenant's real cuentas.json off disk
    # when present (data-demo/cuentas.json for "demo") and falls back to its
    # own small _SEED otherwise. Don't duplicate that seed data here.
    from core import cuentas as core_cuentas
    core_cuentas.listar()

    print(f"[seed_db] tenant '{tenant_slug}' ({tid}) seeded", flush=True)


if __name__ == "__main__":
    slug = sys.argv[1] if len(sys.argv) > 1 else "demo"
    run(slug)
