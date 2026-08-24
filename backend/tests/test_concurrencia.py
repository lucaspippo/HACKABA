"""
P9·A — La sesión de Ángela es REQUEST-SCOPED (contextvars): dos sesiones
simultáneas con usuarios/roles/features/idiomas distintos JAMÁS se cruzan.

Contexto: el demo público de YC va sin login por rol elegido y varios partners
pueden chatear A LA VEZ. Con los globals viejos, la identidad de un request
podía pisar la de otro en vuelo — delante de la gente que decide si nos financia.
"""
from __future__ import annotations

import contextvars
import threading

import angela


FEATURES_DEPOSITO = ["deposito", "logistica", "perfil", "angela"]
FEATURES_DUENO = ["panel", "inventario", "saneamiento", "cuentas", "caja",
                  "oportunidades", "perfil", "angela"]


def _en_contexto(fn):
    """Corre fn en un contexto NUEVO (como hace cada request real)."""
    resultado = {}

    def wrapper():
        try:
            resultado["valor"] = fn()
        except Exception as e:  # noqa: BLE001 — el test decide
            resultado["error"] = e

    ctx = contextvars.copy_context()
    hilo = threading.Thread(target=lambda: ctx.run(wrapper))
    hilo.start()
    hilo.join(timeout=30)
    if "error" in resultado:
        raise resultado["error"]
    return resultado.get("valor")


def test_dos_sesiones_simultaneas_no_se_cruzan():
    """El corazón del fix: A (depósito) y B (dueño) entrelazados con barreras
    para forzar el solapamiento real — cada uno ejecuta con SU identidad."""
    barrera = threading.Barrier(2, timeout=30)
    resultados = {}

    def sesion_a():
        angela._set_sesion(usuario="ramon", rol="Depósito",
                           features=FEATURES_DEPOSITO, idioma="es")
        barrera.wait()   # los dos setearon su sesión: máximo peligro de pisada
        # tras el set del otro thread, MI identidad tiene que seguir intacta
        resultados["a_usuario"] = angela._usuario_actual()
        resultados["a_features"] = angela._features_actuales()
        # capa 2: depósito NO accede a cuentas aunque el otro thread sí pueda
        res, _ = angela._run_tool("cuentas_corrientes", {})
        resultados["a_cuentas"] = res
        barrera.wait()

    def sesion_b():
        angela._set_sesion(usuario="emilio", rol="Dueño",
                           features=FEATURES_DUENO, idioma="en")
        barrera.wait()
        resultados["b_usuario"] = angela._usuario_actual()
        resultados["b_idioma"] = angela._idioma_actual()
        res, _ = angela._run_tool("cuentas_corrientes", {})
        resultados["b_cuentas"] = res
        barrera.wait()

    ca, cb = contextvars.copy_context(), contextvars.copy_context()
    ta = threading.Thread(target=lambda: ca.run(sesion_a))
    tb = threading.Thread(target=lambda: cb.run(sesion_b))
    ta.start(); tb.start()
    ta.join(timeout=30); tb.join(timeout=30)

    # Identidades intactas en cada lado, en paralelo:
    assert resultados["a_usuario"] == "ramon"
    assert resultados["b_usuario"] == "emilio"
    assert resultados["a_features"] == set(FEATURES_DEPOSITO)
    assert resultados["b_idioma"] == "en"
    # Anti-fuga bajo concurrencia: depósito bloqueado, dueño con datos.
    assert resultados["a_cuentas"].get("error") == "sin_acceso"
    assert "error" not in resultados["b_cuentas"]


def test_el_contexto_de_un_request_no_contamina_al_siguiente():
    """Un request nuevo (contexto nuevo) arranca con los defaults, aunque otro
    haya seteado una sesión en SU contexto."""
    def primero():
        angela._set_sesion(usuario="celeste", rol="Compras",
                           features=["inventario"], idioma="en")
        return angela._usuario_actual()

    def segundo():
        # contexto virgen: nada del primero debe verse acá
        return (angela._usuario_actual(), angela._features_actuales(),
                angela._idioma_actual())

    assert _en_contexto(primero) == "celeste"
    usuario, features, idioma = _en_contexto(segundo)
    assert usuario == "dueño"        # default, no "celeste"
    assert features is None          # default, no ["inventario"]
    from core import paths
    assert idioma == paths.DEFAULT_LANG


def test_muchas_sesiones_en_paralelo_sin_pisadas():
    """Estrés liviano: 8 sesiones concurrentes, cada una lee SU usuario."""
    errores = []

    def sesion(n):
        def cuerpo():
            angela._set_sesion(usuario=f"user{n}", rol="Rol",
                               features=["perfil"], idioma="es")
            for _ in range(50):
                if angela._usuario_actual() != f"user{n}":
                    errores.append(n)
                    return
        ctx = contextvars.copy_context()
        ctx.run(cuerpo)

    hilos = [threading.Thread(target=sesion, args=(i,)) for i in range(8)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=30)
    assert not errores, f"sesiones pisadas: {errores}"
