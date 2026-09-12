"""core/db/angela_conversations_repo.py — round trips for Ángela's raw
transcript store. Same conventions as test_whatsapp_repo.py: a throwaway
`db_tenant`, explicit tenant_id on every call."""
import datetime

from sqlalchemy import text

from core.db import angela_conversations_repo as repo
from core.db.engine import tenant_connection


def test_get_or_create_is_stable_within_the_window(db_tenant):
    c1 = repo.get_or_create_open_conversation(db_tenant, "aldo")
    c2 = repo.get_or_create_open_conversation(db_tenant, "aldo")
    assert c1["id"] == c2["id"]


def test_different_actors_get_different_conversations(db_tenant):
    a = repo.get_or_create_open_conversation(db_tenant, "aldo")
    b = repo.get_or_create_open_conversation(db_tenant, "emilio")
    assert a["id"] != b["id"]


def test_different_channels_get_different_conversations(db_tenant):
    chat = repo.get_or_create_open_conversation(db_tenant, "aldo", channel="chat")
    voz = repo.get_or_create_open_conversation(db_tenant, "aldo", channel="voz")
    assert chat["id"] != voz["id"]


def test_stale_conversation_starts_a_new_one(db_tenant):
    old = repo.get_or_create_open_conversation(db_tenant, "aldo")
    stale = datetime.datetime.now().astimezone() - datetime.timedelta(hours=6)
    with tenant_connection(db_tenant) as conn:
        conn.execute(
            text("UPDATE angela_conversations SET last_message_at = :t "
                 "WHERE tenant_id = :tid AND id = :id"),
            {"t": stale, "tid": db_tenant, "id": old["id"]},
        )
    fresh = repo.get_or_create_open_conversation(db_tenant, "aldo")
    assert fresh["id"] != old["id"]


def test_messages_persist_in_order_and_carry_tools_used(db_tenant):
    conv = repo.get_or_create_open_conversation(db_tenant, "aldo")
    repo.add_message(db_tenant, conv["id"], "user", "¿cuánto vendimos hoy?")
    repo.add_message(db_tenant, conv["id"], "assistant", "Vendiste $120.000",
                     tools_used=["consultar_serie"])
    msgs = repo.list_messages(db_tenant, conv["id"])
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["content"] == "¿cuánto vendimos hoy?"
    assert msgs[1]["tools_used"] == ["consultar_serie"]
    assert msgs[0]["tools_used"] == []


def test_adding_a_message_updates_last_message_at(db_tenant):
    conv = repo.get_or_create_open_conversation(db_tenant, "aldo")
    repo.add_message(db_tenant, conv["id"], "user", "hola")
    got = repo.get_conversation(db_tenant, conv["id"])
    assert got["last_message_at"] >= conv["last_message_at"]


def test_list_conversations_orders_by_last_message_desc(db_tenant):
    a = repo.get_or_create_open_conversation(db_tenant, "aldo", channel="chat")
    b = repo.get_or_create_open_conversation(db_tenant, "emilio", channel="chat")
    repo.add_message(db_tenant, a["id"], "user", "primero")
    repo.add_message(db_tenant, b["id"], "user", "segundo, más reciente")
    convs = repo.list_conversations(db_tenant)
    assert [c["id"] for c in convs] == [b["id"], a["id"]]


def test_list_conversations_filters_by_actor(db_tenant):
    a = repo.get_or_create_open_conversation(db_tenant, "aldo")
    repo.get_or_create_open_conversation(db_tenant, "emilio")
    convs = repo.list_conversations(db_tenant, actor="aldo")
    assert [c["id"] for c in convs] == [a["id"]]


def test_get_conversation_missing_returns_none(db_tenant):
    assert repo.get_conversation(db_tenant, "nope") is None
