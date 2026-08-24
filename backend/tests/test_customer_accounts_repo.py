from core.db import customer_accounts_repo

_SEED = [
    {"id": "perez", "nombre": "Almacén Don Pérez", "saldo": 30_000_000,
     "limite_credito": 32_000_000, "plazo_dias": 30, "dias_sin_pagar": 45,
     "promedio_pago_dias": 30,
     "movimientos": [
         {"fecha": "2026-05-13", "tipo": "venta", "monto": 18_000_000, "detalle": "Pedido mensual"},
     ]},
]


def test_seed_if_empty_populates(db_tenant):
    customer_accounts_repo.seed_if_empty(db_tenant, _SEED)
    accounts = customer_accounts_repo.list_accounts(db_tenant)
    assert len(accounts) == 1
    assert accounts[0]["id"] == "perez"
    assert accounts[0]["saldo"] == 30_000_000
    assert len(accounts[0]["movimientos"]) == 1
    assert accounts[0]["movimientos"][0]["tipo"] == "venta"


def test_seed_if_empty_is_noop_when_data_exists(db_tenant):
    customer_accounts_repo.seed_if_empty(db_tenant, _SEED)
    customer_accounts_repo.upsert_account(db_tenant, {**_SEED[0], "saldo": 1})
    customer_accounts_repo.seed_if_empty(db_tenant, _SEED)  # must not overwrite
    assert customer_accounts_repo.list_accounts(db_tenant)[0]["saldo"] == 1


def test_add_movement_and_upsert_account(db_tenant):
    customer_accounts_repo.seed_if_empty(db_tenant, _SEED)
    customer_accounts_repo.upsert_account(db_tenant, {**_SEED[0], "saldo": 12_000_000, "dias_sin_pagar": 0})
    customer_accounts_repo.add_movement(db_tenant, "perez", {
        "fecha": "2026-06-01", "tipo": "cobro", "monto": 18_000_000, "detalle": "Cobro",
    })
    account = customer_accounts_repo.list_accounts(db_tenant)[0]
    assert account["saldo"] == 12_000_000
    assert len(account["movimientos"]) == 2
