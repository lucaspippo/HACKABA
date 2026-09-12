"""
cobranza.py · A QUIÉN COBRAR PRIMERO, y en qué anda cada gestión.

`cuentas.py` ya calcula quién debe, hace cuántos días, y cuánto se corrió de SU
propio promedio (`atraso_vs_promedio`). Todo eso queda intacto: acá no se
recalcula la mora, se ACTÚA sobre ella.

Esto NO es credit scoring. No decide a quién darle crédito nuevo ni a quién
cortárselo — eso lo decide el dueño. Acá se ordena la deuda que YA existe y se
propone el recordatorio.

CÓMO SE PRIORIZA — la misma disciplina que el anti-quiebre: una fórmula que se
explica en una línea, no un puntaje de 0 a 100 que haya que justificar.

    exceso_dias = dias_sin_pagar − promedio_de_pago_de_ESE_cliente
    exposicion  = saldo × exceso_dias        (pesos × días)

Es la plata que te está financiando, por el tiempo que se pasó DE LO SUYO. Un
cliente que siempre paga a 60 y va por 65 casi no puntúa; uno que siempre paga
a 30 y va por 66 puntúa fuerte aunque deba menos. Esa es exactamente la
diferencia que el dueño hace de memoria, y que se pierde cuando la lista se
ordena por saldo.

Las unidades son peso-día: no se muestran, se usan para ordenar. Lo que se
muestra es el par que las produce ("$19,2M que deberías tener hace 35 días"),
que es lo que una persona entiende sin explicación.

QUÉ HACE ÁNGELA Y QUÉ HACE EL CÓDIGO:
  · el código: la mora, el exceso, el orden, los montos, la liquidez.
  · Ángela: el tono del mensaje y leer la respuesta del cliente ("me paga el
    viernes" → promesa). El texto es del agente; los números, del código.

Nada se envía solo: `proponer()` arma la propuesta y `registrar()` recién
existe cuando un humano aprobó.
"""
from __future__ import annotations

from . import cuentas, fechas, store

# Estados de una gestión. Deliberadamente pocos: cada uno tiene que significar
# algo distinto para el que mira la lista un lunes a la mañana.
ESTADOS = ("pendiente", "recordado", "promesa", "pagado", "sin_respuesta")


# --- LA DEUDA QUE SALE A LA CALLE HOY -------------------------------------------
# Hoy y mañana. Una parada se reasigna la tarde anterior; tres días adelante ya
# es planificación y no operación, y el aviso deja de ser accionable justo en el
# momento en que se lee.
VENTANA_RUTA_DIAS = 2


