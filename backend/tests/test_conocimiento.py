"""E1 — modelo de conocimiento del negocio: CRUD, catálogo, scope por rol y la
capa REST. Aísla el JSON por-tenant borrándolo antes/después (como test_memoria):
el archivo no existe en data/ del piloto, así que git diff de data/ queda en 0."""
import os

import pytest
from fastapi.testclient import TestClient

import auth
import main
from core import conocimiento

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def limpio():
    if os.path.exists(conocimiento.CONOCIMIENTO_JSON):
        os.remove(conocimiento.CONOCIMIENTO_JSON)
    yield
    if os.path.exists(conocimiento.CONOCIMIENTO_JSON):
        os.remove(conocimiento.CONOCIMIENTO_JSON)


@pytest.fixture(scope="module")
def tokens():
    creds = auth.cargar_o_generar_credenciales()
    return {u: client.post("/api/login", json={"username": u, "password": creds[u]}).json()["token"]
            for u in ("emilio", "paula", "vendedor", "deposito")}


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def _pieza(**kw):
    base = dict(texto="A Doña Elsa tolerale 45 días.", tipo="regla", ambito="cliente",
                nodo="clientes", efecto="contexto_para_angela", entidad="Despensa Doña Elsa")
    base.update(kw)
    return conocimiento.crear(**base)


# --- modelo -------------------------------------------------------------------

def test_crear_y_leer():
    p = _pieza()
    assert p["id"].startswith("k")
    assert p["estado"] == "activo"
    assert p["veces_aplicada"] == 0
    assert conocimiento.detalle(p["id"])["texto"].startswith("A Doña Elsa")
    assert len(conocimiento.listar()) == 1


def test_filtros_listar():
    _pieza(nodo="clientes", tipo="regla", entidad="Despensa Doña Elsa")
    _pieza(nodo="deposito", tipo="protocolo", ambito="categoria", entidad="fiambres",
           efecto="requiere_aprobacion")
    assert len(conocimiento.listar(nodo="clientes")) == 1
    assert len(conocimiento.listar(tipo="protocolo")) == 1
    assert len(conocimiento.listar(entidad="fiambres")) == 1
    assert len(conocimiento.listar(ambito="categoria")) == 1


@pytest.mark.parametrize("campo,valor", [
    ("tipo", "opinion"), ("ambito", "planeta"), ("nodo", "marketing"),
    ("efecto", "hacer_magia"),
])
def test_catalogo_cerrado(campo, valor):
    with pytest.raises(conocimiento.ConocimientoInvalido):
        _pieza(**{campo: valor})


def test_no_global_necesita_entidad():
    with pytest.raises(conocimiento.ConocimientoInvalido):
        _pieza(ambito="cliente", entidad=None)


def test_global_sin_entidad_ok():
    p = _pieza(ambito="global", entidad=None, nodo="contexto",
               texto="El IPC que uso es el oficial.")
    assert p["entidad"] is None


def test_texto_vacio_rechazado():
    with pytest.raises(conocimiento.ConocimientoInvalido):
        _pieza(texto="   ")


def test_pausar_activar_y_aplicables():
    p = _pieza()
    assert len(conocimiento.aplicables(nodo="clientes")) == 1
    conocimiento.pausar(p["id"])
    assert conocimiento.detalle(p["id"])["estado"] == "pausado"
    assert conocimiento.aplicables(nodo="clientes") == []  # las pausadas no aplican
    assert len(conocimiento.listar()) == 1                 # pero se siguen listando
    conocimiento.activar(p["id"])
    assert len(conocimiento.aplicables(nodo="clientes")) == 1


def test_aplicables_por_efecto_y_entidad():
    _pieza(entidad="Despensa Doña Elsa", efecto="contexto_para_angela")
    _pieza(entidad="Otro Cliente", efecto="suprime_alerta")
    assert len(conocimiento.aplicables(efecto="suprime_alerta")) == 1
    assert len(conocimiento.aplicables(entidad="Despensa Doña Elsa")) == 1


