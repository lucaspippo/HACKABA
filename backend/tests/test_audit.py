from core.audit import AuditLog


def test_record_devuelve_evento_con_id(tmp_path):
    log = AuditLog(str(tmp_path))
    ev = log.record(actor="emilio", accion="restaurar_version",
                    antes={"v": 2}, despues={"v": 1})
    assert ev["id"] == 1
    assert ev["actor"] == "emilio"
    assert ev["accion"] == "restaurar_version"
    assert ev["antes"] == {"v": 2}
    assert ev["despues"] == {"v": 1}


def test_ids_incrementales_y_list(tmp_path):
    log = AuditLog(str(tmp_path))
    log.record(actor="a", accion="x")
    log.record(actor="b", accion="y")
    eventos = log.list()
    assert [e["id"] for e in eventos] == [1, 2]


def test_persiste_entre_instancias(tmp_path):
    AuditLog(str(tmp_path)).record(actor="a", accion="x")
    assert len(AuditLog(str(tmp_path)).list()) == 1
