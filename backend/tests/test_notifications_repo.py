import datetime

from core.db import notifications_repo

_FECHA = datetime.datetime.now().isoformat(timespec="seconds")


def _evento(**overrides) -> dict:
    ev = {"id": "n1", "para": "paula", "titulo": "A", "cuerpo": "",
          "tipo": "general", "ref": None, "leida": False, "fecha": _FECHA}
    ev.update(overrides)
    return ev


def test_list_empty_when_none(db_tenant):
    assert notifications_repo.list_for(db_tenant, "paula") == []


def test_emit_then_list_for_recipient(db_tenant):
    ev = _evento(id="n123456", titulo="Hola", cuerpo="Actualizaste tu perfil")
    notifications_repo.create(db_tenant, ev)
    items = notifications_repo.list_for(db_tenant, "paula")
    assert len(items) == 1
    assert items[0]["id"] == "n123456"
    assert notifications_repo.list_for(db_tenant, "emilio") == []


def test_list_only_unread(db_tenant):
    notifications_repo.create(db_tenant, _evento(id="n1", leida=False))
    notifications_repo.create(db_tenant, _evento(id="n2", leida=True))
    unread = notifications_repo.list_for(db_tenant, "paula", solo_no_leidas=True)
    assert [n["id"] for n in unread] == ["n1"]


def test_mark_read(db_tenant):
    notifications_repo.create(db_tenant, _evento(id="n1"))
    updated = notifications_repo.mark_read(db_tenant, "n1")
    assert updated["leida"] is True


def test_mark_read_missing_raises(db_tenant):
    import pytest
    with pytest.raises(KeyError):
        notifications_repo.mark_read(db_tenant, "does-not-exist")


def test_total_emitted_with_date_cutoff(db_tenant):
    notifications_repo.create(db_tenant, _evento(id="n1"))
    assert notifications_repo.total_emitidas(db_tenant) == 1
