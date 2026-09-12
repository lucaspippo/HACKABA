from __future__ import annotations

from sqlalchemy import text

from core.db.engine import tenant_connection

_ACCOUNT_COLS = ("id, name, balance, credit_limit, payment_term_days, days_overdue, "
                  "average_payment_days, vat, city, phone, email, source, source_id")


def list_accounts(tenant_id: str) -> list[dict]:
    with tenant_connection(tenant_id) as conn:
        accounts = conn.execute(
            text(f"SELECT {_ACCOUNT_COLS} FROM customer_accounts ORDER BY id")
        ).mappings().all()
        movements = conn.execute(
            text("SELECT customer_id, date, type, amount, description FROM account_movements ORDER BY date")
        ).mappings().all()

    by_account: dict[str, list[dict]] = {}
    for m in movements:
        by_account.setdefault(m["customer_id"], []).append({
            "fecha": m["date"].isoformat(),
            "tipo": m["type"],
            "monto": float(m["amount"]),
            "detalle": m["description"],
        })

    return [
        {
            "id": a["id"],
            "nombre": a["name"],
            "saldo": float(a["balance"]),
            "limite_credito": float(a["credit_limit"]),
            "plazo_dias": a["payment_term_days"],
            "dias_sin_pagar": a["days_overdue"],
            "promedio_pago_dias": a["average_payment_days"],
            "vat": a["vat"],
            "city": a["city"],
            "phone": a["phone"],
            "email": a["email"],
            "source": a["source"],
            "source_id": a["source_id"],
            "movimientos": by_account.get(a["id"], []),
        }
        for a in accounts
    ]


def upsert_account(tenant_id: str, account: dict) -> None:
    """Create-or-update a customer account, overwriting every column.

    This is the NATIVE write path: core/cuentas.py's _save() (used by
    registrar_cobro and any other place that persists a full account dict,
    e.g. after a payment changes `balance`) relies on every field being
    written on conflict — it always hands over the complete, already-correct
    account, so a full overwrite is exactly right here. core/staging.py's
    Odoo-integration branch also uses this for first-time links (an INSERT,
    so there is no prior dueño data to protect yet).

    Do NOT call this for an Odoo re-sync of an already-linked account — use
    `upsert_account_from_odoo` instead, which restricts the UPDATE to the
    columns Odoo actually owns so it can't blank dueño-edited accounting
    fields (see that function's docstring)."""
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "INSERT INTO customer_accounts "
                "(tenant_id, id, name, balance, credit_limit, payment_term_days, days_overdue, "
                "average_payment_days, vat, city, phone, email, source, source_id) "
                "VALUES (:tid, :id, :name, :balance, :credit_limit, :payment_term_days, :days_overdue, "
                ":average_payment_days, :vat, :city, :phone, :email, :source, :source_id) "
                "ON CONFLICT (tenant_id, id) DO UPDATE SET "
                "name = EXCLUDED.name, balance = EXCLUDED.balance, credit_limit = EXCLUDED.credit_limit, "
                "payment_term_days = EXCLUDED.payment_term_days, days_overdue = EXCLUDED.days_overdue, "
                "average_payment_days = EXCLUDED.average_payment_days, "
                "vat = EXCLUDED.vat, city = EXCLUDED.city, phone = EXCLUDED.phone, "
                "email = EXCLUDED.email, source = EXCLUDED.source, source_id = EXCLUDED.source_id"
            ),
            {
                "tid": tenant_id,
                "id": account["id"],
                "name": account["nombre"],
                "balance": account["saldo"],
                "credit_limit": account.get("limite_credito", 0),
                "payment_term_days": account.get("plazo_dias", 30),
                "days_overdue": account.get("dias_sin_pagar", 0),
                "average_payment_days": account.get("promedio_pago_dias"),
                "vat": account.get("vat"),
                "city": account.get("city"),
                "phone": account.get("phone"),
                "email": account.get("email"),
                "source": account.get("source"),
                "source_id": account.get("source_id"),
            },
        )


def upsert_account_from_odoo(tenant_id: str, account: dict) -> None:
    """Create-or-update a customer account coming from Odoo ingestion's
    auto-upsert tier (core/odoo_ingest.py, already-linked records only).

    On CONFLICT, only the columns Odoo's res.partner genuinely supplies are
    overwritten: `name`, `vat`, `city`, `phone`, `email`, `source`,
    `source_id`. `balance`, `credit_limit`, `payment_term_days`,
    `days_overdue` and `average_payment_days` are PolPilot-native accounting
    fields — `balance` in particular is written by core/cuentas.py's
    registrar_cobro, a completely separate write path — so they are
    deliberately left out of the UPDATE SET clause: overwriting them
    unconditionally on every re-sync would silently revert dueño-edited data
    back to the coercer's insert-time defaults (core/staging.py's
    coerce_cliente_odoo hardcodes them to 0/30/None). They ARE still written
    on INSERT (first-time link), since there's no prior dueño data to lose
    then. Mirrors purchase_orders_repo.upsert_from_odoo's existing pattern."""
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "INSERT INTO customer_accounts "
                "(tenant_id, id, name, balance, credit_limit, payment_term_days, days_overdue, "
                "average_payment_days, vat, city, phone, email, source, source_id) "
                "VALUES (:tid, :id, :name, :balance, :credit_limit, :payment_term_days, :days_overdue, "
                ":average_payment_days, :vat, :city, :phone, :email, :source, :source_id) "
                "ON CONFLICT (tenant_id, id) DO UPDATE SET "
                "name = EXCLUDED.name, "
                "vat = EXCLUDED.vat, city = EXCLUDED.city, phone = EXCLUDED.phone, "
                "email = EXCLUDED.email, source = EXCLUDED.source, source_id = EXCLUDED.source_id"
            ),
            {
                "tid": tenant_id,
                "id": account["id"],
                "name": account["nombre"],
                "balance": account["saldo"],
                "credit_limit": account.get("limite_credito", 0),
                "payment_term_days": account.get("plazo_dias", 30),
                "days_overdue": account.get("dias_sin_pagar", 0),
                "average_payment_days": account.get("promedio_pago_dias"),
                "vat": account.get("vat"),
                "city": account.get("city"),
                "phone": account.get("phone"),
                "email": account.get("email"),
                "source": account.get("source"),
                "source_id": account.get("source_id"),
            },
        )


def add_movement(tenant_id: str, customer_id: str, movement: dict) -> None:
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "INSERT INTO account_movements (tenant_id, customer_id, date, type, amount, description) "
                "VALUES (:tid, :cid, :date, :type, :amount, :description)"
            ),
            {
                "tid": tenant_id,
                "cid": customer_id,
                "date": movement["fecha"],
                "type": movement["tipo"],
                "amount": movement["monto"],
                "description": movement.get("detalle"),
            },
        )


def seed_if_empty(tenant_id: str, seed: list[dict]) -> None:
    with tenant_connection(tenant_id) as conn:
        count = conn.execute(text("SELECT count(*) FROM customer_accounts")).scalar_one()
    if count:
        return
    for account in seed:
        upsert_account(tenant_id, account)
        for m in account.get("movimientos", []):
            add_movement(tenant_id, account["id"], m)