def exposicion_en_ruta(dias: int = VENTANA_RUTA_DIAS) -> list[dict]:
    """Por día de reparto y por camión: cuántas paradas y cuánta deuda llevan.

    El ERP sabe cuánto debe cada cliente y sabe qué pedido sale mañana. Lo que
    no hace nadie es LA SUMA POR CAMIÓN, y puesta así la decisión de operación
    se ve sola: o el que va lleva instrucciones, o algunas paradas cambian de
    camión. Es el mismo criterio del resto del módulo — la mora no se recalcula
    acá, se ORDENA por algo que el que la mira puede accionar; sólo que el
    ordenador no es el exceso de días sino dónde va a estar parado alguien.

    ESTO NO RECUPERA PLATA, LA HACE VISIBLE. `expuesto` es deuda que YA existe
    en la cuenta corriente. Cuánto de eso se cobra es trabajo de cobranza, no
    del software, y por eso la tarjeta que sale de acá viaja con
    `naturaleza="riesgo"`: se muestra, no se suma al capital recuperable (ver
    `oportunidades_neg.recuperable`, que es donde esa distinción ya vive).

    UN CLIENTE, UNA VEZ. El mismo cliente puede tener dos pedidos el mismo día
    y en el mismo camión — en el dataset del demo pasa: Supermercado El Puente
    tiene dos paradas el 08/07. Su saldo es UNO: se cuenta una sola vez por
    camión, y una sola vez en el total del día, donde además puede aparecer en
    dos camiones distintos. Sumar por parada infla el total sin que se note, y
    es exactamente el doble conteo que ya nos costó una vez.
    """
    from . import logistica
    if not logistica.hay_datos():
        return []
    try:
        por_nombre = {c["nombre"]: c for c in cuentas.listar()}
    except Exception:  # noqa: BLE001 — sin cuentas no hay exposición que sumar
        return []

    import datetime
    salida = []
    for i in range(max(1, dias)):
        dia = fechas.hoy() + datetime.timedelta(days=i)
        paradas = logistica.salidas(dia.isoformat())
        if not paradas:
            continue
        por_camion: dict[str, dict] = {}
        del_dia: dict[str, dict] = {}
        for p in paradas:
            transporte = p.get("transporte") or "?"
            cam = por_camion.setdefault(transporte, {
                "transporte": transporte, "paradas": 0, "clientes": {},
                "sin_cuenta": 0})
            cam["paradas"] += 1
            c = por_nombre.get(p.get("cliente"))
            if not c:
                # Un cliente sin cuenta corriente no es un error (contado,
                # mostrador). Se cuenta aparte para que el total no mienta por
                # omisión: "no debe nada" y "no sé" no son lo mismo.
                cam["sin_cuenta"] += 1
                continue
            cam["clientes"][c["nombre"]] = c
            del_dia[c["nombre"]] = c

        camiones = []
        for cam in por_camion.values():
            cs = list(cam["clientes"].values())
            camiones.append({
                "transporte": cam["transporte"],
                "paradas": cam["paradas"],
                "clientes": len(cs),
                "sin_cuenta": cam["sin_cuenta"],
                "expuesto": round(sum(c["saldo"] for c in cs), 2),
                "vencidos": [
                    {"cliente": c["nombre"], "id": c.get("id"),
                     "saldo": c["saldo"],
                     "dias_sin_pagar": c.get("dias_sin_pagar"),
                     "plazo_dias": c.get("plazo_dias"),
                     # La regla de la casa ("a X tolerale N días") ya viene
                     # aplicada por cuentas._enriquecer: acá sólo se pasa.
                     "exceso_tolerancia": c.get("exceso_tolerancia")}
                    for c in sorted(cs, key=lambda x: -x["saldo"])
                    if c.get("en_mora")],
            })
        camiones.sort(key=lambda d: -d["expuesto"])
        salida.append({
            "dia": dia.isoformat(),
            "paradas": len(paradas),
            "clientes": len(del_dia),
            "expuesto": round(sum(c["saldo"] for c in del_dia.values()), 2),
            "camiones": camiones,
        })
    return salida


def peor_camion(dias: int = VENTANA_RUTA_DIAS) -> dict | None:
    """El par (día, camión) con más plata en la calle. None si no hay nada."""
    peor = None
    for d in exposicion_en_ruta(dias):
        for cam in d["camiones"]:
            if cam["expuesto"] <= 0:
                continue
            if not peor or cam["expuesto"] > peor["expuesto"]:
                peor = {**cam, "dia": d["dia"]}
    return peor


def _load() -> dict:
    from core.db import blob_repo
    from core.db import tenant as _tenant
    return blob_repo.get_blob("collection_actions", _tenant.current_tenant_id()) or {}


def _save(d: dict) -> None:
    from core.db import blob_repo
    from core.db import tenant as _tenant
    blob_repo.save_blob("collection_actions", _tenant.current_tenant_id(), d)


def gestion_de(cliente_id: str) -> dict:
    g = _load().get(cliente_id) or {}
    return {"estado": g.get("estado", "pendiente"),
            "cuando": g.get("cuando"), "promesa_fecha": g.get("promesa_fecha"),
            "nota": g.get("nota"), "actor": g.get("actor")}


