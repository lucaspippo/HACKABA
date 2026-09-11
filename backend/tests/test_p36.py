"""
P36·E1 — El feed de "Lo que Ángela ya hizo" dice la VERDAD LITERAL: solo
eventos de NEGOCIO, nunca posteriores a la fecha congelada del tenant, sin
duplicados, y con los contadores calculados bajo EXACTAMENTE el mismo filtro
que el feed. Falla si un evento post-freeze se cuela o si contadores ≠ feed.
"""
import datetime

import pytest
from fastapi.testclient import TestClient

import auth
import main
from core import fechas

client = TestClient(main.app)


@pytest.fixture()
def h():
    creds = auth.cargar_o_generar_credenciales()
    tok = client.post("/api/login", json={"username": "emilio", "password": creds["emilio"]}).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


# Audit sintético: negocio dentro de la ventana + trabajo de dev fuera (post-freeze)
# + administrativo + un duplicado exacto (mismo día/acción/despues).
EVENTOS = [
    {"id": 1, "actor": "marta", "accion": "sanear_balanza", "antes": {"n": 3}, "despues": {"n": 0}, "cuando": "2026-07-06T10:00:00"},
    {"id": 2, "actor": "nahuel", "accion": "integrar_staging", "antes": None, "despues": {"archivo": "x.csv"}, "cuando": "2026-07-05T10:00:00"},
    {"id": 3, "actor": "marta", "accion": "sanear_balanza", "antes": {"n": 3}, "despues": {"n": 0}, "cuando": "2026-07-06T10:00:00"},  # DUP exacto
    {"id": 4, "actor": "dev", "accion": "crear_apartado", "antes": {"batch": "ventas.csv"}, "despues": {"nuevas": 0}, "cuando": "2026-07-23T22:00:00"},  # técnico/seed
    {"id": 5, "actor": "dev", "accion": "sanear_fantasma", "antes": {}, "despues": {"n": 0}, "cuando": "2026-07-24T09:00:00"},  # POST-freeze
    {"id": 6, "actor": "ana", "accion": "cambiar_idioma", "antes": {}, "despues": {}, "cuando": "2026-07-06T09:00:00"},  # administrativo
]


@pytest.fixture()
def congelado(monkeypatch):
    monkeypatch.setattr(fechas, "hoy", lambda: datetime.date(2026, 7, 7))
    monkeypatch.setattr(main.store.audit, "list", lambda: list(EVENTOS))


def test_feed_sin_eventos_posteriores_a_la_fecha_congelada(h, congelado):
    a = client.get("/api/actividad", headers=h).json()
    assert a["feed"], "el feed no puede quedar vacío con eventos de negocio válidos"
    for e in a["feed"]:
        assert e["cuando"][:10] <= "2026-07-07", f"evento post-freeze en el feed: {e}"


def test_feed_solo_eventos_de_negocio(h, congelado):
    a = client.get("/api/actividad", headers=h).json()
    acciones = {e["accion"] for e in a["feed"]}
    assert "crear_apartado" not in acciones   # técnico/seed
    assert "cambiar_idioma" not in acciones    # administrativo
    assert "sanear_fantasma" not in acciones   # post-freeze


def test_feed_deduplica_con_contador(h, congelado):
    a = client.get("/api/actividad", headers=h).json()
    balanza = [e for e in a["feed"] if e["accion"] == "sanear_balanza"]
    assert len(balanza) == 1, "el duplicado exacto debe colapsar en una línea"
    assert balanza[0]["veces"] == 2, "la línea colapsada lleva el contador"


def test_contadores_bajo_el_mismo_filtro_que_el_feed(h, congelado):
    a = client.get("/api/actividad", headers=h).json()
    # negocio (no admin, no técnico) y <= fecha congelada: sanear_balanza x2 +
    # integrar_staging = 3 eventos → 2 correcciones + 1 procesado.
    assert a["correcciones"] == 2
    assert a["staging_procesados"] == 1
    # ningún evento del feed queda fuera del universo contado
    total = a["correcciones"] + a["staging_procesados"]
    assert total == 3, "contadores y feed cuentan el MISMO conjunto filtrado"


# --- E4: objetivos medidos --------------------------------------------------

def test_objetivos_medidos_progreso_calculado_y_distribucion():
    from core import objetivos_medidos as om
    actuales = {"dias_cobro": 25, "datos_corregir": 20,
                "liberar_dormido": 19_000_000, "pvp_margen": 8, "concentracion": 41.5}
    objs = om.construir(actuales, "2026-07-07")
    assert len(objs) == 5
    d = {o["id"]: o for o in objs}
    # progreso REAL calculado (no hardcodeado): coincide con la fórmula
    assert round(d["dias_cobro"]["progreso"], 2) == round((29 - 25) / (29 - 20), 2)
    # distribución: uno casi cumplido, uno estancado
    assert d["liberar_dormido"]["progreso"] >= 0.9
    assert d["concentracion"]["estado"] == "estancado"
    assert all(o["progreso"] < 1.0 for o in objs)         # ninguno "cumplido" al 100
    assert all(o["progreso"] > 0.0 for o in objs)         # ninguno en 0%
    # historial = 3 puntos sintéticos + el actual real; fechas ≤ congelada
    for o in objs:
        assert len(o["historial"]) == 4
        assert o["historial"][-1]["valor"] == actuales[o["id"]]
        assert all(p["fecha"] <= "2026-07-07" for p in o["historial"])


def test_objetivos_medidos_responsables_reales():
    from core import objetivos_medidos as om
    objs = om.construir({"dias_cobro": 25, "concentracion": 41.5}, "2026-07-07")
    assert {o["responsable"] for o in objs} <= {"marta", "celeste", "aldo"}
    assert next(o for o in objs if o["id"] == "dias_cobro")["responsable"] == "marta"
