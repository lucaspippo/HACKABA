"""
transcripcion.py · EL ÚNICO PUNTO por donde una voz se convierte en texto.

Gemelo de core/extraccion.py, y por la misma razón: el momento en que un dato
entra al sistema desde una máquina tiene que ser un solo lugar, reemplazable.

TRES CAMINOS, en orden:

  1. El navegador ya transcribió. La Web Speech API corre EN EL BROWSER: el
     empleado habla, el navegador devuelve texto, y acá llega texto. Es
     transcripción real, gratis, sin dependencia nueva en el backend y sin una
     segunda API key. Es el camino normal en Chrome/Android.

  2. Es un audio de MUESTRA. Se reconoce por sha256 del contenido y se responde
     con su transcripción canónica: sin red, sin modelo, idéntica siempre. Para
     la demo grabada, donde Safari/iOS puede no tener Web Speech y la sala puede
     no tener internet.

  3. Audio crudo sin transcribir y sin ser muestra. HOY no hay a quién
     mandárselo y se dice con todas las letras — no se inventa una
     transcripción. Acá se enchufa el proveedor de STT el día que se decida
     cuál (ver `_stt_externo`).

POR QUÉ NO HAY UN CLAUDE-TRANSCRIBE: la API de Anthropic acepta imágenes y PDF,
no audio, y no tiene endpoint de transcripción. Cualquier STT real es un
proveedor aparte (Whisper, Deepgram, AssemblyAI) con su propia key. Esa decisión
todavía no se tomó, así que el hueco queda marcado en vez de tapado.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os

import i18n

from . import paths

MUESTRAS_JSON = os.path.join(paths.DATA_DIR, "audios", "transcripciones.json")

_cache: dict | None = None
_cache_mtime: float | None = None


def _muestras() -> dict:
    """{sha256: texto}. Se relee si el archivo cambia."""
    global _cache, _cache_mtime
    try:
        mtime = os.path.getmtime(MUESTRAS_JSON)
    except OSError:
        _cache, _cache_mtime = {}, None
        return {}
    if _cache is not None and _cache_mtime == mtime:
        return _cache
    try:
        with open(MUESTRAS_JSON, encoding="utf-8") as f:
            datos = json.load(f)
        _cache = {m["sha256"]: m["texto"]
                  for m in (datos.get("muestras") or {}).values()
                  if m.get("sha256") and m.get("texto")}
    except Exception:
        _cache = {}
    _cache_mtime = mtime
    return _cache


def muestras_crudas() -> dict:
    """El JSON entero (lo usa core/voz para la interpretación canónica y la UI
    para ofrecer las frases de muestra)."""
    try:
        with open(MUESTRAS_JSON, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _stt_externo(crudo: bytes, lang: str | None) -> dict | None:
    """El hueco declarado. Cuando se elija proveedor de STT, se implementa acá
    y NADA más del flujo cambia: ni el endpoint, ni core/voz, ni el frontend."""
    return None


def transcribir(*, texto: str | None = None, audio_b64: str | None = None,
                lang: str | None = None) -> dict:
    """Voz → texto. Devuelve {ok, texto, origen} u {ok: False, motivo}."""
    # 1 · el navegador ya hizo el trabajo
    if (texto or "").strip():
        return {"ok": True, "texto": texto.strip(), "origen": "navegador"}

    try:
        crudo = base64.b64decode(audio_b64 or "", validate=False)
    except Exception:
        crudo = b""
    if not crudo:
        return {"ok": False, "motivo": i18n.t("core.voz.sin_audio", lang)}

    # 2 · ¿es una muestra conocida?
    conocido = _muestras().get(hashlib.sha256(crudo).hexdigest())
    if conocido:
        return {"ok": True, "texto": conocido, "origen": "muestra"}

    # 3 · audio real sin transcriptor: se dice, no se inventa
    externo = _stt_externo(crudo, lang)
    if externo:
        return externo
    return {"ok": False, "motivo": i18n.t("core.voz.sin_transcriptor", lang)}
