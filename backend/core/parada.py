"""parada.py — LA PARADA ENRIQUECIDA: quién está parado frente a quién.

El ERP sabe cuánto debe cada cliente, sabe qué se vence en el depósito y —si
alguien lo cargó— sabe lo que el equipo contó. Lo que no sabe nadie es que
**Walter va a estar parado en la puerta de Doña Elsa mañana a las diez**, y ésa
es la pregunta que convierte tres consultas sueltas en una decisión.

Tres preguntas, una pantalla, y las tres fuentes ya existían:

  1. ¿DEBE?  — `cuentas`, con el plazo del sistema Y el de la casa. La regla de
     Aldo ("a Doña Elsa tolerale hasta 45 días") ya viene aplicada por
     `cuentas._enriquecer`: acá sólo se pasa. Sin ella el número miente dos
     veces — marca en falso a quien tiene permiso, y no marca a quien lo pasó.
  2. ¿ALGUIEN DIJO ALGO?  — `notas`, de CUALQUIER autor, últimos 30 días.
     Walter le dijo a nadie que Doña Elsa prometió ponerse al día; Lucía anotó
     que pidió una entrega chica sin factura nueva. Las dos cosas le sirven al
     que toca el timbre, y las dos se morían en el mapa del dueño.
  3. ¿COMPRA ALGO DE LO QUE SE VENCE?  — `vencimientos` × `ventas_cliente`. El
     camión sale igual: si además lleva lo que se vence y este cliente compra,
     el viaje ya está pago.

NO HAY TOTAL ACÁ, Y ES A PROPÓSITO. La suma de deuda por camión ya existe y es
canónica (`cobranza.exposicion_en_ruta`, deduplicada por cliente). Un segundo
total, calculado en otro lado sobre las mismas filas, es exactamente cómo
nacieron los dos dobles conteos que este repo ya pagó — ver PRODUCT.md, The
Counting Rule. Acá cada parada es UN cliente y los montos se citan, no se suman.
"""
from __future__ import annotations

import datetime

# Lo que el equipo dijo de un cliente y todavía sirve al tocar el timbre. El
# mismo número que usa `cruces.VENTANA_NOTAS_DIAS`, y por el mismo motivo: una
# nota de hace tres meses ya no es una señal.
VENTANA_NOTAS_DIAS = 30
# Lo que se vence dentro de la ventana de la logística: si vence dentro de un
# mes y este cliente lo compra, el que va puede ofrecerlo.
VENTANA_VENCE_DIAS = 30


def _desde(dias: int) -> str:
    from .fechas import hoy
    return (hoy() - datetime.timedelta(days=dias)).isoformat()


def _cliente_de(nombre: str) -> dict | None:
    from . import cuentas
    return cuentas.buscar(nombre)


def deuda(nombre: str) -> dict | None:
    """Lo que debe, con los DOS plazos: el del sistema y el de la casa.

    `cuentas` ya calcula todo esto; acá se elige qué mostrar parado en una
    puerta. No se recalcula un solo número.
    """
    c = _cliente_de(nombre)
    if not c:
        return None
    return {
        "cliente_id": c.get("id"),
        "saldo": c.get("saldo"),
        "dias_sin_pagar": c.get("dias_sin_pagar"),
        "plazo_dias": c.get("plazo_dias"),
        "promedio_pago_dias": c.get("promedio_pago_dias"),
        "en_mora": bool(c.get("en_mora")),
        # La regla de la casa, cuando existe para este cliente. `exceso_tolerancia`
        # es contra el plazo que dio el dueño, no contra el del sistema.
        "tolerancia_dias": c.get("tolerancia_dias"),
        "exceso_tolerancia": c.get("exceso_tolerancia"),
        "conocimiento": c.get("conocimiento") or [],
    }


def dijeron(nombre: str, lang: str | None = None,
            dias: int = VENTANA_NOTAS_DIAS) -> list[dict]:
    """Lo que el equipo contó de este cliente, de cualquier autor.

    Es el punto entero: Walter escucha algo y hoy se muere ahí; el que va
    mañana no se entera. Se muestra CON el nombre de quien lo dijo — un aviso
    sin autor no se puede ni preguntar ni desmentir.
    """
    from . import notas as notas_equipo, piso
    out = []
    for n in notas_equipo.sobre_cliente(nombre, desde=_desde(dias)):
        out.append({
            "id": n.get("id"), "autor": n.get("autor"),
            "autor_nombre": piso._nombre(n.get("autor")),
            "fecha": n.get("fecha"), "canal": n.get("canal"),
            "tipo": n.get("tipo"),
            "texto": notas_equipo.texto_en(n, lang),
        })
    return sorted(out, key=lambda x: x["fecha"] or "", reverse=True)


def vence_y_compra(nombre: str, dias: int = VENTANA_VENCE_DIAS) -> list[dict]:
    """Lo que se vence Y este cliente compra.

    `plata_en_riesgo` sale de `vencimientos.en_riesgo` tal cual: es el sobrante
    que no se alcanza a vender, no el valor del lote, y no se recalcula acá.
    """
    from . import vencimientos, ventas_cliente
    c = _cliente_de(nombre)
    if not c or not ventas_cliente.hay_datos():
        return []
    r = vencimientos.en_riesgo(dias)
    if not r.get("disponible"):
        return []
    out = []
    for lote in r.get("items") or []:
        cod = lote.get("codigo")
        if cod is None:
            continue
        mio = next((x for x in ventas_cliente.compradores_de(cod)
                    if x["cliente_id"] == c["id"]), None)
        if not mio:
            continue
        out.append({
            "codigo": cod, "producto": lote.get("producto"),
            "lote": lote.get("lote"), "vencimiento": lote.get("vencimiento"),
            "dias_restantes": lote.get("dias_restantes"),
            "sobrante": lote.get("sobrante"),
            "plata_en_riesgo": lote.get("plata_en_riesgo"),
            # Lo que ESTE cliente se llevó de eso, para que el ofrecimiento no
            # sea a ciegas: "te llevás 306 por año" es un argumento, "comprá
            # esto" no.
            "le_compro": {"monto": mio["monto"], "cantidad": mio["cantidad"],
                          "ultima": mio["ultima"]},
        })
    return sorted(out, key=lambda x: x["dias_restantes"])


def de(cliente: str, lang: str | None = None) -> dict:
    """La parada entera. `cliente` es el nombre tal como viene de logística."""
    return {
        "cliente": cliente,
        "deuda": deuda(cliente),
        "dijeron": dijeron(cliente, lang),
        "vence_y_compra": vence_y_compra(cliente),
    }


def proximas(transporte: str | None = None, dias: int = 2) -> list[dict]:
    """Las paradas sin entregar de los próximos días, en orden.

    `transporte` filtra por substring — así el chofer pide "Walter" y no tiene
    que saber cómo se escribe su camión en el export del TMS.
    """
    from . import logistica
    from .fechas import hoy
    t = (transporte or "").strip().lower()
    out = []
    for i in range(max(1, dias)):
        dia = hoy() + datetime.timedelta(days=i)
        for p in logistica.salidas(dia.isoformat()):
            if t and t not in str(p.get("transporte") or "").lower():
                continue
            out.append({"pedido": p.get("pedido"), "cliente": p.get("cliente"),
                        "direccion": p.get("direccion"), "dia": dia.isoformat(),
                        "estado": p.get("estado_norm"),
                        "transporte": p.get("transporte")})
    return out
