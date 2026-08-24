"""
auditoria.py · EL REGISTRO, legible. Quién decidió qué, cuándo, y qué pasó después.

Esto NO calcula nada nuevo. `core/audit.py` viene guardando cada acción sobre
los datos desde el primer día (actor, acción, antes, después, cuándo) y todos
los bloques escriben ahí — cobranza, comprobantes, saneamiento, staging,
permisos. Lo que faltaba no era el dato: era poder LEERLO.

`/api/audit` devuelve el JSON crudo con slugs internos (`sanear_fantasma_custom`)
y sin orden. Sirve para depurar; no sirve para que un dueño de PyME entienda qué
hizo su asistente. Este módulo es la capa de lectura:

  · CLASIFICA cada acción por lo que TOCA (plata, datos, stock, permisos) y por
    CÓMO se ejecutó (aprobación de un humano / acto propio / automático).
  · TRADUCE el slug a una frase que se lee sin manual, en el idioma del que mira.
  · ENHEBRA: las acciones sobre el mismo cliente/archivo forman un hilo, así
    "le mandé el recordatorio" y "pagó" se leen como una historia y no como dos
    líneas sueltas. Eso es el "qué pasó después".

Los montos que salen acá son los que YA estaban guardados en el evento. No se
recomponen ni se recalculan: si un número no quedó escrito cuando pasó, acá no
aparece. Un registro de auditoría que estima es un registro que miente.

REGLA: agregar una acción auditada nueva al producto y NO declararla acá no
rompe nada — cae en la clase `otros` con su slug legible. Pero se nota, y hay un
test que lo mira.
"""
from __future__ import annotations

from . import fechas, store

# --- QUÉ TOCA cada acción, y CÓMO se ejecutó ---------------------------------
#
# clase → lo que la acción pone en juego. Es el eje del gate: `plata`, `stock` y
#   `permisos` no se ejecutan nunca sin un sí explícito.
# gate  → cómo llegó a ejecutarse:
#     "aprobacion" · un humano miró la propuesta y apretó. El actor ES el que aprobó.
#     "propia"     · la persona actuó sobre lo suyo (su foto, su idioma, su pedido).
#     "sistema"    · lo hizo PolPilot solo. Sólo se permite en lo reversible y
#                    sin criterio comercial (ver core/autonomia.py).
# reversible → tiene versión de respaldo y se deshace con un click.
CLASES = ("plata", "datos", "stock", "permisos", "perfil", "consulta", "tecnico", "otros")

ACCIONES: dict[str, dict] = {
    # --- plata: cobranza y precios. Nada de esto se ejecuta solo. -------------
    "cobranza_recordado":     {"clase": "plata", "gate": "aprobacion"},
    "cobranza_promesa":       {"clase": "plata", "gate": "aprobacion"},
    "cobranza_pagado":        {"clase": "plata", "gate": "aprobacion"},
    "cobranza_sin_respuesta": {"clase": "plata", "gate": "aprobacion"},
    "cobranza_pendiente":     {"clase": "plata", "gate": "aprobacion"},
    "corregir_precio_perdida": {"clase": "plata", "gate": "aprobacion", "reversible": True},
    "aplicar_lista_precios":   {"clase": "plata", "gate": "aprobacion", "reversible": True},
    # --- datos: lo que entra y lo que se limpia ------------------------------
    "cargar_remito":        {"clase": "datos", "gate": "aprobacion"},
    "cargar_factura":       {"clase": "datos", "gate": "aprobacion"},
    "cargar_recibo":        {"clase": "datos", "gate": "aprobacion"},
    "cargar_orden_compra":  {"clase": "datos", "gate": "aprobacion"},
    "integrar_staging":     {"clase": "datos", "gate": "aprobacion", "reversible": True},
    "validacion_montos_ventas": {"clase": "datos", "gate": "aprobacion"},
    "sanear_fantasma_custom":   {"clase": "datos", "gate": "aprobacion", "reversible": True},
    "revertir_version":     {"clase": "datos", "gate": "aprobacion", "reversible": True},
    "restaurar_version":    {"clase": "datos", "gate": "aprobacion", "reversible": True},
    "revertir_normalizacion_nivel1": {"clase": "datos", "gate": "aprobacion", "reversible": True},
    # La ÚNICA que hoy corre sola: normalización nivel 1 al entrar un archivo
    # (mayúsculas, espacios, separadores). No altera significado comercial y
    # queda con respaldo. Es el ejemplo vivo de autonomía graduada.
    "normalizacion_nivel1": {"clase": "datos", "gate": "sistema", "reversible": True},
    "crear_apartado":       {"clase": "datos", "gate": "sistema"},
    # --- stock y piso --------------------------------------------------------
    "preparar_orden_compra": {"clase": "stock", "gate": "aprobacion"},
    "reportar_faltante":  {"clase": "stock", "gate": "propia"},
    "marcar_conteo":      {"clase": "stock", "gate": "propia"},
    "confirmar_entrega":  {"clase": "stock", "gate": "propia"},
    "pedir_reposicion":   {"clase": "stock", "gate": "propia"},
    "registrar_pedido":   {"clase": "stock", "gate": "propia"},
    "resolver_reporte_piso": {"clase": "stock", "gate": "aprobacion"},
    # --- permisos: quién ve qué ---------------------------------------------
    "solicitar_modulo":          {"clase": "permisos", "gate": "propia"},
    "resolver_solicitud_modulo": {"clase": "permisos", "gate": "aprobacion"},
    "cambiar_modulo_empleado":   {"clase": "permisos", "gate": "aprobacion"},
    # el dueño moviendo la perilla de autonomía es, él mismo, una decisión que
    # hay que poder rastrear después (ver core/autonomia.py)
    "cambiar_autonomia_angela":  {"clase": "permisos", "gate": "aprobacion"},
    # --- perfil: lo de cada uno ---------------------------------------------
    "editar_descripcion_perfil": {"clase": "perfil", "gate": "propia"},
    "cambiar_foto_perfil":       {"clase": "perfil", "gate": "propia"},
    "cambiar_idioma":            {"clase": "perfil", "gate": "propia"},
    # --- sin efecto sobre los datos -----------------------------------------
    # Preguntarle algo a Ángela NO es una acción suya: no tocó nada. Queda
    # registrado (para eso está el registro) pero con su propio sello y fuera de
    # la vista por defecto — si no, noventa preguntas tapan las tres decisiones
    # que importan, que es exactamente el problema que este bloque ataca.
    "consulta_angela":    {"clase": "consulta", "gate": "sin_efecto"},
    "reset_demo_publico": {"clase": "tecnico", "gate": "sin_efecto"},
}

