"""
notas.py — LA CAPA NO ESTRUCTURADA: lo que el equipo le cuenta a Ángela.

Un ERP sabe que un cliente debe $42M. No sabe que el repartidor pasó dos veces
y estaba cerrado. Eso vive en la cabeza del que maneja el camión, y se pierde.

PolPilot ya captura ese material por sus propias superficies: la voz del piso
(`core/voz.py`), los reportes de faltante/conteo/entrega (`piso.reportar`) y el
chat con Ángela. Este módulo lo lee como lo que es —texto libre de personas—, le
resuelve las entidades que menciona (cliente, producto, proveedor, ubicación) y
lo deja disponible para cruzarlo contra lo estructurado (ver core/cruces.py).

HONESTIDAD, DOS VECES:
  · Es DATA SINTÉTICA del demo, igual que el resto del dataset (ver
    data-demo/seed_notas.py). No es un canal externo: NO hay WhatsApp conectado,
    y ninguna pantalla dice lo contrario.
  · Las entidades NO se adivinan con NLP: cada nota declara a qué se refiere
    (así lo haría el reporte del piso, que ya pide producto y motivo). Lo que
    Ángela hace con eso es redactar; el cruce lo hace el código.
"""
from __future__ import annotations

import json
import os
import unicodedata

from . import paths

NOTAS_JSON = os.path.join(paths.DATA_DIR, "notas_equipo.json")

# Qué clase de cosa cuenta la nota. Sirve para cruzar sin leer el texto.
TIPOS = ("observacion_campo", "incidencia_entrega", "queja_cliente",
         "pedido_cliente", "estado_deposito", "estado_local", "nota_proveedor")


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _load() -> dict:
    try:
        with open(NOTAS_JSON, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:  # noqa: BLE001 — sin archivo, el módulo se calla
        return {}


def hay_datos() -> bool:
    return bool(_load().get("notas"))


def listar(tipo: str | None = None, cliente: str | None = None,
           producto: str | None = None, proveedor: str | None = None,
           desde: str | None = None) -> list[dict]:
    """Las notas que matchean los filtros, de la más nueva a la más vieja.
    El match de entidad es por substring normalizado (el nombre que escribió la
    persona no siempre es idéntico al del maestro)."""
    out = []
    for n in _load().get("notas", []):
        if tipo and n.get("tipo") != tipo:
            continue
        if desde and (n.get("fecha") or "") < desde:
            continue
        for campo, valor in (("cliente", cliente), ("producto", producto),
                             ("proveedor", proveedor)):
            if valor:
                propio = _norm(n.get(campo))
                pedido = _norm(valor)
                if not propio or not (pedido in propio or propio in pedido):
                    break
        else:
            out.append(dict(n))
    return sorted(out, key=lambda x: x.get("fecha") or "", reverse=True)


def texto_en(n: dict, lang: str | None = None) -> str:
    """El texto en el idioma pedido (la nota nace bilingüe, como todo lo que un
    humano lee en este producto)."""
    if lang == "en" and n.get("texto_en"):
        return n["texto_en"]
    return n.get("texto", "")


def sobre_cliente(nombre: str, desde: str | None = None) -> list[dict]:
    return listar(cliente=nombre, desde=desde)


def sobre_producto(nombre: str, desde: str | None = None) -> list[dict]:
    return listar(producto=nombre, desde=desde)


def por_ubicacion(texto: str, desde: str | None = None) -> list[dict]:
    """Las notas que hablan de un lugar del depósito (la cámara, un pasillo)."""
    t = _norm(texto)
    return [n for n in listar(desde=desde) if t and t in _norm(n.get("ubicacion"))]


def autores() -> dict[str, int]:
    """Cuántas notas dejó cada persona — es la prueba de que la fuente es el
    equipo, no un scraper."""
    out: dict[str, int] = {}
    for n in _load().get("notas", []):
        out[n.get("autor") or "?"] = out.get(n.get("autor") or "?", 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def resumen() -> dict:
    notas = _load().get("notas", [])
    por_canal: dict[str, int] = {}
    por_tipo: dict[str, int] = {}
    for n in notas:
        por_canal[n.get("canal") or "?"] = por_canal.get(n.get("canal") or "?", 0) + 1
        por_tipo[n.get("tipo") or "?"] = por_tipo.get(n.get("tipo") or "?", 0) + 1
    return {
        "hay_datos": bool(notas),
        "notas": len(notas),
        "autores": len(autores()),
        "por_canal": por_canal,
        "por_tipo": por_tipo,
        "desde": min((n.get("fecha") or "" for n in notas), default=None),
        "hasta": max((n.get("fecha") or "" for n in notas), default=None),
    }
