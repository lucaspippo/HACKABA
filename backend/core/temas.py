"""
temas.py · DE QUE HABLA EL PEDIDO — y que se puede apagar por eso.

DOS CONSUMIDORES, UN SOLO MAPA.

1) `tools_del_tema()` — recorta el catalogo de 50 herramientas al punado que
   tiene que ver con lo que se pregunto. Nos lo recomendaron en la sede: a un
   modelo con cincuenta herramientas colgadas le cuesta mas elegir, y cada
   definicion que viaja es input que se paga y se lee. El gate por rol
   (`angela.tools_para`) ya hace exactamente esto con otra llave; esto es la
   misma mecanica con la llave del tema.

2) `nodos_de()` — que TIPOS de nodo del cerebro toca cada herramienta. Cuando
   Angela contesta una pregunta cualquiera dentro de la pantalla del grafo, el
   camino que se ilumina sale de aca: se enciende lo que efectivamente
   consulto, no un recorrido escrito a mano.

LA REGLA DE ORO, Y NO ES NEGOCIABLE:
    si no estamos seguros del tema, van TODAS las herramientas.
Recortar de mas es peor que no recortar: una pregunta que no se puede contestar
porque le escondimos la herramienta es un producto roto, y el ahorro era de
milisegundos. Por eso `tools_del_tema` devuelve el catalogo entero ante la
minima duda, y el NUCLEO viaja siempre.
"""
from __future__ import annotations

import re
import unicodedata

# El punado que viaja SIEMPRE, tenga el pedido el tema que tenga: son las que
# usa para moverse por la app, acordarse y ubicarse. Sin estas, cualquier
# conversacion normal se rompe.
NUCLEO = frozenset({
    "navegar_a", "modificar_vista", "recordar", "recuperar",
    "recuperar_contexto_negocio", "resumen_negocio", "buscar_productos",
    "listar_prioridades", "cancelar_mensaje", "leer_preferencias",
})

# tema -> herramientas de ese tema
TOOLS_POR_TEMA: dict[str, frozenset[str]] = {
    "stock": frozenset({
        "consultar_deposito", "top_inmovilizado", "listar_grupo",
        "analisis_rotacion", "capital_recuperable", "consultar_pronostico",
        "analisis_estacionalidad", "analisis_push_pull",
    }),
    "proveedores": frozenset({
        "consultar_compras", "consultar_envios", "consultar_deposito",
        "consultar_cruces", "generar_documento", "proponer_plan",
        "ejecutar_plan", "proponer_conocimiento",
    }),
    "plata": frozenset({
        "estado_caja", "cerrar_caja", "plata_en", "cuentas_corrientes",
        "mensaje_cobro", "scoring_credito", "capital_recuperable",
        "consultar_evolucion", "consultar_serie",
    }),
    "clientes": frozenset({
        "cuentas_corrientes", "scoring_credito", "mensaje_cobro",
        "consultar_cruces", "consultar_serie",
    }),
    "ventas": frozenset({
        "consultar_serie", "consultar_evolucion", "analisis_estacionalidad",
        "analisis_rotacion", "consultar_pronostico", "consultar_contexto_macro",
        "analisis_push_pull",
    }),
    "datos": frozenset({
        "proponer_correccion", "aplicar_correccion_custom",
        "aplicar_correccion_en_lote", "normalizaciones_staging",
        "revertir_version", "consultar_manual",
    }),
    "equipo": frozenset({
        "crear_recordatorio", "mis_recordatorios", "crear_objetivo",
        "objetivos_negocio", "proponer_conocimiento", "recordar_preferencia",
    }),
    "pantalla": frozenset({
        "crear_pestana", "crear_widget", "gestionar_widget", "gestionar_modulo",
        "reordenar_inicio", "recordar_preferencia",
    }),
}

# Las palabras que delatan el tema, ya normalizadas (sin tildes, minusculas).
#
# CONVENCION: `"venta*"` pega con cualquier palabra que EMPIECE asi —venta,
# ventas, vendedor no—; `"caja"` pega solo con esa palabra exacta. La estrella
# es explicita a proposito. Antes esto era subcadena suelta y costaba caro en
# los dos sentidos: `"rot"` mandaba «que productos no rotan» a proveedores (por
# «rotas»), y de paso stock no lo agarraba — o sea la pregunta perdia
# `analisis_rotacion`, que era justo la herramienta que necesitaba. Meter de
# mas es gratis; dejar afuera la herramienta correcta es el unico error que
# importa.
PISTAS_TEMA: dict[str, tuple[str, ...]] = {
    "stock": ("stock", "deposito*", "inventario", "repon*", "reposicion",
              "quiebre*", "falta*", "sobra*", "inmovilizado*", "vencimiento*",
              "vence*", "lote*", "rotacion", "rota", "rotan", "rotar",
              "almacen", "mercaderia", "gondola", "producto*", "articulo*",
              "unidad*", "caj*"),
    "proveedores": ("proveedor*", "compra*", "pedido*", "remito*", "reclam*",
                    "devoluc*", "entrega*", "envio*", "roto", "rotos", "rotas",
                    "danad*", "flete*", "alegre", "ribera", "recepcion*"),
    "plata": ("plata", "caja", "cajas", "cobr*", "pag*", "deuda*", "factur*",
              "banco*", "efectivo", "cheque*", "saldo*", "credito*",
              "margen*", "rentabilidad", "costo*", "precio*"),
    "clientes": ("cliente*", "moroso*", "cobranza*", "scoring", "fiado",
                 "comprador*", "deudor*"),
    "ventas": ("venta*", "vende*", "vendi*", "factur*", "ticket*", "demanda*",
               "pronostico*", "estacional*", "tendencia*", "crec*", "cay*",
               "compar*", "inflacion"),
    "datos": ("dato*", "error*", "duplicad*", "corregir", "correccion*",
              "limpiar", "normaliz*", "staging", "importar", "version*",
              "manual"),
    "equipo": ("equipo", "recordatorio*", "recordame", "objetivo*", "meta",
               "metas", "empleado*", "encargado*", "turno*", "quien",
               "nahuel", "celeste"),
    "pantalla": ("pantalla*", "vista*", "pestana*", "widget*", "tablero*",
                 "modulo*", "inicio", "mostrar", "ocultar", "acomod*"),
}