def prioridad() -> dict:
    """El orden de cobranza + la liquidez que entra si se cobra.

    Sin idioma: son números y nombres propios."""
    morosos = cuentas.morosos()
    hoy = fechas.hoy()
    items = []
    for c in morosos:
        prom = c.get("promedio_pago_dias") or c.get("plazo_dias") or 30
        dias = c.get("dias_sin_pagar") or 0
        exceso = max(0, dias - prom)
        saldo = float(c.get("saldo") or 0)
        g = gestion_de(c["id"])
        items.append({
            "id": c["id"], "cliente": c["nombre"], "saldo": saldo,
            "dias_sin_pagar": dias, "plazo_dias": c.get("plazo_dias"),
            "promedio_pago_dias": prom,
            "exceso_dias": exceso,
            "atraso_vs_promedio": c.get("atraso_vs_promedio"),
            "score": c.get("score"),
            # la clave de orden: plata × días de más. No se muestra.
            "exposicion": round(saldo * exceso, 2),
            "gestion": g,
        })
    # primero la exposición; a igualdad, el que más se corrió de lo suyo
    items.sort(key=lambda x: (-x["exposicion"], -(x["atraso_vs_promedio"] or 0)))

    total = cuentas.totales()
    pendientes = [x for x in items if x["gestion"]["estado"] in ("pendiente", "sin_respuesta")]
    promesas = [x for x in items if x["gestion"]["estado"] == "promesa"]
    return {
        "disponible": bool(items),
        "items": items,
        "panorama": _panorama(items, pendientes, promesas),
        # LIQUIDEZ, con lo que ya hay: si se cobra lo priorizado, esto entra.
        # No es una proyección — es la suma de saldos que hoy están vencidos.
        "entra_si_cobras": round(sum(x["saldo"] for x in items), 2),
        "entra_si_cobras_pendientes": round(sum(x["saldo"] for x in pendientes), 2),
        "prometido": round(sum(x["saldo"] for x in promesas), 2),
        "promesas_vencidas": sum(
            1 for x in promesas
            if x["gestion"].get("promesa_fecha")
            and str(x["gestion"]["promesa_fecha"]) < hoy.isoformat()),
        "total_adeudado": total.get("total_adeudado"),
        "total_morosos": total.get("total_morosos"),
        "resumen_estados": {e: sum(1 for x in items if x["gestion"]["estado"] == e)
                            for e in ESTADOS},
    }


def _panorama(items: list[dict], pendientes: list[dict], promesas: list[dict]) -> dict:
    """LA VISTA DEL DUEÑO sobre la misma lista. El preventista necesita saber a
    quién visita hoy; el dueño necesita saber dónde está parada la plata y quién
    la está trabajando. Son la misma tabla mirada desde dos alturas.

    Todo se deriva de `items` — que ya salió de cuentas.py. Cero fuente nueva,
    cero número que no se pueda rastrear hasta un saldo real.
    """
    if not items:
        return {"disponible": False}
    exp_total = sum(x["exposicion"] for x in items)
    # "Los tres primeros explican el 100%" no es un hallazgo: es que hay tres.
    # Con pocas cuentas la concentración se cuenta sobre el primero, que sí dice
    # algo ("uno solo es la mitad de tu exposición"). El corte es el tamaño de
    # la lista, no una preferencia de copy.
    cabeza = items[:3] if len(items) > 3 else items[:1]
    sin_tocar = [x for x in items if x["gestion"]["estado"] == "pendiente"]
    en_gestion = [x for x in items
                  if x["gestion"]["estado"] in ("recordado", "promesa")]
    cobrados = [x for x in items if x["gestion"]["estado"] == "pagado"]
    # quién está trabajando cada cuenta: sale del `actor` que quedó auditado al
    # registrar la gestión. Si nadie la tocó, nadie la está trabajando.
    por_actor: dict[str, dict] = {}
    for x in items:
        a = x["gestion"].get("actor")
        if not a:
            continue
        f = por_actor.setdefault(a, {"actor": a, "cuentas": 0, "saldo": 0.0})
        f["cuentas"] += 1
        f["saldo"] = round(f["saldo"] + x["saldo"], 2)
    return {
        "disponible": True,
        # concentración: si unos pocos nombres explican la mitad de la
        # exposición, la estrategia no es "cobrar mejor", es hablar con ellos.
        "concentracion_n": len(cabeza),
        "concentracion_saldo": round(sum(x["saldo"] for x in cabeza), 2),
        "concentracion_share": round(100 * sum(x["exposicion"] for x in cabeza) / exp_total, 1)
                               if exp_total else 0.0,
        "concentracion_nombres": [x["cliente"] for x in cabeza],
        # el estado de la GESTIÓN, en plata (no en cantidad de fichas)
        "sin_tocar": len(sin_tocar),
        "sin_tocar_saldo": round(sum(x["saldo"] for x in sin_tocar), 2),
        "en_gestion": len(en_gestion),
        "en_gestion_saldo": round(sum(x["saldo"] for x in en_gestion), 2),
        "cobrado": len(cobrados),
        "cobrado_saldo": round(sum(x["saldo"] for x in cobrados), 2),
        "pendientes_cuentas": len(pendientes),
        "promesas_cuentas": len(promesas),
        "quien_trabaja": sorted(por_actor.values(), key=lambda f: -f["saldo"]),
        # los días de más, promediados: cuánto se le corrió la cobranza al
        # negocio entero respecto de su propia costumbre.
        "exceso_dias_promedio": round(
            sum(x["exceso_dias"] for x in items) / len(items), 1),
    }


