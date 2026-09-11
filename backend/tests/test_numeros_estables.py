"""
P11·B12 — Números estables en cámara: los agregados monetarios los calcula el
core UNA vez y viajan precomputados en el payload de las tools; el prompt
instruye usarlos textuales. Tres consultas seguidas → el mismo total exacto.
"""
from __future__ import annotations

import angela
from core import cuentas


def test_cuentas_corrientes_trae_totales_precomputados():
    angela._set_sesion(features=None)
    r, _ = angela._run_tool("cuentas_corrientes", {})
    angela._set_sesion()
    t = r["totales"]
    assert t["total_adeudado"] == sum(c["saldo"] for c in r["clientes"])
    assert t["total_morosos"] == sum(c["saldo"] for c in r["morosos"])
    assert t["cantidad_morosos"] == len(r["morosos"])
    # y coincide con la alerta del Inicio (una sola verdad)
    assert t["total_morosos"] == r["alertas"]["impacto_pesos"]


def test_totales_identicos_en_tres_llamadas():
    """La reproducción del bug: 'who owes me money?' 3 veces → 3 totales
    distintos porque el modelo sumaba. El core da SIEMPRE el mismo número."""
    tres = [cuentas.totales() for _ in range(3)]
    assert tres[0] == tres[1] == tres[2]


def test_fallback_morosos_usa_el_total_del_core():
    respuestas = set()
    for _ in range(3):
        angela._set_sesion(features=None)
        respuestas.add(angela._fallback("¿quién me debe plata?")["respuesta"])
    angela._set_sesion()
    assert len(respuestas) == 1   # byte-idéntico las tres veces


def test_top_inmovilizado_trae_total_del_listado():
    angela._set_sesion(features=None)
    r, _ = angela._run_tool("top_inmovilizado", {"n": 5})
    angela._set_sesion()
    assert r["total_inmovilizado_listado"] == round(
        sum(i.get("inmovilizado") or 0 for i in r["items"]), 2)
    assert len(r["items"]) <= 5


def test_listar_grupo_trae_total_del_listado():
    angela._set_sesion(features=None)
    r, _ = angela._run_tool("listar_grupo", {"grupo": "sin_pvp"})
    angela._set_sesion()
    assert "total_inmovilizado_listado" in r and "items" in r


def test_prompt_ordena_usar_totales_textuales():
    sp = angela.SYSTEM_PROMPT
    assert "NÚMEROS ESTABLES" in sp
    assert "Jamás sumes vos una lista" in sp
