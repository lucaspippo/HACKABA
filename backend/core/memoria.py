"""
Memoria del usuario — lo que hace que PolPilot "te conozca".

Guarda, por usuario: preferencias, objetivos declarados, qué datos ya cargó,
y las recomendaciones que Ángela hizo + su resultado. Es lo que personaliza la
experiencia sin que nadie configure nada: a medida que el usuario trabaja y
aprueba cosas, el sistema se afina solo.

Persiste en data/memoria.json. Compatible con `aprobar_categoria` del Plan 2.
"""
from __future__ import annotations

import json

_VACIO = {
    "preferencias": {},
    "vista": {},  # P19·A: preferencias de vista estructuradas (ver VISTA_CATALOGO)
    "categorias_auto": [],
    "objetivos": [],
    "datos_cargados": [],
    "recomendaciones": [],
}


def _load() -> dict:
    from core.db import blob_repo
    from core.db import tenant as _tenant
    return blob_repo.get_blob("user_memory", _tenant.current_tenant_id()) or {}


def _save(data: dict) -> None:
    from core.db import blob_repo
    from core.db import tenant as _tenant
    blob_repo.save_blob("user_memory", _tenant.current_tenant_id(), data)


def _usuario(data: dict, usuario: str) -> dict:
    u = data.setdefault(usuario, {})
    for k, v in _VACIO.items():
        u.setdefault(k, json.loads(json.dumps(v)))  # copia
    return u


def get(usuario: str) -> dict:
    """Toda la memoria de un usuario (secciones garantizadas)."""
    data = _load()
    return _usuario(data, usuario)


# Alias histórico (Plan 2 lo usa para leer categorias_auto).
def preferencias(usuario: str) -> dict:
    return get(usuario)


def set_pref(usuario: str, clave: str, valor) -> dict:
    data = _load()
    _usuario(data, usuario)["preferencias"][clave] = valor
    _save(data)
    return data[usuario]


# --- P19·A — preferencias de VISTA estructuradas ------------------------------
# Lo que Ángela recuerda de CÓMO le gusta ver el negocio a cada persona, con
# catálogo cerrado: cada clave la aplica una parte concreta de la interfaz.
# Nada de memoria oculta: /api/preferencias las lista y las borra una por una
# (Mi perfil las muestra). Todo pasa por acá — chat, endpoints y frontend leen
# EL MISMO archivo (memoria.json, por usuario, en el servidor: sobrevive
# recarga, logout y cambio de máquina).
#
# Catálogo: clave → (validador, descripción i18n-key para Mi perfil).
# - sin_torta: True — nunca más un gráfico de torta/donut para este usuario.
# - margen_pin_umbral: N — productos con margen teórico < N% fijados arriba
#   donde ya se listan márgenes (con datos ya calculados, nada nuevo).
# - orden_home: [bloques] — el orden de los bloques del Inicio (P19·B).
# - widgets: {seccion: [w]} — los bloques visuales pedidos por chat (P19·C).
# - nota:<texto libre> vive en "preferencias" (set_pref), no acá.

BLOQUES_HOME = ["cards", "decisiones", "oportunidades", "feed", "metricas", "plata"]


def _val_bool(v):
    return bool(v)


def _val_umbral(v):
    n = float(v)
    if not (0 < n < 100):
        raise ValueError("el umbral tiene que ser un porcentaje entre 0 y 100")
    return n


def _val_orden(v):
    if not isinstance(v, list) or sorted(v) != sorted(BLOQUES_HOME):
        raise ValueError(f"orden_home tiene que ser una permutación de {BLOQUES_HOME}")
    return list(v)


def _val_widgets(v):
    if not isinstance(v, dict):
        raise ValueError("widgets tiene que ser {seccion: [widgets]}")
    return v


VISTA_CATALOGO = {
    "sin_torta": _val_bool,
    "margen_pin_umbral": _val_umbral,
    "orden_home": _val_orden,
    "widgets": _val_widgets,
    # Both default True when absent: read them with .get(key, True).
    "knowledge_capture": _val_bool,
    "knowledge_in_context": _val_bool,
}


def vista(usuario: str) -> dict:
    """Las preferencias de vista efectivas del usuario (solo claves del catálogo)."""
    data = _load()
    u = _usuario(data, usuario)
    return dict(u.get("vista") or {})


def set_vista(usuario: str, clave: str, valor) -> dict:
    """Setea UNA preferencia de vista validada. Lanza ValueError si la clave no
    existe en el catálogo o el valor no valida — el que llama decide qué decir."""
    if clave not in VISTA_CATALOGO:
        raise ValueError(f"preferencia desconocida: {clave!r} "
                         f"(catálogo: {', '.join(sorted(VISTA_CATALOGO))})")
    valor = VISTA_CATALOGO[clave](valor)
    data = _load()
    u = _usuario(data, usuario)
    u.setdefault("vista", {})[clave] = valor
    _save(data)
    return dict(u["vista"])


def borrar_vista(usuario: str, clave: str) -> bool:
    """Borra una preferencia de vista (o una nota de 'preferencias'). True si existía."""
    data = _load()
    u = _usuario(data, usuario)
    if clave in (u.get("vista") or {}):
        del u["vista"][clave]
        _save(data)
        return True
    if clave in (u.get("preferencias") or {}):
        del u["preferencias"][clave]
        _save(data)
        return True
    return False


def aprobar_categoria(usuario: str, categoria: str) -> None:
    data = _load()
    u = _usuario(data, usuario)
    if categoria not in u["categorias_auto"]:
        u["categorias_auto"].append(categoria)
    _save(data)


def marcar_dato_cargado(usuario: str, dato: str) -> None:
    data = _load()
    u = _usuario(data, usuario)
    if dato not in u["datos_cargados"]:
        u["datos_cargados"].append(dato)
    _save(data)


def registrar_recomendacion(usuario: str, texto: str) -> dict:
    data = _load()
    u = _usuario(data, usuario)
    rec = {"id": len(u["recomendaciones"]) + 1, "texto": texto, "resultado": None}
    u["recomendaciones"].append(rec)
    _save(data)
    return rec


def registrar_resultado(usuario: str, rec_id: int, resultado: str) -> None:
    data = _load()
    u = _usuario(data, usuario)
    for r in u["recomendaciones"]:
        if r["id"] == rec_id:
            r["resultado"] = resultado
    _save(data)


def agregar_archivo_libre(usuario: str, nombre: str, descripcion: str) -> None:
    data = _load()
    u = _usuario(data, usuario)
    u.setdefault("archivos", []).append({"nombre": nombre, "descripcion": descripcion})
    _save(data)


def agregar_objetivo(usuario: str, objetivo: str) -> None:
    data = _load()
    u = _usuario(data, usuario)
    if objetivo not in u["objetivos"]:
        u["objetivos"].append(objetivo)
    _save(data)
