import pytest
from fastapi.testclient import TestClient

import auth
import main


client = TestClient(main.app)


@pytest.fixture()
def h():
    """Header Authorization de emilio (dueño): estos endpoints ahora exigen token."""
    creds = auth.cargar_o_generar_credenciales()
    tok = client.post("/api/login", json={"username": "emilio", "password": creds["emilio"]}).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


def test_get_calidad_devuelve_libro_triado(h):
    r = client.get("/api/calidad", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert "grupos" in body
    assert "total_issues" in body
    assert "impacto_total" in body


def test_versiones_y_restore_round_trip(h):
    # crea una versión y la recupera vía API
    main.store.versiones.save({"prueba": 123}, motivo="test-api")
    r = client.get("/api/versiones", headers=h)
    assert r.status_code == 200
    versiones = r.json()["versiones"]
    assert len(versiones) >= 1
    vid = versiones[-1]["id"]

    r2 = client.post(f"/api/versiones/{vid}/restaurar", headers=h)
    assert r2.status_code == 200
    assert r2.json()["snapshot"] == {"prueba": 123}


def test_restore_inexistente_da_404(h):
    r = client.post("/api/versiones/99999/restaurar", headers=h)
    assert r.status_code == 404


def test_audit_lista_eventos(h):
    main.store.audit.record(actor="test", accion="ping")
    r = client.get("/api/audit", headers=h)
    assert r.status_code == 200
    assert any(e["accion"] == "ping" for e in r.json()["eventos"])


def test_saneamiento_proponer_aplicar_revertir_round_trip(h):
    try:
        # proponer
        r = client.get("/api/saneamiento/proponer/balanza", headers=h)
        assert r.status_code == 200
        assert r.json()["auto"] is True

        # aplicar (el actor sale del token, ya no del body)
        r2 = client.post("/api/saneamiento/aplicar/balanza", json={}, headers=h)
        assert r2.status_code == 200
        body = r2.json()
        assert body["corregidos"] > 0
        vid = body["version_backup"]

        # ya no hay balanza en el libro
        cats = {g["categoria"] for g in client.get("/api/calidad", headers=h).json()["grupos"]}
        assert "balanza" not in cats

        # revertir
        r3 = client.post(f"/api/saneamiento/revertir/{vid}", json={}, headers=h)
        assert r3.status_code == 200
        cats2 = {g["categoria"] for g in client.get("/api/calidad", headers=h).json()["grupos"]}
        assert "balanza" in cats2
    finally:
        main.store.resetear_actual()


def test_saneamiento_categoria_no_auto_da_400(h):
    r = client.post("/api/saneamiento/aplicar/sin_precio", json={}, headers=h)
    assert r.status_code == 400


# --- P9·C2 (M3/M4): equipo real para asignar y actividad real para Inicio ---

def test_equipo_nombres_requiere_token_y_excluye_internos(h):
    assert client.get("/api/equipo/nombres").status_code == 401
    r = client.get("/api/equipo/nombres", headers=h)
    assert r.status_code == 200
    equipo = r.json()["equipo"]
    nombres = [p["nombre"] for p in equipo]
    assert "Emilio" in nombres                      # el dueño real del piloto
    # P11·B9: `superficies` viaja con cada empleado (el "View as" de desktop
    # filtra por eso). P·onboarding: también la `antiguedad` (None para quien no
    # declara ingreso), que es lo que distingue al que recién entró en la lista.
    # Sigue sin haber datos sensibles: ni teléfono, ni features, ni descripción.
    assert all(set(p) == {"username", "nombre", "rol", "superficies", "antiguedad"}
               for p in equipo)
    assert not any(k in p for p in equipo for k in ("telefono", "features", "descripcion"))
    assert "polpilot" not in [p["username"] for p in equipo]  # interno afuera


# --- P13: /api/inicio — el resumen ejecutivo del Home en una llamada ---

def test_inicio_agrega_fuentes_existentes(h):
    assert client.get("/api/inicio").status_code == 401
    r = client.get("/api/inicio", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert {"staging", "calidad", "solicitudes", "actividad",
            "analisis_objetivos", "fase"} <= set(body)
    # El dueño tiene cargar+saneamiento: cada fuente viene con su shape original
    assert "batches" in body["staging"]
    assert {"grupos", "total_issues", "impacto_total"} <= set(body["calidad"])
    assert {"correcciones", "staging_procesados", "alertas_emitidas",
            "hay_ventas", "feed"} <= set(body["actividad"])
    assert {"fase", "titulo", "foco", "mensaje", "datos"} <= set(body["fase"])
    assert isinstance(body["solicitudes"], list)


def test_inicio_respeta_features_por_rol():
    """Un rol sin los módulos recibe null/[] — no datos filtrados de otros."""
    creds = auth.cargar_o_generar_credenciales()
    tok = client.post("/api/login", json={"username": "vendedor",
                                          "password": creds["vendedor"]}).json()["token"]
    r = client.get("/api/inicio", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert body["staging"] is None            # sin feature `cargar`
    assert body["calidad"] is None            # sin feature `saneamiento`
    assert body["analisis_objetivos"] is None  # sin feature `oportunidades`
    assert body["solicitudes"] == []          # no es admin


def test_actividad_cuenta_registros_reales(h):
    assert client.get("/api/actividad").status_code == 401
    main.store.audit.record(actor="test", accion="sanear_balanza",
                            antes={"n": 1}, despues={"n": 0})
    r = client.get("/api/actividad", headers=h)
    assert r.status_code == 200
    a = r.json()
    assert a["correcciones"] >= 1                 # el evento recién grabado
    assert {"correcciones", "staging_procesados", "alertas_emitidas",
            "hay_ventas", "feed"} <= set(a)
    assert any(e["accion"] == "sanear_balanza" for e in a["feed"])
    assert all({"tipo", "accion", "actor", "cuando"} <= set(e) for e in a["feed"])


def test_actividad_excluye_eventos_administrativos(h):
    """P13: cambiar idioma/foto/permisos queda en /api/audit, pero no es
    'trabajo de Ángela' — el feed y los contadores no lo cuentan."""
    main.store.audit.record(actor="test", accion="cambiar_idioma",
                            antes={"idioma": "es"}, despues={"idioma": "en"})
    a = client.get("/api/actividad", headers=h).json()
    assert not any(e["accion"] == "cambiar_idioma" for e in a["feed"])
    # pero el evento sí quedó en la auditoría cruda
    eventos = client.get("/api/audit", headers=h).json()["eventos"]
    assert any(e["accion"] == "cambiar_idioma" for e in eventos)


def test_prioridades_inbox_shape(h):
    r = client.get("/api/prioridades", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert {"act", "watch", "badge", "hay_ventas"} <= set(body)
    assert body["badge"] == sum(1 for c in body["act"] if not c.get("action_taken"))
    assert isinstance(body["act"], list) and isinstance(body["watch"], list)
