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
DEFAULT_HALF_LIFE = {"regla": 180, "excepcion": 120, "protocolo": 365, "contexto": 270}
# A qué se refiere la pieza.
AMBITOS = {"cliente", "proveedor", "categoria", "empleado", "global"}
# Qué hace la pieza en el producto (el efecto verificable).
EFECTOS = {"ajusta_umbral", "suprime_alerta", "genera_alerta",
           "contexto_para_angela", "requiere_aprobacion"}
# Dominio del mapa donde nace la pieza (los 8 nodos del Business Map).
NODOS = {"ventas", "inventario", "deposito", "proveedores",
         "clientes", "caja", "equipo", "contexto"}
ESTADOS = {"activo", "pausado", "pendiente", "revisar", "superada", "archivada"}

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
           incluir_pausadas: bool = True, estado: str | None = None,
           incluir_archivadas: bool = False) -> list[dict]:
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
        elif not incluir_archivadas and p.get("estado") in ("archivada", "superada"):
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
    origen = p.get("origen") or {}
    sup_texto = None
    if p.get("superseded_by"):
        sup = detalle(p["superseded_by"])
        sup_texto = sup["texto"] if sup else None
    return {"id": p["id"], "tipo": p["tipo"], "texto": p["texto"],
            "texto_en": p.get("texto_en"), "nodo": p["nodo"], "efecto": p["efecto"],
            "efecto_profundo": p.get("efecto_profundo", False),
            "veces_aplicada": p.get("veces_aplicada", 0),
            "cuando": origen.get("cuando"), "quien": origen.get("quien"),
            "superseded_by_texto": sup_texto}


def age_days(p: dict, *, today=None) -> int | None:
    """Days since this piece was taught, or None if origen.cuando is
    missing (a piece seeded without provenance)."""
    cuando = (p.get("origen") or {}).get("cuando")
    if not cuando:
        return None
    from datetime import date as _date
    from . import fechas
    ref = today or fechas.hoy()
    try:
        taught = _date.fromisoformat(cuando[:10])
    except ValueError:
        return None
    return (ref - taught).days


def decay_score(p: dict, *, today=None) -> float:
    """Confidence right now: exponential half-life decay from
    last_reinforced_at, read-time only — never mutates the stored row.
        confidence(t) = stored_confidence * 2 ** (-age_days / half_life)
    """
    from datetime import date as _date
    from . import fechas
    ref = today or fechas.hoy()
    reinforced = _date.fromisoformat(p["last_reinforced_at"][:10])
    age = max(0, (ref - reinforced).days)
    half_life = p.get("half_life_days") or DEFAULT_HALF_LIFE[p["tipo"]]
    return float(p["confidence"]) * (2 ** (-age / half_life))


def freshness(p: dict, *, today=None) -> str:
    """"fresco" | "atencion" | "revisar" — the traffic-light bucket over
    decay_score(), same three-tone vocabulary grafo.py/priorities.py
    already use for riesgo/tono."""
    score = decay_score(p, today=today)
    if score >= 0.55:
        return "fresco"
    if score >= 0.35:
        return "atencion"
    return "revisar"


def needs_review(p: dict, *, today=None, threshold: float = 0.35) -> bool:
    """True once decay_score() crosses the review floor. Does NOT change
    estado by itself."""
    return decay_score(p, today=today) < threshold


def reinforce(pid: str) -> dict | None:
    """Bumps evidence_count and resets last_reinforced_at = today, nudging
    confidence up by a decreasing amount so repeated reinforcement
    approaches but never exceeds 1.0."""
    p = detalle(pid)
    if not p:
        return None
    bump = (1.0 - float(p["confidence"])) * 0.2
    nuevo = min(1.0, float(p["confidence"]) + bump)
    from core.db import business_knowledge_repo
    from core.db import tenant as _tenant
    return business_knowledge_repo.update_reinforcement(
        _tenant.current_tenant_id(), pid, confidence=nuevo,
        evidence_count=p["evidence_count"] + 1)


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


def validate_proposal(*, texto: str, tipo: str, ambito: str, nodo: str,
                      efecto: str, entidad: str | None = None) -> dict:
    """Checks a proposal against the same catalog `crear` enforces and returns
    the normalized fields, WITHOUT persisting anything. Ángela proposes with
    this so a bad `nodo` fails while she can still say so, and the piece is
    only written when the user confirms (see main.py's /confirmar)."""
    if not (texto or "").strip():
        raise ConocimientoInvalido("el texto no puede estar vacío")
    _validar(tipo, ambito, nodo, efecto, "activo")
    entidad = (entidad or "").strip() or None
    if ambito != "global" and not entidad:
        raise ConocimientoInvalido("una pieza no-global necesita una entidad concreta")
    return {"texto": texto.strip(), "tipo": tipo, "ambito": ambito,
            "nodo": nodo, "efecto": efecto, "entidad": entidad}


def find_duplicate(*, texto: str, nodo: str, entidad: str | None = None) -> dict | None:
    """An existing piece saying the same thing about the same place, or None.
    Confirming is idempotent through this: the tool-call part stays in the
    thread after a reload, so the same chip can be clicked twice, and the
    model re-proposes a rule it already proposed a few turns back."""
    target = _norm(texto)
    for p in _todas():
        if (_norm(p.get("texto")) == target and p.get("nodo") == nodo
                and _norm(p.get("entidad")) == _norm(entidad)):
            return p
    return None


