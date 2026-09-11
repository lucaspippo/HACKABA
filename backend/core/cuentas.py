"""
Plan 6 · Cuentas corrientes de clientes (deudores) con IA.

Reemplaza el Excel de morosos del dueño. Cada cliente tiene su cuenta: saldo,
límite de crédito, historial y comportamiento de pago. Ángela alerta sobre los
que se atrasan, calcula scoring crediticio y propone recordatorios.

Hoy sembrado con datos demo de Horizonte (incluye el moroso de $30M / 45 días).
Cuando llegue el Excel real o la conexión con Faro, se importa por la Staging Area.
"""
from __future__ import annotations

import json
import os

from . import paths
from . import fechas
from . import conocimiento

# Datos demo de la distribuidora (saldo en $, días desde la última cancelación).
_SEED = [
    {"id": "perez", "nombre": "Almacén Don Pérez", "saldo": 30_000_000, "limite_credito": 32_000_000,
     "plazo_dias": 30, "dias_sin_pagar": 45, "promedio_pago_dias": 30,
     "movimientos": [
         {"fecha": "2026-05-13", "tipo": "venta", "monto": 18_000_000, "detalle": "Pedido mensual"},
         {"fecha": "2026-05-28", "tipo": "venta", "monto": 12_000_000, "detalle": "Reposición"},
     ]},
    {"id": "elcerdito", "nombre": "Fiambrería El Cerdito", "saldo": 2_800_000, "limite_credito": 2_000_000,
     "plazo_dias": 15, "dias_sin_pagar": 60, "promedio_pago_dias": 22,
     "movimientos": [
         {"fecha": "2026-04-28", "tipo": "venta", "monto": 1_500_000, "detalle": "Fiambres"},
         {"fecha": "2026-05-10", "tipo": "venta", "monto": 1_300_000, "detalle": "Quesos"},
     ]},
    {"id": "gonzalez", "nombre": "Despensa González", "saldo": 4_200_000, "limite_credito": 6_000_000,
     "plazo_dias": 30, "dias_sin_pagar": 38, "promedio_pago_dias": 34,
     "movimientos": [
         {"fecha": "2026-05-20", "tipo": "venta", "monto": 4_200_000, "detalle": "Pedido quincenal"},
     ]},
    {"id": "laesquina", "nombre": "Kiosco La Esquina", "saldo": 850_000, "limite_credito": 2_000_000,
     "plazo_dias": 30, "dias_sin_pagar": 12, "promedio_pago_dias": 18,
     "movimientos": [
         {"fecha": "2026-06-15", "tipo": "venta", "monto": 850_000, "detalle": "Golosinas y bebidas"},
     ]},
    {"id": "sancayetano", "nombre": "Minimercado San Cayetano", "saldo": 1_500_000, "limite_credito": 4_000_000,
     "plazo_dias": 30, "dias_sin_pagar": 5, "promedio_pago_dias": 20,
     "movimientos": [
         {"fecha": "2026-06-22", "tipo": "venta", "monto": 1_500_000, "detalle": "Almacén"},
     ]},
    {"id": "larural", "nombre": "Proveeduría La Rural", "saldo": 0, "limite_credito": 5_000_000,
     "plazo_dias": 30, "dias_sin_pagar": 0, "promedio_pago_dias": 25, "movimientos": []},
]


def _seed_inicial() -> list[dict]:
    """El dataset REAL del tenant si existe en disco (p.ej. data-demo/cuentas.json,
    generado por data-demo/generar.py — la fuente de los números canónicos del
    demo), usado SOLO para la siembra inicial en Postgres (una vez por tenant,
    ver customer_accounts_repo.seed_if_empty). _SEED de más arriba es el
    fallback de un tenant sin dataset propio todavía (piloto de test)."""
    cuentas_json = os.path.join(paths.DATA_DIR, "cuentas.json")
    if not os.path.exists(cuentas_json):
        return _SEED
    try:
        return json.load(open(cuentas_json, encoding="utf-8"))
    except Exception:
        return _SEED


def _load() -> list[dict]:
    from core.db import customer_accounts_repo, tenant as _tenant
    tid = _tenant.current_tenant_id()
    customer_accounts_repo.seed_if_empty(tid, _seed_inicial())
    return customer_accounts_repo.list_accounts(tid)


def _save(clientes: list[dict]) -> None:
    from core.db import customer_accounts_repo, tenant as _tenant
    tid = _tenant.current_tenant_id()
    for c in clientes:
        customer_accounts_repo.upsert_account(tid, c)
    # P11·B4: un cobro/venta cambia morosos y objetivos → análisis cacheados afuera.
    from . import analisis_cache
    analisis_cache.datos_cambiaron()


