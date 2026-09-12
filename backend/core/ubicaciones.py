"""
ubicaciones.py — las ubicaciones físicas del depósito (pasillo, rack, cámara,
sucursal...), como entidad real en vez de un texto libre repetido en cada
lote. Vive en el apartado "ubicaciones" (mismo mecanismo genérico que ya usa
"deposito" para los lotes) — sin tabla nueva.
"""
from __future__ import annotations

import uuid

from . import esquema
from .audit import AuditLog

_audit = AuditLog(esquema.DATA_DIR)
_TIPO = "ubicaciones"


def listar() -> list[dict]:
    return esquema.filas(_TIPO)


def crear(nombre: str, actor: str, *, nota: str = "") -> dict:
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("nombre_requerido")
    filas = esquema.filas(_TIPO)
    if any(f["nombre"].strip().lower() == nombre.lower() for f in filas):
        raise ValueError("nombre_duplicado")
    fila = {"id": uuid.uuid4().hex[:10], "nombre": nombre, "nota": nota}
    filas.append(fila)
    esquema.reemplazar_filas(_TIPO, filas)
    _audit.record(actor, "crear_ubicacion", None, fila)
    return fila


def actualizar(id_: str, cambios: dict, actor: str) -> dict:
    filas = esquema.filas(_TIPO)
    for f in filas:
        if f["id"] == id_:
            antes = dict(f)
            f.update({k: v for k, v in cambios.items() if k in ("nombre", "nota")})
            esquema.reemplazar_filas(_TIPO, filas)
            _audit.record(actor, "editar_ubicacion", antes, f)
            return f
    raise KeyError(id_)


def eliminar(id_: str, actor: str) -> None:
    filas = esquema.filas(_TIPO)
    quedan = [f for f in filas if f["id"] != id_]
    if len(quedan) == len(filas):
        raise KeyError(id_)
    borrada = next(f for f in filas if f["id"] == id_)
    esquema.reemplazar_filas(_TIPO, quedan)
    _audit.record(actor, "eliminar_ubicacion", borrada, None)
