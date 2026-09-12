"""
i18n (Prompt 8): la preferencia de idioma vive POR USUARIO en el servidor
(perfiles), con default por tenant (POLPILOT_DEFAULT_LANG). Un solo lugar
(perfiles.idioma_de) la resuelve para cualquier canal — web hoy, WhatsApp mañana.
El catálogo backend (i18n.t) cae a 'es' si falta la clave en 'en' y nunca revienta.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

import angela
import auth
import i18n
import main
from core import paths, perfiles
from tests.conftest import limpiar_tabla_tenant


@pytest.fixture(autouse=True)
def limpio():
    limpiar_tabla_tenant("user_profiles")
    yield
    limpiar_tabla_tenant("user_profiles")


@pytest.fixture()
def tokens():
    creds = auth.cargar_o_generar_credenciales()
    c = TestClient(main.app)
    t = {}
    for u in ("deposito", "paula", "emilio"):
        r = c.post("/api/login", json={"username": u, "password": creds[u]})
        assert r.status_code == 200
        t[u] = r.json()["token"]
    return c, t


# --- resolución del idioma ------------------------------------------------------

def test_sin_eleccion_rige_el_default_del_tenant():
    # el piloto (sin env) arranca en español — regla inviolable del prompt 8
    assert paths.DEFAULT_LANG == "es"
    assert perfiles.idioma_de("deposito") == "es"


def test_la_preferencia_persiste_por_usuario():
    perfiles.set_idioma("deposito", "en")
    assert perfiles.idioma_de("deposito") == "en"
    # y NO contamina a otro usuario
    assert perfiles.idioma_de("paula") == "es"
    # se puede volver
    perfiles.set_idioma("deposito", "es")
    assert perfiles.idioma_de("deposito") == "es"


def test_default_del_tenant_configurable(monkeypatch):
    # simula el tenant demo levantado con POLPILOT_DEFAULT_LANG=en
    monkeypatch.setattr(paths, "DEFAULT_LANG", "en")
    assert perfiles.idioma_de("deposito") == "en"      # nunca eligió → default del tenant
    perfiles.set_idioma("deposito", "es")
    assert perfiles.idioma_de("deposito") == "es"      # su elección pisa el default


def test_idioma_invalido_no_entra():
    with pytest.raises(ValueError):
        perfiles.set_idioma("deposito", "klingon")


# --- API --------------------------------------------------------------------------

def test_idioma_viaja_en_login_y_me(tokens):
    c, t = tokens
    r = c.get("/api/me", params={"token": t["deposito"]})
    assert r.status_code == 200
    assert r.json().get("idioma") == "es"


def test_cambiar_idioma_por_api_y_leerlo(tokens):
    c, t = tokens
    r = c.post("/api/perfil/deposito/idioma",
               json={"token": t["deposito"], "idioma": "en"})
    assert r.status_code == 200 and r.json()["idioma"] == "en"
    assert c.get("/api/me", params={"token": t["deposito"]}).json()["idioma"] == "en"


def test_nadie_cambia_el_idioma_ajeno(tokens):
    c, t = tokens
    r = c.post("/api/perfil/paula/idioma",
               json={"token": t["deposito"], "idioma": "en"})
    assert r.status_code == 403
    assert perfiles.idioma_de("paula") == "es"


def test_idioma_invalido_por_api_da_400(tokens):
    c, t = tokens
    r = c.post("/api/perfil/deposito/idioma",
               json={"token": t["deposito"], "idioma": "fr"})
    assert r.status_code == 400


def test_health_expone_el_default_del_tenant():
    c = TestClient(main.app)
    assert c.get("/api/health").json()["idioma_default"] == paths.DEFAULT_LANG


# --- catálogo t() ------------------------------------------------------------------

def test_t_devuelve_cada_idioma():
    assert "dueño" in i18n.t("authz.solo_dueno", "es")
    assert "owner" in i18n.t("authz.solo_dueno", "en")


def test_t_cae_a_espanol_si_falta_la_clave_en_ingles():
    i18n.CATALOGO["_solo_es"] = {"es": "sólo en criollo"}
    try:
        assert i18n.t("_solo_es", "en") == "sólo en criollo"
    finally:
        del i18n.CATALOGO["_solo_es"]


def test_t_clave_inexistente_devuelve_la_clave():
    # que el bug se VEA en pantalla, no que se esconda
    assert i18n.t("no.existe", "en") == "no.existe"


def test_t_con_parametros():
    assert "es, en" in i18n.t("perfil.idioma_invalido", "en", validos="es, en")


# --- E9a: el router simulado (_fallback) habla el idioma de la conversación --------

@pytest.fixture()
def angela_lang():
    """Setea el idioma/las features de la conversación como lo haría responder()."""
    prev_lang, prev_feats = angela._idioma_actual(), angela._features_actuales()

    def _set(lang, features=None):
        angela._set_sesion(features=features, idioma=lang)

    yield _set
    angela._set_sesion(features=prev_feats, idioma=prev_lang)


def test_fallback_cuentas_responde_en_ingles(angela_lang):
    angela_lang("en")
    r = angela._fallback("who owes me money?")
    assert r["mode"] == "simulado"
    # con o sin morosos — o sin cuentas REALES (P45·T3: el guard responde que
    # falta el dato) — la respuesta sale del catálogo EN
    assert ("overdue" in r["answer"] or "keeping up" in r["answer"]
            or "factory seed" in r["answer"])
    assert "mora" not in r["answer"]


def test_fallback_caja_responde_en_ingles(angela_lang):
    angela_lang("en")
    r = angela._fallback("how much cash do I have in the register?")
    assert "register" in r["answer"]
    # Las tools NO cambian de nombre con el idioma. Actualizado en P9·C7 (M11):
    # "caja" nunca existió en TOOLS — el nombre real es estado_caja.
    assert "estado_caja" in r["tools_used"]
    assert "En caja" not in r["answer"]


def test_fallback_default_responde_en_ingles(angela_lang):
    angela_lang("en")
    r = angela._fallback("hello there")
    assert "Where do we start?" in r["answer"]
    assert "ANTHROPIC_API_KEY" in r["answer"]  # el aviso de modo datos sigue
    # y el monto va con agrupación en-US (coma), nunca 1.234.567
    assert "$" in r["answer"]


def test_fallback_es_queda_byte_igual(angela_lang):
    angela_lang("es")
    r = angela._fallback("hello there")
    assert "¿Por dónde arrancamos?" in r["answer"]
    assert "(Modo datos: para charla libre total falta cargar ANTHROPIC_API_KEY.)" in r["answer"]


def test_fallback_opciones_label_en_enviar_es(angela_lang):
    # El label lo lee el humano (EN); el enviar se re-inyecta al router,
    # cuyo matching es por keywords en español → queda en ES.
    angela_lang("en")
    r = angela._fallback("make me a chart of the money per product")
    assert r["options"], "el widget sin sección debe ofrecer opciones"
    labels = [o["label"] for o in r["options"]]
    assert "On Home" in labels and "In Inventory" in labels
    assert all("poné un gráfico" in o["enviar"] for o in r["options"])


def test_fallback_bloqueo_por_feature_en_ingles(angela_lang):
    angela_lang("en", features={"deposito", "logistica", "perfil", "angela"})
    r = angela._fallback("who owes me money?")
    assert "isn't part of" in r["answer"]     # fb.bloqueado en EN
    assert "cuentas" not in r["tools_used"]


# --- E9b: los textos que PRODUCE core/ salen en el idioma del usuario --------------

def test_quality_labels_en_ingles_y_es_byte_igual():
    from core import quality
    from core.models import Articulo, CATEGORIA_LABEL, Categoria
    arts = [
        Articulo.from_dict({"codigo": 1, "descripcion": "X", "estado": "activo",
                            "stock": 4, "costo_iva": 100, "inmovilizado": 400}),   # sin precio
        Articulo.from_dict({"codigo": 2, "descripcion": "Y", "estado": "anulado",
                            "stock": 10}),                                          # fantasma
    ]
    libro_es = quality.libro_triado(arts)            # default: byte-igual histórico
    por_cat = {g["categoria"]: g for g in libro_es["grupos"]}
    assert por_cat["sin_precio"]["label"] == CATEGORIA_LABEL[Categoria.SIN_PRECIO]
    assert por_cat["fantasma"]["label"] == CATEGORIA_LABEL[Categoria.FANTASMA]

    libro_en = quality.libro_triado(arts, "en")
    por_cat_en = {g["categoria"]: g for g in libro_en["grupos"]}
    assert por_cat_en["sin_precio"]["label"] == "No sale price loaded"
    assert por_cat_en["fantasma"]["label"] == "Cancelled with live stock"
    # los IDs no se traducen JAMÁS (la UI colorea por estado/categoría)
    assert por_cat_en["sin_precio"]["estado"] == "incompleto"
    assert por_cat_en["sin_precio"]["estado_label"] == "incomplete"


def test_grupos_y_salud_labels_en_ingles():
    import data_store as ds
    # ES byte-igual al dict histórico; EN traducido, mismos keys (IDs)
    assert ds.grupos_disponibles() == ds.GRUPOS_LABEL
    assert ds.grupo_label("sin_pvp", "en") == "No sale price loaded"
    r_es, r_en = ds.resumen(), ds.resumen("en")
    assert r_es["resumen"]["salud"]["nivel"] == r_en["resumen"]["salud"]["nivel"]
    assert r_en["resumen"]["salud"]["label"] in (
        "Needs urgent action", "Attention required", "In order")


def test_analisis_objetivos_en_ingles_en_demo():
    """En el tenant demo (ventas validadas) los objetivos salen en EN con lang."""
    import json as _json
    import subprocess
    import sys
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_demo = os.path.join(os.path.dirname(backend), "data-demo")
    env = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": data_demo,
           "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)
    r = subprocess.run([sys.executable, "-c", """
