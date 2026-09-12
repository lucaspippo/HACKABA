"""The single source of truth for which Postgres tables are tenant-scoped
(RLS-enforced, one row/rows per tenant). Add a table here the moment its
migration lands — this list backs both the test suite's per-tenant reset
(tests/conftest.py) and the production per-tenant business-data reset
(core/db/reset.py), and drifting it out of sync with a real migration is
exactly the "forgot to add table X" bug this file exists to prevent (see
core/db/MIGRATING_A_MODULE.md for two real instances of that bug).
"""
from __future__ import annotations

# Login state: NOT part of a "reset to canonical business data" — resetting
# these would log every visitor out and rotate their (already-shared/known)
# password.
AUTH_TABLES = ("auth_credentials", "sessions")

# Every other tenant-scoped table, in migration order. Truncating all of
# these for a tenant and re-triggering each domain module's own first-read
# reproduces exactly what a freshly seeded tenant looks like (see
# data-demo/seed_db.py).
BUSINESS_DATA_TABLES = (
    "account_movements", "customer_accounts",
    "audit_events", "data_versions",
    "inventory_working", "caja_state", "organization_config",
    "purchase_orders", "team_goals", "supplier_conditions",
    "team_notes", "notifications",
    "automation_policies", "retail_counter_data", "internal_transfers",
    "inventory_baseline", "sample_extractions",
    "reminders", "user_memory", "macro_cache", "finance_data",
    "client_sales_data",
    "collection_actions", "expiry_actions", "business_knowledge_pieces", "data_sections",
    "sales_validation",
    "floor_reports", "staging_batches", "user_profiles", "supplier_accounts",
    "users",
    "whatsapp_channels", "whatsapp_messages", "whatsapp_conversations",
    "pattern_feedback",
)

TENANT_SCOPED_TABLES = AUTH_TABLES + BUSINESS_DATA_TABLES
