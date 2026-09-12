"""
Pagos y liquidez (capa sobre lo que la administración ya registra).

PolPilot NO es un sistema contable: lee lo que el negocio ya tiene anotado
(facturas de proveedores por pagar, cuotas de tarjeta por acreditar, cheques
en cartera) y lo vuelve consultable: qué vence, qué entra y cuándo.

Los datos viven en finanzas.json del DATA_DIR del tenant:
{pagos_proveedores: [{proveedor, numero, emision, vencimiento, monto, estado}],
 tarjeta_cuotas:    [{venta_semana, plan, acredita, monto}],
 cheques:           [{cliente, numero, banco, recibido, cobro, monto}]}
Sin archivo (el piloto todavía no cargó nada de esto) todo devuelve vacío:
las pantallas muestran su placeholder honesto, jamás un cero inventado.
"""
from __future__ import annotations

import json
import os

from . import paths, conocimiento
from .fechas import parse_fecha, hoy

VENCIMIENTO_ALERTA_DIAS = 7  # default de "vence pronto"


def _path() -> str:
    return os.path.join(paths.DATA_DIR, "finanzas.json")


def _seed_inicial() -> dict:
    if not os.path.exists(_path()):
        return {"pagos_proveedores": [], "tarjeta_cuotas": [], "cheques": []}
    try:
        with open(_path(), encoding="utf-8") as f:
            d = json.load(f)
        return {"pagos_proveedores": d.get("pagos_proveedores", []),
                "tarjeta_cuotas": d.get("tarjeta_cuotas", []),
                "cheques": d.get("cheques", [])}
    except Exception:
        return {"pagos_proveedores": [], "tarjeta_cuotas": [], "cheques": []}


def _load() -> dict:
    from core.db import blob_repo
    from core.db import tenant as _tenant
    tid = _tenant.current_tenant_id()
    data = blob_repo.get_blob("finance_data", tid)
    if data is None:
        data = _seed_inicial()
        blob_repo.save_blob("finance_data", tid, data)
    return data


# P24·F1 — la proyección 30/60/90 es TRABAJO de PolPilot, no data a cargar.
# Cobros esperados (saldos por cobrar, ubicados en el tiempo según el
# comportamiento histórico de pago de cada cliente) + acreditaciones conocidas
# (cuotas de tarjeta, cheques) − pagos conocidos (facturas de proveedor con su
# vencimiento). Los supuestos van DECLARADOS en el panel: proyección sobre
# plazos históricos de cobro; no incluye gastos no cargados.
def proyeccion_flujo(lang: str | None = None) -> dict:
    import i18n
    from . import cuentas as cuentas_mod
    from .fechas import hoy, parse_fecha
    d = _load()
    h = hoy()
    ventanas = {30: {"cobros": 0.0, "pagos": 0.0}, 60: {"cobros": 0.0, "pagos": 0.0},
                90: {"cobros": 0.0, "pagos": 0.0}}

    def _ventana(dias_hasta: float) -> int | None:
        for v in (30, 60, 90):
            if dias_hasta <= v:
                return v
        return None

    # cobros: cada saldo entra donde su comportamiento histórico lo pone
    try:
        clientes = cuentas_mod.listar()
    except Exception:  # noqa: BLE001
        clientes = []
    for c in clientes:
        saldo = c.get("saldo") or 0
        if saldo <= 0:
            continue
        prom = c.get("promedio_pago_dias") or c.get("plazo_dias") or 30
        dias_restantes = max(0, prom - (c.get("dias_sin_pagar") or 0))
        v = _ventana(dias_restantes)
        if v:
            ventanas[v]["cobros"] += saldo
    # acreditaciones conocidas (tarjeta y cheques ya cargados)
    for c in d["tarjeta_cuotas"]:
        f = parse_fecha(c.get("acredita"))
        if f:
            v = _ventana((f - h).days)
            if v:
                ventanas[v]["cobros"] += c.get("monto") or 0
    for ch in d["cheques"]:
        f = parse_fecha(ch.get("cobro") or ch.get("acredita") or ch.get("fecha"))
        if f:
            v = _ventana((f - h).days)
            if v:
                ventanas[v]["cobros"] += ch.get("monto") or 0
    # pagos conocidos (facturas de proveedor con vencimiento)
    for p in d["pagos_proveedores"]:
        if p.get("estado") == "pagado":
            continue
        f = parse_fecha(p.get("vencimiento"))
        if f:
            v = _ventana(max(0, (f - h).days))
            if v:
                ventanas[v]["pagos"] += p.get("monto") or 0

    filas, acumulado = [], 0.0
    for v in (30, 60, 90):
        neto = ventanas[v]["cobros"] - ventanas[v]["pagos"]
        acumulado += neto
        filas.append({"dias": v, "cobros": round(ventanas[v]["cobros"], 2),
                      "pagos": round(ventanas[v]["pagos"], 2),
                      "neto": round(neto, 2), "acumulado": round(acumulado, 2)})
    # Pieces 10/21/22 — lo que Aldo enseñó sobre la caja se declara como supuestos
    # de la proyección (plazo de pago de un proveedor, piso de sueldos, aguinaldo).
    piezas_caja = conocimiento.aplicables(nodo="caja")
    piso = next((p["params"]["piso"] for p in piezas_caja
                 if (p.get("params") or {}).get("piso")), None)
    return {"disponible": bool(clientes or hay_datos()),
            "ventanas": filas,
            "supuestos": i18n.t("core.pagos.proyeccion_supuestos", lang),
            "piso_caja": piso,
            "notas_conocimiento": [conocimiento.texto_en(p, lang) for p in piezas_caja],
            "conocimiento_aplicado": [conocimiento.resumen_pieza(p) for p in piezas_caja]}


