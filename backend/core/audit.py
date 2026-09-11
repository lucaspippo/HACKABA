from __future__ import annotations

import datetime
import json
import os


class AuditLog:
    """Registro append-only de toda acción sobre los datos: quién, qué,
    antes y después. Es la trazabilidad que sostiene la confianza."""

    def __init__(self, base_dir: str):
        os.makedirs(base_dir, exist_ok=True)
        self.path = os.path.join(base_dir, "audit.json")

    def _load(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def record(self, actor: str, accion: str, antes=None, despues=None) -> dict:
        eventos = self._load()
        evento = {
            "id": len(eventos) + 1,
            "actor": actor,
            "accion": accion,
            "antes": antes,
            "despues": despues,
            "cuando": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        eventos.append(evento)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(eventos, f, ensure_ascii=False, indent=2)
        return evento

    def list(self) -> list[dict]:
        return self._load()
