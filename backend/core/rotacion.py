"""
Rotación y stock excedente — lógica estándar de gestión de inventario.

Hoy el inmovilizado es todo el stock × costo (inmovilizado). Cuando lleguen las ventas
históricas, este módulo separa lo que el negocio NECESITA tener de lo que tiene
DE MÁS (excedente liberable). La fórmula está implementada y testeada; corre en
modo dry-run (devuelve `disponible: False`) hasta que se cargue el CSV de ventas.

Definiciones (estándar de inventory management):
  demanda_diaria      = unidades_vendidas_periodo / días_del_periodo
  stock_seguridad     = demanda_diaria × días_de_reposición (lead time del proveedor)
  stock_necesario     = demanda_diaria × días_de_cobertura_objetivo (incluye seguridad)
  stock_excedente     = max(0, stock_actual − stock_necesario)
  plata_excedente     = stock_excedente × costo_unitario   ← el número de oro
"""
from __future__ import annotations

DIAS_REPOSICION_DEFAULT = 7      # cuánto tarda el proveedor en reponer
DIAS_COBERTURA_DEFAULT = 30      # stock objetivo que se quiere tener a mano


def metricas_articulo(
    stock_actual: float,
    costo_unitario: float,
    unidades_vendidas: float,
    dias_periodo: int,
    dias_reposicion: int = DIAS_REPOSICION_DEFAULT,
    dias_cobertura: int = DIAS_COBERTURA_DEFAULT,
) -> dict:
    demanda_diaria = (unidades_vendidas / dias_periodo) if dias_periodo > 0 else 0.0
    stock_seguridad = demanda_diaria * dias_reposicion
    stock_necesario = demanda_diaria * dias_cobertura
    stock_excedente = max(0.0, stock_actual - stock_necesario)
    return {
        "demanda_diaria": round(demanda_diaria, 3),
        "stock_seguridad": round(stock_seguridad, 1),
        "stock_necesario": round(stock_necesario, 1),
        "stock_excedente": round(stock_excedente, 1),
        "plata_excedente": round(stock_excedente * (costo_unitario or 0), 2),
    }


def analizar(articulos: list[dict], ventas_por_codigo: dict | None = None,
             dias_periodo: int = 0) -> dict:
    """Separa el inmovilizado total en excedente vs. necesario.
    En dry-run (sin ventas) devuelve disponible=False con el total parado."""
    total_parado = round(sum(a.get("inmovilizado") or 0 for a in articulos), 2)
    if not ventas_por_codigo or dias_periodo <= 0:
        return {
            "disponible": False,
            "motivo": "faltan ventas históricas",
            "inmovilizado_total": total_parado,
            "explicacion": "Cuando cargues tus ventas históricas, separo cuánto de esto es "
                           "excedente real (plata liberable) y cuánto necesitás tener sí o sí.",
        }

    excedente = 0.0
    necesario = 0.0
    for a in articulos:
        m = metricas_articulo(
            a.get("stock") or 0, a.get("costo_iva") or 0,
            ventas_por_codigo.get(a.get("codigo"), 0), dias_periodo,
        )
        excedente += m["plata_excedente"]
        necesario += (a.get("inmovilizado") or 0) - m["plata_excedente"]
    return {
        "disponible": True,
        "inmovilizado_total": total_parado,
        "plata_excedente": round(excedente, 2),
        "plata_necesaria": round(max(0.0, necesario), 2),
    }
