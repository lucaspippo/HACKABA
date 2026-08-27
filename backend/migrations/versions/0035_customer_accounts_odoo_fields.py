"""add contact and source-tracking columns to customer_accounts

Revision ID: 0035
Revises: 0034
Create Date: 2026-08-27

customer_accounts has no contact fields today (id, name, balance,
credit_limit, payment_term_days, days_overdue, average_payment_days).
Odoo ingestion (core/odoo_ingest.py) needs vat/city/phone/email to store
what it pulls, plus source/source_id to track where a row came from and
find it again on re-sync. All nullable, additive — existing rows get
NULL, meaning "not from a connector".
"""
from alembic import op
import sqlalchemy as sa

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customer_accounts", sa.Column("vat", sa.Text, nullable=True))
    op.add_column("customer_accounts", sa.Column("city", sa.Text, nullable=True))
    op.add_column("customer_accounts", sa.Column("phone", sa.Text, nullable=True))
    op.add_column("customer_accounts", sa.Column("email", sa.Text, nullable=True))
    op.add_column("customer_accounts", sa.Column("source", sa.Text, nullable=True))
    op.add_column("customer_accounts", sa.Column("source_id", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("customer_accounts", "source_id")
    op.drop_column("customer_accounts", "source")
    op.drop_column("customer_accounts", "email")
    op.drop_column("customer_accounts", "phone")
    op.drop_column("customer_accounts", "city")
    op.drop_column("customer_accounts", "vat")
