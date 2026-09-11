"""
authz.py · Autorización por endpoint — LA capa de acceso, en un solo lugar.

Regla de oro (igual que /api/angela): la identidad SALE DEL TOKEN, NUNCA del
body. Un rol enviado en el request se ignora por completo. Sin token válido →
401; token de un rol sin permiso → 403.

El token viaja en el header `Authorization: Bearer <token>` (estándar). Se
acepta además `?token=` por compatibilidad con las llamadas viejas que ya lo
mandaban así (perfiles, notificaciones, admin). El frontend centraliza el
header en api.js, así que toda llamada autenticada lo lleva sin tocar cada
componente.

"Qué rol puede qué" se resuelve con el MODELO QUE YA EXISTE:
perfiles.features_efectivas(username) — las features del rol (base del seed +
aprobadas por el dueño − deshabilitadas). No se inventan reglas nuevas acá.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Query

import auth
import i18n
from core import paths, perfiles


def _extraer_token(authorization: str | None, token_q: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return token_q  # fallback: ?token= (compat)


def usuario_actual(
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
) -> dict:
    """El usuario logueado, o 401. Es la base de todas las reglas de acceso."""
    tok = _extraer_token(authorization, token)
    u = auth.usuario_por_token(tok) if tok else None
    if not u:
        # Sin usuario resuelto no hay preferencia: rige el default del tenant.
        raise HTTPException(status_code=401,
                            detail=i18n.t("authz.iniciar_sesion", paths.DEFAULT_LANG))
    return u


def require_admin(u: dict = Depends(usuario_actual)) -> dict:
    """Sólo el dueño (scope organización): audit, sync/export, gestión de equipo."""
    if not u.get("es_admin"):
        raise HTTPException(status_code=403,
                            detail=i18n.t("authz.solo_dueno",
                                          perfiles.idioma_de(u["username"])))
    return u


def require_feature(feature: str):
    """Exige que el rol del usuario tenga el módulo `feature`. Reusa el modelo
    de permisos existente (features_efectivas). Devuelve una dependency."""
    def _dep(u: dict = Depends(usuario_actual)) -> dict:
        if feature not in perfiles.features_efectivas(u["username"]):
            raise HTTPException(
                status_code=403,
                detail=i18n.t("authz.sin_feature",
                              perfiles.idioma_de(u["username"]), feature=feature))
        return u
    return _dep
