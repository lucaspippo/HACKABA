from __future__ import annotations

import datetime
import os
import secrets

from cryptography.fernet import Fernet
from sqlalchemy import text

from core.db.engine import tenant_connection, to_local_iso


def _fernet() -> Fernet:
    key = os.environ.get("WHATSAPP_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "WHATSAPP_ENCRYPTION_KEY is not set — required to store/read WhatsApp "
            "Business API tokens. Generate one with: python -c \"from cryptography.fernet "
            "import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode("utf-8"))


# --- channel config (one row per tenant) ------------------------------------

def get_channel(tenant_id: str) -> dict | None:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "SELECT phone_number_id, display_phone_number, business_name, "
                "access_token_encrypted, app_secret_encrypted, verify_token, "
                "greeting_message, enabled, updated_at "
                "FROM whatsapp_channels WHERE tenant_id = :tid"
            ),
            {"tid": tenant_id},
        ).mappings().first()
    if not row:
        return None
    f = _fernet()
    return {
        "phone_number_id": row["phone_number_id"],
        "display_phone_number": row["display_phone_number"],
        "business_name": row["business_name"],
        "access_token": f.decrypt(row["access_token_encrypted"].encode("utf-8")).decode("utf-8"),
        "app_secret": f.decrypt(row["app_secret_encrypted"].encode("utf-8")).decode("utf-8"),
        "verify_token": row["verify_token"],
        "greeting_message": row["greeting_message"] or "",
        "enabled": row["enabled"],
        "updated_at": row["updated_at"].isoformat(),
    }


def save_channel(tenant_id: str, *, phone_number_id: str, display_phone_number: str | None,
                  business_name: str | None, access_token: str, app_secret: str,
                  verify_token: str | None, greeting_message: str, enabled: bool) -> None:
    f = _fernet()
    access_encrypted = f.encrypt(access_token.encode("utf-8")).decode("utf-8")
    secret_encrypted = f.encrypt(app_secret.encode("utf-8")).decode("utf-8")
    token = verify_token or secrets.token_urlsafe(24)
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text(
                "INSERT INTO whatsapp_channels "
                "(tenant_id, phone_number_id, display_phone_number, business_name, "
                " access_token_encrypted, app_secret_encrypted, verify_token, "
                " greeting_message, enabled) "
                "VALUES (:tid, :pnid, :dpn, :bn, :at, :as_, :vt, :gm, :en) "
                "ON CONFLICT (tenant_id) DO UPDATE SET "
                "phone_number_id = EXCLUDED.phone_number_id, "
                "display_phone_number = EXCLUDED.display_phone_number, "
                "business_name = EXCLUDED.business_name, "
                "access_token_encrypted = EXCLUDED.access_token_encrypted, "
                "app_secret_encrypted = EXCLUDED.app_secret_encrypted, "
                "verify_token = EXCLUDED.verify_token, "
                "greeting_message = EXCLUDED.greeting_message, "
                "enabled = EXCLUDED.enabled, updated_at = now()"
            ),
            {"tid": tenant_id, "pnid": phone_number_id, "dpn": display_phone_number,
             "bn": business_name, "at": access_encrypted, "as_": secret_encrypted,
             "vt": token, "gm": greeting_message or None, "en": enabled},
        )


def delete_channel(tenant_id: str) -> None:
    with tenant_connection(tenant_id) as conn:
        conn.execute(text("DELETE FROM whatsapp_channels WHERE tenant_id = :tid"), {"tid": tenant_id})


# --- conversations + messages ------------------------------------------------

def _ahora() -> datetime.datetime:
    return datetime.datetime.now().astimezone()


def get_or_create_conversation(tenant_id: str, customer_phone: str,
                                customer_name: str | None = None) -> dict:
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text("SELECT id, customer_phone, customer_name, status, created_at, last_message_at "
                 "FROM whatsapp_conversations WHERE customer_phone = :phone"),
            {"phone": customer_phone},
        ).mappings().first()
        if row:
            if customer_name and not row["customer_name"]:
                conn.execute(
                    text("UPDATE whatsapp_conversations SET customer_name = :name "
                         "WHERE tenant_id = :tid AND id = :id"),
                    {"name": customer_name, "tid": tenant_id, "id": row["id"]},
                )
            return _to_conversation(row, customer_name if not row["customer_name"] else None)
        cid = "wc" + secrets.token_hex(4)
        now = _ahora()
        conn.execute(
            text("INSERT INTO whatsapp_conversations "
                 "(tenant_id, id, customer_phone, customer_name, status, created_at, last_message_at) "
                 "VALUES (:tid, :id, :phone, :name, 'abierta', :now, :now)"),
            {"tid": tenant_id, "id": cid, "phone": customer_phone, "name": customer_name, "now": now},
        )
        return {"id": cid, "customer_phone": customer_phone, "customer_name": customer_name,
                "status": "abierta", "created_at": to_local_iso(now), "last_message_at": to_local_iso(now)}


def _to_conversation(row, name_override: str | None = None) -> dict:
    return {
        "id": row["id"],
        "customer_phone": row["customer_phone"],
        "customer_name": name_override or row["customer_name"],
        "status": row["status"],
        "created_at": to_local_iso(row["created_at"]),
        "last_message_at": to_local_iso(row["last_message_at"]),
    }


def add_message(tenant_id: str, conversation_id: str, direction: str, body: str,
                 wa_message_id: str | None = None) -> None:
    mid = "wm" + secrets.token_hex(4)
    now = _ahora()
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text("INSERT INTO whatsapp_messages "
                 "(tenant_id, id, conversation_id, direction, body, wa_message_id, created_at) "
                 "VALUES (:tid, :id, :cid, :dir, :body, :wamid, :now)"),
            {"tid": tenant_id, "id": mid, "cid": conversation_id, "dir": direction,
             "body": body, "wamid": wa_message_id, "now": now},
        )
        conn.execute(
            text("UPDATE whatsapp_conversations SET last_message_at = :now "
                 "WHERE tenant_id = :tid AND id = :cid"),
            {"now": now, "tid": tenant_id, "cid": conversation_id},
        )


def list_messages(tenant_id: str, conversation_id: str, limit: int = 20) -> list[dict]:
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(
            text("SELECT id, direction, body, wa_message_id, created_at FROM whatsapp_messages "
                 "WHERE conversation_id = :cid ORDER BY created_at DESC LIMIT :lim"),
            {"cid": conversation_id, "lim": limit},
        ).mappings().all()
    out = [
        {"id": r["id"], "direction": r["direction"], "body": r["body"],
         "wa_message_id": r["wa_message_id"], "cuando": to_local_iso(r["created_at"])}
        for r in rows
    ]
    out.reverse()
    return out


def list_conversations(tenant_id: str, limit: int = 100) -> list[dict]:
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(
            text("SELECT id, customer_phone, customer_name, status, created_at, last_message_at "
                 "FROM whatsapp_conversations ORDER BY last_message_at DESC LIMIT :lim"),
            {"lim": limit},
        ).mappings().all()
    return [_to_conversation(r) for r in rows]


def set_conversation_status(tenant_id: str, conversation_id: str, status: str) -> None:
    with tenant_connection(tenant_id) as conn:
        conn.execute(
            text("UPDATE whatsapp_conversations SET status = :status "
                 "WHERE tenant_id = :tid AND id = :id"),
            {"status": status, "tid": tenant_id, "id": conversation_id},
        )