def find_conflict(*, texto: str, nodo: str, entidad: str | None,
                  efecto: str) -> dict | None:
    """An existing ACTIVE piece with the same (entidad, nodo, efecto) but
    DIFFERENT texto. Distinct from find_duplicate: a duplicate says the
    same thing about the same place; a conflict says something different
    about the same triple."""
    target = _norm(texto)
    for p in listar(nodo=nodo, incluir_pausadas=False):
        if (p.get("efecto") == efecto and _norm(p.get("entidad")) == _norm(entidad)
                and _norm(p.get("texto")) != target):
            return p
    return None


def crear(*, texto: str, tipo: str, ambito: str, nodo: str, efecto: str,
          entidad: str | None = None, texto_en: str | None = None,
          efecto_profundo: bool = False, origen: dict | None = None,
          params: dict | None = None, estado: str = "activo",
          veces_aplicada: int = 0, half_life_days: int | None = None) -> dict:
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
        estado=estado, veces_aplicada=int(veces_aplicada), half_life_days=half_life_days)
    if estado == "pendiente":
        from .audit import AuditLog
        AuditLog(DATA_DIR).record((origen or {}).get("quien", ""), "proponer_conocimiento",
                              None, {"id": pieza["id"], "nodo": pieza["nodo"]})
    return pieza


def edit_piece(pid: str, *, actor: str, is_admin: bool, texto: str | None = None,
               texto_en: str | None = None, tipo: str | None = None,
               ambito: str | None = None, efecto: str | None = None,
               entidad: str | None = None, params: dict | None = None) -> dict | None:
    """Merges the given fields onto the existing piece, validates the result
    against the same catalog crear() enforces, persists, and audits before/
    after. An admin's edit keeps the piece's current estado; anyone else's
    (only the piece's own author reaches here — main.py enforces that) sends
    it back to "pendiente" for re-review, same trust model as a fresh
    proposal. Returns None if pid doesn't exist."""
    actual = detalle(pid)
    if not actual:
        return None
    nuevo_texto = texto if texto is not None else actual["texto"]
    if not (nuevo_texto or "").strip():
        raise ConocimientoInvalido("el texto no puede estar vacío")
    nuevo_ambito = ambito or actual["ambito"]
    nueva_entidad = entidad if entidad is not None else actual.get("entidad")
    nuevo_tipo = tipo or actual["tipo"]
    nuevo_efecto = efecto or actual["efecto"]
    _validar(nuevo_tipo, nuevo_ambito, actual["nodo"], nuevo_efecto, actual["estado"])
    if nuevo_ambito != "global" and not (nueva_entidad or "").strip():
        raise ConocimientoInvalido("una pieza no-global necesita una entidad concreta")
    nuevo_estado = actual["estado"] if is_admin else "pendiente"
    from core.db import business_knowledge_repo
    from core.db import tenant as _tenant
    pieza = business_knowledge_repo.update_content(
        _tenant.current_tenant_id(), pid, texto=nuevo_texto.strip(),
        texto_en=(texto_en if texto_en is not None else actual.get("texto_en")),
        tipo=nuevo_tipo, ambito=nuevo_ambito, efecto=nuevo_efecto,
        entidad=(nueva_entidad or "").strip() or None,
        params=(params if params is not None else actual.get("params") or {}),
        estado=nuevo_estado)
    from .audit import AuditLog
    AuditLog(DATA_DIR).record(actor, "editar_conocimiento", actual, pieza)
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


def archive(pid: str, *, actor: str, motivo: str | None = None) -> dict | None:
    """Retires a piece that was ever active/paused/revisar — replaces
    borrar() as the normal path so nothing that was once confirmed
    disappears without a trace. borrar() stays for a rejected pendiente
    proposal (nothing to preserve) and explicit admin purges."""
    pieza = set_estado(pid, "archivada")
    if pieza:
        from .audit import AuditLog
        AuditLog(DATA_DIR).record(actor, "archivar_conocimiento", None,
                              {"id": pieza["id"], "nodo": pieza["nodo"], "motivo": motivo})
    return pieza


def supersede(pid: str, *, replacement_id: str, actor: str) -> dict | None:
    from core.db import business_knowledge_repo
    from core.db import tenant as _tenant
    pieza = business_knowledge_repo.set_superseded(
        _tenant.current_tenant_id(), pid, superseded_by=replacement_id)
    if pieza:
        from .audit import AuditLog
        AuditLog(DATA_DIR).record(actor, "reemplazar_conocimiento", None,
                              {"id": pieza["id"], "superseded_by": replacement_id})
    return pieza


def reconfirm(pid: str, *, actor: str) -> dict | None:
    """The review-queue "still valid" action: reinforces the piece and,
    if it was in estado="revisar", brings it back to "activo"."""
    p = detalle(pid)
    if not p:
        return None
    pieza = reinforce(pid)
    if p["estado"] == "revisar":
        pieza = set_estado(pid, "activo")
    from .audit import AuditLog
    AuditLog(DATA_DIR).record(actor, "reconfirmar_conocimiento", None, {"id": pid})
    return pieza


def marcar_aplicada(pid: str, n: int = 1) -> dict | None:
    """Suma al contador acumulado REAL. Solo lo llaman eventos discretos (re-
    enseñar / aplicar explícito), JAMÁS el recálculo del análisis (correría en
    cada request y ensuciaría el snapshot sembrado)."""
    from core.db import business_knowledge_repo
    from core.db import tenant as _tenant
    return business_knowledge_repo.increment_applied(_tenant.current_tenant_id(), pid, n)
