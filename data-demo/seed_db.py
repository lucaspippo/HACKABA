"""
Seeds (or resets) a tenant's row, its auth credentials, and every domain
migrated to Postgres (all of core/*.py's storage, per
backend/core/db/MIGRATING_A_MODULE.md). Ports data-demo/generar.py's role
for those domains: seed_domains() below triggers each module's own
first-read, which already knows to prefer its real on-disk dataset over its
in-code fallback. Don't duplicate seed data here.

run() must run as a fresh process per tenant, never called for a second
tenant from within an already-running one: core.paths.TENANT/DATA_DIR are
resolved once at first import (same one-process-per-tenant assumption the
rest of the codebase makes — see the plan's Global Constraints) and won't
retarget just because POLPILOT_TENANT changes later in that same process.
seed_domains() alone is safe to call from within an already-running process
for its OWN tenant — see its docstring.

ensure_tenant() must run BEFORE data-demo/generar.py, not after — generar.py
calls directly into Postgres-backed core modules (core.staging,
core.perfiles, core.comprobantes) partway through, which need the tenant
row to already exist. See deploy/boot.py for the full correct order:
Alembic -> ensure_tenant() -> generar.py -> run() (or just seed_domains()
+ credentials, since ensure_tenant() already ran).

Usage: python seed_db.py [tenant_slug]   (default: demo)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import text  # noqa: E402

from core.db.engine import get_admin_engine  # noqa: E402


def ensure_tenant(tenant_slug: str = "demo", *, name: str | None = None,
                   short_name: str | None = None, source: str | None = None) -> str:
    """Idempotent: creates the `tenants` row if missing, returns its id.
    Split out of run() because it has to happen BEFORE generar.py runs —
    generar.py's sembrar_staging()/sembrar_auditoria()/etc. call directly
    into now-Postgres-backed core modules (core.staging, core.perfiles,
    core.comprobantes), which raise if the tenant has no row yet. A tenant
    that already has a row from an earlier boot masked this for months;
    a genuinely fresh Postgres (first-ever boot, or CI) hit it immediately
    — see deploy/boot.py's step ordering and the CI workflow."""
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
    os.environ["POLPILOT_TENANT"] = tenant_slug
    return str(tid)


DEMO_PASSWORD_ENV = "POLPILOT_DEMO_PASSWORD"
DEFAULT_DEMO_PASSWORD = "demo-password"


def demo_password() -> str:
    """The one password every seeded user gets, so a freshly seeded tenant is
    always loggable-into. Override per environment with POLPILOT_DEMO_PASSWORD
    (do set it for any deployment reachable from outside a dev machine).

    Fixed, but never stored in the clear: seed_credentials() bcrypts it with a
    per-user salt, in every environment.
    """
    return os.environ.get(DEMO_PASSWORD_ENV) or DEFAULT_DEMO_PASSWORD


def seed_credentials(tid: str, roster) -> None:
    """Assert demo_password() for every user in the roster.

    ASSERT, not fill-in-if-missing: this is the repair path for a tenant whose
    hashes drifted (anything that wrote a different hash used to make the
    documented password permanently wrong, since the old code skipped any user
    who already had a row). Re-hashing only when the stored hash doesn't
    already accept the password keeps it idempotent and avoids churning
    updated_at on every boot.
    """
    import bcrypt

    from core.db import credentials_repo

    pw = demo_password().encode("utf-8")
    for username in roster:
        actual = credentials_repo.get(tid, username)
        if actual:
            try:
                if bcrypt.checkpw(pw, actual.encode("utf-8")):
                    continue
            except ValueError:
                pass  # unparseable/corrupt hash — fall through and replace it
        credentials_repo.set(tid, username, bcrypt.hashpw(pw, bcrypt.gensalt()).decode())


def run(tenant_slug: str = "demo", *, name: str | None = None,
        short_name: str | None = None, source: str | None = None) -> None:
    tid = ensure_tenant(tenant_slug, name=name, short_name=short_name, source=source)
    from core.db import credentials_repo

    # auth.USUARIOS is lazy and Postgres-backed (core/db/users_repo.py): the
    # first touch seeds the `users` table from the right in-code roster for
    # this tenant (usuarios_demo.USUARIOS for "demo", the Horizonte seed
    # otherwise — see auth._seed_roster()), so this one access covers both
    # "what usernames need a credential" below AND seeding `users` itself.
    import auth
    roster = auth.USUARIOS

    seed_credentials(tid, roster)
    seed_domains()
    print(f"[seed_db] tenant '{tenant_slug}' ({tid}) seeded", flush=True)


