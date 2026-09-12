"""core/angela_transcripts.py — the facade wired into /api/angela and
/api/angela/stream. Same monkeypatch convention as test_audit.py: the module
resolves the tenant itself, so tests pin it via core.db.tenant."""
from core import angela_transcripts


def _pin(db_tenant, monkeypatch):
    monkeypatch.setattr("core.db.tenant.current_tenant_id", lambda: db_tenant)


def test_record_turn_stores_both_sides(db_tenant, monkeypatch):
    _pin(db_tenant, monkeypatch)
    conv = angela_transcripts.record_turn(
        "aldo", "¿cuánto vendimos hoy?", "Vendiste $120.000",
        tools_used=["consultar_serie"])
    full = angela_transcripts.get_transcript(conv["id"])
    assert [m["role"] for m in full["messages"]] == ["user", "assistant"]
    assert full["messages"][0]["content"] == "¿cuánto vendimos hoy?"
    assert full["messages"][1]["content"] == "Vendiste $120.000"
    assert full["messages"][1]["tools_used"] == ["consultar_serie"]


def test_record_turn_skips_empty_sides(db_tenant, monkeypatch):
    """A cap/error turn can arrive with no real answer — don't write a blank
    row for it."""
    _pin(db_tenant, monkeypatch)
    conv = angela_transcripts.record_turn("aldo", "hola", "")
    full = angela_transcripts.get_transcript(conv["id"])
    assert [m["role"] for m in full["messages"]] == ["user"]


def test_consecutive_turns_land_in_the_same_conversation(db_tenant, monkeypatch):
    _pin(db_tenant, monkeypatch)
    c1 = angela_transcripts.record_turn("aldo", "hola", "hola, ¿en qué te ayudo?")
    c2 = angela_transcripts.record_turn("aldo", "¿qué vendimos?", "$120.000")
    assert c1["id"] == c2["id"]
    full = angela_transcripts.get_transcript(c1["id"])
    assert len(full["messages"]) == 4


def test_list_conversations_filters_by_channel(db_tenant, monkeypatch):
    _pin(db_tenant, monkeypatch)
    angela_transcripts.record_turn("aldo", "hola", "hola", channel="chat")
    angela_transcripts.record_turn("aldo", "faltan cajas", "anotado", channel="voz")
    voice_only = angela_transcripts.list_conversations(channel="voz")
    assert all(c["channel"] == "voz" for c in voice_only)
    assert len(voice_only) == 1


def test_get_transcript_missing_returns_none(db_tenant, monkeypatch):
    _pin(db_tenant, monkeypatch)
    assert angela_transcripts.get_transcript("nope") is None
