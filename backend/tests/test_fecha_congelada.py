"""
P9·B — La fecha de referencia del demo está CONGELADA (POLPILOT_DEMO_TODAY).

El dataset demo se genera contra una fecha fija (2026-07-07) y los análisis
(evolución, estacionalidad, inmovilizado, "días sin venta") leen el "hoy" de
core.fechas.hoy(): con la var seteada dan SIEMPRE los mismos números — hoy,
en el deploy y el día de la grabación del video para YC. Sin la var (el
piloto) todo sigue con la fecha real, exactamente como siempre.
"""
from __future__ import annotations

import datetime
import types

from core import fechas, evolucion


class _RelojFalso(datetime.date):
    """Un date.today() que miente, para simular 'otro día'."""
    _hoy = datetime.date(2030, 1, 1)

    @classmethod
    def today(cls):
        return cls._hoy


def _mockear_reloj(monkeypatch, fecha: datetime.date):
    _RelojFalso._hoy = fecha
    falso = types.SimpleNamespace(date=_RelojFalso, datetime=datetime.datetime)
    monkeypatch.setattr(fechas, "datetime", falso)


def test_congelada_devuelve_la_fecha_fija(monkeypatch):
    monkeypatch.setenv("POLPILOT_DEMO_TODAY", "2026-07-07")
    assert fechas.hoy() == datetime.date(2026, 7, 7)


def test_congelada_ignora_el_reloj_real(monkeypatch):
    """Mockear el reloj a DOS días distintos: con la var puesta, hoy() ni lo mira."""
    monkeypatch.setenv("POLPILOT_DEMO_TODAY", "2026-07-07")
    for dia in (datetime.date(2026, 7, 14), datetime.date(2026, 9, 1)):
        _mockear_reloj(monkeypatch, dia)
        assert fechas.hoy() == datetime.date(2026, 7, 7)


def test_sin_la_var_rige_la_fecha_real(monkeypatch):
    """El piloto (sin env) sigue con date.today() de siempre."""
    monkeypatch.delenv("POLPILOT_DEMO_TODAY", raising=False)
    _mockear_reloj(monkeypatch, datetime.date(2030, 1, 1))
    assert fechas.hoy() == datetime.date(2030, 1, 1)


def test_var_malformada_no_explota(monkeypatch):
    monkeypatch.setenv("POLPILOT_DEMO_TODAY", "esto-no-es-una-fecha")
    assert fechas.hoy() == datetime.date.today()


def test_analisis_identico_en_dias_distintos(monkeypatch):
    """El caso de negocio entero: el MISMO análisis corrido 'dos días distintos'
    (reloj mockeado) da números idénticos si la fecha está congelada."""
    monkeypatch.setenv("POLPILOT_DEMO_TODAY", "2026-07-07")
    filas = evolucion._ventas_demo(hoy=datetime.date(2026, 7, 7))
    indices = {m: 1.0 for m in evolucion.agregados_mensuales(filas)}

    _mockear_reloj(monkeypatch, datetime.date(2026, 7, 14))
    dia_uno = evolucion.comparar(filas, indices)
    _mockear_reloj(monkeypatch, datetime.date(2026, 8, 30))
    dia_dos = evolucion.comparar(filas, indices)

    assert dia_uno == dia_dos
    assert dia_uno.get("hay_datos")
