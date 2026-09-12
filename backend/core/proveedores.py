"""
proveedores.py — la ficha real de cada proveedor (contacto, teléfono, email),
en vez del texto libre que hoy vive suelto en cada producto/reposición. Vive
en el apartado "proveedores" (mismo mecanismo genérico que "deposito") — sin
tabla nueva. El nombre sigue siendo la clave de matching contra el resto del
sistema (reposicion.condiciones_de, ordenes.py) — no se toca esa integración,
sólo se le suma una ficha administrable.
"""
from __future__ import annotations

import uuid

from . import esquema
from .audit import AuditLog

_audit = AuditLog(esquema.DATA_DIR)
_TIPO = "proveedores"
_CAMPOS = ("nombre", "contacto", "telefono", "email", "notas")


def listar() -> list[dict]:
    return esquema.filas(_TIPO)


def crear(datos: dict, actor: str) -> dict:
    nombre = (datos.get("nombre") or "").strip()
    if not nombre:
        raise ValueError("nombre_requerido")
    filas = esquema.filas(_TIPO)
    if any(f["nombre"].strip().lower() == nombre.lower() for f in filas):
        raise ValueError("nombre_duplicado")
    fila = {"id": uuid.uuid4().hex[:10], **{c: datos.get(c, "") for c in _CAMPOS}}
    fila["nombre"] = nombre
    filas.append(fila)
    esquema.reemplazar_filas(_TIPO, filas)
    _audit.record(actor, "crear_proveedor", None, fila)
    return fila


def actualizar(id_: str, cambios: dict, actor: str) -> dict:
    filas = esquema.filas(_TIPO)
    for f in filas:
        if f["id"] == id_:
            antes = dict(f)
            f.update({k: v for k, v in cambios.items() if k in _CAMPOS})
            esquema.reemplazar_filas(_TIPO, filas)
            _audit.record(actor, "editar_proveedor", antes, f)
            return f
    raise KeyError(id_)


def eliminar(id_: str, actor: str) -> None:
    filas = esquema.filas(_TIPO)
    quedan = [f for f in filas if f["id"] != id_]
    if len(quedan) == len(filas):
        raise KeyError(id_)
    borrado = next(f for f in filas if f["id"] == id_)
    esquema.reemplazar_filas(_TIPO, quedan)
    _audit.record(actor, "eliminar_proveedor", borrado, None)
