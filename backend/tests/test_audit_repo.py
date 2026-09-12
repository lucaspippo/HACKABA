from core.db import audit_repo


def test_record_then_list(db_tenant):
    evento = audit_repo.record(db_tenant, actor="emilio", action="registrar_cobro",
                               before={"saldo": 100}, after={"saldo": 0})
    assert evento["actor"] == "emilio"
    assert evento["accion"] == "registrar_cobro"
    assert evento["antes"] == {"saldo": 100}
    assert evento["despues"] == {"saldo": 0}
    assert isinstance(evento["id"], int)

    eventos = audit_repo.list_events(db_tenant)
    assert len(eventos) == 1
    assert eventos[0]["id"] == evento["id"]


def test_events_are_ordered_and_scoped_per_tenant(db_tenant):
    audit_repo.record(db_tenant, actor="a", action="uno")
    audit_repo.record(db_tenant, actor="a", action="dos")
    eventos = audit_repo.list_events(db_tenant)
    assert [e["accion"] for e in eventos] == ["uno", "dos"]


def test_record_without_before_after_is_fine(db_tenant):
    evento = audit_repo.record(db_tenant, actor="sistema", action="reset_demo_publico")
    assert evento["antes"] is None
    assert evento["despues"] is None
