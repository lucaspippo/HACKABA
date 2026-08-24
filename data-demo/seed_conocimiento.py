"""
Siembra del CONOCIMIENTO DEL NEGOCIO del demo — "lo que Aldo le enseñó a Ángela".

Las 22 piezas no estructuradas (reglas, excepciones, protocolos, contexto) que
ningún ERP tiene, atribuidas a Aldo entre el 5 de junio y el 6 de julio de 2026,
coherentes con el dataset del demo (mismos clientes, proveedores, categorías y
empleados). Cada pieza tiene un efecto verificable — dónde se ve está en
KNOWLEDGE_SINTETICO.md.

Idempotente y determinista (ids fijos k01…k22): si el archivo ya existe no se
toca — `start_demo` compara byte-a-byte con el snapshot commiteado. Se siembra
SOLO en el tenant demo (data-demo/). El piloto no tiene este archivo.

`efecto` acá es el efecto REALMENTE cableado hoy (algunas piezas quedaron en
`contexto_para_angela` porque el efecto profundo tocaba un cálculo correcto o
faltaba dato — ver KNOWLEDGE_SINTETICO.md). `params` guarda los números que el
motor usa; `veces_aplicada` es el acumulado histórico sembrado (real, no se mueve
en cada recálculo).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(HERE, "conocimiento_negocio.json")


def _o(cuando):
    return {"quien": "aldo", "cuando": cuando}


# id, texto/texto_en, tipo, ambito, entidad, nodo, efecto, params, cuando, veces_aplicada.
# `texto` es como lo diría Aldo (español); `texto_en` es la versión que Ángela le
# muestra al reviewer en inglés — el frontend elige según idioma (i18n estricto).
PIEZAS = [
    # --- CLIENTES (6) ---
    {"id": "k01", "tipo": "regla", "ambito": "cliente", "entidad": "Despensa Doña Elsa",
     "nodo": "clientes", "efecto": "ajusta_umbral", "veces_aplicada": 7,
     "params": {"tolerancia_dias": 45, "desde_anio": 2011},
     "texto": "A Despensa Doña Elsa tolerale hasta 45 días — es cliente desde 2011 y nunca me falló.",
     "texto_en": "Give Despensa Doña Elsa up to 45 days — a customer since 2011 who never let me down.",
     "origen": _o("2026-06-05")},
    {"id": "k02", "tipo": "regla", "ambito": "global", "entidad": None,
     "nodo": "clientes", "efecto": "ajusta_umbral", "veces_aplicada": 3,
     "params": {"tope_cc": 5000000, "meses_antiguedad": 6},
     "texto": "A los clientes nuevos, máximo $5.000.000 de cuenta corriente en los primeros 6 meses.",
     "texto_en": "New customers: max $5,000,000 of credit line in the first 6 months.",
     "origen": _o("2026-06-06")},
    {"id": "k03", "tipo": "protocolo", "ambito": "cliente", "entidad": "Despensa Doña Elsa",
     "nodo": "clientes", "efecto": "requiere_aprobacion", "veces_aplicada": 2,
     "params": {"dias_gatillo": 60},
     "texto": "Si un moroso pasa los 60 días, prepará la intimación pero NO la mandes sin mi OK.",
     "texto_en": "If an overdue account passes 60 days, prepare the demand letter but do NOT send it without my OK.",
     "origen": _o("2026-06-08")},
    {"id": "k04", "tipo": "contexto", "ambito": "global", "entidad": None,
     "nodo": "clientes", "efecto": "contexto_para_angela", "veces_aplicada": 4,
     "params": {"marca": "concentracion"},
     "texto": "Los tres grandes concentran el 41% pero son los que pagan en fecha: el riesgo es de concentración, no de cobro.",
     "texto_en": "The three big ones concentrate 41% but they're the ones who pay on time: the risk is concentration, not collection.",
     "origen": _o("2026-06-10")},
    {"id": "k05", "tipo": "excepcion", "ambito": "cliente", "entidad": "Rotisería Avenida",
     "nodo": "clientes", "efecto": "suprime_alerta", "veces_aplicada": 5,
     "params": {"motivo": "vencimiento_corto"},
     "texto": "A Rotisería Avenida sí le vendemos por debajo del margen objetivo: nos compra el vencimiento corto que si no tiramos.",
     "texto_en": "We do sell Rotisería Avenida below target margin: they buy the short-dated stock we'd otherwise throw out.",
     "origen": _o("2026-06-12")},
    {"id": "k06", "tipo": "contexto", "ambito": "cliente", "entidad": "Comedor Escolar N°12",
     "nodo": "clientes", "efecto": "contexto_para_angela", "veces_aplicada": 2,
     "params": {"mes_cierre": 1},
     "texto": "El Comedor Escolar N°12 factura poco en enero: cierra por vacaciones de verano.",
     "texto_en": "School Cafeteria No.12 bills little in January: it closes for summer break.",
     "origen": _o("2026-06-13")},

    # --- PROVEEDORES (4) ---
    {"id": "k07", "tipo": "regla", "ambito": "proveedor", "entidad": "Lácteos Campo Alegre",
     "nodo": "proveedores", "efecto": "ajusta_umbral", "veces_aplicada": 6,
     "params": {"evitar_dia": "viernes", "motivo": "media_dotacion"},
     "texto": "Los viernes no se hacen pedidos: el depósito está a media dotación.",
     "texto_en": "No orders on Fridays: the warehouse runs at half staff.",
     "origen": _o("2026-06-15")},
    {"id": "k08", "tipo": "contexto", "ambito": "proveedor", "entidad": "Lácteos Campo Alegre",
     "nodo": "proveedores", "efecto": "contexto_para_angela", "veces_aplicada": 8,
     "params": {},
     "texto": "Lácteos Campo Alegre sube la lista todos los meses desde hace un año.",
     "texto_en": "Lácteos Campo Alegre raises its price list every month, for the past year.",
     "origen": _o("2026-06-15")},
    {"id": "k09", "tipo": "protocolo", "ambito": "proveedor", "entidad": None,
     "nodo": "proveedores", "efecto": "requiere_aprobacion", "veces_aplicada": 3,
     "params": {"umbral_suba_pct": 15},
     "texto": "Si una lista de precios sube más del 15%, no la apliques: avisame y la negocio.",
     "texto_en": "If a price list rises more than 15%, don't apply it: tell me and I'll negotiate it.",
     "origen": _o("2026-06-18")},
    {"id": "k10", "tipo": "regla", "ambito": "proveedor", "entidad": "Frigorífico La Ribera",
     "nodo": "caja", "efecto": "contexto_para_angela", "veces_aplicada": 4,
     "params": {"plazo_pago_dias": 30},
     "texto": "A Frigorífico La Ribera se le paga a 30 días, no a 60 como al resto.",
     "texto_en": "Frigorífico La Ribera is paid at 30 days, not 60 like the rest.",
     "origen": _o("2026-06-20")},

    # --- INVENTARIO Y DEPÓSITO (5) ---
    {"id": "k11", "tipo": "regla", "ambito": "categoria", "entidad": "GASEOSA COLA LA RIBERA",
     "nodo": "inventario", "efecto": "genera_alerta", "veces_aplicada": 9,
     "params": {"critico": True},
     "texto": "GASEOSA COLA LA RIBERA nunca puede quebrar: trae gente al local.",
     "texto_en": "GASEOSA COLA LA RIBERA can never run out: it brings people into the store.",
     "origen": _o("2026-06-22")},
    {"id": "k12", "tipo": "excepcion", "ambito": "categoria", "entidad": "balanza",
     "nodo": "deposito", "efecto": "suprime_alerta", "veces_aplicada": 11,
     "params": {"balanza": 2, "umbral_pct": 1.0},
     "texto": "La balanza 2 desvía siempre un poco: si es menos del 1%, no me alertes.",
     "texto_en": "Scale 2 always drifts a bit: if it's under 1%, don't alert me.",
     "origen": _o("2026-06-24")},
    {"id": "k13", "tipo": "protocolo", "ambito": "global", "entidad": None,
     "nodo": "deposito", "efecto": "contexto_para_angela", "veces_aplicada": 1,
     "params": {"umbral_c": 4, "horas": 2, "responsable": "aldo"},
     "texto": "Si la cámara de frío pasa de 4°C por más de 2 horas, avisame a mí primero, no al depósito.",
     "texto_en": "If the cold room goes above 4°C for more than 2 hours, tell me first, not the warehouse.",
     "origen": _o("2026-06-25")},
    {"id": "k14", "tipo": "contexto", "ambito": "categoria", "entidad": "limpieza y perfumería",
     "nodo": "inventario", "efecto": "contexto_para_angela", "veces_aplicada": 3,
     "params": {},
     "texto": "El stock dormido de limpieza es de una compra grande que hicimos por precio: no es error de gestión.",
     "texto_en": "The dormant cleaning stock is from a big buy we made on price: it's not a management error.",
     "origen": _o("2026-06-27")},
    {"id": "k15", "tipo": "regla", "ambito": "categoria", "entidad": "fiambres y quesos (balanza)",
     "nodo": "inventario", "efecto": "contexto_para_angela", "veces_aplicada": 4,
     "params": {"dias_max_stock": 15},
     "texto": "Fiambres: nunca más de 15 días de stock, se vencen.",
     "texto_en": "Cold cuts: never more than 15 days of stock, they spoil.",
     "origen": _o("2026-06-28")},

    # --- EQUIPO (4) ---
    {"id": "k16", "tipo": "regla", "ambito": "empleado", "entidad": "vanesa",
     "nodo": "equipo", "efecto": "contexto_para_angela", "veces_aplicada": 6,
     "params": {"categoria": "fiambres y quesos (balanza)", "revisor": "vanesa"},
     "texto": "Los precios de fiambres los revisa Vanesa antes de aplicarlos.",
     "texto_en": "Cold-cut prices are reviewed by Vanesa before they're applied.",
     "origen": _o("2026-06-29")},
    {"id": "k17", "tipo": "contexto", "ambito": "empleado", "entidad": "tomas",
     "nodo": "equipo", "efecto": "contexto_para_angela", "veces_aplicada": 2,
     "params": {"dias": ["martes", "jueves"]},
     "texto": "Tomás maneja depósito los martes y jueves nada más.",
     "texto_en": "Tomás runs the warehouse on Tuesdays and Thursdays only.",
     "origen": _o("2026-07-01")},
    {"id": "k18", "tipo": "protocolo", "ambito": "global", "entidad": None,
     "nodo": "equipo", "efecto": "requiere_aprobacion", "veces_aplicada": 3,
     "params": {"accion": "correccion_stock_lote"},
     "texto": "Las correcciones de stock en lote las aprueba solo el dueño.",
     "texto_en": "Batch stock corrections are approved only by the owner.",
     "origen": _o("2026-07-02")},
    {"id": "k19", "tipo": "contexto", "ambito": "empleado", "entidad": "diego",
     "nodo": "equipo", "efecto": "contexto_para_angela", "veces_aplicada": 5,
     "params": {"tema": "cobranzas"},
     "texto": "Diego es el que más consulta cobranzas: es su tema.",
     "texto_en": "Diego is the one who checks collections the most: it's his thing.",
     "origen": _o("2026-07-03")},

    # --- CAJA Y CONTEXTO ECONÓMICO (3) ---
    {"id": "k20", "tipo": "regla", "ambito": "global", "entidad": None,
     "nodo": "contexto", "efecto": "contexto_para_angela", "veces_aplicada": 3,
     "params": {"ipc": "oficial"},
     "texto": "El IPC que uso para deflactar es el oficial, no el de la cámara.",
     "texto_en": "The CPI I use to deflate is the official one, not the chamber's.",
     "origen": _o("2026-07-04")},
    {"id": "k21", "tipo": "regla", "ambito": "global", "entidad": None,
     "nodo": "caja", "efecto": "genera_alerta", "veces_aplicada": 4,
     "params": {"piso": 10000000},
     "texto": "Nunca dejes la caja por debajo de $10.000.000: es el colchón de sueldos.",
     "texto_en": "Never let cash drop below $10,000,000: it's the payroll cushion.",
     "origen": _o("2026-07-05")},
    {"id": "k22", "tipo": "contexto", "ambito": "global", "entidad": None,
     "nodo": "caja", "efecto": "contexto_para_angela", "veces_aplicada": 2,
     "params": {"meses_aguinaldo": [6, 12]},
     "texto": "En junio y diciembre hay aguinaldo: la caja de esos meses no se compara con el resto.",
     "texto_en": "June and December have the 13th-salary: those months' cash isn't comparable to the rest.",
     "origen": _o("2026-07-06")},
]


# Las 10 piezas con EFECTO PROFUNDO cableado a un motor (modifican un hallazgo
# concreto). El resto son contexto que Ángela tiene en cuenta pero no mueve un
# número. Fuente única para la distinción honesta del panel (E3·4).
PROFUNDAS = {"k01", "k04", "k07", "k08", "k10", "k11", "k12", "k14", "k21", "k22"}


def _normalizar(p):
    """Completa la forma canónica de la pieza (misma que core/conocimiento.crear)."""
    return {
        "id": p["id"], "texto": p["texto"], "texto_en": p.get("texto_en"),
        "tipo": p["tipo"], "ambito": p["ambito"],
        "entidad": p.get("entidad"), "nodo": p["nodo"], "efecto": p["efecto"],
        "params": p.get("params", {}), "origen": p["origen"], "estado": "activo",
        "veces_aplicada": int(p.get("veces_aplicada", 0)),
        "efecto_profundo": p["id"] in PROFUNDAS,
    }


def sembrar() -> bool:
    """Crea conocimiento_negocio.json si falta. True si lo creó, False si ya existía."""
    if os.path.exists(DESTINO):
        return False
    data = {"piezas": [_normalizar(p) for p in PIEZAS]}
    with open(DESTINO, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True


if __name__ == "__main__":
    creado = sembrar()
    print(f"conocimiento: {'sembrado (22 piezas)' if creado else 'ya existía'}")
