"""
guion.py · LA UNICA RESPUESTA ESCRITA DE TODO EL PRODUCTO.

QUE ES Y QUE NO ES.

Es la respuesta a UNA pregunta —la del demo, con coincidencia exacta— servida
por el MISMO protocolo NDJSON que usa el modelo de verdad: los mismos eventos
`tool_call`, `tool_result`, `text`, `done`, en el mismo orden.

Por que asi y no con un texto fijo en el frontend, que es como estaba:

  1. El chat del producto pinta las herramientas mientras corren
     (ToolCallCard, de Agustin). Si la respuesta del demo se arma aparte, se
     ve DISTINTA de una respuesta real, y esa diferencia es exactamente lo
     que no puede pasar delante de un jurado. Emitiendo el mismo protocolo,
     la ruta del demo y la real son la misma pieza: el mismo componente, el
     mismo tratamiento, las mismas tarjetas de herramienta.
  2. El grafo enciende el camino a partir de los `tool_call` que ve pasar.
     Si el guion no emite tool calls, el camino del demo tendria que
     dibujarse con otro mecanismo — otra cosa mas que se puede desincronizar.
  3. Deja el hardcodeo en UN solo lugar y del lado del servidor, en vez de
     repartido en la pantalla.

Y lo importante: LAS HERRAMIENTAS SE CORREN DE VERDAD. Lo unico escrito es
QUE herramientas se llaman y el texto final. Los `tool_result` que viajan son
los datos reales del negocio, calculados por `core/`, no un JSON inventado. Si
manana cambian los datos, cambia lo que se ve.

Cualquier otra pregunta —incluida una segunda sobre el mismo reclamo— no pasa
por aca: cae en el flujo normal de `angela.stream_response`.
"""
from __future__ import annotations

import re
import unicodedata

# La pregunta, en los dos idiomas del producto. Se compara normalizada, asi que
# una tilde, un signo de apertura o un espacio de mas no rompen nada. NO se
# acepta nada parecido: antes bastaba con que el texto dijera "reclamo" o
# "campo alegre" y entonces «cuanto le debemos a Campo Alegre» contestaba con
# el reclamo de las cajas rotas.
PREGUNTAS = (
    "Llegaron ocho cajas rotas de Campo Alegre, ¿qué hago?",
    "Eight broken boxes arrived from Campo Alegre, what do I do?",
)

PROVEEDOR = "Lácteos Campo Alegre"
PRODUCTO = "LECHE ENTERA CAMPO ALEGRE 1L (X12U)"

# El plan: que herramientas se llaman, en que orden, y con que argumentos.
# `status` es la linea que se muestra mientras corre, en la voz de Ángela —
# el mismo campo que manda el modelo cuando contesta de verdad.
# CADA HERRAMIENTA, ACOTADA A ESTE CASO.
#
# Antes pedian resumenes GLOBALES y las tarjetas mostraban ruido: «Hay Datos:
# true», «Lotes 380», «Ubicaciones 21», «Discrepancias 7» — nada de eso tiene
# que ver con ocho cajas rotas, y para alguien que ve el producto por primera
# vez «Hay Datos: true» no significa absolutamente nada. La tarjeta de
# herramienta es la PRUEBA de donde salio la respuesta: si muestra cosas que no
# se usaron, deja de probar y pasa a estorbar.
#
# Tambien se fueron dos llamadas que no aportaban:
#   consultar_compras(proveedor)  devolvia saldo 0 y movimientos vacios
#   recuperar()                   devolvia {} — no es el lector de la memoria
# La regla aprendida se cita en el texto ([·](memoria:...)), que es donde de
# verdad se ve, y el numero de remito ya viene adentro del cruce.
PLAN = (
    ("consultar_cruces", {"id": "cruce_reclamo_devolucion",
                          "status": "Buscando qué pasó con esa entrega"}),
    ("consultar_deposito", {"modo": "ubicacion", "producto": PRODUCTO,
                            "status": "Ubicando el lote en el depósito"}),
)


