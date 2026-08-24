"""
Evolución: deflactación contra casos a mano, interanual, YTD, sin datos,
INDEC caído y que la demo no contamine. El motor es puro (recibe filas e
índices), así que nada acá toca la red.
"""
from __future__ import annotations

import os

import pytest

import angela
from core import evolucion, macro

# Índices inventados fáciles de verificar a mano (dic-2016=100 da igual acá:
# lo que importa es el cociente).
INDICES = {
    "2025-05": 100.0, "2025-06": 110.0, "2025-07": 120.0,
    "2026-04": 190.0, "2026-05": 200.0,  # mes base = 2026-05 (el último)
}


@pytest.fixture(autouse=True)
def sin_flag(monkeypatch):
    monkeypatch.delenv("POLPILOT_DEMO_EVOLUCION", raising=False)


# --- deflactación pura, a mano ---

def test_deflactar_casos_a_mano():
    # índice 100 → 200: la plata de 2025-05 vale el doble en pesos de 2026-05
    assert evolucion.deflactar(1000, "2025-05", INDICES, "2026-05") == 2000.0
    # 110 → 200
    assert evolucion.deflactar(1000, "2025-06", INDICES, "2026-05") == round(1000 * 200 / 110, 2)
    # sin índice → None, nunca inventa
    assert evolucion.deflactar(1000, "1999-01", INDICES, "2026-05") is None


def test_mes_sin_indice_usa_el_anterior():
    # 2026-06 no está publicado: se deflacta con 2026-05 (el último disponible)
    assert evolucion._mes_indice_para("2026-06", INDICES) == "2026-05"
    assert evolucion._mes_indice_para("2015-01", INDICES) is None


def test_agregados_y_monto_fila():
    filas = [
        {"fecha": "2026-05-10", "cantidad": 2, "precio": 100.0},   # 200
        {"fecha": "2026-05-20", "cantidad": 0, "precio": 50.0},    # 50 (total sin cantidad)
        {"fecha": "10/05/2026", "cantidad": 1, "precio": 30.0},    # 30, formato dd/mm
        {"fecha": "2026-06-01", "cantidad": 1, "precio": 500.0},
    ]
    agg = evolucion.agregados_mensuales(filas)
    assert agg == {"2026-05": 280.0, "2026-06": 500.0}


# --- interanual y YTD contra números elegidos a mano ---

def test_interanual_real():
    # jun-2025: $1.000 con índice 110 → $1.818,18 de hoy. jun-2026: $1.500
    # (índice de jun no está → usa may 200, factor 1). Real: 1500/1818.18 - 1 = -17.5%
    filas = [
        {"fecha": "2025-06-15", "cantidad": 1, "precio": 1000.0},
        {"fecha": "2026-06-15", "cantidad": 1, "precio": 1500.0},
    ]
    r = evolucion.comparar(filas, INDICES)
    inter = r["interanual"]
    assert inter["variacion_nominal_pct"] == 50.0
    assert inter["real_anterior"] == round(1000 * 200 / 110, 2)
    assert inter["variacion_real_pct"] == round((1500 / (1000 * 200 / 110) - 1) * 100, 1)


def test_ytd():
    filas = [
        {"fecha": "2025-05-01", "cantidad": 1, "precio": 1000.0},
        {"fecha": "2025-06-01", "cantidad": 1, "precio": 1000.0},
        {"fecha": "2026-05-01", "cantidad": 1, "precio": 2000.0},
        {"fecha": "2026-06-01", "cantidad": 1, "precio": 2000.0},
    ]
    r = evolucion.comparar(filas, INDICES)
    ytd = r["ytd"]
    assert ytd["meses"] == 2 and ytd["variacion_nominal_pct"] == 100.0
    # real anterior: 1000×200/100 + 1000×200/110 = 2000 + 1818.18 = 3818.18
    assert ytd["real_anterior"] == round(2000 + 1000 * 200 / 110, 2)


def test_alerta_descriptiva_solo_con_caida_fuerte():
    filas_caida = [
        {"fecha": "2025-06-15", "cantidad": 1, "precio": 1000.0},
        {"fecha": "2026-06-15", "cantidad": 1, "precio": 1500.0},  # -17.5% real
    ]
    r = evolucion.comparar(filas_caida, INDICES)
    alertas = evolucion.alertas_de(r)
    assert len(alertas) == 1 and alertas[0]["tipo"] == "caida_real_interanual"
    assert "menos en términos reales" in alertas[0]["detalle"]  # descriptivo, no consejo
    assert "conviene" not in alertas[0]["detalle"].lower()

    filas_ok = [
        {"fecha": "2025-06-15", "cantidad": 1, "precio": 1000.0},
        {"fecha": "2026-06-15", "cantidad": 1, "precio": 2000.0},  # +10% real
    ]
    assert evolucion.alertas_de(evolucion.comparar(filas_ok, INDICES)) == []


# --- estados: sin datos, demo, INDEC caído ---

def test_sin_datos_es_honesto():
    p = evolucion.panorama()
    assert p["hay_datos"] is False and p["demo"] is False
    assert "ventas históricas" in p["mensaje"]


def test_demo_con_flag_y_marcada(monkeypatch):
    monkeypatch.setenv("POLPILOT_DEMO_EVOLUCION", "1")
    monkeypatch.setattr(macro, "ipc_serie",
                        lambda: {"disponible": True, "indices": INDICES})
    p = evolucion.panorama()
    assert p["hay_datos"] is True and p["demo"] is True  # marcada, no se confunde
    assert len(p["serie"]) == 24
    # y NO persiste nada: el apartado real sigue vacío
    assert evolucion.hay_datos() is False


def test_indec_caido_no_inventa_deflactor(monkeypatch):
    monkeypatch.setenv("POLPILOT_DEMO_EVOLUCION", "1")
    monkeypatch.setattr(macro, "ipc_serie",
                        lambda: {"disponible": False, "motivo": "la fuente no respondió"})
    p = evolucion.panorama()
    assert p["hay_indice"] is False and "aviso_indice" in p
    assert all(x["real"] is None for x in p["serie"])  # nominal sí, real jamás inventado


# --- Ángela: paridad y honestidad ---

def test_angela_tool_existe_y_router_sin_datos():
    assert "consultar_evolucion" in {t["name"] for t in angela.TOOLS}
    r = angela._fallback("¿cómo vengo contra el año pasado?")
    assert "consultar_evolucion" in r["tools_usadas"]
    assert "ventas históricas" in r["respuesta"]  # sin datos: lo dice, no inventa


def test_angela_router_con_demo(monkeypatch):
    monkeypatch.setenv("POLPILOT_DEMO_EVOLUCION", "1")
    monkeypatch.setattr(macro, "ipc_serie",
                        lambda: {"disponible": True, "indices": INDICES})
    r = angela._fallback("¿cómo vengo contra el año pasado?")
    assert "real" in r["respuesta"] and "ajustado por inflación" in r["respuesta"]
    assert "demostración" in r["respuesta"]  # la demo nunca pasa por real
