"""
ficha.py — EL PRODUCTO, contestando las preguntas que se hacen parado.

El desktop tiene 34 secciones. El criterio para el teléfono no es cuáles caben:
es que **la entrada correcta a un dato en el celular casi nunca es una lista.**
Una lista de 430 productos no la scrollea nadie con guantes puestos. Se llega
acá por una búsqueda, por un escaneo o desde una tarea que ya lo trae enfocado,
y lo que se abre es la ficha de ESE producto.

Las preguntas son las que la gente hace de verdad, y cada una ya tenía su motor:

  · ¿DÓNDE ESTÁ?      — `deposito._ubicaciones_de`. La primera pregunta del
                        depósito, y hoy vive en un análisis del dueño.
  · ¿CUÁNTO HAY?      — el stock del catálogo, con lo que `quality` diga de él
                        (negativo, fantasma, sin precio, balanza, costo viejo).
  · ¿A CUÁNTO SE VENDE? — el pvp y, si el costo con el que se calculó es viejo,
                        cuántos días tiene.
  · ¿SE VENCE ALGO?   — los lotes de `vencimientos.en_riesgo`, tal cual.
  · ¿QUIÉN LO COMPRA? — `ventas_cliente.compradores_de`, los primeros.
  · ¿ALGUIEN DIJO ALGO? — `notas.sobre_producto`. Lo que el equipo contó de
                        este producto y hoy se muere en el mapa del dueño.

ACÁ NO SE CALCULA NINGÚN NÚMERO NUEVO (PRODUCT.md, The Counting Rule). Todos
salen de su motor y se citan. No hay total: una ficha es UN producto, y sumar
sus lotes con su inmovilizado con lo que le compran daría un número que no
responde ninguna pregunta.
"""
from __future__ import annotations

import datetime

# Cuánto para atrás se mira lo que el equipo dijo de un producto. El mismo
# número que `parada.VENTANA_NOTAS_DIAS`, y por el mismo motivo: una nota de
# hace tres meses ya no es una señal.
VENTANA_NOTAS_DIAS = 30
# Los lotes que se miran: la misma ventana con la que trabaja la logística.
VENTANA_VENCE_DIAS = 30
# Cuántos compradores se muestran. Los tres primeros contestan "¿a quién se lo
# ofrezco?"; los treinta siguientes son una lista que nadie lee en un teléfono.
TOPE_COMPRADORES = 3


def _articulo(codigo: int) -> dict | None:
    from . import store
    for a in store.raw_actual():
        if a.get("codigo") == codigo:
            return a
    return None


def _problemas(a: dict, lang: str | None) -> list[dict]:
    """Lo que el libro de calidad ya dice de este artículo, sin recalcular nada."""
    import i18n
    from . import quality
    from .models import Articulo
    return [{"categoria": i.categoria.value,
             "label": i18n.t(f"core.calidad.{i.categoria.value}", lang),
             "estado": i.estado.value,
             "detalle": i.detalle}
            for i in quality.clasificar(Articulo.from_dict(a))]


def _lotes(codigo: int, dias: int) -> list[dict]:
    from . import vencimientos
    r = vencimientos.en_riesgo(dias)
    if not r.get("disponible"):
        return []
    return [{"lote": x.get("lote"), "vencimiento": x.get("vencimiento"),
             "dias_restantes": x.get("dias_restantes"),
             "cantidad": x.get("cantidad"), "sobrante": x.get("sobrante"),
             # Se CITA de vencimientos: es el sobrante que no se alcanza a
             # vender, no el valor del lote, y no se recalcula acá.
             "plata_en_riesgo": x.get("plata_en_riesgo")}
            for x in (r.get("items") or []) if x.get("codigo") == codigo]


def _compradores(codigo: int) -> list[dict]:
    from . import ventas_cliente
    if not ventas_cliente.hay_datos():
        return []
    filas = ventas_cliente.compradores_de(codigo) or []
    return [{"cliente_id": c.get("cliente_id"), "cliente": c.get("nombre"),
             "cantidad": c.get("cantidad"), "monto": c.get("monto"),
             "ultima": c.get("ultima")}
            for c in filas[:TOPE_COMPRADORES]]


def _dijeron(nombre: str, lang: str | None, dias: int) -> list[dict]:
    from . import notas as notas_equipo, piso
    from .fechas import hoy
    desde = (hoy() - datetime.timedelta(days=dias)).isoformat()
    out = [{"id": n.get("id"), "autor": n.get("autor"),
            "autor_nombre": piso._nombre(n.get("autor")),
            "fecha": n.get("fecha"), "canal": n.get("canal"),
            "texto": notas_equipo.texto_en(n, lang)}
           for n in notas_equipo.sobre_producto(nombre, desde=desde)]
    return sorted(out, key=lambda x: x["fecha"] or "", reverse=True)


def producto(codigo: int, lang: str | None = None) -> dict | None:
    """La ficha entera de un producto, o None si ese código no existe.

    Devolver None y que la pantalla lo diga es la única respuesta honesta a un
    escaneo de algo que no está en el catálogo — que es un caso REAL del
    depósito, no una rareza.
    """
    a = _articulo(codigo)
    if not a:
        return None
    from . import deposito
    nombre = a.get("descripcion") or ""
    return {
        "codigo": codigo,
        "producto": nombre,
        "categoria": a.get("tipo"),
        "proveedor": a.get("proveedor"),
        "estado": a.get("estado"),
        "um": a.get("um"),
        "stock": a.get("stock"),
        "pvp": a.get("pvp"),
        "costo_neto": a.get("costo_neto"),
        "antiguedad_costo_dias": (int(a["antiguedad_costo_dias"])
                                  if a.get("antiguedad_costo_dias") else None),
        "venta_x_peso": bool(a.get("venta_x_peso")),
        "ubicaciones": deposito._ubicaciones_de(codigo),
        "problemas": _problemas(a, lang),
        "lotes": _lotes(codigo, VENTANA_VENCE_DIAS),
        "compradores": _compradores(codigo),
        "dijeron": _dijeron(nombre, lang, VENTANA_NOTAS_DIAS),
    }
