"""Re-seed a domain when its on-disk seed file changed.

THE TRAP THIS CLOSES. Fourteen `core/*.py` modules seed the same way: read
the tenant's blob, and only if it is missing fall back to the real dataset in
`data-demo/<file>.json` and save it. That is correct for a productive tenant —
its data is its own — and it is a trap for the public demo: `generar.py`
rewrites the dataset on every boot, the blob already exists from the first
boot ever, and the new dataset never arrives. Measured in production: the
operation map's channel band said "0 de 17" for days because
`notas_equipo.json` had grown to 31 notes and `team_notes` still held the 17
from the first seed. The apartados had the same problem.

THE RULE, IN ONE LINE. A tenant that regenerates its dataset on every boot
(`POLPILOT_SEED_ON_BOOT=1`) re-seeds any domain whose JSON changed since it
was last seeded. A productive tenant never re-seeds on its own.

WHY THE HASH IS OF THE FILE, NEVER OF THE BLOB. On the demo, visitors write:
a collection action, a stock count, a decided expiry. The blob therefore
ALWAYS differs from the JSON, so "did the blob change?" is useless. The
question that has an answer is "did the SEED change?", and the SHA-256 of the
file answers exactly that.

WHY ONE HASH PER DOMAIN, NOT ONE GLOBAL. Changing `notas_equipo.json` re-seeds
the notes and leaves the counts a visitor did in the warehouse alone. A single
global hash would wipe everything on any file's change.

WHAT THIS DOES NOT COVER, said plainly: a tenant that has never gone through
`seed_domains()` has no recorded baseline, so a changed file is its FIRST
seed, not a change — no warning, nothing cleared. The warning below protects
the dangerous transition (a tenant that was seeding on boot and stopped), not
a tenant that was never registered here.
"""
from __future__ import annotations

import hashlib
import os

from sqlalchemy import text

from core.db.engine import tenant_connection

# What the decision function can answer. `sembrar` and `nada` both just call
# the module's own loader (its first read seeds when the blob is missing) —
# they differ only in whether the hash gets recorded.
SEMBRAR = "sembrar"        # first time for this domain: seed and record
NADA = "nada"              # nothing to do (no seed file, or same hash)
RESEMBRAR = "resembrar"    # file changed and this tenant re-seeds on boot
AVISAR = "avisar"          # file changed and this tenant does NOT re-seed


def hash_de(rutas: list[str]) -> str | None:
    """SHA-256 over the domain's seed files, in the order given.

    Returns None when NONE of them exists on disk — a domain with no on-disk
    seed (organizacion, extraccion) keeps its in-code fallback and is simply
    not tracked here. A domain whose files partly exist still hashes: what
    matters is that the digest changes when the content does.
    """
    h = hashlib.sha256()
    visto = False
    for r in rutas:
        if not os.path.exists(r):
            continue
        visto = True
        with open(r, "rb") as f:
            for bloque in iter(lambda: f.read(65536), b""):
                h.update(bloque)
    return h.hexdigest() if visto else None


def decidir(previo: str | None, actual: str | None,
            resiembra_habilitada: bool) -> str:
    """Pure, and the whole policy lives here so it can be read at a glance."""
    if actual is None:
        return NADA
    if previo is None:
        # NO BASELINE. Measured in production, and the reason this branch
        # exists: on the first boot with this mechanism the demo recorded the
        # hash of the 31-note file next to a blob that still held 17 — and
        # from then on `previo == actual` said "nothing to do" forever. The
        # band kept reading "0 de 17".
        #
        # Without a baseline we cannot prove the stored data came from THIS
        # file. A tenant that regenerates its dataset on every boot must end
        # up with what the file says, so the honest move is to make it true.
        # One that does NOT re-seed keeps its data untouched and simply
        # records where it stands.
        return RESEMBRAR if resiembra_habilitada else SEMBRAR
    if previo == actual:
        return NADA
    return RESEMBRAR if resiembra_habilitada else AVISAR


def estado(tenant_id: str) -> dict[str, str]:
    with tenant_connection(tenant_id) as conn:
        filas = conn.execute(
            text("SELECT dominio, seed_hash FROM seed_state WHERE tenant_id = :tid"),
            {"tid": tenant_id},
        ).all()
    return {d: h for d, h in filas}


def anotar(tenant_id: str, dominio: str, seed_hash: str) -> None:
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text("INSERT INTO seed_state (tenant_id, dominio, seed_hash, seeded_at) "
                 "VALUES (:tid, :dom, :h, now()) "
                 "ON CONFLICT (tenant_id, dominio) DO UPDATE SET "
                 "seed_hash = EXCLUDED.seed_hash, seeded_at = now()"),
            {"tid": tenant_id, "dom": dominio, "h": seed_hash},
        )


def resiembra_habilitada() -> bool:
    """The same gate that decides whether the dataset is regenerated at all —
    not a new one. `render.yaml` already documents it as demo-only."""
    import deploy_guard
    return deploy_guard.seed_on_boot()


def sembrar(dominio: str, rutas: list[str], tablas: list[str], cargar) -> str:
    """Seed ONE domain, clearing it first when its seed file changed.

    `cargar` is the module's own first read — the seeding path that already
    existed and that this function does not replace. All this adds is who
    empties the blob, and when. Returns the action taken, so the caller (and
    the tests) can say what happened without re-deriving it.
    """
    from core.db import reset as _reset
    from core.db import tenant as _tenant
    tid = _tenant.current_tenant_id()
    actual = hash_de(rutas)
    accion = decidir(estado(tid).get(dominio), actual, resiembra_habilitada())
    if accion == RESEMBRAR:
        _reset.truncate_tables(tid, tablas)
        print(f"[seed] {dominio}: el dataset en disco cambió — resembrado",
              flush=True)
    elif accion == AVISAR:
        print(f"[seed] WARNING {dominio}: el dataset en disco cambió, pero este "
              f"tenant no resiembra solo (POLPILOT_SEED_ON_BOOT != 1). Los datos "
              f"guardados quedan intactos.", flush=True)
    cargar()
    if accion in (SEMBRAR, RESEMBRAR):
        anotar(tid, dominio, actual)
    return accion


def revisar(dominio: str, rutas: list[str]) -> str:
    """Compare and report, touching nothing. This is what a tenant that does
    NOT re-seed runs at boot, so that a changed dataset is never silent."""
    from core.db import tenant as _tenant
    accion = decidir(estado(_tenant.current_tenant_id()).get(dominio),
                     hash_de(rutas), False)
    if accion == AVISAR:
        print(f"[seed] WARNING {dominio}: el dataset en disco cambió desde la "
              f"última siembra. Este tenant no resiembra solo.", flush=True)
    return accion