import json
from core import analisis
o_en = analisis.objetivos(lang="en")["objetivos"]
o_es = analisis.objetivos()["objetivos"]
print(json.dumps({"en": {x["id"]: x for x in o_en}, "es": {x["id"]: x for x in o_es}}))
"""], cwd=backend, env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    o = _json.loads(r.stdout)
    dormido_en, dormido_es = o["en"]["liquidar_dormido"], o["es"]["liquidar_dormido"]
    assert dormido_en["titulo"].startswith("Wake up $")
    assert "sleeping stock" in dormido_en["titulo"]
    assert dormido_es["titulo"].startswith("Despertar $")          # ES intacto
    if "crecimiento" in o["en"]:
        assert "units sold in the last 12 months" in o["en"]["crecimiento"]["detalle"]


def test_mensaje_cobro_firma_con_el_nombre_del_tenant(monkeypatch):
    """P14: el recordatorio de cobro firma con el negocio del TENANT — en el
    demo no puede decir 'Horizonte' (fuga del piloto en cámara)."""
    from core import cuentas, paths
    monkeypatch.setattr(paths, "NOMBRE_CORTO", "Distribuidora del Litoral")
    m = cuentas.mensaje_cobro("perez")["mensaje"]
    assert "Distribuidora del Litoral" in m
    assert "Horizonte" not in m


def test_oportunidades_bilingues_y_es_verbatim():
    """P14: data_store.oportunidades() sale del catálogo — EN traducido y el
    ES byte-igual al texto histórico. Los IDs no se traducen."""
    import data_store as ds
    es = ds.oportunidades()
    en = ds.oportunidades("en")
    por_id_es = {o["id"]: o for o in es["concretas"]}
    por_id_en = {o["id"]: o for o in en["concretas"]}
    # ES intacto (verbatim al histórico)
    assert por_id_es["balanza"]["titulo"] == "Corregí las balanzas y dejá de regalar fiambre"
    assert por_id_es["sin_pvp"]["titulo"] == "Cargá los precios que faltan y vendé lo que hoy no podés cobrar bien"
    assert por_id_es["sin_pvp"]["impacto_label"] == "en stock sin precio firme"
    # EN traducido
    assert por_id_en["balanza"]["titulo"] == "Fix the scales and stop giving away deli meat"
    assert "active products without a sale price" in por_id_en["sin_pvp"]["descripcion"]
    # Los pendientes existen en ambos idiomas con los MISMOS ids
    assert {p["id"] for p in es["pendientes"]} == {p["id"] for p in en["pendientes"]}
    for p in en["pendientes"]:
        if p["id"] == "rotacion":
            assert p["falta"] == "sales history"


def test_cuentas_mensaje_cobro_en_ingles_y_es_byte_igual():
    from core import cuentas
    c = cuentas.get("perez")
    assert c, "el seed demo de cuentas trae a perez"
    # ES default: BYTE-IGUAL al histórico (incluido el replace de comas)
    extra = (f" Históricamente pagás a los {c['promedio_pago_dias']} días; hoy estás "
             f"{c['atraso_vs_promedio']}% más tarde.") if c["atraso_vs_promedio"] > 0 else ""
    historico = (f"Hola, te escribo de Horizonte. Te recuerdo que tenés un saldo pendiente de "
                 f"${c['saldo']:,.0f} con {c['dias_sin_pagar']} días.{extra} ¿Coordinamos el pago? "
                 f"Gracias.").replace(",", ".")
    assert cuentas.mensaje_cobro("perez")["mensaje"] == historico
    # EN: el mensaje de WhatsApp sale en inglés, con agrupación en-US
    m_en = cuentas.mensaje_cobro("perez", "en")["mensaje"]
    assert "Hi, this is Horizonte." in m_en
    assert "outstanding balance" in m_en
    assert f"${c['saldo']:,.0f}" in m_en                            # $30,000,000


def test_evolucion_sin_datos_en_ingles(monkeypatch):
    from core import evolucion, macro
    monkeypatch.delenv("POLPILOT_DEMO_EVOLUCION", raising=False)
    monkeypatch.setattr(macro, "ipc_serie", lambda lang=None: {"disponible": False})
    if evolucion.hay_datos():
        pytest.skip("el piloto cargó ventas: este test cubre el estado sin datos")
    p_es = evolucion.panorama()
    assert p_es["mensaje"] == ("Se activa al cargar las ventas históricas (el mismo CSV que "
                               "despierta rotación, margen y quiebre de stock).")
    p_en = evolucion.panorama("en")
    assert p_en["hay_datos"] is False
    assert "historical sales" in p_en["mensaje"]
    assert "ventas" not in p_en["mensaje"]


def test_fase_en_ingles_y_es_byte_igual():
    from core import fase
    f_es, f_en = fase.actual(), fase.actual("en")
    assert f_es["fase"] == f_en["fase"]                             # el ID no cambia
    assert f_es["titulo"] in ("Puesta a punto", "En operación")
    assert f_en["titulo"] in ("Getting set up", "Up and running")
    assert f_en["mensaje"] and "tenés" not in f_en["mensaje"]


# --- E9a: el 403 de require_feature sale en el idioma del usuario ------------------

def test_403_de_require_feature_habla_el_idioma_del_usuario(tokens):
    c, t = tokens
    # deposito (sin el módulo cuentas) elige inglés → el 403 le habla en inglés
    perfiles.set_idioma("deposito", "en")
    r = c.get("/api/cuentas", params={"token": t["deposito"]})
    assert r.status_code == 403
    assert r.json()["detail"] == "Your role doesn't have access to the «cuentas» module."
    # paula (es, sin el módulo deposito) lo recibe en castellano, byte-igual
    r = c.get("/api/deposito", params={"token": t["paula"]})
    assert r.status_code == 403
    assert r.json()["detail"] == "Tu rol no tiene acceso al módulo «deposito»."
