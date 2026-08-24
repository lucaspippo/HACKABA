"""
Conocimiento del negocio — "lo que Aldo le enseñó a Ángela".

La capa NO estructurada que ningún ERP tiene: reglas de operación, criterios de
excepción, protocolos ante eventos y contexto que explica los datos. Vive hoy en
la cabeza del dueño; acá se vuelve un registro real, consultable y con efecto
verificable en lo que el usuario ve (ver core/*.py que llaman a `aplicables`).

Persiste en <DATA_DIR>/conocimiento_negocio.json (por-tenant, como toda la data:
el piloto no tiene archivo → git diff de data/ queda en cero). Es conocimiento
COMPARTIDO del negocio (no memoria por-usuario): el dueño ve todo y escribe; cada
empleado ve lo de su ámbito (ver `visibles_para`).

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
ESTADOS = {"activo", "pausado"}

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


def _load() -> dict:
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


def _save(data: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONOCIMIENTO_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _norm(s) -> str:
    return (s or "").strip().lower()


# --- lectura ------------------------------------------------------------------

def listar(nodo: str | None = None, tipo: str | None = None,
           entidad: str | None = None, ambito: str | None = None,
           incluir_pausadas: bool = True) -> list[dict]:
    """Piezas que matchean los filtros. Por defecto incluye las pausadas (Mi
    perfil las lista para reactivarlas); los motores piden incluir_pausadas=False
    vía `aplicables`."""
    piezas = _load()["piezas"]
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
        if not incluir_pausadas and p.get("estado") != "activo":
            continue
        out.append(p)
    return out


def detalle(pid: str) -> dict | None:
    for p in _load()["piezas"]:
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
    piezas = _load()["piezas"] if piezas is None else piezas
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
          entidad: str | None = None, origen: dict | None = None,
          params: dict | None = None, estado: str = "activo",
          veces_aplicada: int = 0) -> dict:
    """Crea y persiste una pieza validada. `origen` = {quien, cuando} (quién la
    enseñó y cuándo). Lanza ConocimientoInvalido si algún campo cae fuera de
    catálogo — el que llama decide qué mensaje mostrar."""
    if not (texto or "").strip():
        raise ConocimientoInvalido("el texto no puede estar vacío")
    _validar(tipo, ambito, nodo, efecto, estado)
    if ambito != "global" and not (entidad or "").strip():
        raise ConocimientoInvalido("una pieza no-global necesita una entidad concreta")
    pieza = {
        "id": "k" + secrets.token_hex(4),
        "texto": texto.strip(),
        "tipo": tipo,
        "ambito": ambito,
        "entidad": (entidad or "").strip() or None,
        "nodo": nodo,
        "efecto": efecto,
        "params": params or {},
        "origen": origen or {},
        "estado": estado,
        "veces_aplicada": int(veces_aplicada),
    }
    data = _load()
    data["piezas"].append(pieza)
    _save(data)
    return pieza


def _mutar(pid: str, cambio) -> dict | None:
    data = _load()
    for p in data["piezas"]:
        if p.get("id") == pid:
            cambio(p)
            _save(data)
            return p
    return None


def set_estado(pid: str, estado: str) -> dict | None:
    if estado not in ESTADOS:
        raise ConocimientoInvalido(f"estado desconocido: {estado!r}")
    return _mutar(pid, lambda p: p.__setitem__("estado", estado))


def pausar(pid: str) -> dict | None:
    return set_estado(pid, "pausado")


def activar(pid: str) -> dict | None:
    return set_estado(pid, "activo")


def borrar(pid: str) -> bool:
    data = _load()
    antes = len(data["piezas"])
    data["piezas"] = [p for p in data["piezas"] if p.get("id") != pid]
    if len(data["piezas"]) != antes:
        _save(data)
        return True
    return False


def marcar_aplicada(pid: str, n: int = 1) -> dict | None:
    """Suma al contador acumulado REAL. Solo lo llaman eventos discretos (re-
    enseñar / aplicar explícito), JAMÁS el recálculo del análisis (correría en
    cada request y ensuciaría el snapshot sembrado)."""
    return _mutar(pid, lambda p: p.__setitem__(
        "veces_aplicada", int(p.get("veces_aplicada", 0)) + n))
