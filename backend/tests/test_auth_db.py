import auth


def test_login_success_creates_db_backed_session(db_tenant, monkeypatch):
    monkeypatch.setattr("core.db.tenant.current_tenant_id", lambda: db_tenant)
    import bcrypt

    from core.db import credentials_repo
    credentials_repo.set(db_tenant, "emilio", bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode())

    result = auth.login("emilio", "testpass123")
    assert result is not None
    assert result["usuario"]["username"] == "emilio"

    perfil = auth.usuario_por_token(result["token"])
    assert perfil is not None
    assert perfil["username"] == "emilio"


def test_login_wrong_password_fails(db_tenant, monkeypatch):
    monkeypatch.setattr("core.db.tenant.current_tenant_id", lambda: db_tenant)
    import bcrypt

    from core.db import credentials_repo
    credentials_repo.set(db_tenant, "emilio", bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode())

    assert auth.login("emilio", "wrong") is None


def test_login_unknown_user_fails(db_tenant, monkeypatch):
    monkeypatch.setattr("core.db.tenant.current_tenant_id", lambda: db_tenant)
    assert auth.login("nobody", "whatever") is None
