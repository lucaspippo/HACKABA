from core.db import team_goals_repo


def test_list_empty_when_no_goals(db_tenant):
    assert team_goals_repo.list_goals(db_tenant) == []


def test_get_by_id_returns_none_when_missing(db_tenant):
    assert team_goals_repo.get(db_tenant, "ob123456") is None


def test_create_then_list(db_tenant):
    goal = {"id": "ob123456", "nombre": "Vender 10% más", "responsable": "Paula",
            "fecha": "2026-09-01", "estado": "pendiente", "creado_por": "emilio"}
    team_goals_repo.create(db_tenant, goal)
    goals = team_goals_repo.list_goals(db_tenant)
    assert len(goals) == 1
    assert goals[0]["id"] == "ob123456"
    assert goals[0]["nombre"] == "Vender 10% más"


def test_update_status(db_tenant):
    goal = {"id": "ob123456", "nombre": "X", "responsable": "Y",
            "fecha": "2026-09-01", "estado": "pendiente", "creado_por": "emilio"}
    team_goals_repo.create(db_tenant, goal)
    team_goals_repo.update_status(db_tenant, "ob123456", "en_proceso")
    assert team_goals_repo.get(db_tenant, "ob123456")["estado"] == "en_proceso"