def _enriquecer(c: dict) -> dict:
    """P25·B3 — el score COMBINA atraso vs plazo Y desvío vs el comportamiento
    histórico del cliente (el promedio sale de su historial real de pagos):
    riesgoso = muy pasado del plazo (>1.5×), sobre el límite, o pagando ≥80%
    más tarde que SU propio promedio. El chip y la explicación salen de los
    MISMOS campos: no pueden divergir."""
    plazo = c.get("plazo_dias", 30)
    dias = c.get("dias_sin_pagar", 0)
    prom = c.get("promedio_pago_dias") or plazo
    en_mora = c["saldo"] > 0 and dias > plazo
    atraso = round((dias - prom) / prom * 100) if prom and dias > prom else 0
    if dias > plazo * 1.5 or c["saldo"] > c.get("limite_credito", 0) or \
       (en_mora and atraso >= 80):
        score = "riesgoso"
    elif en_mora:
        score = "atencion"
    else:
        score = "confiable"
    # Piece 1 — la regla de Aldo ("a X tolerale N días") reencuadra el atraso:
    # el 113% NO desaparece, pero además se lee contra el límite tolerado
    # (66 días: 21 más que los 45 que le tolerás). Efecto de redacción; el
    # cálculo del atraso vs promedio queda intacto.
    tol, exceso, piezas_tol = None, None, []
    for p in conocimiento.para(c.get("nombre"), nodo="clientes", tipo="regla"):
        t = (p.get("params") or {}).get("tolerancia_dias")
        if t:
            tol = int(t)
            piezas_tol.append(p)
    if tol is not None and dias > tol:
        exceso = dias - tol
    return {
        **c,
        "en_mora": en_mora,
        "score": score,
        "disponible": max(0, c.get("limite_credito", 0) - c["saldo"]),
        "atraso_vs_promedio": atraso,
        **({"tolerancia_dias": tol, "exceso_tolerancia": exceso,
            "conocimiento": [conocimiento.resumen_pieza(p) for p in piezas_tol]}
           if exceso is not None else {}),
    }


def listar() -> list[dict]:
    """Deudores ordenados por monto (de mayor a menor)."""
    return sorted((_enriquecer(c) for c in _load()), key=lambda c: c["saldo"], reverse=True)


def get(cliente_id: str) -> dict | None:
    c = next((x for x in _load() if x["id"] == cliente_id), None)
    return _enriquecer(c) if c else None


def buscar(nombre: str) -> dict | None:
    n = (nombre or "").lower().strip()
    for c in _load():
        if n and n in c["nombre"].lower():
            return _enriquecer(c)
    return None


def morosos() -> list[dict]:
    return [c for c in listar() if c["en_mora"]]


def hay_datos_reales() -> bool:
    """¿Las cuentas de este tenant son datos DE VERDAD o el seed de fábrica?
    El piloto arranca con _SEED (demo de Horizonte): eso no cuenta como
    'cuentas cargadas' — cuando entre el Excel real (ids distintos) pasa solo
    a True. El dataset del demo (clientes del Litoral) ya es la verdad del
    tenant, así que da True."""
    clientes = _load()
    return bool(clientes) and {c["id"] for c in clientes} != {c["id"] for c in _SEED}


def alertas() -> dict:
    """Para el Inicio: los morosos son alertas de negocio reales."""
    m = morosos()
    return {"cantidad": len(m), "impacto_pesos": round(sum(c["saldo"] for c in m), 2)}


def totales() -> dict:
    """P11·B12: los agregados monetarios los calcula EL CORE, una sola vez.
    El modelo los repite textuales — jamás suma la lista él mismo (en cámara
    ese total tiene que ser idéntico las tres veces que se pregunte)."""
    clientes = listar()
    mor = [c for c in clientes if c["en_mora"]]
    return {
        "total_adeudado": round(sum(c["saldo"] for c in clientes), 2),
        "clientes_con_deuda": sum(1 for c in clientes if c["saldo"] > 0),
        "total_morosos": round(sum(c["saldo"] for c in mor), 2),
        "cantidad_morosos": len(mor),
    }


def scoring_venta(nombre: str, monto: float = 0, lang: str | None = None) -> dict:
    """¿Cuánto se le puede vender a crédito a este cliente?"""
    import i18n
    c = buscar(nombre)
    if not c:
        return {"conocido": False,
                "mensaje": i18n.t("core.cuentas.scoring_desconocido", lang, nombre=nombre)}
    disp = c["disponible"]
    if monto and monto > disp:
        return {"conocido": True, "cliente": c["nombre"], "disponible": disp, "autoriza": False,
                "mensaje": i18n.t("core.cuentas.scoring_supera", lang, nombre=c["nombre"],
                                  disp=i18n.pesos(disp, lang), monto=i18n.pesos(monto, lang))}
    detalle = i18n.t(f"core.cuentas.score_{c['score']}", lang)
    return {"conocido": True, "cliente": c["nombre"], "disponible": disp, "score": c["score"], "autoriza": True,
            "mensaje": i18n.t("core.cuentas.scoring_ok", lang, nombre=c["nombre"],
                              detalle=detalle, disp=i18n.pesos(disp, lang))}


