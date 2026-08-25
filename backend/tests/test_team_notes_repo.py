from core.db import team_notes_repo


def test_get_returns_none_when_no_row(db_tenant):
    assert team_notes_repo.get_data(db_tenant) is None


def test_save_then_get_roundtrip(db_tenant):
    data = {"notas": [{"tipo": "observacion_campo", "texto": "Frío en la cámara 2"}]}
    team_notes_repo.save_data(db_tenant, data)
    assert team_notes_repo.get_data(db_tenant) == data
