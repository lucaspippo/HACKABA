"""
traslados.py — separar la mercadería que se mueve de la que se VENDE.

Cuando la distribuidora manda mercadería a sus propios locales, el ERP lo
registra como venta: hay remito, hay precio de lista, hay salida de depósito.
Contablemente puede estar bien; para decidir está mal. Consecuencias reales que
el dueño ve todos los días y no sabe explicar:

  · un local propio aparece entre sus "mejores clientes",
  · el ranking de más vendidos lo encabeza lo que se manda en bulto a la
    góndola, no lo que le compran los clientes.

Este módulo lee esos movimientos y arma las DOS lecturas: la cruda (como sale
del ERP) y la real (sólo venta a clientes externos). El resto del sistema ya
trabaja con la real — las ventas de `esquema.filas("venta")` nunca incluyeron
estos movimientos. Acá se hace visible la diferencia.
"""
from __future__ import annotations

import datetime
import json
import os

from . import esquema, fechas, paths

TRASLADOS_JSON = os.path.join(paths.DATA_DIR, "traslados_internos.json")


def _load() -> dict:
    try:
        with open(TRASLADOS_JSON, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:  # noqa: BLE001
        return {}


def hay_datos() -> bool:
    return bool(_load().get("filas"))


def filas() -> list[dict]:
    return list(_load().get("filas") or [])


def locales_propios() -> list[str]:
    return list(_load().get("locales_propios") or [])


def _monto(f: dict) -> float:
    return float(f.get("cantidad") or 0) * float(f.get("precio") or 0)


def resumen(lang: str | None = None) -> dict:
    """Lo que se movió a locales propios en 12 meses y en qué deforma las
    estadísticas. Sin traslados cargados, `disponible=False`: nada que separar."""
    if not hay_datos():
        return {"disponible": False}
    from . import cuentas
    hoy = fechas.hoy()
    corte = (hoy - datetime.timedelta(days=365)).isoformat()

    # --- lo movido a los locales propios ---------------------------------------
    por_local: dict[str, dict] = {}
    u_traslado: dict[str, float] = {}
    total = 0.0
    for f in filas():
        if (f.get("fecha") or "") < corte:
            continue
        m = _monto(f)
        total += m
        d = por_local.setdefault(f.get("destino") or "?", {"monto": 0.0, "movimientos": 0})
        d["monto"] += m
        d["movimientos"] += 1
        prod = f.get("producto") or ""
        u_traslado[prod] = u_traslado.get(prod, 0.0) + float(f.get("cantidad") or 0)
    if total <= 0:
        return {"disponible": False}

    # --- la venta REAL, por producto (unidades: así se lee "lo más vendido") ---
    u_real: dict[str, float] = {}
    for f in esquema.filas("venta"):
        if f.get("codigo") is None or (f.get("fecha") or "") < corte:
            continue
        prod = f.get("producto") or ""
        u_real[prod] = u_real.get(prod, 0.0) + float(f.get("cantidad") or 0)

    real = sorted(u_real.items(), key=lambda kv: -kv[1])
    pos_real = {p: i + 1 for i, (p, _) in enumerate(real)}
    crudo_map = dict(u_real)
    for p, u in u_traslado.items():
        crudo_map[p] = crudo_map.get(p, 0.0) + u
    crudo = sorted(crudo_map.items(), key=lambda kv: -kv[1])

    # El producto que MÁS sube de puesto por culpa del traslado: ése es el que
    # el dueño ve arriba de su ranking sin entender por qué.
    distorsionado = None
    for i, (prod, u) in enumerate(crudo[:20], 1):
        pr = pos_real.get(prod)
        if pr is None or prod not in u_traslado:
            continue
        salto = pr - i
        if distorsionado is None or salto > distorsionado["salto"]:
            distorsionado = {
                "producto": prod, "pos_crudo": i, "pos_real": pr, "salto": salto,
                "unidades_crudo": round(u, 1),
                "unidades_real": round(u_real.get(prod, 0.0), 1),
                "unidades_traslado": round(u_traslado[prod], 1),
            }

    # --- el local que se cuela en el ranking de clientes -----------------------
    locales = sorted(por_local.items(), key=lambda kv: -kv[1]["monto"])
    top_local = {"local": locales[0][0], **locales[0][1]} if locales else None
    superados = []
    if top_local:
        try:
            for c in cuentas.listar():
                fact = sum(float(m.get("monto") or 0) for m in (c.get("movimientos") or [])
                           if m.get("tipo") == "venta" and (m.get("fecha") or "") >= corte)
                if fact > 0:
                    superados.append({"cliente": c["nombre"], "monto": round(fact, 2)})
        except Exception:  # noqa: BLE001
            superados = []
        superados.sort(key=lambda c: -c["monto"])
        # dónde entraría el local propio si fuera un cliente más
        puesto = 1 + sum(1 for c in superados if c["monto"] > top_local["monto"])
        top_local["puesto_como_cliente"] = puesto
        top_local["monto"] = round(top_local["monto"], 2)
        # a QUIÉN desplaza: el cliente real que quedaría justo debajo. Sin esto
        # el copy compara contra el #1 y dice una mentira ("arriba de X" cuando
        # X está arriba). None si entra último y no desplaza a nadie.
        top_local["desplaza"] = (superados[puesto - 1]["cliente"]
                                 if len(superados) >= puesto else None)

    return {
        "disponible": True,
        "total_12m": round(total, 2),
        "movimientos": sum(d["movimientos"] for d in por_local.values()),
        "locales": [{"local": n, "monto": round(d["monto"], 2),
                     "movimientos": d["movimientos"]} for n, d in locales],
        "top_local": top_local,
        "clientes_reales": superados[:5],
        "distorsionado": distorsionado,
        "ranking_crudo": [{"producto": p, "unidades": round(u, 1)} for p, u in crudo[:8]],
        "ranking_real": [{"producto": p, "unidades": round(u, 1)} for p, u in real[:8]],
    }
