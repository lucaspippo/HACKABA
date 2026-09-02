"""
Conocimiento del negocio — "lo que Aldo le enseñó a Ángela".

La capa NO estructurada que ningún ERP tiene: reglas de operación, criterios de
excepción, protocolos ante eventos y contexto que explica los datos. Vive hoy en
la cabeza del dueño; acá se vuelve un registro real, consultable y con efecto
verificable en lo que el usuario ve (ver core/*.py que llaman a `aplicables`).

Persists in Postgres, one row per piece (table `business_knowledge_pieces`,
migration 0039 — see `core/db/business_knowledge_repo.py`). The only tenant
seeded from a file is demo (<DATA_DIR>/conocimiento_negocio.json — the
piloto tenant has no file, so git diff of data-demo/ stays at zero); that
seed runs once, the first time the tenant reads with no rows of its own yet.
This is SHARED business knowledge (not per-user memory): the owner sees and
writes everything; each employee sees only their scope (see `visibles_para`).

Besides the owner writing one by hand, a piece can also be born from a
finding Ángela detected and the owner confirmed — see `pattern_feedback.learn()`,
the generic "Teach Ángela" mechanism any detection engine (core/patrones.py,
core/oportunidades_neg.py, and whatever gets added later) can use with no
new code here. A piece can also start as a chat-proposed "pendiente" state —
see `crear()`/`aprobar()`/`rechazar()` below and angela.py's
proponer_conocimiento tool — never active until someone with that node
reviews it.

Diseño del contador `veces_aplicada`: es acumulado y PERSISTIDO, se siembra con
la historia real de la pieza y solo lo mueve un evento discreto (re-enseñar /
aplicar explícito) — NUNCA el recálculo del análisis, que corre en cada request
y haría churn del snapshot sembrado (start_demo.py lo vigila). "Aplicadas hoy" es
un derivado que se calcula en vivo sobre los hallazgos del día (no se persiste).
"""
from __future__ import annotations

import json
import os
import secrets

from . import paths

DATA_DIR = paths.DATA_DIR  # por-tenant: env POLPILOT_DATA_DIR o data/ (core/paths.py)
CONOCIMIENTO_JSON = os.path.join(DATA_DIR, "conocimiento_negocio.json")

# Las cuatro clases de conocimiento no estructurado (las que pide YC).
TIPOS = {"regla", "excepcion", "protocolo", "contexto"}
# A qué se refiere la pieza.
AMBITOS = {"cliente", "proveedor", "categoria", "empleado", "global"}
# Qué hace la pieza en el producto (el efecto verificable).
EFECTOS = {"ajusta_umbral", "suprime_alerta", "genera_alerta",
           "contexto_para_angela", "requiere_aprobacion"}
# Dominio del mapa donde nace la pieza (los 8 nodos del Business Map).
NODOS = {"ventas", "inventario", "deposito", "proveedores",
         "clientes", "caja", "equipo", "contexto"}
ESTADOS = {"activo", "pausado", "pendiente"}

# Scope por rol: qué feature (módulo del perfil) habilita ver las piezas de cada
# nodo. El dueño (es_admin) ve todo; un empleado ve un nodo si tiene su módulo,
# más lo global y lo que sea sobre su propia persona. Server-side, sin bypass.
NODO_FEATURE = {
    "inventario": "inventario",
    "proveedores": "inventario",
    "deposito": "deposito",
    "clientes": "cuentas",
    "caja": "caja",
    "equipo": "equipo",
    "ventas": "oportunidades",
    "contexto": "panel",
}


def _seed_inicial() -> dict:
    if not os.path.exists(CONOCIMIENTO_JSON):
        return {"piezas": []}
    try:
        with open(CONOCIMIENTO_JSON, encoding="utf-8") as f:
            d = json.load(f)
            if isinstance(d, list):  # tolerar un formato viejo de lista pura
                return {"piezas": d}
            d.setdefault("piezas", [])
            return d
    except Exception:
        return {"piezas": []}


def _todas() -> list[dict]:
    """Every piece for the current tenant, one row per piece (see migration
    0039 — this used to be a single JSONB blob, see business_knowledge_repo.py's
    module docstring)."""
    from core.db import business_knowledge_repo
    from core.db import tenant as _tenant
    tid = _tenant.current_tenant_id()
    business_knowledge_repo.seed_if_empty(tid, _seed_inicial())
    return business_knowledge_repo.list_pieces(tid)


def _norm(s) -> str:
    return (s or "").strip().lower()


# --- lectura ------------------------------------------------------------------

