"""add source-tracking columns to purchase_orders

Revision ID: 0036
Revises: 0035
Create Date: 2026-08-27

Odoo ingestion (core/odoo_ingest.py) needs to track which purchase orders
came from Odoo and stay idempotent on re-sync. source/source_id identify
the row's origin; source_status holds Odoo's own state string (e.g.
"confirmada") separately from `status`, which holds it mapped into
PolPilot's borrador/aprobada/recibida/cancelada workflow — so the mapping
never loses the original value. All nullable, additive.

No new unique index is needed: (tenant_id, number) is already this
table's primary key (see 0009_purchase_orders.py), and Odoo's own PO
numbers (e.g. "P00006") never collide with PolPilot-originated ones
(e.g. "OC-2026-0901"), so ON CONFLICT (tenant_id, number) is enough to
upsert idempotently by number.
"""
from alembic import op
import sqlalchemy as sa

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("purchase_orders", sa.Column("source", sa.Text, nullable=True))
    op.add_column("purchase_orders", sa.Column("source_id", sa.Text, nullable=True))
    op.add_column("purchase_orders", sa.Column("source_status", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("purchase_orders", "source_status")
    op.drop_column("purchase_orders", "source_id")
    op.drop_column("purchase_orders", "source")
