"""Reglas del sugeridor de módulos (P6):
- al dueño/admin NUNCA se le sugiere pedir módulos;
- el matching es por palabra (borde), no substring ("venta" no dispara "vend");
- la sugerencia sale de la descripción real del usuario.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import perfiles  # noqa: E402


def _con_descripcion(username, texto):
    """Aplica una descripción temporal y devuelve las sugerencias."""
    r = perfiles.set_descripcion(username, texto)
    return r["sugerencias"]


def _restaurar(username):
    d = perfiles._load()
    d["usuarios"].get(username, {}).pop("descripcion", None)
    perfiles._save(d)


def test_admin_nunca_recibe_sugerencias():
    # emilio es el dueño del piloto: tiene es_admin y no se pide permisos a sí mismo
    assert perfiles.sugerir_modulos("emilio") == []
    try:
        sugs = _con_descripcion("emilio", "cobro el fiado y manejo la caja y el deposito")
        assert sugs == [], "al admin no se le sugiere nada, diga lo que diga su descripción"
    finally:
        _restaurar("emilio")


def test_matching_por_palabra_no_substring():
    # "bocas de venta" NO debe disparar cobranzas (la señal vieja "vend" matcheaba "venta")
    try:
        sugs = _con_descripcion("deposito", "superviso las bocas de venta del local")
        assert "cobranzas" not in {s["modulo"] for s in sugs}
    finally:
        _restaurar("deposito")


def test_sugerencia_sale_de_la_descripcion_real():
    try:
        sugs = {s["modulo"] for s in _con_descripcion("deposito", "ahora tambien cobro el fiado de los clientes")}
        assert "cuentas" in sugs or "cobranzas" in sugs
        # y si la descripción no dice nada de plata, no hay sugerencias de cobranza
        sugs2 = {s["modulo"] for s in _con_descripcion("deposito", "acomodo los pallets nomas")}
        assert "cuentas" not in sugs2 and "cobranzas" not in sugs2
    finally:
        _restaurar("deposito")


# --- P11·B5: señales ambiguas afuera — mencionar una palabra no es hacer el trabajo ---

def test_vencimientos_de_pago_no_sugiere_deposito():
    """LA reproducción del bug: la administradora que mira 'los vencimientos de
    pago a proveedores' recibía la sugerencia de pedir acceso a Depósito."""
    try:
        sugs = {s["modulo"] for s in _con_descripcion(
            "deposito", "miro los vencimientos de pago a proveedores y concilio la caja")}
        assert "deposito" not in sugs
    finally:
        _restaurar("deposito")


def test_orden_de_los_pasillos_no_sugiere_documentos():
    try:
        sugs = {s["modulo"] for s in _con_descripcion(
            "vendedor", "mantengo el orden de los pasillos y los remitos firmados")}
        assert "documentos" not in sugs
    finally:
        _restaurar("vendedor")


# --- P11·B5: auditoría COMPLETA del demo — cada sugerencia visible, defendible ---

def test_auditoria_sugerencias_demo():
    """El mapa completo y congelado de sugerencias por usuario del demo. Si una
    señal nueva vuelve a ensuciar esto, el test lo muestra con nombre y apellido.
    Cada entrada tiene su defensa en la descripción del perfil:
      brian → logistica (arma pallets POR reparto y carga los camiones)
      nahuel → alertas (etiqueta lotes y fechas de vencimiento)
      tomas → inventario (repone puntas de góndola)
      walter → cuentas/cobranzas (cobra el contado en la ruta)
      diego → logistica (levanta pedidos para el reparto) + inventario (góndolas)
      lucia → logistica (su cartera es una ruta de reparto)
      vanesa → inventario (vive mirando los precios de balanza)

    P16: la sugerencia de vanesa se materializó como SOLICITUD pendiente
    (sembrada por generar.py) — mientras esté pendiente, sugerir_modulos no la
    repite (comportamiento correcto). El test acepta cualquiera de los dos
    estados, pero exige que la defensa exista: sugerencia visible O solicitud
    pendiente por ese mismo módulo."""
    import json as _json
    import os as _os
    import subprocess as _sp
    import sys as _sys
    backend = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    env = {**_os.environ, "POLPILOT_TENANT": "demo",
           "POLPILOT_DATA_DIR": _os.path.join(_os.path.dirname(backend), "data-demo"),
           "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)
    r = _sp.run([_sys.executable, "-c", """
import json
import auth
from core import perfiles
out = {u: [s["modulo"] for s in perfiles.sugerir_modulos(u)]
       for u, v in auth.USUARIOS.items() if not v.get("interno")}
pend = [(s["usuario"], s["modulo"]) for s in perfiles.solicitudes(estado="pendiente")]
print(json.dumps({"sugerencias": out, "pendientes": pend}))
"""], cwd=backend, env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    d = _json.loads(r.stdout)
    sugerencias = d["sugerencias"]
    pendientes = {tuple(p) for p in d["pendientes"]}
    # vanesa: sugerencia visible O solicitud pendiente (según el estado del demo)
    vanesa = sugerencias.pop("vanesa")
    assert vanesa == ["inventario"] or ("vanesa", "inventario") in pendientes, \
        f"vanesa sin defensa: sugerencias={vanesa}, pendientes={pendientes}"
    assert sugerencias == {
        "aldo": [], "marta": [], "celeste": [], "ramon": [],
        # tomas ya NO recibe la sugerencia de inventario: la capa del empleado de
        # a pie se lo OTORGÓ como feature de lectura (responde stock/negativos a
        # Ángela desde el piso). Su descripción sigue justificándolo; ahora lo tiene.
        "brian": [], "nahuel": [], "tomas": [],
        # P·onboarding — el que recién entró tampoco necesita pedir nada: entra
        # con las mismas features que el resto del depósito de a pie.
        "kevin": [],
        "walter": ["cuentas", "cobranzas"], "osmar": [],
        "diego": ["logistica", "inventario"], "lucia": ["logistica"],
        "norma": [],
    }
