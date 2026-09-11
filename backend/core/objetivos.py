"""
Objetivos del equipo — persistencia SERVER-SIDE (P9·C5, M9).

Antes, `crear_objetivo` de Ángela vivía solo en el localStorage de quien lo
pedía: el resto del equipo no lo veía y un navegador limpio lo borraba. Ahora
el objetivo se persiste acá (JSON por tenant, como recordatorios) y el tablero
de todos lo sincroniza. El id puede venir del cliente (uid del tablero) para
que la mezcla local↔server sea idempotente, sin duplicados.
"""
from __future__ import annotations

import datetime
import json
import os
import secrets

from . import paths

DATA_DIR = paths.DATA_DIR
OBJETIVOS_JSON = os.path.join(DATA_DIR, "objetivos.json")

ESTADOS = ("pendiente", "en_proceso", "listo")


def _ahora() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _load() -> list[dict]:
    try:
        return json.load(open(OBJETIVOS_JSON, encoding="utf-8"))
    except Exception:
        return []


def _save(items: list[dict]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(items, open(OBJETIVOS_JSON, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


def crear(nombre: str, responsable: str | None = None, fecha: str | None = None,
          creado_por: str | None = None, oid: str | None = None) -> dict:
    items = _load()
    if oid:
        ya = next((o for o in items if o["id"] == oid), None)
        if ya:
            return ya  # idempotente: el cliente reintenta sin duplicar
    o = {
        "id": oid or "ob" + secrets.token_hex(3),
        "nombre": (nombre or "").strip(),
        "responsable": responsable or "Sin asignar",
        "fecha": fecha or "sin fecha",
        "estado": "pendiente",
        "creado_por": creado_por or "dueño",
        "creado": _ahora(),
    }
    items.insert(0, o)
    _save(items)
    return o


def listar() -> list[dict]:
    return _load()


def cambiar_estado(oid: str, estado: str) -> dict:
    if estado not in ESTADOS:
        raise ValueError(f"estado inválido: {estado}")
    items = _load()
    o = next((x for x in items if x["id"] == oid), None)
    if not o:
        raise KeyError("objetivo inexistente")
    o["estado"] = estado
    _save(items)
    return o