def listar(nodo: str | None = None, tipo: str | None = None,
           entidad: str | None = None, ambito: str | None = None,
           incluir_pausadas: bool = True, estado: str | None = None) -> list[dict]:
    """Pieces matching the filters. Includes paused ones by default (Mi perfil
    lists them so they can be reactivated) but NEVER pending ones — an
    unreviewed proposal isn't the same as a paused piece, and mixing it into
    the general listing would show it as if it were already confirmed
    knowledge. Engines ask for incluir_pausadas=False via `aplicables`
    (which also never sees pending ones: it still requires estado=="activo").
    To see pending pieces, ask explicitly with estado="pendiente" (see
    `pendientes`), which also ignores incluir_pausadas."""
    piezas = _todas()
    out = []
    for p in piezas:
        if nodo and p.get("nodo") != nodo:
            continue
        if tipo and p.get("tipo") != tipo:
            continue
        if ambito and p.get("ambito") != ambito:
            continue
        if entidad and _norm(p.get("entidad")) != _norm(entidad):
            continue
        if estado:
            if p.get("estado") != estado:
                continue
        elif not incluir_pausadas:
            if p.get("estado") != "activo":
                continue
        elif p.get("estado") == "pendiente":
            continue
        out.append(p)
    return out


def pendientes(nodo: str | None = None) -> list[dict]:
    """Unreviewed proposals — what a user left via `proponer_conocimiento`
    (angela.py) and nobody has activated or rejected yet. Role scope is
    applied by the caller via `visibles_para(usuario, conocimiento.pendientes())`:
    the same node/feature criterion that already governs which ACTIVE
    knowledge each user sees also governs what's theirs to review — no
    separate permission catalog."""
    return listar(nodo=nodo, estado="pendiente")


def detalle(pid: str) -> dict | None:
    for p in _todas():
        if p.get("id") == pid:
            return p
    return None


def aplicables(nodo: str | None = None, entidad: str | None = None,
               efecto: str | None = None, ambito: str | None = None,
               tipo: str | None = None) -> list[dict]:
    """Las piezas ACTIVAS que un motor de análisis debe tener en cuenta para un
    hallazgo. Es el punto de enganche del efecto: los core/*.py la llaman al
    redactar/calcular. Solo lectura — NO toca `veces_aplicada` (correría en cada
    request y haría churn del snapshot)."""
    out = listar(nodo=nodo, entidad=entidad, ambito=ambito, tipo=tipo,
                 incluir_pausadas=False)
    if efecto:
        out = [p for p in out if p.get("efecto") == efecto]
    return out


def _match_entidad(entidad: str | None, nombre: str | None) -> bool:
    """La `entidad` de la pieza es un nombre de display ('Despensa Doña Elsa',
    'GASEOSA COLA LA RIBERA'); el motor tiene el nombre real del cliente/producto.
    Match por substring en cualquier dirección, normalizado."""
    if not entidad or not nombre:
        return False
    a, b = _norm(entidad), _norm(nombre)
    return a in b or b in a


def para(nombre: str | None = None, *, nodo: str | None = None,
         efecto: str | None = None, tipo: str | None = None,
         incluir_global: bool = False) -> list[dict]:
    """Piezas ACTIVAS que aplican a un hallazgo concreto. Si se da `nombre`,
    matchea por entidad (fuzzy); con incluir_global suma además las globales del
    mismo filtro. El helper que llaman los motores para enganchar el efecto."""
    out = []
    for p in aplicables(nodo=nodo, efecto=efecto, tipo=tipo):
        if nombre is None:
            out.append(p)
        elif _match_entidad(p.get("entidad"), nombre):
            out.append(p)
        elif incluir_global and p.get("ambito") == "global":
            out.append(p)
    return out


def texto_en(p: dict, lang: str | None = None) -> str:
    """El texto de la pieza en el idioma pedido (el frontend igual recibe ambos)."""
    if lang == "en" and p.get("texto_en"):
        return p["texto_en"]
    return p.get("texto", "")


def resumen_pieza(p: dict) -> dict:
    """La forma compacta que viaja al frontend en `conocimiento_aplicado`: lo que
    el mapa necesita para el chip, el panel 'Lo que Aldo me enseñó' y el nodo del
    camino de conocimiento. Lleva ambos idiomas — el frontend elige por idioma."""
    return {"id": p["id"], "tipo": p["tipo"], "texto": p["texto"],
            "texto_en": p.get("texto_en"), "nodo": p["nodo"], "efecto": p["efecto"],
            "efecto_profundo": p.get("efecto_profundo", False),
            "veces_aplicada": p.get("veces_aplicada", 0),
            "cuando": (p.get("origen") or {}).get("cuando")}


# --- scope por rol ------------------------------------------------------------

def visibles_para(usuario: dict, piezas: list[dict] | None = None) -> list[dict]:
    """Filtra las piezas a lo que ESTE usuario puede ver. El dueño (es_admin) ve
    todo. Un empleado ve: lo global, lo que es sobre su propia persona, y los
    nodos cuyos módulos tiene habilitados. Server-side, sin escalada por body."""
    piezas = _todas() if piezas is None else piezas
    if usuario.get("es_admin"):
        return list(piezas)
    from . import perfiles
    username = usuario.get("username")
    feats = set(perfiles.features_efectivas(username))
    out = []
    for p in piezas:
        if p.get("ambito") == "global":
            out.append(p)
        elif p.get("ambito") == "empleado" and _norm(p.get("entidad")) == _norm(username):
            out.append(p)
        elif NODO_FEATURE.get(p.get("nodo")) in feats:
            out.append(p)
    return out


