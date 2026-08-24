"""
Plan 11 · Arquitectura de conectores.

PolPilot nunca habla directo con Faro/Tango: habla con un CONECTOR que abstrae
la comunicación. Una sola interfaz (IConector), un conector por sistema.

Hoy:
  - ConectorCSV: export/import manual (Fase 1, funciona).
  - ConectorBCRA: contexto macro (ya construido en core/macro.py).
  - ConectorMCP: el slot vacío para cuando Faro/Tango expongan MCP (Fase 3).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from . import macro, sync


class IConector(ABC):
    """Interfaz estándar. Todo sistema externo se conecta implementando esto."""
    nombre: str = "abstracto"

    @abstractmethod
    def pull_data(self, **kwargs) -> dict:
        """Trae datos del sistema externo hacia PolPilot."""

    @abstractmethod
    def push_action(self, accion: dict) -> dict:
        """Manda un cambio de PolPilot hacia el sistema externo."""

    @abstractmethod
    def get_schema(self) -> dict:
        """Describe qué datos expone el sistema."""


class ConectorCSV(IConector):
    """Fase 1: el usuario exporta/importa CSV. La Staging Area procesa la entrada;
    el delta export genera la salida."""
    nombre = "csv"

    def pull_data(self, csv_texto: str = "", **kwargs) -> dict:
        from . import staging
        return staging.crear_batch(kwargs.get("nombre", "import.csv"), csv_texto)

    def push_action(self, accion: dict) -> dict:
        return sync.generar_delta_export(accion.get("formato", "generico"))

    def get_schema(self) -> dict:
        return {"entrada": "CSV con encabezados", "salida": "delta CSV (solo cambios)"}


class ConectorBCRA(IConector):
    """Conector oficial al BCRA (cotizaciones). Ya implementado en core/macro.py."""
    nombre = "bcra"

    def pull_data(self, **kwargs) -> dict:
        return macro.consultar(kwargs.get("indicadores", ["dolar"]))

    def push_action(self, accion: dict) -> dict:
        return {"ok": False, "motivo": "el BCRA es solo lectura"}

    def get_schema(self) -> dict:
        return {"indicadores": ["dolar", "inflacion"]}


class ConectorMCP(IConector):
    """Fase 3: slot para Model Context Protocol. Cuando Faro/Tango expongan un MCP
    server, se enchufan acá los métodos reales (1-2 días de trabajo)."""
    nombre = "mcp"

    def __init__(self, servidor: str | None = None):
        self.servidor = servidor

    def pull_data(self, **kwargs) -> dict:
        raise NotImplementedError("Conector MCP: pendiente de que el sistema externo exponga MCP.")

    def push_action(self, accion: dict) -> dict:
        raise NotImplementedError("Conector MCP: pendiente de que el sistema externo exponga MCP.")

    def get_schema(self) -> dict:
        return {"estado": "slot vacío", "fase": 3}


# Registro de conectores disponibles.
CONECTORES = {"csv": ConectorCSV, "bcra": ConectorBCRA, "mcp": ConectorMCP}


def disponibles() -> list[dict]:
    out = []
    for nombre, cls in CONECTORES.items():
        try:
            inst = cls()
            estado = "activo" if nombre in ("csv", "bcra") else "pendiente"
            out.append({"nombre": nombre, "estado": estado, "schema": inst.get_schema()})
        except Exception:
            out.append({"nombre": nombre, "estado": "pendiente"})
    return out
