"""core/db/whatsapp_repo.py — round trips for the WhatsApp Business channel
config, conversations and messages. Same conventions as
test_odoo_connections_repo.py (throwaway `db_tenant`, explicit tenant_id)."""
from sqlalchemy import text

from core.db import whatsapp_repo
from core.db.engine import tenant_connection


def test_save_then_get_channel_roundtrip(db_tenant):
    whatsapp_repo.save_channel(
        db_tenant, phone_number_id="123456", display_phone_number=None,
        business_name=None, access_token="tok-1", app_secret="secret-1",
        verify_token="verify-1", greeting_message="Hola!", enabled=True,
    )
    c = whatsapp_repo.get_channel(db_tenant)
    assert c["phone_number_id"] == "123456"
    assert c["access_token"] == "tok-1"
    assert c["app_secret"] == "secret-1"
    assert c["verify_token"] == "verify-1"
    assert c["greeting_message"] == "Hola!"
    assert c["enabled"] is True


def test_get_missing_channel_returns_none(db_tenant):
    assert whatsapp_repo.get_channel(db_tenant) is None


def test_channel_secrets_stored_encrypted_at_rest(db_tenant):
    whatsapp_repo.save_channel(
        db_tenant, phone_number_id="1", display_phone_number=None, business_name=None,
        access_token="s3cr3t-token", app_secret="s3cr3t-app-secret",
        verify_token="v", greeting_message="", enabled=True,
    )
    with tenant_connection(db_tenant) as conn:
        row = conn.execute(
            text("SELECT access_token_encrypted, app_secret_encrypted FROM whatsapp_channels "
                 "WHERE tenant_id = :tid"), {"tid": db_tenant},
        ).mappings().first()
    assert "s3cr3t-token" not in row["access_token_encrypted"]
    assert "s3cr3t-app-secret" not in row["app_secret_encrypted"]


def test_save_channel_is_idempotent_upsert(db_tenant):
    whatsapp_repo.save_channel(
        db_tenant, phone_number_id="1", display_phone_number=None, business_name=None,
        access_token="tok-a", app_secret="secret-a", verify_token="v", greeting_message="",
        enabled=True,
    )
    whatsapp_repo.save_channel(
        db_tenant, phone_number_id="1", display_phone_number=None, business_name=None,
        access_token="tok-b", app_secret="secret-b", verify_token="v", greeting_message="",
        enabled=False,
    )
    c = whatsapp_repo.get_channel(db_tenant)
    assert c["access_token"] == "tok-b"
    assert c["enabled"] is False


def test_save_channel_generates_verify_token_when_missing(db_tenant):
    whatsapp_repo.save_channel(
        db_tenant, phone_number_id="1", display_phone_number=None, business_name=None,
        access_token="tok", app_secret="secret", verify_token=None, greeting_message="",
        enabled=True,
    )
    c = whatsapp_repo.get_channel(db_tenant)
    assert c["verify_token"]


def test_delete_channel_removes_it(db_tenant):
    whatsapp_repo.save_channel(
        db_tenant, phone_number_id="1", display_phone_number=None, business_name=None,
        access_token="tok", app_secret="secret", verify_token="v", greeting_message="",
        enabled=True,
    )
    whatsapp_repo.delete_channel(db_tenant)
    assert whatsapp_repo.get_channel(db_tenant) is None


def test_get_or_create_conversation_is_stable_per_phone(db_tenant):
    c1 = whatsapp_repo.get_or_create_conversation(db_tenant, "+5491100000099", "Juan")
    c2 = whatsapp_repo.get_or_create_conversation(db_tenant, "+5491100000099")
    assert c1["id"] == c2["id"]
    assert c2["customer_name"] == "Juan"


def test_messages_persist_in_order_and_update_last_message_at(db_tenant):
    conv = whatsapp_repo.get_or_create_conversation(db_tenant, "+5491100000098")
    whatsapp_repo.add_message(db_tenant, conv["id"], "in", "Hola, ¿tienen aceite?")
    whatsapp_repo.add_message(db_tenant, conv["id"], "out", "Sí, ¿cuánto necesitás?")
    msgs = whatsapp_repo.list_messages(db_tenant, conv["id"])
    assert [m["direction"] for m in msgs] == ["in", "out"]
    assert [m["body"] for m in msgs] == ["Hola, ¿tienen aceite?", "Sí, ¿cuánto necesitás?"]


def test_list_conversations_orders_by_last_message_desc(db_tenant):
    a = whatsapp_repo.get_or_create_conversation(db_tenant, "+541")
    b = whatsapp_repo.get_or_create_conversation(db_tenant, "+542")
    whatsapp_repo.add_message(db_tenant, a["id"], "in", "primero")
    whatsapp_repo.add_message(db_tenant, b["id"], "in", "segundo, más reciente")
    convs = whatsapp_repo.list_conversations(db_tenant)
    assert [c["id"] for c in convs] == [b["id"], a["id"]]


def test_set_conversation_status(db_tenant):
    conv = whatsapp_repo.get_or_create_conversation(db_tenant, "+543")
    whatsapp_repo.set_conversation_status(db_tenant, conv["id"], "necesita_atencion")
    convs = whatsapp_repo.list_conversations(db_tenant)
    assert convs[0]["status"] == "necesita_atencion"