def hay_datos() -> bool:
    d = _load()
    return bool(d["pagos_proveedores"] or d["tarjeta_cuotas"] or d["cheques"])


def pagos_vencidos() -> list[dict]:
    h = hoy()
    out = []
    for p in _load()["pagos_proveedores"]:
        v = parse_fecha(p.get("vencimiento"))
        if p.get("estado") == "pendiente" and v and v < h:
            out.append({**p, "dias_vencido": (h - v).days})
    return sorted(out, key=lambda x: x["dias_vencido"], reverse=True)


def pagos_por_vencer(dias: int = VENCIMIENTO_ALERTA_DIAS) -> list[dict]:
    h = hoy()
    out = []
    for p in _load()["pagos_proveedores"]:
        v = parse_fecha(p.get("vencimiento"))
        if p.get("estado") == "pendiente" and v and 0 <= (v - h).days <= dias:
            out.append({**p, "dias_restantes": (v - h).days})
    return sorted(out, key=lambda x: x["dias_restantes"])


def tarjeta_por_acreditar(dias: int = 30) -> list[dict]:
    """Cuotas de tarjeta que acreditan dentro de N días."""
    h = hoy()
    out = []
    for c in _load()["tarjeta_cuotas"]:
        a = parse_fecha(c.get("acredita"))
        if a and 0 <= (a - h).days <= dias:
            out.append({**c, "dias_restantes": (a - h).days})
    return sorted(out, key=lambda x: x["dias_restantes"])


def cheques_en_cartera() -> list[dict]:
    h = hoy()
    out = []
    for c in _load()["cheques"]:
        f = parse_fecha(c.get("cobro"))
        out.append({**c, "dias_para_cobro": (f - h).days if f else None})
    return sorted(out, key=lambda x: (x["dias_para_cobro"] is None, x["dias_para_cobro"]))


def resumen() -> dict:
    """Totales YA calculados por el core (regla B12: el modelo y la UI los
    repiten textuales, nunca los recalculan)."""
    d = _load()
    pendientes = [p for p in d["pagos_proveedores"] if p.get("estado") == "pendiente"]
    semana = pagos_por_vencer(7)
    tarj = tarjeta_por_acreditar(7)
    cheq = cheques_en_cartera()
    return {
        "hay_datos": hay_datos(),
        "por_pagar_total": round(sum(p["monto"] for p in pendientes), 2),
        "por_pagar_semana": round(sum(p["monto"] for p in semana), 2),
        "pagos_vencidos": len(pagos_vencidos()),
        "vencidos_total": round(sum(p["monto"] for p in pagos_vencidos()), 2),
        "tarjeta_7dias": round(sum(c["monto"] for c in tarj), 2),
        "cheques_cartera": len(cheq),
        "cheques_total": round(sum(c["monto"] for c in cheq), 2),
    }