def proponer(cliente_id: str, lang: str | None = None) -> dict | None:
    """El recordatorio LISTO PARA MANDAR, con los números del cliente. No manda
    nada: devuelve la propuesta para que un humano la apruebe o la edite.

    El borrador sale del template determinista de `cuentas.mensaje_cobro` a
    propósito: en cámara dice siempre lo mismo y funciona sin red. Si el dueño
    quiere otro tono, se lo pide a Ángela y edita — el campo es editable."""
    c = cuentas.get(cliente_id)
    if not c:
        return None
    msg = cuentas.mensaje_cobro(cliente_id, lang) or {}
    prom = c.get("promedio_pago_dias") or c.get("plazo_dias") or 30
    return {
        "id": cliente_id,
        "cliente": c["nombre"],
        "saldo": c["saldo"],
        "dias_sin_pagar": c["dias_sin_pagar"],
        "exceso_dias": max(0, (c.get("dias_sin_pagar") or 0) - prom),
        "promedio_pago_dias": prom,
        "atraso_vs_promedio": c.get("atraso_vs_promedio"),
        "mensaje": msg.get("mensaje", ""),
        "gestion": gestion_de(cliente_id),
    }


def registrar(cliente_id: str, estado: str, actor: str = "dueño",
              nota: str | None = None, promesa_fecha: str | None = None,
              mensaje: str | None = None) -> dict:
    """El SÍ del humano queda escrito y auditado. Recién acá existe la gestión.

    `mensaje` se guarda tal como se mandó (con las ediciones del dueño): sin
    eso, "le mandé un recordatorio" no es verificable."""
    if estado not in ESTADOS:
        raise ValueError(f"estado desconocido: {estado!r}")
    c = cuentas.get(cliente_id)
    if not c:
        raise KeyError("cliente inexistente")
    if promesa_fecha and not fechas.parse_fecha(promesa_fecha):
        raise ValueError("fecha de promesa ilegible")

    d = _load()
    antes = d.get(cliente_id, {}).get("estado", "pendiente")
    d[cliente_id] = {"estado": estado, "cuando": fechas.hoy().isoformat(),
                     "actor": actor, "nota": nota,
                     "promesa_fecha": promesa_fecha,
                     "mensaje": mensaje}
    _save(d)
    # mismo riel de auditoría que el resto de la casa
    store.audit.record(actor=actor, accion=f"cobranza_{estado}",
                       antes={"cliente": c["nombre"], "estado": antes},
                       despues={"cliente": c["nombre"], "estado": estado,
                                "saldo": c["saldo"],
                                "promesa_fecha": promesa_fecha})
    return {"ok": True, "id": cliente_id, "cliente": c["nombre"],
            "gestion": gestion_de(cliente_id)}
