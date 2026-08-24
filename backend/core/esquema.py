"""
Esquema adaptativo — el grafo de relaciones del negocio.

Cuando llega un tipo de dato que el sistema nunca tuvo, Ángela: (1) identifica
el tipo por sus columnas, (2) detecta cómo se relaciona con lo que ya existe,
(3) crea el apartado y las relaciones. Un dato nuevo no vive solo: se conecta.

Acá vive el conocimiento del rubro: qué tipos hay, qué columnas los identifican,
con qué se relacionan y qué se ACTIVA cuando se conectan.
"""
from __future__ import annotations

import json
import os
import unicodedata

from . import paths
from . import store

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = paths.DATA_DIR  # por-tenant: env POLPILOT_DATA_DIR o data/ (ver core/paths.py)
APARTADOS_JSON = os.path.join(DATA_DIR, "apartados.json")

# El grafo: cada tipo, sus señales de columna, con qué se relaciona y qué activa.
TIPOS = {
    "producto": {
        "nombre": "Inventario",
        "senales": ["stock", "costo", "pvp", "precio de venta", "articulo", "producto", "deposito"],
        "relaciona_con": [],
        "activa": [],
    },
    "venta": {
        "nombre": "Ventas",
        "senales": ["fecha", "cantidad", "vendido", "venta", "kilos", "ticket", "comprobante"],
        "relaciona_con": ["producto", "cliente"],
        "activa": ["rotación por producto", "margen real por producto",
                   "alertas de quiebre de stock", "stock excedente liberable"],
    },
    "cliente": {
        "nombre": "Clientes",
        "senales": ["cliente", "razon social", "cuit", "localidad", "telefono"],
        "relaciona_con": ["venta"],
        "activa": ["ranking de clientes por volumen", "cuentas corrientes con nombre"],
    },
    "proveedor": {
        "nombre": "Proveedores",
        "senales": ["proveedor", "razon social", "cuit", "rubro proveedor"],
        "relaciona_con": ["producto"],
        "activa": ["costo de reposición por proveedor", "órdenes de pedido por proveedor"],
    },
    "cuenta_corriente": {
        "nombre": "Cuentas corrientes",
        "senales": ["saldo", "deuda", "vencimiento", "plazo", "dias", "mora"],
        "relaciona_con": ["cliente"],
        "activa": ["identificación de morosos (nombre, monto, días)", "alertas de cobro"],
    },
    # PolPilot NO es un WMS: lee el resultado del sistema de depósito (Faro u otro)
    # y lo vuelve consultable/alertable vía Ángela. La lógica de picking es de ellos.
    "deposito": {
        "nombre": "Depósito",
        "senales": ["ubicacion", "pasillo", "estanteria", "rack", "camara", "lote",
                    "partida", "vencimiento", "fisico"],
        "relaciona_con": ["producto"],
        "activa": ["consultas de ubicación por producto", "alertas de vencimiento próximo",
                   "discrepancias entre stock contable y físico"],
    },
    # El circuito de compra (P10): la foto del comprobante entra por visión y
    # persiste acá. La OC espera su remito; el remito mueve stock; la factura
    # golpea la cuenta del proveedor.
    "ordenes_compra": {
        "nombre": "Órdenes de compra",
        "senales": ["orden de compra", "nota de pedido", "oc "],
        "relaciona_con": ["proveedor", "producto"],
        "activa": ["control remito ↔ orden de compra al recibir mercadería"],
    },
    "recepciones": {
        "nombre": "Recepciones",
        "senales": ["recepcion", "remito", "recibido", "ingreso deposito"],
        "relaciona_con": ["proveedor", "producto", "ordenes_compra"],
        "activa": ["mercadería que entra al stock con control contra lo pedido"],
    },
    "compras": {
        "nombre": "Compras",
        "senales": ["factura", "cuit", "iva", "neto gravado", "comprobante compra"],
        "relaciona_con": ["proveedor", "recepciones"],
        "activa": ["cuenta corriente del proveedor (cuánto le debés y cuándo vence)"],
    },
    # Ídem con el TMS: leemos envíos/entregas, no optimizamos rutas.
    "logistica": {
        "nombre": "Logística",
        "senales": ["entrega", "envio", "reparto", "pedido", "direccion", "destino",
                    "transporte", "camion", "chofer", "fecha prevista", "remito"],
        "relaciona_con": ["cliente", "venta"],
        "activa": ["estado de envío por cliente", "alertas de entregas atrasadas",
                   "resumen del día de reparto"],
    },
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def detectar_tipo(headers: list[str]) -> dict:
    """Identifica el tipo de dato por sus columnas. Devuelve {tipo, confianza, ambiguo}."""
    h = " ".join(_norm(x) for x in headers)
    puntajes = {}
    for tipo, d in TIPOS.items():
        puntajes[tipo] = sum(1 for s in d["senales"] if s in h)
    mejor = max(puntajes, key=puntajes.get)
    top = puntajes[mejor]
    segundo = sorted(puntajes.values(), reverse=True)[1] if len(puntajes) > 1 else 0
    return {
        "tipo": mejor if top > 0 else "producto",
        "confianza": top,
        "ambiguo": top > 0 and top == segundo,
    }


# --- Apartados activos (qué secciones de datos existen en el tenant) ---

def _load() -> dict:
    try:
        return json.load(open(APARTADOS_JSON, encoding="utf-8"))
    except Exception:
        return {}


def _save(d: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(d, open(APARTADOS_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    # P11·B4: cualquier escritura de apartados (recepciones, compras, ventas,
    # staging integrado) invalida los análisis cacheados.
    from . import analisis_cache
    analisis_cache.datos_cambiaron()


def apartados_activos() -> list[str]:
    """Qué tipos de dato ya existen. 'producto' siempre (es el inventario base)."""
    return sorted({"producto", *_load().keys()})


def existe(tipo: str) -> bool:
    return tipo in apartados_activos()


def filas(tipo: str) -> list[dict]:
    """Las filas guardadas de un apartado (lista vacía si no existe)."""
    d = _load().get(tipo)
    return list(d.get("filas", [])) if d else []


def plan_integracion(tipo: str, lang: str | None = None) -> dict:
    """Qué va a pasar al integrar este tipo: apartado nuevo + relaciones + qué se activa.
    `lang` traduce lo VISIBLE (nombre, lista de qué activa); el tipo y las
    relaciones son IDs y no cambian. ES byte-igual a TIPOS (la fuente histórica)."""
    import i18n
    tkey = tipo if tipo in TIPOS else "producto"
    d = TIPOS[tkey]
    activos = apartados_activos()
    relaciones = [r for r in d["relaciona_con"] if r in activos]
    activa = ([i18n.t(f"core.esquema.activa_{tkey}_{i}", lang)
               for i in range(len(d["activa"]))]
              if relaciones or not d["relaciona_con"] else [])
    return {
        "tipo": tipo,
        "nombre": i18n.t(f"core.esquema.{tkey}", lang),
        "apartado_nuevo": tipo not in activos,
        "relaciona_con": relaciones,
        "activa": activa,
    }


def crear_apartado(tipo: str, filas: list[dict]) -> dict:
    """Crea (o mergea) el apartado y guarda sus filas. El sistema se expande solo."""
    data = _load()
    previas = data.get(tipo, {}).get("filas", [])
    data[tipo] = {"nombre": TIPOS.get(tipo, {}).get("nombre", tipo), "filas": previas + filas}
    _save(data)
    return {"tipo": tipo, "total": len(data[tipo]["filas"]), "nuevas": len(filas)}


def validar_referencias_producto(filas: list[dict]) -> dict:
    """Integridad referencial: cada fila debe referenciar un producto que exista
    (por código o por nombre). Las huérfanas se marcan (no se integran ciegas).
    Aplica a ventas, depósito y cualquier tipo que se relacione con producto."""
    codigos = {d.get("codigo") for d in store.raw_actual()}
    nombres = {_norm(d.get("descripcion")) for d in store.raw_actual()}
    huerfanas = []
    for i, f in enumerate(filas):
        cod = f.get("codigo")
        nom = _norm(f.get("producto") or f.get("descripcion"))
        if cod is not None and cod in codigos:
            continue
        if nom and nom in nombres:
            continue
        huerfanas.append(i)
    return {"huerfanas": huerfanas, "ok": len(filas) - len(huerfanas)}


# Nombre histórico (los primeros llamadores eran sólo de ventas).
validar_integridad_ventas = validar_referencias_producto