# --- escritura ----------------------------------------------------------------

class ConocimientoInvalido(ValueError):
    """Un campo no valida (tipo/ámbito/efecto/nodo fuera de catálogo)."""


def _validar(tipo: str, ambito: str, nodo: str, efecto: str, estado: str) -> None:
    for valor, catalogo, nombre in (
        (tipo, TIPOS, "tipo"), (ambito, AMBITOS, "ámbito"), (nodo, NODOS, "nodo"),
        (efecto, EFECTOS, "efecto"), (estado, ESTADOS, "estado"),
    ):
        if valor not in catalogo:
            raise ConocimientoInvalido(
                f"{nombre} desconocido: {valor!r} (catálogo: {', '.join(sorted(catalogo))})")


def crear(*, texto: str, tipo: str, ambito: str, nodo: str, efecto: str,
          entidad: str | None = None, texto_en: str | None = None,
          efecto_profundo: bool = False, origen: dict | None = None,
          params: dict | None = None, estado: str = "activo",
          veces_aplicada: int = 0) -> dict:
    """Creates and persists a validated piece. `origen` = {quien, cuando}
    (who taught it and when — a human, or origen.quien="Ángela" when the
    piece comes from a learned finding, see pattern_feedback.learn()). Raises
    ConocimientoInvalido if any field falls outside the catalog — the caller
    decides what message to show."""
    if not (texto or "").strip():
        raise ConocimientoInvalido("el texto no puede estar vacío")
    _validar(tipo, ambito, nodo, efecto, estado)
    if ambito != "global" and not (entidad or "").strip():
        raise ConocimientoInvalido("una pieza no-global necesita una entidad concreta")
    from core.db import business_knowledge_repo
    from core.db import tenant as _tenant
    pieza = business_knowledge_repo.create(
        _tenant.current_tenant_id(), id="k" + secrets.token_hex(4),
        texto=texto.strip(), texto_en=texto_en, tipo=tipo, ambito=ambito,
        entidad=(entidad or "").strip() or None, nodo=nodo, efecto=efecto,
        efecto_profundo=efecto_profundo, params=params or {}, origen=origen or {},
        estado=estado, veces_aplicada=int(veces_aplicada))
    if estado == "pendiente":
        from .audit import AuditLog
        AuditLog(DATA_DIR).record((origen or {}).get("quien", ""), "proponer_conocimiento",
                              None, {"id": pieza["id"], "nodo": pieza["nodo"]})
    return pieza


def set_estado(pid: str, estado: str) -> dict | None:
    if estado not in ESTADOS:
        raise ConocimientoInvalido(f"estado desconocido: {estado!r}")
    from core.db import business_knowledge_repo
    from core.db import tenant as _tenant
    return business_knowledge_repo.set_status(_tenant.current_tenant_id(), pid, estado)


def pausar(pid: str) -> dict | None:
    return set_estado(pid, "pausado")


def activar(pid: str) -> dict | None:
    return set_estado(pid, "activo")


def borrar(pid: str) -> bool:
    from core.db import business_knowledge_repo
    from core.db import tenant as _tenant
    return business_knowledge_repo.delete(_tenant.current_tenant_id(), pid)


def aprobar(pid: str, actor: str) -> dict | None:
    """A reviewer confirms a pending proposal: it becomes active (only then
    do `aplicables()`/`para()` see it), audited with who approved it."""
    pieza = set_estado(pid, "activo")
    if pieza:
        from .audit import AuditLog
        AuditLog(DATA_DIR).record(actor, "aprobar_conocimiento", None,
                              {"id": pieza["id"], "nodo": pieza["nodo"]})
    return pieza


def rechazar(pid: str, actor: str) -> bool:
    """A reviewer discards a pending proposal — it's deleted, not paused
    (there's nothing useful about reactivating something that never got
    confirmed). The audit log is the permanent record, not the row."""
    pieza = detalle(pid)
    ok = borrar(pid)
    if ok:
        from .audit import AuditLog
        AuditLog(DATA_DIR).record(actor, "rechazar_conocimiento", None,
                              {"id": pid, "nodo": (pieza or {}).get("nodo")})
    return ok


def marcar_aplicada(pid: str, n: int = 1) -> dict | None:
    """Suma al contador acumulado REAL. Solo lo llaman eventos discretos (re-
    enseñar / aplicar explícito), JAMÁS el recálculo del análisis (correría en
    cada request y ensuciaría el snapshot sembrado)."""
    from core.db import business_knowledge_repo
    from core.db import tenant as _tenant
    return business_knowledge_repo.increment_applied(_tenant.current_tenant_id(), pid, n)