# Clases que NO se listan por defecto: no tocaron plata, stock ni datos. El chip
# sigue estando; el que las quiere ver las pide.
SIN_EFECTO = ("consulta", "tecnico")


def ficha(accion: str) -> dict:
    """Clase, gate y reversibilidad de una acción. Nunca falla: lo no declarado
    cae en `otros` con gate desconocido — visible, no escondido."""
    if accion in ACCIONES:
        f = ACCIONES[accion]
    elif (accion or "").startswith("sanear_"):
        # familia entera: una categoría del libro de calidad por slug
        f = {"clase": "datos", "gate": "aprobacion", "reversible": True}
    else:
        f = {"clase": "otros", "gate": "desconocido"}
    return {"clase": f["clase"], "gate": f["gate"],
            "reversible": bool(f.get("reversible"))}


# --- El hilo: acciones distintas sobre el MISMO sujeto ------------------------
# Un registro plano no responde "y después qué pasó". Con el sujeto (el cliente,
# el archivo, el producto, la persona) las líneas se enhebran solas.

def _sujeto(e: dict) -> str | None:
    for lado in (e.get("despues"), e.get("antes")):
        if not isinstance(lado, dict):
            continue
        for k in ("cliente", "proveedor", "usuario", "archivo", "batch",
                  "producto", "codigo", "local"):
            v = lado.get(k)
            if v:
                return str(v)
    return None


# --- El impacto: SOLO el que quedó escrito -----------------------------------
# Si el evento no guardó un monto, acá no hay monto. No se busca en otra fuente
# ni se estima: el número del registro tiene que ser el número de ese momento.

def _impacto(e: dict) -> float | None:
    for lado in (e.get("despues"), e.get("antes")):
        if not isinstance(lado, dict):
            continue
        for k in ("saldo", "impacto_pesos", "monto", "total"):
            v = lado.get(k)
            if isinstance(v, (int, float)) and v:
                return float(v)
    return None


def _frase(e: dict, lang: str | None) -> str:
    """El slug, en castellano (o inglés) de persona. Sin key pelado en pantalla."""
    import i18n
    accion = e.get("accion") or ""
    clave = f"audit.acc.{accion}"
    if clave in i18n.CATALOGO:
        return i18n.t(clave, lang)
    if accion.startswith("sanear_"):
        return i18n.t("audit.acc.sanear", lang,
                      cat=accion[len("sanear_"):].replace("_", " "))
    return i18n.t("audit.acc.generico", lang, accion=accion.replace("_", " "))


