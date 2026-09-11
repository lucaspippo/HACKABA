"""
P24·D6 — Alertas personales por umbral: la regla se persiste, se evalúa DE
VERDAD contra los datos, y al cumplirse la notificación llega por la campanita.
Condición no cumplida → silencio.
"""
from __future__ import annotations

import os

import pytest

from core import notificaciones, recordatorios


@pytest.fixture(autouse=True)
def limpio():
    files = [recordatorios.RECORDATORIOS_JSON if hasattr(recordatorios, "RECORDATORIOS_JSON")
             else os.path.join(recordatorios.DATA_DIR, "recordatorios.json"),
             notificaciones.NOTIFICACIONES_JSON]
    backup = {}
    for f in files:
        if os.path.exists(f):
            backup[f] = open(f, encoding="utf-8").read()
            os.remove(f)
    yield
    for f in files:
        if os.path.exists(f):
            os.remove(f)
        if f in backup:
            open(f, "w", encoding="utf-8").write(backup[f])


def _notifs(username: str) -> list[dict]:
    return notificaciones.listar(username)


def test_umbral_dormido_no_cumplido_silencio(monkeypatch):
    # umbral altísimo: la condición NO se cumple → ni disparo ni notificación
    from core import analisis
    monkeypatch.setattr(analisis, "kpis",
                        lambda lang=None: {"dormido": {"monto": 68_927_214, "pct": 15.5}})
    r = recordatorios.crear("Avisame si la dormida pasa los 900M", "emilio", "emilio",
                            {"tipo": "dormido_supera", "monto": 900_000_000})
    assert r["estado"] == "latente"
    disparados = recordatorios.evaluar()
    assert disparados == []
    assert _notifs("emilio") == []


def test_umbral_dormido_cumplido_notifica(monkeypatch):
    from core import analisis
    monkeypatch.setattr(analisis, "kpis",
                        lambda lang=None: {"dormido": {"monto": 75_000_000, "pct": 16.0}})
    recordatorios.crear("Avisame si la dormida pasa los 70M", "emilio", "emilio",
                        {"tipo": "dormido_supera", "monto": 70_000_000})
    disparados = recordatorios.evaluar()
    assert len(disparados) == 1
    ns = _notifs("emilio")
    assert len(ns) == 1 and ns[0]["tipo"] == "recordatorio_disparado"
    assert "70" in ns[0]["cuerpo"] or "75" in ns[0]["cuerpo"]
    # y NO se re-dispara en la próxima evaluación (quedó "disparado")
    assert recordatorios.evaluar() == []
    assert len(_notifs("emilio")) == 1


def test_umbral_cliente_atraso(monkeypatch):
    from core import cuentas
    monkeypatch.setattr(cuentas, "listar", lambda: [
        {"nombre": "Autoservicio 9 de Julio", "dias_sin_pagar": 58},
        {"nombre": "El Puente", "dias_sin_pagar": 17},
    ])
    recordatorios.crear("Avisame si un cliente pasa los 45 días", "emilio", "emilio",
                        {"tipo": "cliente_atraso_dias", "dias": 45})
    disparados = recordatorios.evaluar()
    assert len(disparados) == 1
    assert "9 de Julio" in disparados[0]["detalle_disparo"]
    assert len(_notifs("emilio")) == 1


def test_programado_dispara_el_dia(monkeypatch):
    from core import fechas
    dia_hoy = fechas.hoy().weekday()
    recordatorios.crear("Revisar los pedidos de la semana", "emilio", "emilio",
                        {"tipo": "programado", "dia_semana": dia_hoy})
    recordatorios.crear("Otro día", "emilio", "emilio",
                        {"tipo": "programado", "dia_semana": (dia_hoy + 3) % 7})
    disparados = recordatorios.evaluar()
    assert len(disparados) == 1  # solo el de HOY
    assert len(_notifs("emilio")) == 1
