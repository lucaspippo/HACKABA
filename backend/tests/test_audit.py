from core.audit import AuditLog


def _log(db_tenant, monkeypatch):
    monkeypatch.setattr("core.db.tenant.current_tenant_id", lambda: db_tenant)
    return AuditLog()


def test_record_devuelve_evento_con_id(db_tenant, monkeypatch):
    log = _log(db_tenant, monkeypatch)
    ev = log.record(actor="emilio", accion="restaurar_version",
                    antes={"v": 2}, despues={"v": 1})
    assert isinstance(ev["id"], int)
    assert ev["actor"] == "emilio"
    assert ev["accion"] == "restaurar_version"
    assert ev["antes"] == {"v": 2}
    assert ev["despues"] == {"v": 1}


def test_ids_incrementales_y_list(db_tenant, monkeypatch):
    log = _log(db_tenant, monkeypatch)
    ev1 = log.record(actor="a", accion="x")
    ev2 = log.record(actor="b", accion="y")
    eventos = log.list()
    assert [e["id"] for e in eventos] == [ev1["id"], ev2["id"]]
    assert ev2["id"] > ev1["id"]


def test_persiste_entre_instancias(db_tenant, monkeypatch):
    monkeypatch.setattr("core.db.tenant.current_tenant_id", lambda: db_tenant)
    AuditLog().record(actor="a", accion="x")
    assert len(AuditLog().list()) == 1
