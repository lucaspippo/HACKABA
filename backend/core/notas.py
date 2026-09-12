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


def _seed_inicial() -> dict:
    """The tenant's REAL notes if they exist on disk (e.g. data-demo/
    notas_equipo.json), used ONLY to seed Postgres the first time (once per
    tenant). This module has no write API — {} is the fallback for a tenant
    with no file at all, same as the old missing-file behavior."""
    try:
        with open(NOTAS_JSON, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:  # noqa: BLE001 — sin archivo, el módulo se calla
        return {}


def _load() -> dict:
    from core.db import team_notes_repo, tenant as _tenant
    tid = _tenant.current_tenant_id()
    data = team_notes_repo.get_data(tid)
    if data is None:
        data = _seed_inicial()
        team_notes_repo.save_data(tid, data)
    return data


def hay_datos() -> bool:
    return bool(_load().get("notas"))


def listar(tipo: str | None = None, cliente: str | None = None,
           producto: str | None = None, proveedor: str | None = None,
           desde: str | None = None, excluir: set | frozenset | None = None) -> list[dict]:
    """Las notas que matchean los filtros, de la más nueva a la más vieja.
    El match de entidad es por substring normalizado (el nombre que escribió la
    persona no siempre es idéntico al del maestro).

    `excluir` es el CONTRAFÁCTICO: los ids que hay que leer como si no
    existieran, para poder preguntar «¿y si este dato no estuviera?». No borra
    nada —la nota sigue en la base, con su autor y su fecha— y por eso se puede
    hacer delante de alguien y devolverla un segundo después. Es un parámetro y
    no un estado global a propósito: quién excluye qué tiene que verse en la
    llamada, no adivinarse.
    """
    excluir = excluir or frozenset()
    out = []
    for n in _load().get("notas", []):
        if n.get("id") in excluir:
            continue
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


def por_ubicacion(texto: str, desde: str | None = None,
                  excluir: set | frozenset | None = None) -> list[dict]:
    """Las notas que hablan de un lugar del depósito (la cámara, un pasillo)."""
    t = _norm(texto)
    return [n for n in listar(desde=desde, excluir=excluir)
            if t and t in _norm(n.get("ubicacion"))]


def autores() -> dict[str, int]:
    """Cuántas notas dejó cada persona — es la prueba de que la fuente es el
    equipo, no un scraper."""
    out: dict[str, int] = {}
    for n in _load().get("notas", []):
        out[n.get("autor") or "?"] = out.get(n.get("autor") or "?", 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


# --- QUIÉN ES LA ÚNICA FUENTE DE QUÉ ------------------------------------------
#
# EL PUNTO CIEGO. Un ERP sabe cuánto te debe un cliente; no sabe que la única
# persona que pisa ese local es Walter. Si Walter se toma vacaciones, la
# empresa no pierde los datos —siguen ahí— pierde lo que NO está en ningún
# dato: que está cerrado salteado, que el dueño pidió hablar con Aldo.
#
# Esto NO se calcula sobre `conocimiento` (las reglas de la casa), y conviene
# decir por qué: en el dataset del demo las 22 piezas las enseñó el dueño, así
# que un mapa de riesgo sobre eso diría «si se va Aldo se pierde todo», que es
# cierto y no sirve. Sobre las notas del equipo hay 13 autores reales, y ahí el
# mapa dice algo que se puede accionar.
#
# La unidad es la ENTIDAD, no la nota (PRODUCT.md, The Counting Rule): dos
# notas de Walter sobre el mismo cliente son UNA fuente humana, no dos.

CAMPOS_ENTIDAD = ("cliente", "producto", "proveedor", "ubicacion")


def cobertura_humana(excluir: set | frozenset | None = None) -> dict:
    """Por cada entidad que el equipo nombró: quiénes son sus fuentes humanas.

    Devuelve `{campo: {entidad: [autores...]}}` más el resumen. `excluir` acepta
    NOMBRES DE PERSONA (no ids de nota): es el "apagá a Walter" de la demo, y
    devuelve el mapa como quedaría sin esa persona.
    """
    excluir = {str(x).lower() for x in (excluir or ())}
    por_campo: dict[str, dict[str, set]] = {c: {} for c in CAMPOS_ENTIDAD}
    for n in _load().get("notas", []):
        autor = (n.get("autor") or "").strip()
        if not autor or autor.lower() in excluir:
            continue
        for campo in CAMPOS_ENTIDAD:
            valor = (n.get(campo) or "").strip()
            if valor:
                por_campo[campo].setdefault(valor, set()).add(autor)
    salida = {campo: {ent: sorted(aut) for ent, aut in sorted(d.items())}
              for campo, d in por_campo.items()}
    unicas = [{"campo": campo, "entidad": ent, "autor": aut[0]}
              for campo, d in salida.items() for ent, aut in d.items()
              if len(aut) == 1]
    return {
        "por_campo": salida,
        "una_sola_fuente": sorted(unicas, key=lambda x: (x["autor"], x["entidad"])),
        "entidades": sum(len(d) for d in salida.values()),
        "autores": len({a for d in salida.values() for aut in d.values() for a in aut}),
        "excluidos": sorted(excluir),
    }


def riesgo_por_persona() -> list[dict]:
    """Qué se apaga si cada persona no está. Ordenado por cuánto duele.

    `solo_suyas` son las entidades de las que esa persona es la ÚNICA fuente:
    lo que la empresa deja de saber si falta. `compartidas` son aquellas donde
    alguien más también aporta — se degrada, no se apaga.
    """
    base = cobertura_humana()
    por_persona: dict[str, dict] = {}
    for campo, d in base["por_campo"].items():
        for ent, autores_ent in d.items():
            for a in autores_ent:
                reg = por_persona.setdefault(a, {"autor": a, "solo_suyas": [],
                                                 "compartidas": []})
                destino = "solo_suyas" if len(autores_ent) == 1 else "compartidas"
                reg[destino].append({"campo": campo, "entidad": ent})
    out = list(por_persona.values())
    for r in out:
        r["n_solo_suyas"] = len(r["solo_suyas"])
        r["n_compartidas"] = len(r["compartidas"])
    out.sort(key=lambda r: (-r["n_solo_suyas"], -r["n_compartidas"], r["autor"]))
    return out


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