def test_para_matchea_por_entidad_fuzzy():
    # el motor tiene el nombre real ("...2.25L (X6U)"); la pieza, el genérico
    _pieza(nodo="inventario", ambito="categoria", entidad="GASEOSA COLA LA RIBERA",
           efecto="genera_alerta")
    assert len(conocimiento.para("GASEOSA COLA LA RIBERA 2.25L (X6U)", nodo="inventario")) == 1
    assert conocimiento.para("OTRA COSA", nodo="inventario") == []


def test_para_incluir_global():
    _pieza(ambito="global", entidad=None, nodo="caja", efecto="genera_alerta",
           texto="Nunca bajes de $10M.")
    assert conocimiento.para("cualquiera", nodo="caja") == []
    assert len(conocimiento.para("cualquiera", nodo="caja", incluir_global=True)) == 1


def test_texto_en_elige_idioma():
    p = {"texto": "hola", "texto_en": "hi"}
    assert conocimiento.texto_en(p, "en") == "hi"
    assert conocimiento.texto_en(p, "es") == "hola"
    assert conocimiento.texto_en({"texto": "hola"}, "en") == "hola"  # sin texto_en, cae al ES


def test_resumen_pieza_lleva_ambos_idiomas():
    p = _pieza()
    r = conocimiento.resumen_pieza({**p, "texto_en": "EN version"})
    assert r["texto"] and r["texto_en"] == "EN version"
    assert set(r) >= {"id", "tipo", "texto", "texto_en", "nodo", "efecto", "veces_aplicada"}


def test_marcar_aplicada_incrementa():
    p = _pieza()
    conocimiento.marcar_aplicada(p["id"])
    conocimiento.marcar_aplicada(p["id"], 2)
    assert conocimiento.detalle(p["id"])["veces_aplicada"] == 3


def test_borrar():
    p = _pieza()
    assert conocimiento.borrar(p["id"]) is True
    assert conocimiento.detalle(p["id"]) is None
    assert conocimiento.borrar("kNADA") is False


# --- scope por rol (server-side) ---------------------------------------------

def _u(username, admin=False):
    return {"username": username, "es_admin": admin}


def test_scope_admin_ve_todo():
    _pieza(nodo="clientes")
    _pieza(nodo="deposito", ambito="categoria", entidad="fiambres")
    _pieza(nodo="caja", ambito="global", entidad=None)
    assert len(conocimiento.visibles_para(_u("emilio", admin=True))) == 3


def test_scope_empleado_deposito():
    _pieza(nodo="clientes", entidad="Despensa Doña Elsa")           # NO (cuentas)
    _pieza(nodo="deposito", ambito="categoria", entidad="fiambres")  # SÍ (tiene deposito)
    _pieza(nodo="caja", ambito="global", entidad=None)               # SÍ (global)
    vis = conocimiento.visibles_para(_u("deposito"))
    nodos = sorted(p["nodo"] for p in vis)
    assert nodos == ["caja", "deposito"]  # global + su nodo; clientes no


def test_scope_empleado_ve_lo_suyo_propio():
    _pieza(nodo="equipo", ambito="empleado", entidad="deposito",
           texto="Maneja depósito martes y jueves.")  # sobre SÍ mismo
    _pieza(nodo="equipo", ambito="empleado", entidad="paula",
           texto="Consulta cobranzas.")               # sobre otra persona
    vis = conocimiento.visibles_para(_u("deposito"))
    assert len(vis) == 1 and vis[0]["entidad"] == "deposito"


def test_scope_vendedor_ve_clientes_no_deposito():
    _pieza(nodo="clientes", entidad="Despensa Doña Elsa")  # SÍ (cuentas)
    _pieza(nodo="deposito", ambito="categoria", entidad="fiambres")  # NO
    vis = conocimiento.visibles_para(_u("vendedor"))
    assert [p["nodo"] for p in vis] == ["clientes"]


# --- REST ---------------------------------------------------------------------

