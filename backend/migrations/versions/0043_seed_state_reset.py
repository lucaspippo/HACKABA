"""drop the baselines recorded by the first pass of the re-seed mechanism

Revision ID: 0043
Revises: 0042
Create Date: 2026-09-08

0042 shipped with a hole in its FIRST boot: with no baseline yet, every domain
was treated as a first seed — the hash of the on-disk file was recorded next
to a blob that had been seeded from an OLDER file, and from then on the two
"agreed" forever. Measured on the deployed demo: the operation map's band kept
reading "0 de 17" after the deploy that was supposed to fix it, and locations,
vendors and reconciliation stayed empty.

`decidir()` now re-seeds when there is no baseline AND the tenant regenerates
its dataset on boot. This migration clears the baselines that pass wrote, so
the corrected rule gets to run once on every tenant.

Deleting these rows is safe by construction: seed_state holds only "which file
each domain was last seeded from". Losing it makes the next boot re-evaluate —
which is exactly the point — and a tenant that does NOT re-seed on boot simply
records its baseline again without touching a single row of its own data.
"""
from alembic import op

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM seed_state")


def downgrade() -> None:
    # Nothing to restore: the rows are a cache of the last seed, and the next
    # boot writes them again.
    pass
