"""
Fechas — parsing tolerante para los exports de las PyMEs.

Los CSV llegan con fechas en cualquier formato (ISO, dd/mm/aaaa, dd-mm-aaaa).
Acá vive el parser único para que depósito, logística y recordatorios no
dupliquen la misma heurística.
"""
from __future__ import annotations

import datetime
import os

_FORMATOS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y")


def parse_fecha(s) -> datetime.date | None:
    """Devuelve la fecha o None si no se puede interpretar (nunca explota)."""
    if isinstance(s, datetime.datetime):
        return s.date()
    if isinstance(s, datetime.date):
        return s
    texto = str(s or "").strip()
    if not texto:
        return None
    for fmt in _FORMATOS:
        try:
            return datetime.datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


def hoy() -> datetime.date:
    """El "hoy" de referencia de TODOS los análisis (P9·B).

    Con POLPILOT_DEMO_TODAY (ISO, ej. 2026-07-07) la fecha queda CONGELADA:
    el tenant demo da siempre los mismos números — hoy, en el deploy y el día
    de la grabación del video. Sin la var (el piloto), fecha real de siempre.
    Se lee por llamada (barato) para que los tests puedan mockear el entorno.
    """
    congelada = os.environ.get("POLPILOT_DEMO_TODAY", "").strip()
    if congelada:
        try:
            return datetime.datetime.strptime(congelada, "%Y-%m-%d").date()
        except ValueError:
            pass  # var malformada: mejor la fecha real que explotar
    return datetime.date.today()
