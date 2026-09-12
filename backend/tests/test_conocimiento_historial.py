import pytest
from fastapi.testclient import TestClient

import auth
import main
from core import conocimiento
from core.audit import AuditLog
from tests.conftest import limpiar_tabla_tenant

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def limpio():
    limpiar_tabla_tenant("business_knowledge_pieces")
    limpiar_tabla_tenant("audit_events")
    yield
    limpiar_tabla_tenant("business_knowledge_pieces")
    limpiar_tabla_tenant("audit_events")


@pytest.fixture(scope="module")
def token():
    creds = auth.cargar_o_generar_credenciales()
    return client.post("/api/login", json={"username": "emilio", "password": creds["emilio"]}).json()["token"]


def test_list_for_returns_only_events_about_this_piece():
    p1 = conocimiento.crear(texto="Pieza uno", tipo="contexto", ambito="global",
                            nodo="caja", efecto="contexto_para_angela")
    p2 = conocimiento.crear(texto="Pieza dos", tipo="contexto", ambito="global",
                            nodo="caja", efecto="contexto_para_angela")
    AuditLog().record("aldo", "editar_conocimiento", {"id": p1["id"]}, {"id": p1["id"], "texto": "cambiado"})
    AuditLog().record("aldo", "editar_conocimiento", {"id": p2["id"]}, {"id": p2["id"], "texto": "otro cambio"})
    eventos = AuditLog().list_for(p1["id"])
    assert len(eventos) == 1
    assert eventos[0]["despues"]["id"] == p1["id"]


def test_historial_endpoint_needs_a_session():
    p = conocimiento.crear(texto="x", tipo="contexto", ambito="global",
                           nodo="caja", efecto="contexto_para_angela")
    assert client.get(f"/api/conocimiento/{p['id']}/historial").status_code in (401, 403)


def test_historial_endpoint_returns_events(token):
    p = conocimiento.crear(texto="x", tipo="contexto", ambito="global",
                           nodo="caja", efecto="contexto_para_angela")
    AuditLog().record("aldo", "editar_conocimiento", {"id": p["id"]}, {"id": p["id"], "texto": "y"})
    r = client.get(f"/api/conocimiento/{p['id']}/historial",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()["eventos"]) == 1
