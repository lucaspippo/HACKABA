"""Global search: one box, every entity the person is allowed to see.

WHAT THIS IS NOT. It computes nothing. Every hit is a row that already exists
in memory or in Postgres — the catalog, the accounts, the vendors, the
logistics orders, the purchase orders — and every hit carries WHERE it lives,
so the click lands on the section with the item already focused instead of on
row 1 of 430. `/api/buscar` (products only, gated on `inventario`) stays as it
is: Ángela's tool uses it and it returns enriched pricing this does not.

WHY IT IS NOT UNGATED. "Take the gate off `inventario`" cannot mean "everyone
sees everything": a driver has no business reading a customer's balance. So
the gate moves from the ENDPOINT to each TYPE of result — the same modules
the sidebar already uses. Someone with `cuentas` and no `inventario` searches
customers and gets no products, and the endpoint itself is open to anyone
logged in. That is what makes it a global search instead of a warehouse one.

The vendor / purchase-order / logistics types deliberately mirror the
frontend's own rule (DesktopApp's `extraNav`): those screens ride on
`inventario` and `deposito`, so their rows do too.
"""
from __future__ import annotations

import unicodedata

# One type, one place it lives, one module that has to be enabled to see it.
# `seccion` and `foco` speak the app's own navigation vocabulary — the same
# pairs Prioridades and the map already hand to `onNavegar`.
POR_TIPO_MODULO = {
    "producto": "inventario",
    "cliente": "cuentas",
    "proveedor": "inventario",
    "orden_compra": "inventario",
    "pedido": "deposito",
}

TOPE_POR_TIPO = 5
TOPE_TOTAL = 20


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _hit(tipo, id_, etiqueta, seccion, foco, detalle=None) -> dict:
    return {"tipo": tipo, "id": id_, "etiqueta": etiqueta,
            "detalle": detalle, "seccion": seccion, "foco": foco}


def _nodo_pedido(numero: str) -> str:
    """The map's own id for a logistics order, from the map's own sanitizer —
    never re-derived here, or a rename would silently stop focusing."""
    from . import mapa_operacion
    return mapa_operacion._sid(f"ped:{numero}")


def buscar(q: str, features=None, tope: int = TOPE_TOTAL) -> list[dict]:
    """Rows whose name contains `q`, across every type this person may see.

    `features=None` means no filtering (Ángela's own tools, tests). Short
    queries return nothing: with one letter every row matches and the palette
    becomes noise.
    """
    qn = _norm(q)
    if len(qn) < 2:
        return []
    permitido = (lambda _m: True) if features is None else (lambda m: m in set(features))

    por_tipo: dict[str, list] = {}

    if permitido(POR_TIPO_MODULO["producto"]):
        import data_store as ds
        por_tipo["producto"] = [
            _hit("producto", a["codigo"], a["descripcion"], "productos",
                 f"q:{a['descripcion']}",
                 detalle=f"#{a['codigo']}")
            for a in ds.buscar_productos(q, limit=TOPE_POR_TIPO)]

    if permitido(POR_TIPO_MODULO["cliente"]):
        from . import cuentas
        por_tipo["cliente"] = [
            _hit("cliente", c["id"], c["nombre"], "cuentas", f"cliente-{c['id']}")
            for c in cuentas.listar() if qn in _norm(c.get("nombre"))][:TOPE_POR_TIPO]

    from . import esquema

    if permitido(POR_TIPO_MODULO["proveedor"]):
        por_tipo["proveedor"] = [
            _hit("proveedor", p.get("id"), p.get("nombre"), "proveedores",
                 f"q:{p.get('nombre')}", detalle=p.get("notas") or None)
            for p in esquema.filas("proveedores")
            if qn in _norm(p.get("nombre"))][:TOPE_POR_TIPO]

    if permitido(POR_TIPO_MODULO["orden_compra"]):
        por_tipo["orden_compra"] = [
            _hit("orden_compra", o.get("numero"), o.get("numero"),
                 "ordenes_compra", f"q:{o.get('numero')}",
                 detalle=o.get("proveedor"))
            for o in esquema.filas("ordenes_compra")
            if qn in _norm(o.get("numero")) or qn in _norm(o.get("proveedor"))][:TOPE_POR_TIPO]

    if permitido(POR_TIPO_MODULO["pedido"]):
        # The only type with no list screen of its own: the map is where a
        # logistics order actually reads (its node opens the panel with what
        # is happening to it), so that is where the hit lands.
        por_tipo["pedido"] = [
            _hit("pedido", p.get("pedido"), p.get("pedido"), "mapa",
                 _nodo_pedido(p.get("pedido")),
                 detalle=f"{p.get('cliente')} · {p.get('estado')}")
            for p in esquema.filas("logistica")
            if qn in _norm(p.get("pedido")) or qn in _norm(p.get("cliente"))][:TOPE_POR_TIPO]

    # Round-robin so one crowded type (430 products) cannot bury the others.
    salida, i = [], 0
    while len(salida) < tope:
        tomo = False
        for tipo in POR_TIPO_MODULO:
            filas = por_tipo.get(tipo) or []
            if i < len(filas):
                salida.append(filas[i])
                tomo = True
                if len(salida) >= tope:
                    break
        if not tomo:
            break
        i += 1
    return salida


def parece_pregunta(q: str) -> bool:
    """Does this read like a question for Ángela rather than a name to find?

    Deliberately crude and stated out loud: more than four words, or a
    question mark. It only decides ORDER — Ángela's row is in the palette
    either way, and so are the hits.
    """
    q = (q or "").strip()
    return q.endswith("?") or len(q.split()) > 4
