"""
P25 — Oportunidades de verdad + el ciclo de corrección de cámara + composición.
"""
from __future__ import annotations

import hashlib
import json
import os
import time

import pytest

import angela
from core import memoria, oportunidades_neg, saneamiento, store
from core import evolucion


def _hash() -> str:
    return hashlib.sha256(json.dumps(store.raw_actual(), sort_keys=True).encode()).hexdigest()


@pytest.fixture(autouse=True)
def limpio():
    store.resetear_actual()
    if os.path.exists(memoria.MEMORIA_JSON):
        os.remove(memoria.MEMORIA_JSON)
    usuario, rol = angela._usuario_actual(), angela._rol_actual()
    yield
    angela._set_sesion(usuario=usuario, rol=rol)
    store.resetear_actual()
    if os.path.exists(memoria.MEMORIA_JSON):
        os.remove(memoria.MEMORIA_JSON)


# --- A · las tarjetas: cada una con plata + acción + drill honesto -------------

def test_cards_solo_plata_con_accion():
    """El criterio duro: toda card tiene $, tipo-acción, porqué y (si aplica)
    supuestos. En el piloto (sin ventas) caen las que dependen de ventas —
    honesto, no vacío fingido."""
    cards = oportunidades_neg.cards("es")
    for c in cards:
        assert c["monto"] and c["monto"] > 0, c["id"]
        assert c["tipo"] in oportunidades_neg.TIPOS_VALIDOS
        assert c["drill"]["porque"], c["id"]
        assert c["accion_chat"]
        assert c["fuentes"], c["id"]  # P27·C: toda card declara qué crucé
    ids = {c["id"] for c in cards}
    # el piloto tiene cuentas → cobrar_morosos vive; las de ventas caen
    assert "cobrar_morosos" in ids
    assert "ventana_compra" not in ids  # sin condiciones de proveedor en el piloto
    # P27·A10 — "cargar precios" es un ERROR DE DATOS, no una oportunidad:
    # vive en Datos a corregir, nunca más acá.
    assert "cargar_precios" not in ids


def test_cards_bilingues():
    es = {c["id"]: c["titulo"] for c in oportunidades_neg.cards("es")}
    en = {c["id"]: c["titulo"] for c in oportunidades_neg.cards("en")}
    assert set(es) == set(en)
    for k in es:
        assert es[k] != en[k]  # traducidas de verdad


# --- C · composición por categoría (el análisis vertical como serie) -----------

def test_composicion_categorias_suma_100():
    filas = [
        {"fecha": "2026-01-15", "categoria": "bebidas", "cantidad": 10, "precio": 100},
        {"fecha": "2026-01-20", "categoria": "lácteos", "cantidad": 5, "precio": 200},
        {"fecha": "2026-02-10", "categoria": "bebidas", "cantidad": 8, "precio": 100},
    ]
    comp = evolucion.composicion_categorias(filas)
    assert len(comp) == 2
    assert abs(sum(v for k, v in comp[0].items() if k != "mes") - 100) < 0.5
    assert comp[1]["bebidas"] == 100.0  # feb: solo bebidas


# --- F · el ciclo de cámara: abrir→confirmar→cascada→revertir→byte-igual -------

def test_ciclo_correccion_camara_cronometrado():
    hash_canonico = _hash()
    t0 = time.monotonic()
    # abrir: las propuestas están PRE-CALCULADAS (cero re-análisis) — rápido
    p = saneamiento.proponer("fantasma", "es")
    assert p["auto"] and p["cantidad"] > 0
    t_abrir = time.monotonic() - t0
    assert t_abrir < 5, f"proponer tardó {t_abrir:.1f}s — el momento de cámara no espera"
    # confirmar: aplica con backup y la CASCADA es real (los datos cambiaron)
    r = saneamiento.aplicar("fantasma", actor="marta")
    assert r["version_backup"] and _hash() != hash_canonico
    assert saneamiento.proponer("fantasma", "es")["cantidad"] == 0  # el contador bajó
    # revertir: byte-igual — la toma se repite infinitas veces
    saneamiento.revertir(r["version_backup"], actor="marta")
    assert _hash() == hash_canonico
    total = time.monotonic() - t0
    assert total < 30, f"el ciclo entero tardó {total:.1f}s"


def test_condiciones_proveedor_aditivas_no_rompen_sin_archivo(tmp_path, monkeypatch):
    monkeypatch.setattr(oportunidades_neg, "CONDICIONES_JSON",
                        str(tmp_path / "no_existe.json"))
    cards = oportunidades_neg.cards("es")  # sin condiciones → la ventana cae, sin crash
    assert all(c["id"] != "ventana_compra" for c in cards)