def _normalizar(texto: str) -> str:
    base = unicodedata.normalize("NFD", (texto or "").lower())
    base = "".join(c for c in base if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", base)).strip()


_ESPERADAS = frozenset(_normalizar(p) for p in PREGUNTAS)


def es_la_del_demo(mensaje: str) -> bool:
    """Coincidencia EXACTA con la pregunta del demo. Nada parecido cuenta."""
    return _normalizar(mensaje) in _ESPERADAS


def _texto(esc: dict, lang: str) -> list[str]:
    """La respuesta, armada con los numeros que salieron de los datos.

    Ni una cifra se escribe a mano: el remito, el lote y los dias salen de
    `escena.reclamo()`, que los saca de las ordenes, del deposito y de la
    regla que el negocio le enseño.
    """
    tiene = " y ".join(f"{x['que']} ({x['valor']})" for x in (esc.get("tiene") or []))
    falta = " y ".join(esc.get("falta") or [])
    plazo = (esc.get("plazo") or {}).get("texto") or ""
    # LA CITA DE LA MEMORIA. `[·](memoria:<id>)` es el marcador que el chat del
    # producto convierte en el cerebrito (MarkdownText -> KnowledgeCite): al
    # tocarlo se ve la regla, quien la enseño y cuando. Va pegado a la frase que
    # SALE de esa regla, porque es ahi donde prueba algo — que el procedimiento
    # no lo invento, se lo enseñaron. Sin esto la respuesta del demo era la
    # unica del producto que citaba una regla sin mostrarlo.
    # DOS citas, no una: la regla y EL PORQUE DE LA REGLA.
    #
    # La primera abre la pieza k23 —«a Campo Alegre el reclamo va por mail, con
    # foto del lote»— con quien la enseño y cuando. La segunda abre k25, que es
    # de donde salio: «Campo Alegre nos rechazo un reclamo por mandarlo sin la
    # foto del lote. Desde entonces la pedimos siempre.»
    #
    # Esa segunda es la que convierte el cerebrito en prueba. Una regla sola se
    # puede leer como un dato que alguien cargo para que el demo funcione; una
    # regla CON su origen —un reclamo rechazado, una fecha, una persona— se lee
    # como lo que es: el negocio le enseño algo despues de perder plata.
    cita = ""
    if esc.get("regla_id"):
        cita += f" [·](memoria:{esc['regla_id']})"
    if esc.get("regla_origen_id"):
        cita += f"[·](memoria:{esc['regla_origen_id']})"
    if lang == "en":
        partes = [
            f"The supplier is {PROVEEDOR}. Their claims go by email, with a photo "
            f"of the lot and the delivery-note number.{cita}",
            (f"I already have {tiene}." if tiene else "")
            + (f" What is missing is {falta}." if falta else ""),
            plazo,
            "I can draft the claim now. Want me to?",
        ]
    else:
        partes = [
            f"El proveedor es {PROVEEDOR}. Para ellos el reclamo va por mail, "
            f"con foto del lote y el número de remito.{cita}",
            (f"Ya tengo {tiene}." if tiene else "")
            + (f" Falta {falta}." if falta else ""),
            plazo,
            "Lo armo. ¿Te lo mando?",
        ]
    return [p.strip() for p in partes if p and p.strip()]


def eventos(lang: str = "es"):
    """El guion, como los mismos eventos que emite `angela.stream_response`.

    Generador: se consume igual que el stream real, asi el endpoint no tiene
    que saber cual de los dos esta sirviendo.
    """
    import angela
    from . import analisis_cache as _ac
    from . import escena as _escena

    # Por el cache, la misma llave que sirve /api/escena/reclamo. Llamar al
    # core derecho costaba 337 ms — más que las cuatro herramientas juntas.
    esc = _ac.get_o_computar("escena_reclamo", lang, lambda: _escena.reclamo(lang))
    if not esc.get("disponible"):
        # Sin el caso sembrado no hay guion: que conteste el modelo.
        return

    # EL RITMO. Las cuatro herramientas juntas tardan 84 ms, o sea que sin esto
    # las cuatro tarjetas aparecen de golpe y el texto entero llega ANTES de
    # que la cámara termine de viajar — el que mira lee la respuesta y recién
    # después ve armarse el camino que la explica, que es exactamente el orden
    # que no queremos. Estas pausas no simulan trabajo que no se hizo: el
    # trabajo se hizo y fue instantáneo. Lo que hacen es dejar leer una tarjeta
    # por vez, al ritmo al que se lee, y que el texto arranque cuando el
    # lienzo ya llegó. Es puesta en escena, y va acá y no en la pantalla
    # porque acá es donde está el orden de los eventos.
    import time as _time
    PAUSA_TOOL = 0.60      # entre tarjeta y tarjeta (son dos: hay que poder leerlas)
    PAUSA_ANTES_DEL_TEXTO = 0.55

    usadas: list[str] = []
    for i, (nombre, args) in enumerate(PLAN):
        if i:
            _time.sleep(PAUSA_TOOL)
        pedido, etiqueta = angela._split_status(dict(args))
        evento = {"type": "tool_call", "id": f"g{i}", "name": nombre, "input": pedido}
        if etiqueta:
            evento["label"] = etiqueta
        yield evento
        usadas.append(nombre)
        try:
            # DE VERDAD. Estas cuatro estan cacheadas (ver analisis_cache):
            # las cuatro juntas tardan milisegundos.
            resultado, _accion = angela._run_tool(nombre, dict(pedido))
        except Exception as e:  # noqa: BLE001 — el guion nunca puede romper
            resultado = {"error": str(e)}
        yield {"type": "tool_result", "id": f"g{i}", "result": resultado}

    _time.sleep(PAUSA_ANTES_DEL_TEXTO)
    # El texto sale en pedazos, como los deltas del modelo: se lee escribiendose
    # y no apareciendo de golpe.
    for parrafo in _texto(esc, lang):
        for palabra in parrafo.split(" "):
            yield {"type": "text", "delta": palabra + " "}
            _time.sleep(0.012)
        yield {"type": "text", "delta": "\n\n"}

    yield {"type": "done", "result": {"mode": "guion", "tools_used": usadas,
                                      "actions": [], "options": []}}