def _dominios():
    """(domain, seed files, tables to empty on re-seed, the module's own read).

    ONLY the domains with a real file in DATA_DIR are listed: those are the
    ones a changed dataset can reach. The others (organizacion, extraccion,
    sync, users) have no on-disk seed — they keep their in-code fallback and
    are seeded below, untracked, exactly as before.

    `cargar` is never a new seeding path: it is the same first read
    seed_domains() has always called.
    """
    from core import (caja, conocimiento, cuentas, esquema, mostrador, notas,
                      pagos, piso, reposicion, store, traslados, ventas,
                      ventas_cliente)
    return [
        ("inventory_working", ["inventory.json"], ["inventory_working"],
         store.raw_actual),
        ("audit_events", ["audit.json"], ["audit_events"], store.audit.list),
        # account_movements first: it points at customer_accounts.
        ("customer_accounts", ["cuentas.json"],
         ["account_movements", "customer_accounts"], cuentas.listar),
        ("caja_state", ["caja.json"], ["caja_state"], caja.estado),
        ("supplier_conditions", ["proveedores_condiciones.json"],
         ["supplier_conditions"], reposicion.condiciones),
        ("team_notes", ["notas_equipo.json"], ["team_notes"], notas.listar),
        ("retail_counter_data", ["mostrador.json"], ["retail_counter_data"],
         mostrador._load),
        ("internal_transfers", ["traslados_internos.json"],
         ["internal_transfers"], traslados._load),
        ("finance_data", ["finanzas.json"], ["finance_data"], pagos._load),
        ("client_sales_data", ["ventas_por_cliente.json"],
         ["client_sales_data"], ventas_cliente._load),
        ("business_knowledge_pieces", ["conocimiento_negocio.json"],
         ["business_knowledge_pieces"], conocimiento.listar),
        ("data_sections", ["apartados.json"], ["data_sections"], esquema._load),
        ("sales_validation", ["ventas_validacion.json"], ["sales_validation"],
         ventas._val_load),
        # Lo que el piso reportó. El demo arrancaba con cero, y por eso el
        # circuito entero —aviso dirigido, acuse, reclamo del dueño— no se veía
        # en ninguna pantalla aunque el motor existiera.
        ("floor_reports", ["piso_seed/reportes.json"], ["floor_reports"],
         piso.listar),
    ]


def seed_domains() -> None:
    """Triggers every migrated domain module's own first-read seed (real
    on-disk dataset if present, else its in-code fallback) — see the module
    docstring above for why nothing is duplicated here. Modules with no seed
    data at all (purchase_orders, team_goals, notifications — they start
    empty for every tenant, same as the old missing-file behavior) don't
    need a call here.

    Since 0042 this also RE-seeds a domain whose on-disk file changed, on a
    tenant that regenerates its dataset on boot. See core/db/seed_state.py
    for the rule and for why the hash is of the file and never of the blob.

    Unlike run(), this assumes POLPILOT_TENANT/core.paths.TENANT are ALREADY
    correctly set for the current process — true both when run() calls this
    from a fresh subprocess, and when an already-running server process
    (which resolved its own tenant at boot) calls this directly to re-seed
    after core.db.reset.truncate_business_data() (see main.py's
    admin_reset_demo)."""
    import auth
    from core import paths
    from core.db import seed_state
    auth.reload_usuarios()  # users table — reload_usuarios() (not usuarios())
    # so a mid-process call after core.db.reset.truncate_business_data()
    # actually re-seeds instead of returning the stale in-process cache.

    for dominio, archivos, tablas, cargar in _dominios():
        seed_state.sembrar(dominio, [os.path.join(paths.DATA_DIR, a) for a in archivos],
                           tablas, cargar)

    # No on-disk seed: in-code fallback, nothing to track.
    from core import organizacion as core_organizacion
    core_organizacion.get()  # organization_config

    from core import extraccion as core_extraccion
    core_extraccion._muestras()  # sample_extractions

    from core import sync as core_sync
    core_sync._baseline()  # inventory_baseline


def revisar_seeds() -> None:
    """What a tenant that does NOT re-seed runs at boot: compares and warns,
    touching nothing. Without this, a dataset that changed under a productive
    tenant would be silent — and silence is the failure mode this whole
    change exists to remove."""
    from core import paths
    from core.db import seed_state
    for dominio, archivos, _tablas, _cargar in _dominios():
        seed_state.revisar(dominio, [os.path.join(paths.DATA_DIR, a) for a in archivos])

if __name__ == "__main__":
    slug = sys.argv[1] if len(sys.argv) > 1 else "demo"
    run(slug)
