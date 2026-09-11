"""
Seeds (or resets) a tenant's row, its auth credentials, and every domain
migrated to Postgres so far (cuentas, audit, versioning*, inventory, caja —
* versioning has no seed data, it's an empty append-only log for a new
tenant). Ports data-demo/generar.py's role for those domains — as more
core/*.py modules move off JSON, see backend/core/db/MIGRATING_A_MODULE.md,
their seed data joins this script the same way: trigger the module's own
first-read, which already knows to prefer its real on-disk dataset over its
in-code fallback. Don't duplicate seed data here.

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

    # Each call below triggers that module's own first-read seed (real
    # on-disk dataset if present, else its in-code fallback) — see the
    # module docstring above for why nothing is duplicated here. Modules
    # with no seed data at all (purchase_orders, team_goals, notifications —
    # they start empty for every tenant, same as the old missing-file
    # behavior) don't need a call here.
    from core import cuentas as core_cuentas
    core_cuentas.listar()  # customer_accounts / account_movements

    from core import store as core_store
    core_store.raw_actual()  # inventory_working
    core_store.audit.list()  # audit_events

    from core import caja as core_caja
    core_caja.estado()  # caja_state

    from core import organizacion as core_organizacion
    core_organizacion.get()  # organization_config

    from core import reposicion as core_reposicion
    core_reposicion.condiciones()  # supplier_conditions

    from core import notas as core_notas
    core_notas.listar()  # team_notes

    from core import mostrador as core_mostrador
    core_mostrador._load()  # retail_counter_data

    from core import traslados as core_traslados
    core_traslados._load()  # internal_transfers

    from core import sync as core_sync
    core_sync._baseline()  # inventory_baseline

    from core import extraccion as core_extraccion
    core_extraccion._muestras()  # sample_extractions

    from core import pagos as core_pagos
    core_pagos._load()  # finance_data

    from core import ventas_cliente as core_ventas_cliente
    core_ventas_cliente._load()  # client_sales_data

    print(f"[seed_db] tenant '{tenant_slug}' ({tid}) seeded", flush=True)


if __name__ == "__main__":
    slug = sys.argv[1] if len(sys.argv) > 1 else "demo"
    run(slug)
