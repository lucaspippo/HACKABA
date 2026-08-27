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
