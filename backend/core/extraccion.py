"""
extraccion.py · EL ÚNICO PUNTO por donde una foto se convierte en datos.

Antes de este módulo, `/api/factura/leer` llamaba derecho a la visión. Funciona
—y muy bien— pero tiene una dependencia que en una demo grabada es letal: sin
proveedor de LLM configurado (ver config.py) o sin red, `leer_comprobante`
devuelve `sin_vision` y el
momento más impactante del producto ("foto → datos cargados en segundos") se
cae en vivo.

Así que la entrada queda partida en dos caminos, y el orden importa:

  1. ¿La imagen ES uno de los comprobantes de muestra? Se responde con la
     extracción CANÓNICA, sin red, sin LLM, sin variación. Determinista: la
     misma foto da el mismo resultado hoy, en el deploy y el día de la
     grabación. Se reconoce por sha256 de los bytes — no por nombre de archivo
     ni por un flag del cliente, que se pueden falsificar desde el navegador.

  2. Cualquier OTRA imagen va a la visión real, que es la que le importa al
     producto. Ese camino no cambió en nada.

La extracción canónica NO se escribe a mano acá: la emite
`data-demo/comprobantes/generar_comprobantes.py`, el mismo script que dibuja
los PNG. Imagen y extracción no pueden divergir porque salen de la misma
corrida. Si alguien cambia una cantidad del remito, cambian los dos.

Por qué esto no es "hacer trampa": el pipeline de abajo (chequeos, cruce contra
la orden de compra, confirmación, stock, audit) es EXACTAMENTE el mismo por los
dos caminos. Lo único que se saltea es el OCR de una imagen cuyo contenido ya
conocemos. Y `origen` viaja en la respuesta, así que la UI puede decirlo en vez
de esconderlo.

El día que la visión real sea la única fuente, se borra `_muestra_por_hash` y
nada más se toca.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import os

from . import paths

EXTRACCIONES_JSON = os.path.join(paths.DATA_DIR, "comprobantes", "extracciones.json")


def _seed_inicial() -> dict:
    """{sha256: extraccion}, leído una vez de disco."""
    if not os.path.exists(EXTRACCIONES_JSON):
        return {}
    try:
        with open(EXTRACCIONES_JSON, encoding="utf-8") as f:
            datos = json.load(f)
        return {m["sha256"]: m["extraccion"]
                for m in (datos.get("muestras") or {}).values()
                if m.get("sha256") and m.get("extraccion")}
    except Exception:
        return {}


def _muestras() -> dict:
    from core.db import blob_repo
    from core.db import tenant as _tenant
    tid = _tenant.current_tenant_id()
    data = blob_repo.get_blob("sample_extractions", tid)
    if data is None:
        data = _seed_inicial()
        blob_repo.save_blob("sample_extractions", tid, data)
    return data


def _muestra_por_hash(crudo: bytes) -> dict | None:
    ext = _muestras().get(hashlib.sha256(crudo).hexdigest())
    # copia profunda: el que llama EDITA la extracción (la card es editable) y
    # no puede ensuciar el canónico en memoria para la próxima lectura
    return copy.deepcopy(ext) if ext else None


def es_muestra(imagen_b64: str) -> bool:
    """¿Esta imagen se resuelve sin llamar al LLM? Lo usa el freno de gasto por
    IP: una muestra no cuesta un centavo, así que no tiene por qué contra el cap
    (si no, el cap del chat podía dejar la demo sin poder leer un remito)."""
    try:
        crudo = base64.b64decode(imagen_b64 or "", validate=False)
    except Exception:
        return False
    return bool(crudo) and _muestra_por_hash(crudo) is not None


def extraer(imagen_b64: str, media_type: str = "image/jpeg",
            lang: str | None = None) -> dict:
    """Foto → extracción estructurada.

    Devuelve el mismo shape que `vision_facturas.leer_comprobante` más
    `origen`: "muestra" (canónica, determinista) o "vision" (LLM real).
    """
    try:
        crudo = base64.b64decode(imagen_b64 or "", validate=False)
    except Exception:
        crudo = b""

    if crudo:
        ext = _muestra_por_hash(crudo)
        if ext is not None:
            return {"ok": True, "extraccion": ext, "origen": "muestra"}

    from . import vision_facturas
    r = vision_facturas.leer_comprobante(imagen_b64, media_type, lang)
    r["origen"] = "vision"
    return r
