from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Categoria(str, Enum):
    FANTASMA = "fantasma"
    NEGATIVO = "negativo"
    SIN_PRECIO = "sin_precio"
    BALANZA = "balanza"
    COSTO_VIEJO = "costo_viejo"


class EstadoCalidad(str, Enum):
    COMPLETO = "completo"
    INCONSISTENTE = "inconsistente"
    MAL_CONFIGURADO = "mal_configurado"
    INCOMPLETO = "incompleto"
    DESACTUALIZADO = "desactualizado"


# Mayor número = peor (define el color/estado general del registro).
PRIORIDAD = {
    EstadoCalidad.INCONSISTENTE: 4,
    EstadoCalidad.MAL_CONFIGURADO: 3,
    EstadoCalidad.INCOMPLETO: 2,
    EstadoCalidad.DESACTUALIZADO: 1,
    EstadoCalidad.COMPLETO: 0,
}

CATEGORIA_ESTADO = {
    Categoria.FANTASMA: EstadoCalidad.INCONSISTENTE,
    Categoria.NEGATIVO: EstadoCalidad.INCONSISTENTE,
    Categoria.BALANZA: EstadoCalidad.MAL_CONFIGURADO,
    Categoria.SIN_PRECIO: EstadoCalidad.INCOMPLETO,
    Categoria.COSTO_VIEJO: EstadoCalidad.DESACTUALIZADO,
}

CATEGORIA_LABEL = {
    Categoria.FANTASMA: "Anulado con stock vivo",
    Categoria.NEGATIVO: "Stock negativo (el sistema miente)",
    Categoria.SIN_PRECIO: "Sin precio de venta cargado",
    Categoria.BALANZA: "Balanza con peso fuera de rango",
    Categoria.COSTO_VIEJO: "Costo desactualizado (+1 año)",
}


@dataclass
class Articulo:
    codigo: int
    descripcion: str
    estado: str  # "activo" | "anulado"
    stock: float = 0.0
    costo_iva: float | None = None
    pvp: float | None = None
    venta_x_peso: bool = False
    cota_inf: float | None = None
    cota_sup: float | None = None
    valor_peso: float | None = None
    antiguedad_costo_dias: float | None = None
    inmovilizado: float = 0.0
    sku: str | None = None
    source: str | None = None
    source_id: str | None = None
    free_qty: float | None = None
    incoming_qty: float | None = None
    outgoing_qty: float | None = None
    pricing_status: str | None = None
    precio_lista: float | None = None
    moneda: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "Articulo":
        return cls(
            codigo=int(d["codigo"]),
            descripcion=d["descripcion"],
            estado=d.get("estado", "activo"),
            stock=d.get("stock") or 0.0,
            costo_iva=d.get("costo_iva"),
            pvp=d.get("pvp"),
            venta_x_peso=bool(d.get("venta_x_peso")),
            cota_inf=d.get("cota_inf"),
            cota_sup=d.get("cota_sup"),
            valor_peso=d.get("valor_peso"),
            antiguedad_costo_dias=d.get("antiguedad_costo_dias"),
            inmovilizado=d.get("inmovilizado") or 0.0,
            sku=d.get("sku"),
            source=d.get("source"),
            source_id=d.get("source_id"),
            free_qty=d.get("free_qty"),
            incoming_qty=d.get("incoming_qty"),
            outgoing_qty=d.get("outgoing_qty"),
            pricing_status=d.get("pricing_status"),
            precio_lista=d.get("precio_lista"),
            moneda=d.get("moneda"),
        )


@dataclass
class Issue:
    codigo: int
    categoria: Categoria
    estado: EstadoCalidad
    impacto_pesos: float
    detalle: str
