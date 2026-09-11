"""
P·onboarding — el empleado nuevo y el manual con el que Ángela le enseña.

Lo que se protege acá:

  1. ANTIGÜEDAD REAL: "nuevo" no es un flag que alguien prende a mano — sale de
     la fecha de ingreso del perfil contra el "hoy" del sistema. Quien no
     declara ingreso sigue exactamente como estaba (aditivo).
  2. EL NUEVO NO ES UN USUARIO CAPADO: tiene las MISMAS features que el resto
     del depósito de a pie y la misma vista-herramienta; el onboarding es un
     plus, no un reemplazo.
  3. DETERMINISMO: cada dato del manual sale de un archivo real (ubicaciones del
     WMS, días de reposición de cada proveedor, reglas del dueño, ritmo de venta)
     y coincide con lo que devuelven los módulos de siempre. Nada lo inventa el
     modelo.
  4. SCOPE: el manual respeta «Quién ve qué». Un rol sin depósito no ve las
     ubicaciones por esta puerta, y las reglas llegan ya filtradas por ámbito.

El grueso corre en un SUBPROCESO contra el dataset demo canónico (mismo patrón
que test_consultas/test_kpis): el tenant se elige por env, no por import.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DEMO = os.path.join(os.path.dirname(BACKEND), "data-demo")
ENV = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": DATA_DEMO,
       "POLPILOT_DEMO_TODAY": "2026-07-07", "PYTHONIOENCODING": "utf-8"}
ENV.pop("ANTHROPIC_API_KEY", None)


def _en_demo(codigo: str) -> dict:
    # encoding explícito: en Windows el decode por locale (cp1252) rompe los
    # acentos de los datos reales, y acá se comparan nombres con acento.
    r = subprocess.run([sys.executable, "-c", codigo], cwd=BACKEND, env=ENV,
                       capture_output=True, text=True, encoding="utf-8", timeout=180)
    assert r.returncode == 0, r.stderr[-800:]
    return json.loads(r.stdout.strip().splitlines()[-1])


# --- 1 · la antigüedad sale del dato, no de una etiqueta ------------------------

def test_antiguedad_del_nuevo_y_de_los_de_siempre():
    out = _en_demo(
        "import json, auth;"
        "print(json.dumps({'kevin': auth.antiguedad('kevin'),"
        " 'ramon': auth.antiguedad('ramon'),"
        " 'puesto': auth.puesto('kevin')}, ensure_ascii=False))")
    # con la fecha congelada del demo, entró hace exactamente una semana
    assert out["kevin"]["dias"] == 7 and out["kevin"]["semanas"] == 1
    assert out["kevin"]["nuevo"] is True
    # los 13 de siempre no declaran ingreso: nada cambia para ellos
    assert out["ramon"] is None
    # el mentor se resuelve a una persona REAL del equipo
    assert out["puesto"]["mentor"]["username"] == "ramon"


def test_el_nuevo_viaja_en_la_lista_del_equipo():
    """La lista que alimenta "Ver como" y el equipo manda la antigüedad de cada
    persona: sin eso el chip "Nuevo" sería una lista aparte."""
    out = _en_demo(
        "import json, auth, main;"
        "from fastapi.testclient import TestClient;"
        "creds = auth.cargar_o_generar_credenciales();"
        "c = TestClient(main.app);"
        "tk = c.post('/api/login', json={'username':'aldo','password':creds['aldo']}).json()['token'];"
        "eq = c.get('/api/equipo/nombres', headers={'Authorization': 'Bearer '+tk}).json()['equipo'];"
        "print(json.dumps({'n': len(eq),"
        " 'nuevos': [p['username'] for p in eq if (p.get('antiguedad') or {}).get('nuevo')],"
        " 'kevin': any(p['username']=='kevin' for p in eq)}, ensure_ascii=False))")
    assert out["kevin"] and out["n"] == 14
    assert out["nuevos"] == ["kevin"]


# --- 2 · el nuevo tiene lo mismo que el resto del depósito ----------------------

def test_el_nuevo_no_es_un_usuario_capado():
    out = _en_demo(
        "import json, auth;"
        "print(json.dumps({'kevin': auth.USUARIOS['kevin']['features'],"
        " 'tomas': auth.USUARIOS['tomas']['features'],"
        " 'rol': auth.USUARIOS['kevin']['rol']}, ensure_ascii=False))")
    # mismas features que el otro de depósito de a pie: ni una de más, ni una de menos
    assert set(out["kevin"]) == set(out["tomas"])
    # y su rol cae en el catálogo de depósito (vista-herramienta, voz, chips)
    assert "depósito" in out["rol"].lower()


# --- 3 · determinismo: los datos son los de los módulos de siempre --------------

def test_el_manual_dice_lo_mismo_que_los_modulos():
    out = _en_demo(
        "import json, auth;"
        "from core import onboarding, deposito, reposicion;"
        "u = auth.perfil_publico('kevin');"
        "g = onboarding.guia(u);"
        "print(json.dumps({"
        " 'ubis_guia': g['ubicaciones']['total'],"
        " 'ubis_deposito': deposito.resumen()['ubicaciones'],"
        " 'lotes_guia': g['ubicaciones']['lotes'],"
        " 'lotes_deposito': deposito.resumen()['lotes'],"
        " 'provs_guia': [p['proveedor'] for p in g['reposicion']['proveedores']],"
        " 'provs_archivo': [c['proveedor'] for c in reposicion.condiciones()],"
        " 'ribera_guia': [p['dias_reposicion'] for p in g['reposicion']['proveedores']"
        "                 if 'Ribera' in p['proveedor']][0],"
        " 'ribera_modulo': reposicion.dias_reposicion('Frigorífico La Ribera')[0],"
        " 'donde_jamon': onboarding.donde_esta('jamon cocido')['resultados'][0]['ubicacion'],"
        "}, ensure_ascii=False))")
    assert out["ubis_guia"] == out["ubis_deposito"]
    assert out["lotes_guia"] == out["lotes_deposito"]
    assert sorted(out["provs_guia"]) == sorted(out["provs_archivo"])
    assert out["ribera_guia"] == out["ribera_modulo"] == 3
    # la ubicación es la del export, no una inventada
    assert "Cámara" in out["donde_jamon"]


def test_cada_cuanto_cruza_ritmo_real_y_tiempo_del_proveedor():
    """"¿Cada cuánto reponemos esto?" se contesta con las tres cifras que hacen
    falta: lo que se vende por día, los días de stock y lo que tarda el
    proveedor. Ninguna sola alcanza, y ninguna se estima."""
    out = _en_demo(
        "import json;"
        "from core import onboarding;"
        "r = onboarding.cada_cuanto('GASEOSA COLA EL PARANA');"
        "print(json.dumps(r['items'][0], ensure_ascii=False))")
    assert out["unidades_12m"] > 0 and out["por_dia"] > 0
    assert out["dias_de_stock"] > 0
    assert out["dias_reposicion_proveedor"] > 0
    assert out["lead_es_dato_propio"] is True


def test_el_manual_no_inventa_lo_que_no_existe():
    out = _en_demo(
        "import json;"
        "from core import onboarding;"
        "print(json.dumps({'donde': onboarding.donde_esta('sillon de tres cuerpos'),"
        " 'cuanto': onboarding.cada_cuanto('sillon de tres cuerpos')}, ensure_ascii=False))")
    assert out["donde"]["encontrados"] == 0 and out["donde"]["resultados"] == []
    assert out["cuanto"]["encontrados"] == 0 and out["cuanto"]["items"] == []


# --- 4 · el manual respeta «Quién ve qué» ---------------------------------------

def test_scope_del_manual_por_rol():
    out = _en_demo(
        "import json, auth, angela;"
        "res = {};"
        "u = auth.perfil_publico('kevin');"
        "angela._set_sesion(usuario='kevin', rol=u['rol'], features=u['features']);"
        "res['kevin_ubis'] = angela._run_tool('consultar_manual', {'tema':'ubicaciones'})[0].get('hay_datos');"
        "res['kevin_reglas'] = len(angela._run_tool('consultar_manual', {'tema':'reglas'})[0]['reglas']);"
        "d = auth.perfil_publico('diego');"
        "angela._set_sesion(usuario='diego', rol=d['rol'], features=d['features']);"
        "res['diego_ubis'] = angela._run_tool('consultar_manual', {'tema':'ubicaciones'})[0].get('sin_modulo');"
        "from core import conocimiento;"
        "res['diego_reglas'] = [[conocimiento.detalle(r['id'])['nodo'],"
        "                        conocimiento.detalle(r['id'])['ambito']]"
        "   for r in angela._run_tool('consultar_manual', {'tema':'reglas'})[0]['reglas']];"
        "print(json.dumps(res, ensure_ascii=False))")
    assert out["kevin_ubis"] is True
    assert out["kevin_reglas"] > 0
    # el preventista no tiene depósito: el manual no es una puerta lateral
    assert out["diego_ubis"] == "deposito"
    # y del depósito sólo le llegan las reglas GLOBALES (la del frío, que es de
    # todos); las de ámbito acotado a depósito no entran a su manual
    assert all(ambito == "global" for nodo, ambito in out["diego_reglas"] if nodo == "deposito")


def test_los_procesos_se_recortan_a_lo_que_la_persona_puede_hacer():
    out = _en_demo(
        "import json;"
        "from core import onboarding;"
        "print(json.dumps({"
        " 'con_todo': [p['id'] for p in onboarding.procesos({'deposito','cargar'})],"
        " 'sin_cargar': [p['id'] for p in onboarding.procesos({'deposito'})],"
        " 'pelado': [p['id'] for p in onboarding.procesos(set())]}, ensure_ascii=False))")
    assert "recepcion" in out["con_todo"] and "factura" in out["con_todo"]
    # sin el módulo de carga no se le enseña un botón que no ve
    assert "recepcion" not in out["sin_cargar"] and "faltante" in out["sin_cargar"]
    # preguntarle a Ángela no necesita módulos: es de todos
    assert out["pelado"] == ["preguntar"]


def test_los_pasos_estan_en_los_dos_idiomas():
    """Convención de la casa: todo string que lee un humano nace bilingüe."""
    from core import onboarding
    for p in onboarding.PROCESOS:
        assert p["pasos"] and p["pasos_en"], p["id"]
        assert len(p["pasos"]) == len(p["pasos_en"]), p["id"]


# --- 5 · el endpoint -----------------------------------------------------------

def test_endpoint_onboarding_devuelve_la_guia_del_que_pregunta():
    out = _en_demo(
        "import json, auth, main;"
        "from fastapi.testclient import TestClient;"
        "creds = auth.cargar_o_generar_credenciales();"
        "c = TestClient(main.app);"
        "tk = c.post('/api/login', json={'username':'kevin','password':creds['kevin']}).json()['token'];"
        "r = c.get('/api/onboarding', headers={'Authorization': 'Bearer '+tk});"
        "g = r.json();"
        "print(json.dumps({'status': r.status_code, 'quien': g['persona']['username'],"
        " 'nuevo': g['persona']['antiguedad']['nuevo'],"
        " 'temas': [k for k in ('ubicaciones','reposicion','procesos','reglas','contactos')"
        "           if g.get(k)],"
        " 'contactos': [c2['para'] for c2 in g['contactos']]}, ensure_ascii=False))")
    assert out["status"] == 200
    assert out["quien"] == "kevin" and out["nuevo"] is True
    assert set(out["temas"]) == {"ubicaciones", "reposicion", "procesos", "reglas", "contactos"}
    assert set(out["contactos"]) == {"deposito", "compras", "administracion", "dueno"}


def test_onboarding_pide_sesion():
    out = _en_demo(
        "import json, main;"
        "from fastapi.testclient import TestClient;"
        "c = TestClient(main.app);"
        "print(json.dumps({'sin_token': c.get('/api/onboarding').status_code}))")
    assert out["sin_token"] == 401