def mensaje_cobro(cliente_id: str, lang: str | None = None) -> dict | None:
    """Redacta el recordatorio de cobro para que el dueño lo mande por su
    canal (WhatsApp cuando esté conectado; hoy se copia). No es PDF."""
    import i18n
    c = get(cliente_id)
    if not c:
        return None
    extra = (i18n.t("core.cuentas.cobro_extra", lang, prom=c["promedio_pago_dias"],
                    atraso=c["atraso_vs_promedio"])
             if c["atraso_vs_promedio"] > 0 else "")
    from . import paths
    return {
        "cliente": c["nombre"],
        "mensaje": i18n.t("core.cuentas.cobro_mensaje", lang,
                          empresa=paths.NOMBRE_CORTO,
                          saldo=i18n.pesos(c["saldo"], lang),
                          dias=c["dias_sin_pagar"], extra=extra),
    }


def registrar_cobro(cliente_id: str, monto: float, medio: str = "transferencia") -> dict:
    from core.db import customer_accounts_repo, tenant as _tenant

    clientes = _load()
    c = next((x for x in clientes if x["id"] == cliente_id), None)
    if not c:
        raise KeyError("cliente inexistente")
    c["saldo"] = max(0, c["saldo"] - monto)
    c["dias_sin_pagar"] = 0
    c.setdefault("movimientos", []).append({"fecha": fechas.hoy().isoformat(), "tipo": "cobro",
                                            "monto": monto, "detalle": "Cobro"})

    tid = _tenant.current_tenant_id()
    customer_accounts_repo.upsert_account(tid, c)
    customer_accounts_repo.add_movement(tid, cliente_id, c["movimientos"][-1])
    from . import analisis_cache
    analisis_cache.datos_cambiaron()

    # El grafo propaga: un cobro de cuenta corriente es plata que entra a la caja del día.
    # Best-effort: si la caja está cerrada o falla, no rompemos el cobro (que ya se guardó).
    try:
        from . import caja
        if caja.estado().get("abierta"):
            caja.movimiento("ingreso", medio, float(monto), f"Cobro cta. cte. {c['nombre']}")
    except Exception:
        pass
    return _enriquecer(c)


def estado_cuenta(cliente_id: str, lang: str | None = None) -> dict:
    """Documento PDF: estado de cuenta del cliente."""
    import i18n
    c = get(cliente_id)
    if not c:
        raise ValueError("cliente inexistente")
    # P18·B — franja honesta: con UN movimiento por cliente no hay aging
    # 30/60/90 defendible; sí hay verdad de "al día vs vencido" (plazo).
    vencido = c["saldo"] if c["en_mora"] else 0
    al_dia = c["saldo"] - vencido
    # La línea de LECTURA de Ángela: comportamiento histórico vs atraso actual.
    if c["saldo"] and c["atraso_vs_promedio"] > 0:
        lectura = i18n.t("core.cuentas.ec_lectura_atraso", lang,
                         prom=c["promedio_pago_dias"], pct=c["atraso_vs_promedio"])
        if c.get("exceso_tolerancia") is not None:  # Piece 1 — reencuadre vs tolerancia
            lectura += " " + i18n.t("core.cuentas.ec_lectura_tolerancia", lang,
                                    dias=c["dias_sin_pagar"], tol=c["tolerancia_dias"],
                                    exceso=c["exceso_tolerancia"])
    elif c["saldo"]:
        lectura = i18n.t("core.cuentas.ec_lectura_normal", lang,
                         prom=c["promedio_pago_dias"])
    else:
        lectura = i18n.t("core.cuentas.ec_lectura_al_dia", lang)
    return {
        "tipo": "estado_cuenta",
        "titulo": i18n.t("core.cuentas.ec_titulo", lang, nombre=c["nombre"]),
        "subtitulo": f"{paths.EMPRESA} · {fechas.hoy().strftime('%d/%m/%Y')}",
        "veredicto": lectura,
        "conocimiento_aplicado": c.get("conocimiento") or [],
        "kpis": [
            {"label": i18n.t("core.cuentas.ec_kpi_saldo", lang),
             "valor": i18n.pesos(c["saldo"], lang)},
            {"label": i18n.t("core.cuentas.ec_kpi_vencido", lang),
             "valor": i18n.pesos(vencido, lang)},
            {"label": i18n.t("core.cuentas.ec_kpi_al_dia", lang),
             "valor": i18n.pesos(al_dia, lang)},
            {"label": i18n.t("core.cuentas.ec_kpi_dias", lang),
             "valor": str(c["dias_sin_pagar"])},
            {"label": i18n.t("core.cuentas.ec_kpi_limite", lang),
             "valor": i18n.pesos(c["disponible"], lang)},
        ],
        "tablas": [{
            "titulo": i18n.t("core.cuentas.ec_movimientos", lang),
            "columnas": [i18n.t("core.cuentas.ec_col_fecha", lang),
                         i18n.t("core.cuentas.ec_col_tipo", lang),
                         i18n.t("core.cuentas.ec_col_monto", lang)],
            "filas": [[m["fecha"], m["tipo"], i18n.pesos(m["monto"], lang)]
                      for m in c.get("movimientos", [])],
        }],
        "nota": i18n.t("core.cuentas.ec_nota", lang,
                       score=i18n.t(f"core.cuentas.score_id_{c['score']}", lang),
                       plazo=c["plazo_dias"]),
    }