# Que TIPOS de nodo del cerebro toca cada herramienta. Se usa para encender el
# camino cuando la respuesta no es la del demo. Lo que no esta aca no enciende
# nada: preferimos no iluminar antes que iluminar de mentira.
NODOS_POR_TOOL: dict[str, tuple[str, ...]] = {
    "consultar_deposito": ("producto", "ubicacion", "local"),
    "top_inmovilizado": ("producto", "rubro"),
    "listar_grupo": ("producto", "rubro"),
    "buscar_productos": ("producto",),
    "analisis_rotacion": ("producto", "rubro"),
    "analisis_estacionalidad": ("producto", "rubro"),
    "analisis_push_pull": ("producto", "local"),
    "capital_recuperable": ("producto", "rubro"),
    "consultar_pronostico": ("producto",),
    "consultar_compras": ("proveedor", "producto", "remito"),
    "consultar_envios": ("remito", "proveedor", "ubicacion"),
    "consultar_cruces": ("producto", "proveedor", "cliente", "nota",
                         "conocimiento"),
    "cuentas_corrientes": ("cliente", "cuenta"),
    "scoring_credito": ("cliente", "cuenta"),
    "mensaje_cobro": ("cliente", "cuenta"),
    "estado_caja": ("cuenta",),
    "cerrar_caja": ("cuenta",),
    "plata_en": ("cuenta", "local"),
    "consultar_serie": ("producto", "rubro"),
    "consultar_evolucion": ("producto", "rubro", "cliente"),
    "listar_prioridades": ("nota", "producto", "cliente", "proveedor"),
    "resumen_negocio": ("producto", "cliente", "cuenta"),
    "proponer_conocimiento": ("conocimiento", "persona"),
    "recordar": ("conocimiento", "persona"),
    "recuperar": ("conocimiento", "persona"),
    "mis_recordatorios": ("persona",),
    "crear_recordatorio": ("persona",),
    "objetivos_negocio": ("persona",),
    "generar_documento": ("proveedor", "remito", "producto"),
    "proponer_plan": ("producto", "proveedor"),
    "ejecutar_plan": ("producto", "proveedor"),
}


def _normalizar(texto: str) -> str:
    """minusculas, sin tildes, sin signos."""
    base = unicodedata.normalize("NFD", (texto or "").lower())
    base = "".join(c for c in base if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", base)).strip()


def _pega(pista: str, palabras: set[str]) -> bool:
    """`"venta*"` pega con toda palabra que empiece asi; `"caja"` solo con esa."""
    if pista.endswith("*"):
        raiz = pista[:-1]
        return any(p.startswith(raiz) for p in palabras)
    return pista in palabras


def temas_de(texto: str) -> set[str]:
    """Los temas que toca el pedido. Vacio = no lo sabemos (y ahi van todas)."""
    palabras = set(_normalizar(texto).split())
    if not palabras:
        return set()
    return {tema for tema, pistas in PISTAS_TEMA.items()
            if any(_pega(p, palabras) for p in pistas)}


def tools_del_tema(catalogo: list[dict], texto: str) -> list[dict]:
    """`catalogo` recortado a lo que hace falta para ESTE pedido.

    Ante la duda, entero. Se recorta solo cuando el tema se reconoce sin
    ambiguedad y lo que queda alcanza para trabajar; si el recorte deja menos
    que el nucleo + 4, no vale la pena arriesgarse y vuelve el catalogo
    completo.
    """
    temas = temas_de(texto)
    if not temas:
        return catalogo
    permitidas = set(NUCLEO)
    for tema in temas:
        permitidas |= TOOLS_POR_TEMA.get(tema, frozenset())
    recortado = [t for t in catalogo if t["name"] in permitidas]
    if len(recortado) < len(NUCLEO) + 4:
        return catalogo
    return recortado


def nodos_de(tools_usadas) -> list[str]:
    """Los tipos de nodo que tocaron esas herramientas, sin repetir."""
    vistos: list[str] = []
    for nombre in (tools_usadas or []):
        for tipo in NODOS_POR_TOOL.get(nombre, ()):
            if tipo not in vistos:
                vistos.append(tipo)
    return vistos