def registro(lang: str | None = None, clase: str | None = None,
             actor: str | None = None, desde: str | None = None,
             hasta: str | None = None, q: str | None = None,
             limite: int = 300) -> dict:
    """El historial completo, legible y filtrable. Más nuevo primero.

    `resumen` se cuenta SIEMPRE sobre el registro entero (no sobre el filtro):
    los totales de la cabecera no pueden bailar cuando alguien toca un chip."""
    hoy = fechas.hoy().isoformat()
    crudos = store.audit.list()

    filas = []
    for e in crudos:
        f = ficha(e.get("accion") or "")
        cuando = e.get("cuando") or ""
        filas.append({
            "id": e.get("id"),
            "accion": e.get("accion"),
            "texto": _frase(e, lang),
            "actor": e.get("actor"),
            "cuando": cuando,
            "dia": cuando[:10],
            "clase": f["clase"],
            "gate": f["gate"],
            "reversible": f["reversible"],
            # quién puso el sí. En este producto el que aprueba ES el actor:
            # la identidad sale del token, nunca del body (ver authz.py).
            "aprobado_por": e.get("actor") if f["gate"] == "aprobacion" else None,
            "sujeto": _sujeto(e),
            "impacto": _impacto(e),
            "antes": e.get("antes"),
            "despues": e.get("despues"),
        })

    # El resumen: sobre TODO, antes de filtrar.
    resumen = {
        "total": len(filas),
        "por_clase": {c: sum(1 for x in filas if x["clase"] == c) for c in CLASES},
        "aprobadas": sum(1 for x in filas if x["gate"] == "aprobacion"),
        "automaticas": sum(1 for x in filas if x["gate"] == "sistema"),
        "propias": sum(1 for x in filas if x["gate"] == "propia"),
        "reversibles": sum(1 for x in filas if x["reversible"]),
        # lo que se deja fuera de la lista por defecto, DICHO: un registro que
        # esconde filas sin avisar deja de ser un registro.
        "sin_efecto_ocultos": sum(1 for x in filas if x["clase"] in SIN_EFECTO),
        # el argumento de confianza, en un número: de todo lo que tocó plata,
        # stock o permisos, cuánto se ejecutó sin que un humano dijera que sí.
        "sensibles": sum(1 for x in filas if x["clase"] in ("plata", "stock", "permisos")),
        "sensibles_sin_aprobacion": sum(
            1 for x in filas
            if x["clase"] in ("plata", "stock", "permisos") and x["gate"] == "sistema"),
        "actores": sorted({x["actor"] for x in filas if x["actor"]}),
        "hoy": hoy,
    }

    # Los hilos se arman sobre TODO (si no, filtrar por clase cortaría la
    # historia justo donde se pone interesante).
    hilos: dict[str, int] = {}
    for x in filas:
        if x["sujeto"]:
            hilos[x["sujeto"]] = hilos.get(x["sujeto"], 0) + 1
    for x in filas:
        x["en_hilo"] = hilos.get(x["sujeto"] or "", 0) if x["sujeto"] else 0

    # --- filtros ------------------------------------------------------------
    if clase:
        filas = [x for x in filas if x["clase"] == clase]
    else:
        # sin filtro explícito, lo que no tocó nada no entra en la lista
        filas = [x for x in filas if x["clase"] not in SIN_EFECTO]
    if actor:
        filas = [x for x in filas if x["actor"] == actor]
    if desde:
        filas = [x for x in filas if x["dia"] >= desde]
    if hasta:
        filas = [x for x in filas if x["dia"] <= hasta]
    if q:
        aguja = q.strip().lower()
        filas = [x for x in filas
                 if aguja in (x["texto"] or "").lower()
                 or aguja in (x["sujeto"] or "").lower()
                 or aguja in (x["actor"] or "").lower()]

    filas.sort(key=lambda x: (x["cuando"] or "", x["id"] or 0), reverse=True)
    total_filtrado = len(filas)
    return {"eventos": filas[:limite], "mostrados": min(total_filtrado, limite),
            "total_filtrado": total_filtrado, "resumen": resumen}


def hilo(sujeto: str, lang: str | None = None) -> list[dict]:
    """La historia de UN sujeto, de lo más viejo a lo más nuevo: el
    "qué pasó después" leído de corrido."""
    todo = registro(lang=lang, limite=10_000)["eventos"]
    de_el = [x for x in todo if (x["sujeto"] or "").lower() == (sujeto or "").lower()]
    de_el.sort(key=lambda x: (x["cuando"] or "", x["id"] or 0))
    return de_el