def test_rest_requiere_login():
    assert client.get("/api/conocimiento").status_code == 401


def test_rest_crear_solo_dueno(tokens):
    body = dict(texto="Gaseosa nunca puede quebrar.", tipo="regla", ambito="categoria",
                nodo="inventario", efecto="genera_alerta", entidad="GASEOSA COLA LA RIBERA")
    r = client.post("/api/conocimiento", json=body, headers=_h(tokens["emilio"]))
    assert r.status_code == 200 and r.json()["pieza"]["id"].startswith("k")
    # un empleado NO puede crear (require_admin), aunque mande rol en el body
    r2 = client.post("/api/conocimiento", json=body, headers=_h(tokens["deposito"]))
    assert r2.status_code == 403


def test_rest_crear_body_invalido_400(tokens):
    body = dict(texto="x", tipo="opinion", ambito="global", nodo="contexto",
                efecto="contexto_para_angela")
    r = client.post("/api/conocimiento", json=body, headers=_h(tokens["emilio"]))
    assert r.status_code == 400


def test_rest_listar_scopeado(tokens):
    client.post("/api/conocimiento", headers=_h(tokens["emilio"]), json=dict(
        texto="Cámara de frío: avisame a mí.", tipo="protocolo", ambito="global",
        nodo="deposito", efecto="requiere_aprobacion"))
    client.post("/api/conocimiento", headers=_h(tokens["emilio"]), json=dict(
        texto="A Doña Elsa 45 días.", tipo="regla", ambito="cliente",
        nodo="clientes", efecto="contexto_para_angela", entidad="Despensa Doña Elsa"))
    # el dueño ve las 2; el de depósito ve solo deposito (clientes queda fuera)
    assert client.get("/api/conocimiento", headers=_h(tokens["emilio"])).json()["total"] == 2
    dep = client.get("/api/conocimiento", headers=_h(tokens["deposito"])).json()
    assert dep["total"] == 1 and dep["piezas"][0]["nodo"] == "deposito"


def test_rest_detalle_404_fuera_de_ambito(tokens):
    pid = client.post("/api/conocimiento", headers=_h(tokens["emilio"]), json=dict(
        texto="A Doña Elsa 45 días.", tipo="regla", ambito="cliente",
        nodo="clientes", efecto="contexto_para_angela",
        entidad="Despensa Doña Elsa")).json()["pieza"]["id"]
    # el dueño lo ve; el de depósito recibe 404 (no es de su ámbito, sin filtrar)
    assert client.get(f"/api/conocimiento/{pid}", headers=_h(tokens["emilio"])).status_code == 200
    assert client.get(f"/api/conocimiento/{pid}", headers=_h(tokens["deposito"])).status_code == 404


def test_rest_estado_y_borrar_solo_dueno(tokens):
    pid = client.post("/api/conocimiento", headers=_h(tokens["emilio"]), json=dict(
        texto="La balanza 2 desvía menos de 1%.", tipo="excepcion", ambito="categoria",
        nodo="deposito", efecto="suprime_alerta", entidad="balanza")).json()["pieza"]["id"]
    # pausar como empleado → 403; como dueño → ok
    assert client.post(f"/api/conocimiento/{pid}/estado", json={"estado": "pausado"},
                       headers=_h(tokens["deposito"])).status_code == 403
    r = client.post(f"/api/conocimiento/{pid}/estado", json={"estado": "pausado"},
                    headers=_h(tokens["emilio"]))
    assert r.status_code == 200 and r.json()["pieza"]["estado"] == "pausado"
    # borrar como empleado → 403; como dueño → ok
    assert client.delete(f"/api/conocimiento/{pid}", headers=_h(tokens["deposito"])).status_code == 403
    assert client.delete(f"/api/conocimiento/{pid}", headers=_h(tokens["emilio"])).status_code == 200
    assert client.get(f"/api/conocimiento/{pid}", headers=_h(tokens["emilio"])).status_code == 404
