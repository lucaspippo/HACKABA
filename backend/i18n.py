"""
i18n del backend — UN catálogo para todo texto que un usuario puede leer.

Convención de la casa (desde el prompt 8): todo string nuevo que llegue a un
humano NACE BILINGÜE — entra acá en "es" y "en" el mismo día. Los keys internos
(features, tools, rutas, categorías) NO se traducen: son identificadores.

Uso:
    from i18n import t
    t("authz.sin_acceso", lang, modulo="cuentas")

Reglas:
  - `lang` viene SIEMPRE del backend (perfiles.idioma_de(username) o
    paths.DEFAULT_LANG del tenant) — nunca del body del cliente, para que el
    idioma no sea spoofeable y Ángela le hable a cada uno en su idioma también
    por canales sin interfaz (WhatsApp mañana).
  - Default 'es': el piloto y los tests existentes no cambian de comportamiento.
  - Key faltante en 'en' → cae a 'es' (nunca revienta, nunca muestra el key pelado
    si existe en algún idioma; si no existe en ninguno, devuelve el key para que
    el bug se VEA en pantalla y se arregle).

El tono: el "es" es el criollo cálido de siempre; el "en" es plain-spoken de
negocio con la misma personalidad — nunca corporativo acartonado.
"""
from __future__ import annotations

from core import paths

# TODO(i18n direction) — UI-facing copy should move to the frontend.
#
# The mainstream shape for a web app is: the server ships keys + params, the
# client renders with Intl (plurals, dates, currency are locale rules the
# browser already implements, and this module hand-rolls them in Python).
#
# What blocks a straight migration: Ángela and external MCP clients consume
# FINISHED sentences and will never run frontend/src/lib/locales/. The
# narrative templates here are also coupled to the calculations they explain
# (see core.opn.qi_q1b), so they are authored next to the code that computes
# their numbers, not as UI chrome.
#
# The agreed split (docs/superpowers/specs/2026-09-01-structured-insight-
# contract-design.md, §"i18n direction"):
#   - narrative sentences (pattern, hypothesis, method labels) stay here;
#   - raw numbers ship as typed data and are formatted client-side;
#   - section headings, badge labels and button copy belong in the frontend
#     locales — move them as they are touched.

CATALOGO: dict[str, dict[str, str]] = {
    # --- authz / errores transversales -----------------------------------------
    "authz.sin_token": {
        "es": "Falta identificarse: entrá de nuevo.",
        "en": "You need to sign in again.",
    },
    "authz.token_vencido": {
        "es": "Se venció tu sesión. Entrá de nuevo.",
        "en": "Your session expired. Sign in again.",
    },
    "authz.solo_dueno": {
        "es": "Sólo el dueño puede hacer esto.",
        "en": "Only the owner can do this.",
    },
    "authz.sin_modulo": {
        "es": "Tu rol no tiene acceso a este módulo. Pedíselo al dueño desde tu perfil.",
        "en": "Your role doesn't have access to this module. Ask the owner from your profile.",
    },
    # --- perfil / idioma --------------------------------------------------------
    "perfil.solo_propio": {
        "es": "Sólo podés editar tu propio perfil.",
        "en": "You can only edit your own profile.",
    },
    "perfil.idioma_invalido": {
        "es": "Ese idioma no lo hablo (todavía). Valen: {validos}.",
        "en": "I don't speak that language (yet). Valid: {validos}.",
    },
    # --- authz.py (dependencias de acceso) ---------------------------------------
    "authz.iniciar_sesion": {
        "es": "Necesitás iniciar sesión.",
        "en": "You need to sign in.",
    },
    "authz.sin_feature": {
        "es": "Tu rol no tiene acceso al módulo «{feature}».",
        "en": "Your role doesn't have access to the «{feature}» module.",
    },
    # --- api / main.py (detail de HTTPException que ve un humano) -----------------
    "api.sesion_invalida": {
        "es": "Sesión inválida.",
        "en": "Invalid session.",
    },
    "api.sesion_requerida": {
        "es": "Necesitás iniciar sesión para hablar con Ángela.",
        "en": "You need to sign in to talk to Ángela.",
    },
    "api.login_incorrecto": {
        "es": "Usuario o contraseña incorrectos.",
        "en": "Wrong username or password.",
    },
    "api.nada_que_reclamar": {
        "es": "No hay faltantes para reclamar en este remito.",
        "en": "There are no shortfalls to claim on this delivery note.",
    },
    "api.usuario_inexistente": {
        "es": "usuario inexistente",
        "en": "no such user",
    },
    "api.cliente_inexistente": {
        "es": "cliente inexistente",
        "en": "no such customer",
    },
    "api.empleado_inexistente": {
        "es": "empleado inexistente",
        "en": "no such employee",
    },
    "api.notificacion_inexistente": {
        "es": "notificación inexistente",
        "en": "no such notification",
    },
    "api.patron_inexistente": {
        "es": "Ese hallazgo ya no está activo (puede que alguien ya haya opinado sobre él).",
        "en": "That finding isn't live anymore (someone may have already given feedback on it).",
    },
    "api.recordatorio_ajeno": {
        "es": "Esa tarea es de otra persona.",
        "en": "That task belongs to someone else.",
    },
    "api.recordatorio_inexistente": {
        "es": "recordatorio inexistente",
        "en": "no such reminder",
    },
    "api.descripcion_vacia": {
        "es": "La descripción está vacía.",
        "en": "The description is empty.",
    },
    "api.recordatorio_vacio": {
        "es": "El recordatorio está vacío.",
        "en": "The reminder is empty.",
    },
    "api.archivo_vacio": {
        "es": "El archivo está vacío.",
        "en": "The file is empty.",
    },
    "api.contenido_vacio": {
        "es": "El contenido está vacío.",
        "en": "The content is empty.",
    },
    # --- P39 · lo que el piso reporta y el cruce que produce -------------------
    "core.piso.motivo_roto": {
        "es": "{n} rotas / falladas",
        "en": "{n} broken / damaged",
    },
    "core.piso.motivo_faltante": {
        "es": "faltan {n}",
        "en": "{n} missing",
    },
    "core.piso.motivo_vencido": {
        "es": "{n} vencidas o por vencer",
        "en": "{n} expired or about to",
    },
    "core.piso.motivo_no_pedido": {
        "es": "{n} que no habíamos pedido",
        "en": "{n} we didn't order",
    },
    "core.piso.prov_desconocido": {
        "es": "Proveedor sin identificar",
        "en": "Unidentified supplier",
    },
    "core.piso.reclamo_t": {
        "es": "Reclamarle a {proveedor} la mercadería que no llegó bien",
        "en": "Claim the goods that arrived wrong from {proveedor}",
    },
    "core.piso.reclamo_r": {
        "es": "{quien} reportó {n} diferencias desde el depósito. Está sin reclamar.",
        "en": "{quien} reported {n} discrepancies from the warehouse. Nobody has claimed it yet.",
    },
    "core.piso.reclamo_r_1": {
        "es": "{quien} reportó una diferencia desde el depósito. Está sin reclamar.",
        "en": "{quien} reported a discrepancy from the warehouse. Nobody has claimed it yet.",
    },
    "core.piso.reclamo_q1": {
        "es": "{quien} reportó {n} diferencias con mercadería de {proveedor}. "
              "A tu costo de catálogo son {monto}.",
        "en": "{quien} reported {n} discrepancies with goods from {proveedor}. "
              "At your catalog cost that's {monto}.",
    },
    "core.piso.reclamo_q1_1": {
        "es": "{quien} reportó una diferencia con mercadería de {proveedor}. "
              "A tu costo de catálogo son {monto}.",
        "en": "{quien} reported one discrepancy with goods from {proveedor}. "
              "At your catalog cost that's {monto}.",
    },
    "core.piso.reclamo_q2": {
        "es": "No toqué el stock ni le escribí a nadie: esto es lo que reportó el "
              "piso, cruzado con tus costos. El reclamo lo mandás vos.",
        "en": "I didn't touch stock and I didn't write to anyone: this is what the "
              "floor reported, crossed with your costs. Sending the claim is your call.",
    },
    "core.piso.reclamo_q3": {
        "es": "Lo controlé contra la orden de compra {oc}, que está abierta.",
        "en": "I checked it against purchase order {oc}, which is still open.",
    },
    "core.piso.reclamo_chat": {
        "es": "Armame el reclamo a {proveedor} por la mercadería que llegó mal",
        "en": "Draft the claim to {proveedor} for the goods that arrived wrong",
    },
    "core.piso.reclamo_s1": {
        "es": "Valorizado al costo de catálogo de hoy; la nota de crédito real la "
              "define el proveedor.",
        "en": "Valued at today's catalog cost; the actual credit note is up to the "
              "supplier.",
    },
    "core.piso.f_reportes": {
        "es": "reportes del depósito",
        "en": "warehouse reports",
    },
    "core.piso.f_stock": {"es": "costos del catálogo", "en": "catalog costs"},
    "core.piso.f_oc": {"es": "órdenes de compra abiertas", "en": "open purchase orders"},
    "core.method.floor_report_claim": {
        "es": "Cantidad reportada por el equipo × costo de catálogo del producto.",
        "en": "Quantity reported by the team × the product's catalog cost."},
    "core.method.floor_report_po_check": {
        "es": "Controlado contra la orden de compra abierta de ese proveedor.",
        "en": "Checked against that supplier's open purchase order."},
    "api.reporte_inexistente": {
        "es": "ese reporte no existe",
        "en": "no such report",
    },
    "api.modulo_no_pedible": {
        "es": "Ese módulo no se pide: viene de fábrica o lo maneja el dueño.",
        "en": "That module can't be requested: it's built in or the owner handles it.",
    },
    "api.grupo_desconocido": {
        "es": "Grupo desconocido: {nombre}",
        "en": "Unknown group: {nombre}",
    },
    "api.sin_foto": {
        "es": "sin foto",
        "en": "no photo",
    },
    "api.sin_mostrador": {
        "es": "Este negocio no tiene locales propios cargados.",
        "en": "This business has no own stores on file.",
    },
    "api.oc_preparada": {
        "es": "Listo: dejé la orden {numero} para {proveedor} en borrador, "
              "firmada por vos. No sale hasta que la mandes.",
        "en": "Done: I left order {numero} for {proveedor} as a draft, signed by "
              "you. It doesn't go out until you send it.",
    },
    "api.pdf_no_disponible": {
        "es": "El render de PDF no está disponible en este servidor (faltan librerías del sistema).",
        "en": "PDF rendering isn't available on this server (missing system libraries).",
    },
    "api.pdf_error": {
        "es": "No pude generar el PDF. Probá de nuevo en un momento.",
        "en": "I couldn't generate the PDF. Try again in a moment.",
    },
    "api.solo_preferencias": {
        "es": "Sólo podés ver tus propias preferencias.",
        "en": "You can only see your own preferences.",
    },
    "api.conocimiento_inexistente": {
        "es": "Ese conocimiento no existe o no es de tu ámbito.",
        "en": "That knowledge doesn't exist or isn't in your scope.",
    },
    "api.version_inexistente": {
        "es": "Versión inexistente: {version_id}",
        "en": "No such version: {version_id}",
    },
    "api.whatsapp_sin_cuenta": {
        "es": "Tu número no está asociado a ninguna cuenta de PolPilot. "
              "Pedile al dueño que te dé de alta.",
        "en": "Your number isn't linked to any PolPilot account. "
              "Ask the owner to set you up.",
    },
    # --- modulo.* labels (auth.MODULOS traducidos; el ES es el default del dict) --
    # --- notificaciones del sistema (localizadas al idioma del RECEPTOR) -----
    "notif.solicitud_titulo": {
        "es": "{nombre} pide un módulo nuevo",
        "en": "{nombre} is asking for a new module",
    },
    "notif.solicitud_cuerpo": {
        "es": "{nombre} actualizó su descripción de rol. Ángela sugiere habilitarle: {label}.",
        "en": "{nombre} updated their role description. Ángela suggests enabling: {label}.",
    },
    # P39·1.2 — el empleado pide con SUS palabras; el dueño decide con el porqué
    # a la vista (aprobarlo tilda la celda en «Quién ve qué»).
    "notif.solicitud_cuerpo_pedido": {
        "es": "{nombre} pide acceso a {label} para trabajar. Dice: «{motivo}»",
        "en": "{nombre} is asking for access to {label} to do their job. They say: “{motivo}”",
    },
    "modulo.panel": {"es": "Panel principal", "en": "Main panel"},
    "modulo.mapa": {"es": "El mapa de tu negocio", "en": "Your Business Map"},
    "modulo.inventario": {"es": "Inventario inteligente", "en": "Smart inventory"},
    "modulo.saneamiento": {"es": "Saneamiento de datos", "en": "Data cleanup"},
    "modulo.finanzas": {"es": "Caja y finanzas", "en": "Cash & finance"},
    "modulo.cuentas": {"es": "Cuentas corrientes", "en": "Customer accounts"},
    "modulo.caja": {"es": "Caja diaria", "en": "Daily register"},
    "modulo.documentos": {"es": "Documentos", "en": "Documents"},
    "modulo.alertas": {"es": "Alertas", "en": "Alerts"},
    "modulo.oportunidades": {"es": "Oportunidades", "en": "Opportunities"},
    "modulo.equipo": {"es": "Mi equipo", "en": "My team"},
    "modulo.cargar": {"es": "Cargar datos", "en": "Load data"},
    "modulo.gestion_equipo": {"es": "Gestión de equipo (maestro)",
                              "en": "Team management (master)"},
    "modulo.cobranzas": {"es": "Cobranzas", "en": "Collections"},
    "modulo.auditoria": {"es": "Registro de auditoría", "en": "Audit trail"},
    "modulo.conectores": {"es": "Conectores", "en": "Connectors"},

    # --- P45·T1 · la plata parada que la rotación no puede clasificar ----------
    "core.analisis.sin_clasificar": {
        "es": "Anulados con stock vivo: la mercadería está, pero el sistema los "
              "dio de baja y no hay ventas con las que medirles la rotación.",
        "en": "Voided items still holding stock: the goods are there, but the "
              "system retired them and there are no sales to measure turnover against.",
    },

    # --- P43·C5.3 · el label de un PDF ya generado, en el idioma del que MIRA ---
    # El `titulo` guardado queda congelado (es el nombre del archivo, escrito en
    # el idioma del PDF); esto es sólo la etiqueta de la lista. Las keys son las
    # de core/documentos.generar().
    "doc.tipo.resumen_ejecutivo": {"es": "Resumen ejecutivo de inventario",
                                   "en": "Inventory executive summary"},
    "doc.tipo.reporte_cierres": {"es": "Cierres por local",
                                 "en": "Register closings by store"},
    "doc.tipo.orden_pedido": {"es": "Orden de pedido a proveedor",
                              "en": "Purchase order to supplier"},
    "doc.tipo.carta": {"es": "Carta", "en": "Letter"},
    "doc.tipo.estado_cuenta": {"es": "Estado de cuenta", "en": "Account statement"},
    "modulo.administracion": {"es": "Administración", "en": "Administration"},
    "modulo.deposito": {"es": "Depósito", "en": "Warehouse"},
    "modulo.logistica": {"es": "Logística y reparto", "en": "Logistics & delivery"},
    "modulo.evolucion": {"es": "Evolución (histórico ajustado por inflación)",
                         "en": "Evolution (inflation-adjusted history)"},
    "modulo.perfil": {"es": "Mi perfil", "en": "My profile"},
    "modulo.angela": {"es": "Ángela", "en": "Ángela"},
    "modulo.admin_contexto": {"es": "Contexto externo (admin)",
                              "en": "External context (admin)"},
    # --- fb.* · router simulado de Ángela (_fallback) ------------------------------
    # El ES es EXACTAMENTE el texto histórico (fuente de verdad del tono).
    # fb: transversales
    "fb.bloqueado": {
        "es": "Esa consulta es del área de {feature}, que no está dentro de lo "
              "que manejo para tu rol. Si lo necesitás, hablalo con el dueño o con "
              "quien esté a cargo.",
        "en": "That question belongs to the {feature} area, which isn't part of "
              "what I handle for your role. If you need it, talk to the owner or "
              "whoever's in charge.",
    },
    "fb.offtopic": {
        "es": "Eso está fuera de lo que manejo para tu negocio, pero sobre tu empresa "
              "—inventario, plata parada, precios, tu equipo— te ayudo con lo que necesites.",
        "en": "That's outside what I handle for your business, but on your company "
              "—inventory, idle money, prices, your team— I'll help with whatever you need.",
    },
    # Guardarrailes demo pública (P9·F): desvío de UNA línea, con la
    # personalidad de la casa, sin tools y sin gastar tokens.
    "fb.jailbreak": {
        "es": "Soy Ángela — me ocupo solo de la operación de este negocio. "
              "Preguntame por stock, plata, clientes o el equipo.",
        "en": "I'm Ángela — I only handle this business's operations. "
              "Ask me about stock, money, customers or the team.",
    },
    "angela.cap_alcanzado": {
        "es": "Esta sesión de demo llegó a su límite de chat — recargá la página "
              "para arrancar una nueva.",
        "en": "This demo session reached its chat limit — refresh to start a new one.",
    },
    # Comprobantes por foto (P10) — chequeos, cruces y sync simulado.
    "core.comp.chk_suma": {
        "es": "La suma de los ítems no cierra contra el total declarado "
              "(difiere {pct}%). {pista}",
        "en": "The line items don't add up to the declared total "
              "(off by {pct}%). {pista}",
    },
    # --- La voz del piso ------------------------------------------------------
    "core.voz.sin_audio": {
        "es": "No me llegó ningún audio.",
        "en": "No audio reached me.",
    },
    "core.voz.sin_transcriptor": {
        "es": "No pude escuchar el audio en este equipo. Contame por escrito y lo cargo igual.",
        "en": "I couldn't listen to the audio on this device. Type it out and I'll load it just the same.",
    },
    "core.voz.sin_producto": {
        "es": "Dijiste «{dicho}» y no encuentro ese producto en tu catálogo. "
              "Elegilo vos y lo anoto.",
        "en": "You said “{dicho}” and I can't find that product in your catalog. "
              "Pick it and I'll note it.",
    },
    "core.voz.varios_productos": {
        "es": "Hay {n} productos que pueden ser el que dijiste. Marcá cuál es — "
              "esto mueve stock y no lo elijo yo.",
        "en": "There are {n} products that could be the one you said. Mark which — "
              "this moves stock and I don't pick it myself.",
    },
    "core.voz.falta_producto": {
        "es": "No te entendí de qué producto hablás.",
        "en": "I didn't catch which product you mean.",
    },
    "core.voz.falta_cantidad": {
        "es": "No te entendí cuántos. Poné el número y listo.",
        "en": "I didn't catch how many. Enter the number and that's it.",
    },
    "core.voz.dudoso": {
        "es": "El audio no se entiende del todo — revisá lo que puse antes de confirmar.",
        "en": "The audio isn't fully clear — check what I filled in before confirming.",
    },
    "core.voz.confirmado": {
        "es": "Anotado. El dueño lo ve en Equipo.",
        "en": "Noted. The owner sees it under Team.",
    },
    "core.voz.bloqueado": {
        "es": "Falta resolver {n} cosa(s) antes de que pueda anotar esto.",
        "en": "{n} thing(s) still need sorting before I can note this.",
    },

    # --- El borde: números que vienen de una máquina (visión o voz) ---------
    "core.val.fecha_locale": {
        "es": "En el papel dice «{texto}» — o sea {correcta}, no {modelo}. "
              "Las fechas acá se escriben día/mes/año; la tomo del papel.",
        "en": "The paper says “{texto}” — that's {correcta}, not {modelo}. "
              "Dates here are written day/month/year; I'm taking the paper's.",
    },
    "core.val.cant_escala_oc": {
        "es": "«{producto}»: dice {recibido} y habías pedido {pedido} — es "
              "exactamente {factor} veces. Eso no es mercadería de más ni de "
              "menos: es el separador de miles leído mal. Confirmame el número.",
        "en": "“{producto}”: it says {recibido} and you ordered {pedido} — exactly "
              "{factor}× off. That's not extra or missing goods: it's the thousands "
              "separator misread. Confirm the number for me.",
    },
    "core.val.cant_decimal": {
        "es": "«{producto}» se vende por unidad y dice {cantidad}. Una unidad "
              "no viene partida: puede ser un «1.234» leído como 1,234.",
        "en": "“{producto}” is sold by unit and it says {cantidad}. A unit doesn't "
              "come in fractions: this could be “1,234” read as 1.234.",
    },
    "core.val.cant_magnitud": {
        "es": "«{producto}»: {cantidad} cuando de este producto suelen entrar "
              "{tipico}. Puede estar bien, pero mejor mirarlo.",
        "en": "“{producto}”: {cantidad} when this product usually comes in at "
              "{tipico}. Might be right, but worth a look.",
    },
    "core.val.cant_invalida": {
        "es": "«{producto}»: cantidad {cantidad}. No puedo ingresar eso al stock.",
        "en": "“{producto}”: quantity {cantidad}. I can't take that into stock.",
    },
    "core.val.cant_ilegible": {
        "es": "«{producto}»: no pude leer la cantidad. Escribila vos.",
        "en": "“{producto}”: I couldn't read the quantity. Type it yourself.",
    },
    "core.val.bloqueado": {
        "es": "No cargo nada todavía: hay {n} cantidad(es) que no me cierran. "
              "Corregilas arriba y volvé a confirmar.",
        "en": "I'm not loading anything yet: {n} quantity(ies) don't add up. "
              "Fix them above and confirm again.",
    },
    "core.comp.reclamo_prop": {
        "es": "Faltan {n} ítem(s) de lo que pediste. ¿Le reclamo a {proveedor}?",
        "en": "{n} item(s) short of what you ordered. Shall I claim it from {proveedor}?",
    },
    "core.comp.reclamo_hecho": {
        "es": "Anotado: {n} faltante(s) de {proveedor} quedaron para reclamar. "
              "Los vas a ver agrupados en Equipo, con el monto.",
        "en": "Noted: {n} shortfall(s) from {proveedor} queued for claiming. "
              "You'll see them grouped under Team, with the amount.",
    },
    "core.comp.chk_prov_parecido": {
        "es": "«{nombre}» se parece a tu proveedor «{conocido}» — ¿es el mismo? "
              "Mejor confirmarlo antes de crear un duplicado.",
        "en": "“{nombre}” looks like your supplier “{conocido}” — same one? "
              "Better to confirm before creating a duplicate.",
    },
    "core.comp.chk_prov_nuevo": {
        "es": "«{nombre}» no está entre tus proveedores conocidos: sería un alta nueva.",
        "en": "“{nombre}” isn't among your known suppliers: this would be a new one.",
    },
    "core.comp.chk_precio": {
        "es": "El precio de «{producto}» (${precio}) está muy lejos del costo de "
              "catálogo (${costo}): puede ser un error de escala.",
        "en": "The price for “{producto}” (${precio}) is way off the catalog "
              "cost (${costo}): could be a scale error.",
    },
    "core.comp.recibo_sin_cliente": {
        "es": "No encuentro al cliente «{nombre}» en las cuentas corrientes: "
              "no cargo el cobro a ciegas.",
        "en": "I can't find customer “{nombre}” in accounts receivable: "
              "I won't log the payment blindly.",
    },
    "vision.formato": {
        "es": "Ese archivo no es una imagen que pueda leer (JPG, PNG o WebP).",
        "en": "That file isn't an image I can read (JPG, PNG or WebP).",
    },
    "vision.tamano": {
        "es": "La imagen pasa el límite de 5 MB — sacale una foto más liviana.",
        "en": "The image is over the 5 MB limit — try a lighter photo.",
    },
    "vision.sin_api": {
        "es": "Para leer fotos necesito la conexión con Claude, y acá no está activa.",
        "en": "Reading photos needs the Claude connection, and it isn't active here.",
    },
    "vision.fallo": {
        "es": "No pude leer la foto ahora — probá de nuevo en un momento.",
        "en": "I couldn't read the photo just now — try again in a moment.",
    },
    "vision.no_es_comprobante": {
        "es": "Eso no parece un comprobante — probá con una foto de una factura de proveedor.",
        "en": "That doesn't look like an invoice — try a photo of a supplier invoice.",
    },
    "vision.ilegible": {
        "es": "La foto está muy borrosa para leerla con confianza — sacale otra con más luz y de frente.",
        "en": "The photo is too blurry to read confidently — take another one with more light, straight on.",
    },
    # Comprobantes de muestra del demo — el orden cuenta la historia.
    "muestras.remito_t": {
        "es": "1 · Remito — llega el camión",
        "en": "1 · Delivery note (remito) — the truck arrives",
    },
    "muestras.remito_d": {
        "es": "Lácteos Campo Alegre entrega la mercadería de la orden OC-2026-0847. "
              "Ángela la controla contra lo pedido ANTES de ingresarla al stock.",
        "en": "Lácteos Campo Alegre delivers the goods from order OC-2026-0847. "
              "Ángela checks it against what was ordered BEFORE taking it into stock.",
    },
    "muestras.factura_t": {
        "es": "2 · Factura A — llega a cobrar",
        "en": "2 · Invoice (factura A) — time to pay",
    },
    "muestras.factura_d": {
        "es": "La factura de esa misma entrega. Ángela la cruza contra el remito "
              "recién ingresado y la asienta en la cuenta del proveedor.",
        "en": "The invoice for that same delivery. Ángela checks it against the "
              "delivery note just taken in and posts it to the supplier's account.",
    },
    "muestras.recibo_t": {
        "es": "3 · Recibo — el moroso pagó",
        "en": "3 · Receipt — the late payer paid",
    },
    "muestras.recibo_d": {
        "es": "Almacén San Martín (49 días de mora) paga $8.000.000 a cuenta: la "
              "deuda baja y su scoring se recompone solo.",
        "en": "Almacén San Martín (49 days overdue) pays $8,000,000 on account: "
              "the debt drops and their score recovers on its own.",
    },
    "muestras.lista_t": {
        "es": "Lista de precios del proveedor — Lácteos Campo Alegre",
        "en": "Supplier price list — Lácteos Campo Alegre",
    },
    "muestras.lista_d": {
        "es": "El tarifario nuevo: 23 productos. Ángela detecta las subas normales, "
              "un salto sospechoso y un código pisado — y no aplica nada sin tu OK.",
        "en": "The new price sheet: 23 products. Ángela spots the normal increases, "
              "one suspicious jump and one mixed-up code — and applies nothing "
              "without your OK.",
    },
    # P22·A — lista de precios: el diff, la aplicación y la voz de Ángela
    "core.lista.nota_diff": {
        "es": "Nada se aplica sin tu OK; los dudosos quedan retenidos hasta que decidas.",
        "en": "Nothing is applied without your OK; doubtful ones stay on hold until "
              "you decide.",
    },
    "core.lista.nada_que_aplicar": {
        "es": "No quedó ningún ítem aplicable (todos retenidos o sin precio).",
        "en": "No applicable items left (all held back or missing a price).",
    },
    "core.comp.pro_lista": {
        "es": "Listo: actualicé el costo de {n} productos con la lista de {proveedor}. "
              "Tu margen teórico pasó de {antes} a {despues}, y el capital inmovilizado "
              "se revaluó con los costos nuevos — lo ves en Trend ya recalculado. "
              "Guardé el backup #{backup}: decime «revertí la lista de precios» y "
              "vuelve todo como estaba.",
        "en": "Done: I updated costs for {n} products from {proveedor}'s list. Your "
              "theoretical margin moved from {antes} to {despues}, and tied-up capital "
              "was revalued at the new costs — Trend already shows it recalculated. "
              "Backup #{backup} saved — say \"revert the price update\" and everything "
              "goes back.",
    },
    "core.comp.pro_lista_retenidos": {
        "es": "Retuve {n} ítems dudosos para que los mires: no toqué esos costos.",
        "en": "I held back {n} doubtful items for you to review: I didn't touch "
              "those costs.",
    },
    "core.comp.sin_compras": {
        "es": "Todavía no cargaste compras por comprobante. Sacale una foto a una "
              "factura de proveedor en «Cargar datos» y la ingreso yo.",
        "en": "You haven't loaded any purchases from documents yet. Snap a photo "
              "of a supplier invoice in \"Load data\" and I'll take it in.",
    },
    "fb.compras_recientes": {
        "es": "Esto es lo último que cargaste por comprobante: {lista}. "
              "¿Querés el detalle de alguno?",
        "en": "Here's the latest you loaded from documents: {lista}. "
              "Want the detail on any of them?",
    },
    "fb.compras_proveedor": {
        "es": "A {proveedor} le debés {saldo}{venc}.",
        "en": "You owe {proveedor} {saldo}{venc}.",
    },
    "fb.compras_vence": {
        "es": " (vence el {fecha})",
        "en": " (due {fecha})",
    },
    "core.comp.sync_simulado": {
        "es": "En cola para sincronizar al ERP (Faro) — simulado en esta demo.",
        "en": "Queued for ERP sync (Faro) — simulated in this demo.",
    },
    # El mensaje PROACTIVO de Ángela al confirmarse una carga por foto (B1):
    # qué entró, el cruce que corresponde y qué impactó. Lo compone el core
    # con números ya calculados — determinista, jamás recalculado por el modelo.
    "core.comp.pro_remito": {
        "es": "Cargué el remito {numero} de {proveedor}: {n} productos entraron al stock, con respaldo.",
        "en": "I loaded delivery note {numero} from {proveedor}: {n} products went into stock, with a backup.",
    },
    "core.comp.pro_remito_oc": {
        "es": "Lo crucé contra la orden {oc}: {n} de {m} renglones coinciden{dif}. La orden quedó cerrada.",
        "en": "I checked it against order {oc}: {n} of {m} line items match{dif}. The order is now closed.",
    },
    "core.comp.pro_remito_dif": {
        "es": ", {d} con diferencias para revisar",
        "en": ", {d} with differences to review",
    },
    "core.comp.pro_remito_sin_oc": {
        "es": "No encontré una orden de compra abierta de ese proveedor, así que lo ingresé sin cruce.",
        "en": "I didn't find an open purchase order from that supplier, so I took it in without a cross-check.",
    },
    "core.comp.pro_sin_catalogo": {
        "es": "Ojo: {lista} no está en el catálogo y quedó afuera del ingreso.",
        "en": "Heads up: {lista} isn't in the catalog and was left out.",
    },
    "core.comp.pro_factura": {
        "es": "Registré la factura {numero} de {proveedor} por {total}.",
        "en": "I recorded invoice {numero} from {proveedor} for {total}.",
    },
    "core.comp.pro_factura_cierra": {
        "es": "La crucé contra el remito ingresado: los montos cierran.",
        "en": "I checked it against the delivery note taken in: the amounts match.",
    },
    "core.comp.pro_factura_dif": {
        "es": "La crucé contra el remito ingresado: hay {n} diferencias para revisar.",
        "en": "I checked it against the delivery note taken in: there are {n} differences to review.",
    },
    "core.comp.pro_factura_sin_remito": {
        "es": "No encontré un remito reciente de ese proveedor para cruzarla.",
        "en": "I didn't find a recent delivery note from that supplier to check it against.",
    },
    "core.comp.pro_factura_cuenta": {
        "es": "Tu cuenta con {proveedor} queda en {saldo}, vence el {fecha}.",
        "en": "Your account with {proveedor} now stands at {saldo}, due {fecha}.",
    },
    "core.comp.pro_recibo": {
        "es": "Registré el cobro de {cliente} por {monto}: la deuda bajó de {antes} a {despues} "
              "y su scoring quedó {score}.",
        "en": "I recorded the payment from {cliente} for {monto}: their debt went from {antes} "
              "down to {despues} and their score is now {score}.",
    },
    "core.comp.pro_oc": {
        "es": "Cargué la orden de compra {numero} de {proveedor} con {n} renglones: queda abierta "
              "esperando el remito.",
        "en": "I loaded purchase order {numero} from {proveedor} with {n} line items: it stays open "
              "waiting for the delivery note.",
    },
    "fb.recepciones_recientes": {
        "es": "Remitos ingresados al stock: {lista}.",
        "en": "Delivery notes taken into stock: {lista}.",
    },
    "fb.cobros_recientes": {
        "es": "Cobros registrados: {lista}.",
        "en": "Payments recorded: {lista}.",
    },
    "notif.comprobante_t": {
        "es": "{actor} cargó un comprobante por foto",
        "en": "{actor} loaded a document from a photo",
    },
    "notif.quiebre_t": {
        "es": "Ángela avisa: quiebre de stock inminente",
        "en": "Ángela flags an imminent stock-out",
    },
    "notif.quiebre_c": {
        "es": "{producto} se queda sin stock en {dias} días — es tu producto #{pos} por ingresos. Conviene reponer antes de que quiebre.",
        "en": "{producto} runs out of stock in {dias} days — it's your #{pos} product by revenue. Worth reordering before it breaks.",
    },
    "fb.cancelar": {
        "es": "Listo, lo cancelo. No toqué nada.",
        "en": "Done, cancelled. I didn't touch a thing.",
    },
    "fb.listo": {"es": "Listo.", "en": "Done."},
    # fb: anomalías de negocio
    "fb.debajo_costo": {
        "es": "Ojo: esos productos figuran con el costo más alto que el precio, pero casi siempre es un "
              "error de carga —el costo viene con IVA y el precio sin IVA, o quedó un precio viejo—, no que "
              "estés vendiendo a pérdida de verdad. No te conviene ponerles un margen a ciegas. Lo más seguro: "
              "cargás la lista de precios actualizada y los recalculo, o revisamos los de mayor impacto uno por "
              "uno. ¿Te los muestro ordenados por plata?",
        "en": "Heads up: those products show a cost higher than the price, but it's almost always a data-entry "
              "error —the cost includes VAT and the price doesn't, or an old price stuck around—, not you "
              "actually selling at a loss. Slapping a blind margin on them is a bad idea. Safest move: load the "
              "updated price list and I'll recalculate them, or we review the biggest ones one by one. "
              "Want me to show them sorted by money?",
    },
    "fb.duplicados": {
        "es": "Son productos con el mismo nombre y distinto código. Hay que decidir caso por caso si es el "
              "mismo (y lo unifico) o si son distintos. Te los muestro juntos para revisarlos; cuando me "
              "confirmes cuáles son el mismo, los unifico sin contar el stock dos veces.",
        "en": "Those are products with the same name and a different code. It's a case-by-case call: same "
              "product (I merge them) or actually different. I'll show them side by side; once you confirm "
              "which ones match, I merge them without counting the stock twice.",
    },
    "fb.stock_anormal": {
        "es": "Ese stock altísimo casi seguro es un error de tipeo (un cero de más). Decime el valor correcto "
              "y lo corrijo con backup, o confirmame que está bien y lo dejo como está.",
        "en": "That sky-high stock is almost surely a typo (an extra zero). Tell me the right number and I'll "
              "fix it with a backup, or confirm it's fine and I'll leave it alone.",
    },
    # fb: macro
    "fb.macro_dolar": {
        "es": "El dólar oficial está a ${valor} (BCRA, {fecha}). "
              "Qué hacer con eso depende de tus números, no del dólar: decime qué "
              "categoría estás por reponer y te muestro cuánto tenés parado ahí y "
              "a qué costo estás reponiendo. ",
        "en": "The official dollar is at ${valor} (BCRA, {fecha}). "
              "What to do with that depends on your numbers, not the dollar: tell me "
              "which category you're about to restock and I'll show you how much is "
              "sitting there and at what cost you're replacing it. ",
    },
    "fb.macro_caido": {
        "es": "No pude traer la cotización ahora (la fuente del BCRA no respondió) y no "
              "te la voy a inventar. Lo que sí tengo son tus números: decime qué categoría "
              "estás por reponer y lo miramos con tu stock y tu costo real. ",
        "en": "I couldn't get the exchange rate just now (the BCRA source didn't answer) "
              "and I won't make it up. What I do have is your numbers: tell me which "
              "category you're about to restock and we'll look at it with your real "
              "stock and cost. ",
    },
    "fb.macro_cierre": {
        "es": "Con eso sobre la mesa, la decisión de comprar o esperar es tuya.",
        "en": "With that on the table, buying or waiting is your call.",
    },
    "fb.macro_hoy": {"es": "hoy", "en": "today"},
    # fb: recordatorios
    "fb.rec_det_vencimiento": {
        "es": "si algo del depósito vence en menos de {dias} días",
        "en": "if anything in the warehouse expires in less than {dias} days",
    },
    "fb.rec_pregunta_cliente": {
        "es": "¿De qué cliente es la entrega que querés vigilar? Decime el nombre "
              "y te aviso si no sale.",
        "en": "Which customer's delivery do you want me to watch? Give me the name "
              "and I'll warn you if it doesn't go out.",
    },
    "fb.rec_det_entrega": {
        "es": "si la entrega de {cliente} no sale",
        "en": "if the delivery for {cliente} doesn't go out",
    },
    "fb.rec_ese_cliente": {"es": "ese cliente", "en": "that customer"},
    "fb.rec_det_remito": {
        "es": "cuando llegue un remito de {origen}",
        "en": "when a delivery note from {origen} arrives",
    },
    "fb.rec_ese_origen": {"es": "ese origen", "en": "that source"},
    "fb.rec_confirmado": {
        "es": "Listo, quedó anotado: te aviso {detalle}. Lo vas a ver en tu panel "
              "apenas se cumpla (y por WhatsApp cuando conectemos el canal).",
        "en": "Done, it's noted: I'll warn you {detalle}. You'll see it on your panel "
              "the moment it happens (and on WhatsApp once we hook up the channel).",
    },
    "fb.rec_anotado": {
        "es": "Anotado. Te lo dejo en tus recordatorios.",
        "en": "Noted. I left it in your reminders.",
    },
    "fb.rec_sin_pendientes": {
        "es": "No tenés recordatorios pendientes.",
        "en": "You have no pending reminders.",
    },
    "fb.rec_marca_disparado": {"es": "AHORA", "en": "NOW"},
    "fb.rec_marca_activo": {"es": "pendiente", "en": "pending"},
    "fb.rec_marca_latente": {"es": "vigilando", "en": "watching"},
    "fb.rec_pre_disparados": {
        "es": "Tenés {n} que se dispararon y piden atención",
        "en": "You have {n} that went off and need attention",
    },
    "fb.rec_pre_anotados": {
        "es": "Tenés {n} anotados",
        "en": "You have {n} noted",
    },
    # fb: logística / reparto
    "fb.log_sin_datos": {
        "es": "Todavía no tengo los datos de reparto: se cargan con el export del "
              "sistema de envíos por «Cargar datos». Apenas lo subas te digo qué sale "
              "hoy, qué está atrasado y dónde está cada pedido.",
        "en": "I don't have the delivery data yet: it loads from your shipping "
              "system's export via \"Load data\". As soon as you upload it I'll tell "
              "you what goes out today, what's running late and where each order is.",
    },
    "fb.log_estado_entregado": {"es": "ya se entregó", "en": "was already delivered"},
    "fb.log_estado_en_camino": {"es": "está en camino", "en": "is on its way"},
    "fb.log_estado_pendiente": {"es": "todavía no salió", "en": "hasn't gone out yet"},
    "fb.log_transporte": {
        "es": "Lo lleva {transporte}.",
        "en": "{transporte} is carrying it.",
    },
    "fb.log_atrasada_ojo": {
        "es": "OJO: está atrasada, era para el {fecha}.",
        "en": "WATCH OUT: it's late, it was due {fecha}.",
    },
    "fb.log_pedido": {
        "es": "El pedido de {cliente} ({pedido}) {estado} "
              "(previsto: {fecha}).{extra}{atraso} "
              "(Fuente: último export de reparto.)",
        "en": "{cliente}'s order ({pedido}) {estado} "
              "(expected: {fecha}).{extra}{atraso} "
              "(Source: latest delivery export.)",
    },
    "fb.log_no_encuentro": {
        "es": "No encuentro un pedido con ese cliente en el último export de reparto. "
              "¿Cómo figura el nombre?",
        "en": "I can't find an order for that customer in the latest delivery export. "
              "How is the name listed?",
    },
    "fb.log_al_dia": {
        "es": "No hay entregas atrasadas. El reparto viene al día.",
        "en": "No late deliveries. Distribution is right on schedule.",
    },
    "fb.log_atrasadas": {
        "es": "Tenés {n} entregas atrasadas. La más vieja: {cliente} "
              "(pedido {pedido}), era para el {fecha} y figura "
              "«{estado}». ¿Te creo un recordatorio o le aviso al que reparte?",
        "en": "You have {n} late deliveries. The oldest: {cliente} "
              "(order {pedido}), due {fecha} and listed as "
              "\"{estado}\". Want me to create a reminder or warn the driver?",
    },
    "fb.log_sin_hoy": {
        "es": "Hoy no hay entregas previstas.",
        "en": "No deliveries scheduled today.",
    },
    "fb.log_hoy": {
        "es": "Hoy hay {n} entregas previstas ({detalle}).",
        "en": "There are {n} deliveries scheduled today ({detalle}).",
    },
    "fb.log_arrastre": {
        "es": "Y arrastrás {n} atrasadas de días anteriores. ¿Te las muestro?",
        "en": "And you're dragging {n} late ones from previous days. Want to see them?",
    },
    "fb.log_fuente": {
        "es": "(Fuente: último export de reparto.)",
        "en": "(Source: latest delivery export.)",
    },
    # fb: depósito
    "fb.dep_sin_datos": {
        "es": "Todavía no tengo el detalle del depósito (ubicaciones, lotes, "
              "vencimientos): se carga con el export del sistema de depósito por "
              "«Cargar datos». Apenas lo subas te digo qué vence, dónde está cada "
              "cosa y si el stock físico coincide con el del sistema.",
        "en": "I don't have the warehouse detail yet (locations, batches, expiry "
              "dates): it loads from your warehouse system's export via \"Load "
              "data\". As soon as you upload it I'll tell you what's expiring, where "
              "everything is, and whether physical stock matches the system.",
    },
    "fb.dep_sin_vencimientos": {
        "es": "No hay lotes que venzan en los próximos {dias} días. El depósito "
              "viene bien de rotación. (Fuente: último export del depósito.)",
        "en": "No batches expiring in the next {dias} days. The warehouse is "
              "rotating just fine. (Source: latest warehouse export.)",
    },
    "fb.dep_vence_hoy": {"es": "vence HOY", "en": "expires TODAY"},
    "fb.dep_vence_en": {"es": "vence en {dias} días", "en": "expires in {dias} days"},
    "fb.dep_linea_lote": {
        "es": "• {producto} — lote {lote}, {ubicacion}: {cuando}",
        "en": "• {producto} — batch {lote}, {ubicacion}: {cuando}",
    },
    "fb.dep_vencen": {
        "es": "Tenés {n} lotes que vencen en menos de {dias} días:",
        "en": "You have {n} batches expiring in less than {dias} days:",
    },
    "fb.dep_ya_vencidos": {
        "es": "Además hay {n} lotes YA vencidos que conviene bajar de la góndola.",
        "en": "There are also {n} batches ALREADY expired that should come off the shelf.",
    },
    "fb.dep_crear_recordatorio": {
        "es": "¿Te creo un recordatorio para que no se repita?",
        "en": "Want me to create a reminder so it doesn't happen again?",
    },
    "fb.dep_sin_discrepancias": {
        "es": "El stock físico del depósito coincide con el del sistema. "
              "Sin diferencias.",
        "en": "Physical warehouse stock matches the system. No differences.",
    },
    "fb.dep_discrepancias": {
        "es": "Hay {n} productos donde el físico no coincide con el sistema. "
              "El peor: {descripcion} — el sistema dice {contable} "
              "y en el depósito hay {fisico}. ¿Revisamos esos primero?",
        "en": "There are {n} products where physical stock doesn't match the system. "
              "The worst: {descripcion} — the system says {contable} "
              "and the warehouse has {fisico}. Shall we check those first?",
    },
    "fb.dep_no_encuentro": {
        "es": "No encuentro ese producto en el último export del depósito. "
              "¿Cómo figura el nombre o el código?",
        "en": "I can't find that product in the latest warehouse export. "
              "How is the name or code listed?",
    },
    "fb.dep_ubicacion": {
        "es": "{producto}: está en {ubicacion}, lote {lote}, "
              "{cantidad} unidades{extra}. Vence el {vencimiento}. "
              "(Fuente: último export del depósito.)",
        "en": "{producto}: it's in {ubicacion}, batch {lote}, "
              "{cantidad} units{extra}. Expires {vencimiento}. "
              "(Source: latest warehouse export.)",
    },
    "fb.dep_mas_ubicaciones": {
        "es": "(y {n} ubicaciones más)",
        "en": "(plus {n} more locations)",
    },
    "fb.dep_resumen": {
        "es": "El depósito tiene {lotes} lotes en {ubicaciones} ubicaciones. "
              "Por vencer: {por_vencer}. Vencidos: {vencidos}. "
              "Diferencias físico/sistema: {discrepancias}. ¿Qué querés mirar?",
        "en": "The warehouse has {lotes} batches across {ubicaciones} locations. "
              "About to expire: {por_vencer}. Expired: {vencidos}. "
              "Physical/system differences: {discrepancias}. What do you want to look at?",
    },
    # fb: normalizaciones del staging
    "fb.norm_revertida": {
        "es": "Listo, deshice la normalización de «{revertido}»: "
              "el archivo volvió a como vino. Quedó en el registro.",
        "en": "Done, I undid the normalization of \"{revertido}\": "
              "the file is back to how it arrived. It's on the record.",
    },
    "fb.norm_confirmar": {
        "es": "En «{batch}»: {resumen} ¿Confirmás que la deshago?",
        "en": "In \"{batch}\": {resumen} Confirm you want me to undo it?",
    },
    "fb.norm_detalle": {
        "es": "En «{batch}»: {resumen} El detalle completo está en "
              "Datos pendientes, y si algo no te cierra la revierto entera.",
        "en": "In \"{batch}\": {resumen} The full detail is in "
              "Pending data, and if anything looks off I'll revert the whole thing.",
    },
    # fb: gestión de módulos
    "fb.mod_aplicado_on": {
        "es": "Listo, le habilité {etiqueta} a {nombre}. Le llega la "
              "notificación y ya lo ve en su PolPilot. Quedó en el registro.",
        "en": "Done, I enabled {etiqueta} for {nombre}. They get the "
              "notification and can already see it in their PolPilot. It's on the record.",
    },
    "fb.mod_aplicado_off": {
        "es": "Listo, le deshabilité {etiqueta} a {nombre}. Le llega la "
              "notificación y ya lo ve en su PolPilot. Quedó en el registro.",
        "en": "Done, I disabled {etiqueta} for {nombre}. They get the "
              "notification and can already see it in their PolPilot. It's on the record.",
    },
    "fb.mod_confirmar_on": {
        "es": "Voy a habilitarle {etiqueta} a {nombre}. ¿Confirmás? Queda registrado y "
              "le aviso yo.",
        "en": "I'm about to enable {etiqueta} for {nombre}. Confirm? It goes on the "
              "record and I'll let them know.",
    },
    "fb.mod_confirmar_off": {
        "es": "Voy a sacarle {etiqueta} a {nombre}. ¿Confirmás? Queda registrado y "
              "le aviso yo.",
        "en": "I'm about to remove {etiqueta} from {nombre}. Confirm? It goes on the "
              "record and I'll let them know.",
    },
    "fb.mod_solicitud": {
        "es": "Eso lo aprueba el dueño: le dejé la solicitud de {etiqueta} a {dueno} "
              "con tu pedido. Te aviso apenas la resuelva.",
        "en": "That one's for the owner to approve: I left the {etiqueta} request "
              "with {dueno} on your behalf. I'll let you know as soon as they resolve it.",
    },
    "fb.mod_pedile_dueno": {
        "es": "eso lo tiene que hacer el dueño; pedile a {dueno}",
        "en": "that's for the owner to do; ask {dueno}",
    },
    # Notificaciones de perfiles (P9·C1): el nombre del dueño REAL del tenant,
    # en el idioma del destinatario.
    "notif.sol_titulo": {
        "es": "Tu pedido de {label}: {estado}",
        "en": "Your {label} request: {estado}",
    },
    "notif.sol_estado_aprobada": {"es": "aprobada", "en": "approved"},
    "notif.sol_estado_rechazada": {"es": "rechazada", "en": "declined"},
    "notif.sol_cuerpo_aprobada": {
        "es": "{dueno} aprobó tu solicitud de {label}.",
        "en": "{dueno} approved your request for {label}.",
    },
    "notif.sol_cuerpo_rechazada": {
        "es": "{dueno} rechazó tu solicitud de {label}.",
        "en": "{dueno} declined your request for {label}.",
    },
    "notif.sol_motivo": {"es": " Motivo: {motivo}", "en": " Reason: {motivo}"},
    "notif.mod_titulo_on": {
        "es": "Se habilitó {modulo} en tu PolPilot",
        "en": "{modulo} was enabled in your PolPilot",
    },
    "notif.mod_titulo_off": {
        "es": "Se deshabilitó {modulo} en tu PolPilot",
        "en": "{modulo} was disabled in your PolPilot",
    },
    "notif.mod_cuerpo_on": {
        "es": "{dueno} te habilitó el módulo {modulo}.",
        "en": "{dueno} enabled the {modulo} module for you.",
    },
    "notif.mod_cuerpo_off": {
        "es": "{dueno} te deshabilitó el módulo {modulo}.",
        "en": "{dueno} disabled the {modulo} module for you.",
    },
    "fb.mod_dueno": {
        "es": "Eso lo maneja el dueño.",
        "en": "That one's handled by the owner.",
    },
    # fb: config de organización
    "fb.margen_dueno": {
        "es": "Eso cambia una regla de toda la empresa, así que necesito que lo apruebe "
              "el dueño. ¿Se lo propongo?",
        "en": "That changes a company-wide rule, so I need the owner to approve it. "
              "Shall I propose it to them?",
    },
    "fb.margen_ok": {
        "es": "Listo. Dejé el margen mínimo de la empresa en {pct}%. Desde ahora te "
              "aviso lo que esté por debajo. Esto aplica para todo tu equipo.",
        "en": "Done. I set the company's minimum margin at {pct}%. From now on I'll "
              "flag anything below it. This applies to your whole team.",
    },
    # fb: pestañas y widgets
    "fb.pestana_creada": {
        "es": "Listo, te armé la pestaña «{nombre}» en el inventario. Queda guardada.",
        "en": "Done, I set up the \"{nombre}\" tab in your inventory. It's saved.",
    },
    "fb.pestana_cual": {
        "es": "¿Para qué categoría querés la pestaña? Puedo armarte una de balanzas, "
              "fantasmas, stock negativo o sin precio.",
        "en": "Which category do you want the tab for? I can build one for scales, "
              "ghosts, negative stock or no-price items.",
    },
    "fb.widget_donde": {
        "es": "Te armo el gráfico. ¿Dónde lo querés, en el Inicio o en Inventario?",
        "en": "I'll build the chart. Where do you want it, on Home or in Inventory?",
    },
    "fb.widget_listo": {
        "es": "Listo, te puse «{titulo}» en {seccion}. Queda guardado para la próxima.",
        "en": "Done, I put \"{titulo}\" on {seccion}. It's saved for next time.",
    },
    "fb.widget_sec_inicio": {"es": "el Inicio", "en": "Home"},
    "fb.widget_sec_inventario": {"es": "Inventario", "en": "Inventory"},
    # fb: modificar vista
    "fb.vista_topn": {
        "es": "ahora ves {n} productos en el inicio",
        "en": "you now see {n} products on home",
    },
    "fb.vista_sin_franja": {
        "es": "saqué la franja de ahorro",
        "en": "I removed the savings strip",
    },
    "fb.vista_con_franja": {
        "es": "volví a mostrar la franja de ahorro",
        "en": "I brought back the savings strip",
    },
    "fb.vista_margen": {
        "es": "agregué la columna de margen al inventario",
        "en": "I added the margin column to the inventory",
    },
    # P19·A — preferencias con memoria (respuestas del router simulado)
    "fb.pref_sin_torta": {
        "es": "Anotado — no ves un gráfico de torta nunca más: de acá en adelante "
              "todo sale en barras. Lo podés ver y borrar en Mi perfil.",
        "en": "Noted — you'll never see a pie chart again: from now on everything "
              "comes out as bars. You can see and delete this in My profile.",
    },
    "fb.pref_margen_pin": {
        "es": "Listo: todo lo que tenga margen menor a {umbral}% queda fijado arriba "
              "en el inventario, con la columna de margen a la vista. Lo podés borrar "
              "en Mi perfil cuando quieras.",
        "en": "Done: anything with margin under {umbral}% is now pinned up top in the "
              "inventory, with the margin column showing. You can delete this in "
              "My profile anytime.",
    },
    "fb.pref_margen_umbral": {
        "es": "¿Debajo de qué margen lo querés fijado arriba? Decime el número "
              "(por ejemplo: \"menor a 18%\").",
        "en": "Under what margin do you want them pinned up top? Give me the number "
              "(for example: \"under 18%\").",
    },
    "fb.pref_lista": {
        "es": "Esto es lo que recuerdo de cómo te gusta ver las cosas: {lista}. "
              "Lo ves y lo borrás en Mi perfil.",
        "en": "This is what I remember about how you like things: {lista}. "
              "You can see and delete it in My profile.",
    },
    "fb.pref_lista_vacia": {
        "es": "Todavía no me dijiste ningún gusto de vista. Probá con "
              "\"no me gustan los gráficos de torta\".",
        "en": "You haven't told me any view preferences yet. Try "
              "\"I don't like pie charts\".",
    },
    "fb.pref_lista_sin_torta": {
        "es": "nada de gráficos de torta",
        "en": "no pie charts",
    },
    "fb.pref_lista_margen": {
        "es": "margen menor a {umbral}% fijado arriba",
        "en": "margin under {umbral}% pinned up top",
    },
    "fb.pref_lista_orden": {
        "es": "el orden de tu Inicio a tu manera",
        "en": "your Home blocks in your own order",
    },
    "fb.orden_listo": {
        "es": "Listo, te reordené el Inicio y queda así de ahora en más — recargá "
              "las veces que quieras. \"Volvé a como estaba\" y lo deshago.",
        "en": "Done, I rearranged your Home and it stays that way from now on — "
              "reload as many times as you like. Say \"put it back\" and I'll undo it.",
    },
    "fb.orden_reset": {
        "es": "Listo, tu Inicio volvió al orden original.",
        "en": "Done, your Home is back to its original order.",
    },
    "fb.widget_parada_listo": {
        "es": "Listo: te dejé la card con la plata parada en productos de más de "
              "{dias} días arriba de tu Inicio. El número se recalcula solo cada "
              "vez que entrás, y la sacás con la X o pidiéndomelo.",
        "en": "Done: I pinned the card with money stuck in products idle {dias}+ "
              "days at the top of your Home. The number recalculates itself every "
              "time you come in — remove it with the X or just ask me.",
    },
    "fb.widget_parada_sin_ventas": {
        "es": "Ese dato sale de las ventas y todavía no están validadas — no te "
              "voy a inventar un número. Lo más cercano que tengo hoy es dónde "
              "está la plata por producto: ¿te armo esa?",
        "en": "That number comes from sales data, which isn't validated yet — I'm "
              "not going to make it up. The closest I have today is money by "
              "product: want that one?",
    },
    "fb.widget_cambiado": {
        "es": "Listo, la pasé a tabla — y así queda.",
        "en": "Done, it's a table now — and it stays that way.",
    },
    "fb.widget_quitado": {
        "es": "Listo, la saqué. Si la querés de vuelta, pedímela.",
        "en": "Done, I removed it. Ask me if you ever want it back.",
    },
    # P21 — consultas genéricas (el contrato habla claro cuando rechaza)
    "core.forecast.sin_ventas": {
        "es": "No hay ventas cargadas todavía — el pronóstico se desbloquea con ese historial.",
        "en": "No sales data loaded yet — the forecast unlocks once that history is in.",
    },
    "core.forecast.sin_demanda_reciente": {
        "es": "Sin ventas en los últimos 12 meses: no hay demanda reciente para proyectar.",
        "en": "No sales in the last 12 months: there is no recent demand to project.",
    },
    "core.consulta.sin_ventas": {
        "es": "No hay ventas cargadas todavía — esta consulta se desbloquea con ese CSV.",
        "en": "No sales data loaded yet — this query unlocks with that CSV.",
    },
    "core.consulta.sin_granularidad": {
        "es": "Las ventas están cargadas por mes, no por día — el detalle diario no existe "
              "en el sistema. Te lo puedo armar mes a mes.",
        "en": "Sales are loaded by month, not by day — daily detail doesn't exist in the "
              "system. I can build it month by month.",
    },
    "core.consulta.sin_ipc": {
        "es": "Para deflactar necesito el índice IPC y no está cargado — te lo doy en "
              "pesos nominales.",
        "en": "To adjust for inflation I need the CPI index and it's not loaded — I can "
              "give it to you in nominal pesos.",
    },
    "core.consulta.cat_inexistente": {
        "es": "No tengo la categoría «{texto}» en los datos.",
        "en": "There's no \"{texto}\" category in the data.",
    },
    "core.consulta.prod_inexistente": {
        "es": "No encontré ningún producto que matchee «{texto}» en las ventas.",
        "en": "I couldn't find any product matching \"{texto}\" in the sales data.",
    },
    "core.consulta.cliente_inexistente": {
        "es": "No tengo ningún cliente que matchee «{texto}» en cuentas corrientes.",
        "en": "No customer matches \"{texto}\" in accounts receivable.",
    },
    "core.consulta.varios_prod": {
        "es": "{texto} ({n} productos)",
        "en": "{texto} ({n} products)",
    },
    "core.consulta.total_ventas": {
        "es": "Ventas totales",
        "en": "Total sales",
    },
    "core.consulta.ventana_vacia": {
        "es": "En esa ventana no hay ventas registradas.",
        "en": "There are no recorded sales in that window.",
    },
    "core.consulta.sin_datos_metrica": {
        "es": "No hay datos suficientes para esa métrica (faltan precios o ventas).",
        "en": "Not enough data for that metric (missing prices or sales).",
    },
    "core.consulta.fuente_desconocida": {
        "es": "No tengo la fuente «{texto}» — trabajo con ventas, inventario, cuentas y caja.",
        "en": "I don't have a \"{texto}\" source — I work with sales, inventory, accounts "
              "and cash register.",
    },
    "core.consulta.metrica_invalida": {
        "es": "La métrica «{metrica}» no aplica a {fuente}.",
        "en": "The \"{metrica}\" metric doesn't apply to {fuente}.",
    },
    "core.consulta.agrupar_invalido": {
        "es": "No puedo agrupar {fuente} por «{agrupar}».",
        "en": "I can't group {fuente} by \"{agrupar}\".",
    },
    "core.consulta.deflactar_unidades": {
        "es": "Las unidades no se deflactan — la inflación es de los pesos, no de los "
              "paquetes. Te lo doy en unidades tal cual o en pesos constantes.",
        "en": "Units don't get inflation-adjusted — inflation applies to pesos, not "
              "packages. I can give you plain units or constant pesos.",
    },
    "core.consulta.fecha_invalida": {
        "es": "La fecha de «{campo}» tiene que venir como AAAA-MM.",
        "en": "The \"{campo}\" date must come as YYYY-MM.",
    },
    "core.consulta.u_unidades": {
        "es": "unidades",
        "en": "units",
    },
    "core.consulta.u_pesos_reales": {
        "es": "$ constantes (base {base})",
        "en": "constant $ (base {base})",
    },
    "core.consulta.u_dias": {
        "es": "días",
        "en": "days",
    },
    "core.consulta.hoy": {
        "es": "hoy",
        "en": "today",
    },
    "core.consulta.m_inmovilizado": {
        "es": "Capital inmovilizado",
        "en": "Tied-up capital",
    },
    "core.consulta.m_stock": {
        "es": "Stock",
        "en": "Stock",
    },
    "core.consulta.m_margen_teorico": {
        "es": "Margen teórico",
        "en": "Theoretical margin",
    },
    "core.consulta.m_dias_rotacion": {
        "es": "Días de rotación",
        "en": "Days to turn",
    },
    "core.consulta.m_saldo": {
        "es": "Saldo adeudado",
        "en": "Balance owed",
    },
    "core.consulta.m_dias_sin_pagar": {
        "es": "Días sin pagar",
        "en": "Days without paying",
    },
    "core.consulta.caja_vacia": {
        "es": "La caja de hoy no tiene movimientos todavía.",
        "en": "Today's cash register has no movements yet.",
    },
    "core.consulta.caja_hoy": {
        "es": "Caja de hoy por medio de pago",
        "en": "Today's register by payment method",
    },
    # P23·A — participación con denominador explícito
    "core.consulta.sujeto_igual_universo": {
        "es": "La participación de «{sujeto}» sobre sí mismo es siempre 100% — no "
              "dice nada. Usá un universo mayor (ej. total_negocio).",
        "en": "\"{sujeto}\"'s share of itself is always 100% — it says nothing. "
              "Use a larger universe (e.g. total_negocio).",
    },
    "core.consulta.sujeto_fuera": {
        "es": "«{sujeto}» no está adentro de «{universo}» — vive en {donde}.",
        "en": "\"{sujeto}\" isn't inside \"{universo}\" — it lives in {donde}.",
    },
    "core.consulta.participacion_sin_sujeto": {
        "es": "La participación necesita un sujeto: un producto o una categoría.",
        "en": "A share query needs a subject: a product or a category.",
    },
    "core.consulta.composicion_temporal": {
        "es": "Una composición a lo largo del tiempo es una PARTICIPACIÓN: el sujeto "
              "como % de un universo, período a período.",
        "en": "A composition over time is a SHARE: the subject as % of a universe, "
              "period by period.",
    },
    "core.consulta.participacion_nombre": {
        "es": "{sujeto} — % de {universo}",
        "en": "{sujeto} — % of {universo}",
    },
    "core.consulta.widget_sub": {
        "es": "{unidad} · {ventana}",
        "en": "{unidad} · {ventana}",
    },
    "core.consulta.caja_nota": {
        "es": "La caja registra el día corriente — no hay serie histórica.",
        "en": "The register tracks the current day — there is no historical series.",
    },
    # P19·D — orquestación visible (los pasos del plan, con números reales)
    "core.plan.paso_fantasma": {
        "es": "Normalizar los {n} productos fantasma (anulados con stock vivo)",
        "en": "Normalize the {n} ghost products (cancelled but still with stock)",
    },
    "core.plan.paso_balanza": {
        "es": "Corregir las {n} balanzas mal calibradas",
        "en": "Fix the {n} miscalibrated scales",
    },
    "core.plan.paso_recalcular": {
        "es": "Recalcular el capital inmovilizado",
        "en": "Recalculate tied-up capital",
    },
    "core.plan.paso_cola": {
        "es": "Actualizar la cola de sincronización al ERP (simulada en esta demo)",
        "en": "Refresh the ERP sync queue (simulated in this demo)",
    },
    "core.plan.nota_backup": {
        "es": "Todo con backup: cada paso se puede revertir.",
        "en": "Everything with backup: every step can be reverted.",
    },
    "core.plan.hecho_backup": {
        "es": "backup #{backup} guardado",
        "en": "backup #{backup} saved",
    },
    "core.plan.cola_detalle": {
        "es": "{n} cambios listos para exportar al ERP",
        "en": "{n} changes ready to export to the ERP",
    },
    "core.plan.paso_fallo": {
        "es": "El paso «{paso}» falló — me detuve ahí. Lo hecho hasta acá tiene su backup.",
        "en": "The step \"{paso}\" failed — I stopped there. What's done so far has its backup.",
    },
    "fb.plan_propuesta": {
        "es": "Eso lleva {n} acciones: {lista}. Todo con backup — ¿te lo ejecuto?",
        "en": "That takes {n} actions: {lista}. Everything with backup — want me to run it?",
    },
    "fb.plan_fuera": {
        "es": " Ojo: {fuera} quedan afuera de lo automático (requieren conteo físico "
              "o decisión de precio).",
        "en": " Note: {fuera} stay out of the automatic run (they need a physical "
              "count or a pricing decision).",
    },
    "fb.plan_nada": {
        "es": "No hay correcciones automáticas pendientes ahora mismo. Lo que queda "
              "(stock negativo, productos sin precio) requiere conteo físico o una "
              "decisión de precio tuya.",
        "en": "There are no automatic fixes pending right now. What's left (negative "
              "stock, unpriced products) needs a physical count or a pricing decision "
              "from you.",
    },
    "fb.plan_ejecutado": {
        "es": "Listo — {n} acciones, todas con backup. El capital inmovilizado pasó "
              "de {antes} a {despues}. Todo quedó en el feed y la auditoría; "
              "si querés revertir, decímelo.",
        "en": "Done — {n} actions, all backed up. Tied-up capital moved from {antes} "
              "to {despues}. Everything's in the feed and the audit log; say the "
              "word and I revert.",
    },
    "fb.plan_op_dale": {
        "es": "Dale, ejecutá el plan",
        "en": "Go ahead, run the plan",
    },
    "fb.plan_op_no": {
        "es": "Mejor no",
        "en": "Better not",
    },
    "fb.consulta_ofrezco_mes": {
        "es": "¿Te lo armo así?",
        "en": "Want me to build it that way?",
    },
    "fb.op_mes_a_mes": {
        "es": "Dale, mes a mes",
        "en": "Sure, month by month",
    },
    "fb.consulta_fijada": {
        "es": "Listo: te dejé el gráfico de {nombre} fijo en Evolución — ventas mes a "
              "mes, en unidades ({mes}: {valor}). Se recalcula solo cada vez que entrás; "
              "lo sacás con la X o pidiéndomelo.",
        "en": "Done: I pinned the {nombre} chart in Trend — monthly sales, in units "
              "({mes}: {valor}). It recalculates itself every time you come in; remove "
              "it with the X or just ask me.",
    },
    # P25·A — oportunidades de verdad (tarjetas con drill-down)
    "core.opn.morosos_t": {"es": "Cobrar a los {n} morosos", "en": "Collect from the {n} overdue customers"},
    "core.opn.morosos_r": {"es": "El peor: {peor}, {dias} días sin pagar.",
                            "en": "Worst: {peor}, {dias} days without paying."},
    "core.opn.morosos_chat": {"es": "ayudame a cobrarles a los morosos",
                               "en": "help me collect from the overdue customers"},
    "core.opn.morosos_p1": {"es": "{n} clientes en mora suman {total} vencidos.",
                             "en": "{n} overdue customers add up to {total} past due."},
    "core.opn.morosos_p2": {"es": "{peor} lleva {dias} días sin pagar cuando su promedio histórico es {prom} — el desvío es la señal.",
                             "en": "{peor} is {dias} days without paying vs a {prom}-day historical average — the deviation is the signal."},
    "core.opn.morosos_p2_lbl": {"es": "Días sin pagar vs. su promedio histórico ({peor})",
                                 "en": "Days unpaid vs. historical average ({peor})"},
    "core.opn.morosos_i": {"es": "{dias} días sin pagar", "en": "{dias} days without paying"},
    "core.opn.overdue_total_ev": {"es": "Saldo vencido total", "en": "Total overdue balance"},
    "core.opn.dormido_t": {"es": "Despertar el stock dormido", "en": "Wake up the sleeping stock"},
    "core.opn.dormido_r": {"es": "{pct}% de tu stock no rota; liquidar los 5 peores libera {top5}.",
                            "en": "{pct}% of your stock doesn't turn; clearing the worst 5 frees {top5}."},
    "core.opn.dormido_chat": {"es": "armame el plan para liquidar el stock dormido",
                               "en": "build me the plan to clear the sleeping stock"},
    "core.opn.dormido_p1": {"es": "Hay {monto} ({pct}% del stock) en productos que no rotan.",
                             "en": "There's {monto} ({pct}% of stock) in products that don't turn."},
    "core.opn.dormido_p2": {"es": "Los 5 peores concentran {top5}: liquidarlos es plata líquida esta semana.",
                             "en": "The worst 5 concentrate {top5}: clearing them is cash this week."},
    "core.opn.dormido_dias": {"es": "rota cada {dias} días", "en": "turns every {dias} days"},
    "core.opn.dormido_sin_venta": {"es": "sin una venta en el año", "en": "no sale in a year"},
    "core.opn.dormido_s1": {"es": "Supuesto: liquidación al costo actual (sin remate por debajo del costo).",
                             "en": "Assumption: clearance at current cost (no below-cost fire sale)."},
    "core.opn.dormant_value_ev": {"es": "Valor de stock dormido", "en": "Value of dormant stock"},
    "core.opn.dormant_top5_ev": {"es": "Valor de los 5 productos dormidos principales",
                                "en": "Value of the top 5 dormant products"},
    "core.opn.morosos_g": {"es": "Pagos de {nombre}", "en": "{nombre}'s payments"},
    "core.opn.dormido_g": {"es": "Los peores dormidos (plata parada)", "en": "Worst sleepers (money sitting)"},
    # P27·A3 — la ventana de compra con razonamiento de dueño
    "core.opn.ventana_t": {"es": "Ventana de compra — {proveedor}",
                            "en": "Buying window — {proveedor}"},
    "core.opn.ventana_r2": {"es": "Su lista nueva llega {cuando} con ~{suba}% de suba: adelantá SOLO lo que ibas a comprar igual.",
                             "en": "Their new list lands {cuando} with a ~{suba}% rise: only move up what you were going to buy anyway."},
    "core.opn.ventana_ya": {"es": "en estos días", "en": "any day now"},
    "core.opn.ventana_en": {"es": "en {n} días", "en": "in {n} days"},
    "core.opn.ventana_chat": {"es": "armame la orden de reposición de {proveedor} antes de la próxima lista",
                               "en": "build my {proveedor} replenishment order before the next price list"},
    "core.opn.ventana_q1": {"es": "{proveedor} manda lista nueva cada ~{frec} días; la próxima llega {cuando} y las últimas subieron ~{suba}% promedio.",
                             "en": "{proveedor} sends a new price list every ~{frec} days; the next one lands {cuando} and recent ones rose ~{suba}% on average."},
    "core.opn.ventana_q2": {"es": "No es comprar de más: {n} productos de rotación alta se te terminan antes de la lista SIGUIENTE — esa compra de {compra} la hacés sí o sí. La única decisión es a qué precio.",
                             "en": "This is not overbuying: {n} fast-moving products run out before the list AFTER next — that {compra} purchase happens no matter what. The only decision is at which price."},
    "core.opn.ventana_q3": {"es": "Pagarla hoy, antes de la suba de {suba}%, ahorra ~{ahorro}.",
                             "en": "Paying it today, before the {suba}% rise, saves ~{ahorro}."},
    "core.opn.ventana_p3": {"es": "La inflación corriente ({ipc}% mensual, {fuente}) sostiene el patrón de subas.",
                             "en": "Current inflation ({ipc}% monthly, {fuente}) supports the price-rise pattern."},
    "core.opn.ventana_cob": {"es": "cobertura: {dias} días de venta", "en": "coverage: {dias} days of sales"},
    "core.opn.ventana_s1": {"es": "Supuesto: consumo estable (promedio de los últimos 12 meses).",
                             "en": "Assumption: stable consumption (12-month average)."},
    "core.opn.ventana_s3": {"es": "Supuesto: la próxima lista repite la suba (~{suba}%), como las últimas {n} listas del historial.",
                             "en": "Assumption: the next list repeats the rise (~{suba}%), like the last {n} lists on record."},
    "core.opn.ventana_g": {"es": "Subas de lista de {proveedor}", "en": "{proveedor} price-list increases"},
    "core.opn.ventana_g_v": {"es": "últimas {n} listas", "en": "last {n} lists"},
    "core.opn.window_purchase_ev": {"es": "Monto de la compra en esta ventana",
                                   "en": "Purchase amount in this window"},
    "core.opn.window_savings_ev": {"es": "Ahorro estimado por comprar ahora",
                                  "en": "Estimated savings from buying now"},
    # E2·piezas 7+8 — conocimiento de Aldo sobre el proveedor
    "core.opn.ventana_k_suba": {
        "es": "Vos me contaste que {proveedor} sube la lista todos los meses hace un año — por eso conviene comprar antes.",
        "en": "You told me {proveedor} raises its list every month for the past year — that's why buying ahead pays off."},
    "core.opn.ventana_k_viernes": {
        "es": "Te dejo el pedido en día hábil: los viernes no propongo pedidos, que el depósito está a media dotación, como me pediste.",
        "en": "I schedule the order on a full-staff day: I never propose Friday orders — the warehouse is short-staffed, as you asked."},
    "core.opn.ventana_k_viernes_mov": {
        "es": "Caía viernes; te lo corrí un día antes: los viernes el depósito está a media dotación, como me pediste.",
        "en": "It fell on a Friday, so I moved it a day earlier: Fridays the warehouse is short-staffed, as you asked."},
    # P27·A4 — el cliente que se enfría
    "core.opn.frio_t": {"es": "{nombre} se está enfriando", "en": "{nombre} is cooling off"},
    "core.opn.frio_r": {"es": "Tu {pos}° mejor cliente compró {pct}% menos que su histórico.",
                         "en": "Your #{pos} best customer bought {pct}% less than their usual."},
    "core.opn.frio_chat": {"es": "contame qué pasa con {nombre}: compró mucho menos que su histórico",
                            "en": "tell me what's going on with {nombre}: they bought far less than usual"},
    "core.opn.frio_q1": {"es": "{nombre} compró {actual} en los últimos 6 meses, cuando su ritmo histórico marcaba {esperado} — una caída del {pct}%.",
                          "en": "{nombre} bought {actual} in the last 6 months vs {esperado} at their historical pace — a {pct}% drop."},
    "core.opn.frio_q2": {"es": "Es tu {pos}° mejor cliente por historial: la diferencia son {monto} que dejaron de entrar.",
                          "en": "They're your #{pos} best customer by history: the gap is {monto} that stopped coming in."},
    "core.opn.frio_q2_lbl": {"es": "Caída de facturación vs. lo esperado (tu {pos}° mejor cliente)",
                              "en": "Revenue gap vs. expected (your #{pos} customer by history)"},
    "core.opn.frio_i": {"es": "compró {pct}% menos que su histórico", "en": "bought {pct}% less than their usual"},
    "core.opn.frio_s1": {"es": "Ventana: últimos {dias} días vs SU promedio histórico (los ciclos de compra en cuenta corriente son bimestrales; una ventana menor confunde ciclo con enfriamiento).",
                          "en": "Window: last {dias} days vs THEIR historical average (account purchase cycles run every other month; a shorter window confuses cycle with cooling)."},
    "core.opn.frio_g": {"es": "Compras de {nombre}, mes a mes", "en": "{nombre}'s purchases, month by month"},
    "core.opn.cooling_pace_ev": {"es": "Ritmo de compra actual del cliente",
                                "en": "Client's current purchase pace"},
    # P27·A8 — producto estrella en caída
    "core.opn.estrella_t": {"es": "Un producto estrella viene en caída", "en": "A star product is slipping"},
    "core.opn.estrella_r": {"es": "{producto} es tu #{pos} por facturación y cae hace {n} meses seguidos.",
                             "en": "{producto} is your #{pos} by revenue and has fallen {n} months straight."},
    "core.opn.estrella_r_lbl": {"es": "Meses seguidos de caída ({producto}, #{pos} por facturación)",
                                 "en": "Consecutive months of decline ({producto}, #{pos} by revenue)"},
    "core.opn.estrella_chat": {"es": "mostrame qué está pasando con {producto}: viene cayendo hace meses",
                                "en": "show me what's happening with {producto}: it's been falling for months"},
    "core.opn.estrella_q1": {"es": "{producto} (tu #{pos} por facturación) encadena {n} meses seguidos de caída; el último mes cerró en {ultimo}.",
                              "en": "{producto} (your #{pos} by revenue) is down {n} months in a row; last month closed at {ultimo}."},
    "core.opn.estrella_q2": {"es": "Contra el MISMO mes del año pasado ({prev}) son {perdida} menos por mes — no es estacionalidad.",
                              "en": "Against the SAME month last year ({prev}) that's {perdida} less per month — it's not seasonality."},
    "core.opn.estrella_q3": {"es": "Desde el arranque de la racha dejó de facturar ~{perdida} por mes.",
                              "en": "Since the streak began it stopped billing ~{perdida} per month."},
    "core.opn.estrella_loss_lbl": {"es": "Pérdida de facturación mensual",
                                    "en": "Monthly revenue loss"},
    "core.opn.estrella_i": {"es": "también cae hace {n} meses", "en": "also falling for {n} months"},
    "core.opn.estrella_s1": {"es": "Serie en pesos corrientes: con inflación, una caída nominal es una caída real aún mayor.",
                              "en": "Series in current pesos: with inflation, a nominal drop is an even bigger real drop."},
    # P27·A5 — quiebre inminente
    "core.opn.qi_t": {"es": "Te quedás sin {producto} en {dias} días", "en": "You run out of {producto} in {dias} days"},
    "core.opn.qi_r": {"es": "Es tu #{pos} por facturación. Pedilo hoy.", "en": "It's your #{pos} by revenue. Order it today."},
    "core.opn.qi_chat": {"es": "armame el pedido de {producto} antes de que se corte",
                          "en": "build my {producto} order before it runs out"},
    "core.opn.qi_q1": {"es": "Al ritmo real de venta, el stock de {producto} se agota en {dias} días — y es tu #{pos} por facturación.",
                        "en": "At the real sales pace, {producto}'s stock runs out in {dias} days — and it's your #{pos} by revenue."},
    "core.opn.qi_q2": {"es": "Cada semana sin él en la góndola son ~{semanal} que no facturás.",
                        "en": "Every week without it on the shelf is ~{semanal} you don't bill."},
    "core.opn.qi_i": {"es": "se agota en {dias} días (#{pos} por facturación)", "en": "runs out in {dias} days (#{pos} by revenue)"},
    "core.opn.qi_s1": {"es": "Supuesto: ritmo de venta estable (promedio de los últimos 12 meses).",
                        "en": "Assumption: stable sales pace (12-month average)."},
    "core.opn.stockout_count_ev": {"es": "Productos por quebrar", "en": "Products about to stock out"},
    "core.opn.weekly_revenue_ev": {"es": "Facturación semanal en juego",
                                  "en": "Weekly revenue at stake"},
    # P38·B — el quiebre con ANTICIPACIÓN: el tiempo del proveedor adentro del
    # cálculo. Lo que te queda menos lo que él tarda = los días que tenés para
    # negociar. Sin ese resto, "te quedan 7 días" no es una decisión.
    "core.opn.qi_t2": {"es": "Vas a quebrar stock de {producto} en ~{dias} días",
                        "en": "You're going to run out of {producto} in ~{dias} days"},
    "core.opn.qi_r2": {"es": "Tu #{pos} por facturación. El proveedor tarda {lead} días: te quedan {n} para negociar.",
                        "en": "Your #{pos} by revenue. The supplier takes {lead} days: you have {n} left to negotiate."},
    "core.opn.qi_q1b": {"es": "Vendés ~{u} {unidad} por mes de {producto}. Al ritmo actual te quedan ~{dias} días de stock, y {proveedor} tarda ~{lead} días en reponer.",
                         "en": "You sell ~{u} {unidad} a month of {producto}. At the current pace you have ~{dias} days of stock left, and {proveedor} takes ~{lead} days to restock."},
    "core.opn.qi_q2b": {"es": "Si esperás a que se acabe, vas a comprar apurado y caro.",
                         "en": "If you wait until it's gone, you'll buy in a rush and pay for it."},
    "core.opn.qi_q3_ventana": {"es": "Tenés {n} días para negociar con tiempo.",
                                "en": "You have {n} days to negotiate properly."},
    "core.opn.qi_q3_window_lbl": {"es": "Ventana para negociar", "en": "Negotiating window"},
    "core.opn.qi_q3_ventana_1": {"es": "Te queda un solo día de margen para negociar: mañana ya comprás apurado.",
                                  "en": "You have exactly one day of slack to negotiate: tomorrow you're buying in a rush."},
    "core.opn.qi_q3_justo": {"es": "Llegás justo: el pedido tiene que salir hoy para no quebrar.",
                              "en": "It's tight: the order has to go out today or you break."},
    "core.opn.qi_q3_tarde": {"es": "Ya vas {n} días tarde para llegar sin quiebre: el pedido tiene que salir hoy.",
                              "en": "You're already {n} days late to avoid the stock-out: the order has to go out today."},
    "core.opn.qi_r2_tarde": {"es": "Tu #{pos} por facturación y el proveedor tarda {lead} días: el pedido sale hoy.",
                              "en": "Your #{pos} by revenue and the supplier takes {lead} days: the order goes out today."},
    "core.opn.qi_u_unidades": {"es": "unidades", "en": "units"},
    "core.opn.qi_u_kg": {"es": "kg", "en": "kg"},
    "core.opn.qi_s2": {"es": "Supuesto: {lead} días de reposición (ese proveedor no tiene su plazo cargado).",
                        "en": "Assumption: {lead}-day lead time (that supplier has no term on file)."},
    "core.opn.qi_prop_t": {"es": "Preparar orden de compra", "en": "Draft the purchase order"},
    "core.opn.qi_prop_d": {"es": "{cant} {unidad} de {producto} a {proveedor}, para que entre antes del quiebre ({lead} días de reposición).",
                            "en": "{cant} {unidad} of {producto} from {proveedor}, so it lands before the stock-out ({lead}-day lead time)."},
    # The same three numbers already narrated in qi_q1b/qi_r2 prose, repeated
    # as scannable stat labels next to the chart (P·restock-refine).
    "core.opn.qi_m_coverage": {"es": "Cobertura", "en": "Coverage"},
    "core.opn.qi_m_lead": {"es": "Repone en", "en": "Restocks in"},
    "core.opn.qi_m_window": {"es": "Margen para negociar", "en": "Room to negotiate"},
    "core.opn.qi_m_days": {"es": "{n} días", "en": "{n} days"},
    "core.opn.qi_m_coverage_lbl": {"es": "Días de cobertura", "en": "Days of coverage"},
    "core.opn.qi_m_lead_lbl": {"es": "Lead time del proveedor", "en": "Supplier lead time"},
    "core.opn.qi_m_today": {"es": "sale hoy", "en": "ships today"},
    "core.opn.qi_m_late": {"es": "{n} días tarde", "en": "{n} days late"},
    # E2 — línea genérica de conocimiento en el porqué de una card
    "core.opn.k_ensenaste": {"es": "Vos me enseñaste: «{texto}».", "en": "You taught me: “{texto}”."},
    # E2·pieza 11 — la regla de Aldo hace crítico al quiebre
    "core.opn.qi_k_chip": {"es": "Regla de Aldo: crítico", "en": "Aldo's rule: critical"},
    "core.opn.qi_k_por": {"es": "Me lo marcaste crítico: «{texto}» — por eso va primero.",
                          "en": "You flagged it critical: “{texto}” — that's why it's first."},
    # P27·A6 — pre-pico estacional
    "core.opn.pico_t": {"es": "Pre-pico estacional — {cat}", "en": "Seasonal pre-peak — {cat}"},
    "core.opn.pico_r": {"es": "{mes} multiplica ×{idx} tu venta de {cat}; a ritmo de pico cubrís {dias} días — la compra grande se planifica en {plan}.",
                         "en": "{mes} multiplies your {cat} sales ×{idx}; at peak pace you cover {dias} days — the big buy gets planned in {plan}."},
    "core.opn.pico_chat": {"es": "planificame la compra de {cat} para el pico de {mes}",
                            "en": "plan my {cat} purchase for the {mes} peak"},
    "core.opn.pico_q1": {"es": "En {anios} años de historia, {mes} multiplica ×{idx} la venta de {cat} — pasa todos los años, no es una corazonada.",
                          "en": "Across {anios} years of history, {mes} multiplies {cat} sales ×{idx} — it happens every year, it's not a hunch."},
    "core.opn.pico_q2": {"es": "Con el stock de hoy, a ritmo de pico cubrís {dias} días.",
                          "en": "With today's stock, at peak pace you cover {dias} days."},
    "core.opn.pico_q2_lbl": {"es": "Días de cobertura a ritmo de pico",
                              "en": "Days of coverage at peak pace"},
    "core.opn.pico_q3": {"es": "La compra del mes de pico ronda {compra}. Nada urge hoy: se planifica en {plan}, con el proveedor y el precio negociados.",
                          "en": "The peak-month purchase is around {compra}. Nothing is urgent today: it gets planned in {plan}, with supplier and price negotiated."},
    "core.opn.pico_q3_lbl": {"es": "Compra estimada para el pico (a planificar en {plan})",
                              "en": "Estimated peak-month purchase (to plan for {plan})"},
    "core.opn.pico_s1": {"es": "Supuesto: el pico repite el patrón histórico (índice normalizado por año: la inflación no lo ensucia).",
                          "en": "Assumption: the peak repeats the historical pattern (index normalized per year: inflation doesn't distort it)."},
    "core.opn.peak_multiplier_lbl": {"es": "Multiplicador de pico estacional",
                                      "en": "Seasonal peak multiplier"},
    "core.opn.pico_g": {"es": "Estacionalidad de {cat} (índice por mes)", "en": "{cat} seasonality (index by month)"},
    "core.opn.pico_g_v": {"es": "{anios} años de historia", "en": "{anios} years of history"},
    # P27·A7 — concentración de clientes
    "core.opn.conc_t": {"es": "3 clientes concentran demasiado", "en": "3 customers carry too much"},
    "core.opn.client_concentration_lbl": {"es": "Concentración en los principales clientes",
                                           "en": "Concentration in top clients"},
    "core.opn.conc_monto_label": {"es": "facturado en 12 meses (no es deuda)",
                                   "en": "billed over 12 months (not debt)"},
    "core.opn.conc_r": {"es": "El {pct}% de tu facturación en cuenta corriente de los últimos 12 meses — {monto} — está en 3 clientes. Es exposición, no plata a cobrar: si uno se cae, duele.",
                         "en": "{pct}% of your account-sales revenue over the last 12 months — {monto} — sits with 3 customers. It's exposure, not cash to collect: if one drops, it hurts."},
    "core.opn.conc_chat": {"es": "cómo hago para depender menos de mis 3 clientes más grandes",
                            "en": "how do I depend less on my 3 biggest customers"},
    "core.opn.conc_q1": {"es": "Tus 3 clientes más grandes suman {monto}: el {pct}% de todo lo facturado en cuenta corriente en 12 meses.",
                          "en": "Your 3 biggest customers add up to {monto}: {pct}% of everything billed on account in 12 months."},
    "core.opn.conc_q2": {"es": "Si uno solo se cae, el agujero es serio. Diversificar es defensa: sumar clientes medianos baja el riesgo sin resignar volumen.",
                          "en": "If just one drops, the hole is serious. Diversifying is defense: adding mid-size customers lowers the risk without giving up volume."},
    "core.opn.conc_i": {"es": "{pct}% de tu facturación en cuenta corriente", "en": "{pct}% of your account-sales revenue"},
    "core.opn.conc_s1": {"es": "Base declarada: ventas en cuenta corriente de los últimos 12 meses (los movimientos por cliente; el mostrador no identifica cliente).",
                          "en": "Declared base: account sales over the last 12 months (per-customer movements; counter sales don't identify a customer)."},
    "core.opn.conc_g": {"es": "Participación de tus 5 clientes más grandes", "en": "Share of your 5 biggest customers"},
    "core.opn.conc_g_v": {"es": "últimos 12 meses", "en": "last 12 months"},
    "core.opn.margen_g": {"es": "Ganancia extra por mes si van al promedio", "en": "Extra profit per month at category average"},
    # P27·A — las fuentes cruzadas ("Crucé: …")
    "core.opn.f_cuentas": {"es": "cuentas corrientes", "en": "customer accounts"},
    "core.opn.f_movs": {"es": "movimientos históricos por cliente", "en": "per-customer history"},
    "core.opn.f_ventas12": {"es": "ventas de 12 meses", "en": "12-month sales"},
    "core.opn.f_ventas24": {"es": "ventas por producto (24 meses)", "en": "per-product sales (24 months)"},
    # --- Task 8: structured insight — deadlines and one relabeled baseline -----
    "core.opn.ventana_deadline_basis": {
        "es": "Vence cuando llegue la próxima lista de {proveedor}.",
        "en": "Due when {proveedor}'s next price list lands."},
    "core.opn.qi_deadline_basis": {
        "es": "El proveedor tarda {lead} días en reponer: pedilo para esta fecha o menos.",
        "en": "The supplier takes {lead} days to restock: order by this date or sooner."},
    "core.opn.pico_deadline_basis": {
        "es": "Arranca el pico estacional de {mes}.",
        "en": "The {mes} seasonal peak begins."},
    "core.opn.margen_prom_label": {"es": "promedio de su categoría", "en": "category average"},
    "core.opn.margin_gap_lbl": {"es": "Margen actual vs. el promedio de su categoría",
                                 "en": "Current margin vs. category average"},
    # --- Task 8: structured insight — new method explanations ------------------
    "core.method.debtor_payment_curve": {
        "es": "Pagos registrados del cliente, mes a mes, con los meses sin pago en cero.",
        "en": "The client's recorded payments, month by month, with no-payment months at zero."},
    "core.method.dormant_value": {
        "es": "Valor inmovilizado (cantidad × costo) de los productos sin rotación real en el período analizado.",
        "en": "Immobilized value (quantity × cost) of products with no real turnover in the analyzed period."},
    "core.method.dormant_products": {
        "es": "Productos sin rotación real, ordenados por valor inmovilizado.",
        "en": "Products with no real turnover, sorted by immobilized value."},
    "core.method.dormant_top5_value": {
        "es": "Suma del valor inmovilizado de los 5 productos con mayor plata parada.",
        "en": "Sum of the immobilized value of the 5 products with the most money sitting idle."},
    "core.method.window_purchase": {
        "es": "Faltante proyectado hasta la lista siguiente (ritmo de venta × frecuencia de lista, menos el stock que va a quedar), valuado al costo actual.",
        "en": "Projected shortfall through the following price list (sales pace × list frequency, minus the stock left over), valued at current cost."},
    "core.method.window_savings": {
        "es": "Monto de la compra segura multiplicado por la suba promedio de la última lista del proveedor.",
        "en": "The safe-purchase amount multiplied by the supplier's average recent price-list increase."},
    "core.method.price_rise_history": {
        "es": "Suba promedio de cada lista de precios del proveedor, en orden cronológico.",
        "en": "The average increase of each of the supplier's price lists, in chronological order."},
    "core.method.client_cooling": {
        "es": "Compras del cliente en los últimos {dias} días contra su propio promedio histórico proyectado a la misma ventana.",
        "en": "The client's purchases in the last {dias} days against their own historical average projected to the same window."},
    "core.method.client_cooling_gap": {
        "es": "Diferencia entre lo que el cliente compraría a su ritmo histórico y lo que compró en la ventana.",
        "en": "The gap between what the client would buy at their historical pace and what they actually bought in the window."},
    "core.method.streak_decline": {
        "es": "Meses consecutivos de facturación en baja para ese producto, sobre la serie mensual completa.",
        "en": "Consecutive months of declining revenue for that product, over the full monthly series."},
    "core.method.streak_loss": {
        "es": "Facturación del último mes contra el mismo mes del año anterior (o, si no cayó interanual, contra el arranque de la racha).",
        "en": "Last month's revenue against the same month last year (or, if it didn't drop year over year, against the start of the streak)."},
    "core.method.qi_stockout": {
        "es": "Productos del ranking de facturación cuya cobertura proyectada cae dentro de la ventana de quiebre inminente.",
        "en": "Top-revenue products whose projected coverage falls within the imminent-stockout window."},
    "core.method.qi_weekly_revenue": {
        "es": "Facturación de los últimos 12 meses del producto dividida en 52 semanas.",
        "en": "The product's trailing-12-month revenue divided across 52 weeks."},
    "core.method.days_of_coverage": {
        "es": "Stock proyectado dividido por el ritmo de venta diario del producto.",
        "en": "Projected stock divided by the product's daily sales pace."},
    "core.method.supplier_lead_time": {
        "es": "Días que ese proveedor tarda en reponer, según su historial de entregas.",
        "en": "Days that supplier takes to restock, based on their delivery history."},
    "core.method.negotiating_window": {
        "es": "Días de cobertura menos el tiempo de reposición del proveedor.",
        "en": "Days of coverage minus the supplier's lead time."},
    "core.method.critical_rule": {
        "es": "Regla declarada por el dueño marcando este producto como crítico.",
        "en": "An owner-declared rule flagging this product as critical."},
    "core.method.peak_purchase": {
        "es": "Faltante proyectado para cubrir el mes de pico al ritmo esperado, menos el stock actual, valuado al costo.",
        "en": "Projected shortfall to cover the peak month at expected pace, minus current stock, valued at cost."},
    "core.method.peak_coverage": {
        "es": "Stock actual de la categoría dividido por el ritmo de venta proyectado en el pico.",
        "en": "The category's current stock divided by the projected sales pace at the peak."},
    "core.method.client_concentration": {
        "es": "Facturación en cuenta corriente de los últimos 12 meses de los 3 clientes más grandes, sobre el total.",
        "en": "Last-12-month account-sales revenue of the 3 biggest customers, over the total."},
    "core.method.margin_gap": {
        "es": "Margen del producto (PVP menos costo con IVA, sobre PVP) contra el promedio de su categoría.",
        "en": "The product's margin (PVP minus cost with VAT, over PVP) against its category average."},
    "core.method.margin_extra_profit": {
        "es": "Unidades vendidas por mes multiplicadas por la diferencia entre el precio que igualaría el promedio de categoría y el precio actual.",
        "en": "Units sold per month multiplied by the gap between the price that would match the category average and the current price."},
    "core.method.margin_extra_total": {
        "es": "Suma de la ganancia extra mensual de todos los productos con margen por debajo del promedio de su categoría.",
        "en": "Sum of the extra monthly profit across every product priced below its category's average margin."},
    "core.method.overbuy_waste": {
        "es": "Cantidad de la oferta que no se vende antes de que venza el lote, valuada al costo con el descuento de la oferta.",
        "en": "The portion of the deal that won't sell before the lot expires, valued at cost net of the deal's discount."},
    "core.method.overbuy_savings": {
        "es": "Cantidad absorbible antes del vencimiento, multiplicada por el descuento de la oferta.",
        "en": "The quantity absorbable before expiration, multiplied by the deal's discount."},
    # --- core/cruces.py · los hallazgos que cruzan 3+ dominios -----------------
    # Fuentes (las etiquetas de "Crucé: …")
    "core.cru.f_ventas_cliente": {"es": "qué compra cada cliente",
                                   "en": "what each customer buys"},
    "core.cru.f_vencimientos": {"es": "lotes por vencer del depósito",
                                 "en": "warehouse lots nearing expiry"},
    "core.cru.f_notas": {"es": "notas del equipo a Ángela (voz, reportes y chat)",
                          "en": "team notes to Ángela (voice, floor reports and chat)"},
    "core.cru.f_condiciones": {"es": "condiciones del proveedor",
                                "en": "supplier terms"},
    "core.cru.f_logistica": {"es": "entregas y remitos", "en": "deliveries and notes"},
    "core.cru.f_wms": {"es": "ubicaciones del depósito", "en": "warehouse locations"},
    "core.cru.f_ordenes": {"es": "órdenes de compra abiertas", "en": "open purchase orders"},

    # 1 · cuentas × ventas × depósito
    "core.cru.deuda_venc_t": {
        "es": "{cliente} te debe — y se lleva justo lo que se vence",
        "en": "{cliente} owes you — and buys exactly what's about to expire"},
    "core.cru.deuda_venc_r": {
        "es": "Hace {dias_deuda} días que no paga y {producto} se vence en {dias}. Es el mismo producto que te compra.",
        "en": "{dias_deuda} days without paying, and {producto} expires in {dias}. It's the very product they buy from you."},
    "core.cru.deuda_venc_p1": {
        "es": "{cliente} tiene {saldo} vencidos hace {dias} días.",
        "en": "{cliente} has {saldo} overdue for {dias} days."},
    "core.cru.deuda_venc_p2": {
        "es": "{producto} vence en {dias} días y te sobran {sobra} unidades al ritmo actual: {plata} que se tiran.",
        "en": "{producto} expires in {dias} days and {sobra} units are left over at the current pace: {plata} down the drain."},
    "core.cru.deuda_venc_p3": {
        "es": "No es un producto cualquiera para él: {cliente} ya se llevó {unidades} unidades de ese mismo artículo ({monto}) en {pedidos} pedidos.",
        "en": "It's not just any product for them: {cliente} has already taken {unidades} units of that same item ({monto}) across {pedidos} orders."},
    "core.cru.deuda_venc_i": {"es": "vence en {dias} días · lote {lote}",
                               "en": "expires in {dias} days · lot {lote}"},
    "core.cru.deuda_venc_chat": {
        "es": "armame la propuesta para {cliente}: que sald e parte de la deuda llevándose el {producto} antes de que se venza",
        "en": "draft the offer for {cliente}: settle part of the debt by taking the {producto} before it expires"},

    # 2 · proveedores × ventas × inventario (+ notas)
    "core.cru.prov_estrella_t": {
        "es": "{proveedor} hace ruido — y es el que te surte tu estrella",
        "en": "{proveedor} is wobbling — and they supply your best seller"},
    "core.cru.prov_estrella_r": {
        "es": "{producto} es tu #{pos} en facturación y sale sólo de ahí. Repone en {dias} días.",
        "en": "{producto} is your #{pos} by revenue and comes only from them. They restock in {dias} days."},
    "core.cru.prov_estrella_p1": {
        "es": "{proveedor} te provee {n} productos que facturan {fact} en 12 meses.",
        "en": "{proveedor} supplies {n} products worth {fact} over 12 months."},
    "core.cru.prov_estrella_p2": {
        "es": "Entre ellos {producto}, tu #{pos} del ranking. Si se corta, tardás {dias} días en reponerlo.",
        "en": "Among them {producto}, your #{pos} seller. If it stops, it takes {dias} days to restock."},
    "core.cru.prov_estrella_p3": {
        "es": "{autor} ya lo había anotado: «{texto}»",
        "en": "{autor} had already flagged it: “{texto}”"},
    "core.cru.prov_estrella_p4": {
        "es": "En {rubro} tenés otros {n} proveedores: hay con quién cubrirse, pero hay que hablarlo antes.",
        "en": "You have {n} other suppliers in {rubro}: there's cover, but it has to be arranged in advance."},
    "core.cru.prov_estrella_p4_solo": {
        "es": "En {rubro} no tenés otro proveedor cargado: hoy la dependencia es total.",
        "en": "You have no other supplier loaded for {rubro}: today the dependency is total."},
    "core.cru.prov_estrella_i": {"es": "repone en {dias} días · {n} productos",
                                  "en": "restocks in {dias} days · {n} products"},
    "core.cru.prov_estrella_i2": {"es": "#{pos} en facturación", "en": "#{pos} by revenue"},
    "core.cru.prov_estrella_chat": {
        "es": "¿qué hago con {proveedor} antes de que me deje sin stock?",
        "en": "what should I do about {proveedor} before they leave me without stock?"},

    # 3 · cuentas × historial de pago × ventas
    "core.cru.credito_t": {"es": "A {cliente} le vendés más y te paga más tarde",
                            "en": "You sell {cliente} more, and they pay you later"},
    "core.cru.credito_r": {
        "es": "Pasó de pagar a {viejo} días a pagar a {nuevo}, y ya usa el {pct}% de su límite.",
        "en": "Went from paying in {viejo} days to {nuevo}, and already uses {pct}% of their limit."},
    "core.cru.credito_p1": {
        "es": "En sus {n} pagos registrados, la demora pasó de {viejo} a {nuevo} días.",
        "en": "Across their {n} recorded payments, the delay went from {viejo} to {nuevo} days."},
    "core.cru.credito_p2": {
        "es": "Y en el mismo período el pedido promedio subió de {viejo} a {nuevo}.",
        "en": "Over the same period the average order grew from {viejo} to {nuevo}."},
    "core.cru.credito_p3": {
        "es": "Hoy debe {saldo} sobre un límite de {limite}: {pct}% usado.",
        "en": "Today they owe {saldo} against a {limite} limit: {pct}% used."},
    "core.cru.credito_i": {"es": "{pct}% del límite usado", "en": "{pct}% of the limit used"},
    "core.cru.credito_i2": {"es": "{pct}% de lo que se lleva", "en": "{pct}% of what they take"},
    "core.cru.credito_chat": {
        "es": "¿qué plazo y qué límite le pongo a {cliente}?",
        "en": "what terms and limit should I set for {cliente}?"},

    # 4 · notas × ventas × logística
    "core.cru.queja_t": {"es": "Se quejó {cliente}, y es de los que más te compran",
                          "en": "{cliente} complained — and they're one of your top buyers"},
    "core.cru.queja_r": {
        "es": "{autor} lo anotó esta semana. Es tu cliente #{pos} por volumen.",
        "en": "{autor} logged it this week. They're your #{pos} customer by volume."},
    "core.cru.queja_p1": {"es": "{autor} lo dejó por {canal} el {fecha}: «{texto}»",
                           "en": "{autor} left it by {canal} on {fecha}: “{texto}”"},
    "core.cru.queja_p2": {
        "es": "{cliente} es el #{pos} por lo que compra: {monto} en su historial.",
        "en": "{cliente} ranks #{pos} by purchases: {monto} across their history."},
    "core.cru.queja_p3": {"es": "Y todavía tiene {n} entrega(s) pendiente(s) sin salir.",
                           "en": "And they still have {n} delivery(ies) pending."},
    "core.cru.queja_p3_sin": {"es": "No tiene entregas pendientes: el momento de llamarlo es ahora.",
                               "en": "No deliveries pending: now is the moment to call them."},
    "core.cru.queja_p4": {"es": "Además debe {saldo} hace {dias} días.",
                           "en": "They also owe {saldo} for {dias} days."},
    "core.cru.queja_i": {"es": "cliente #{pos} por volumen", "en": "#{pos} customer by volume"},
    "core.cru.queja_chat": {"es": "¿cómo destrabo lo de {cliente}?",
                             "en": "how do I sort things out with {cliente}?"},

    # 5 · notas × cuentas × ventas
    "core.cru.problemas_t": {"es": "{cliente} puede estar en problemas",
                              "en": "{cliente} may be in trouble"},
    "core.cru.problemas_r": {
        "es": "El reparto lo encontró cerrado {n} veces y lleva {dias} días sin pagar.",
        "en": "Delivery found them shut {n} times and they're {dias} days without paying."},
    "core.cru.problemas_p1": {
        "es": "{n} observaciones del reparto ({autor}) en {fechas}.",
        "en": "{n} field observations from delivery ({autor}) on {fechas}."},
    "core.cru.problemas_p2": {"es": "La última: «{texto}»", "en": "The latest: “{texto}”"},
    "core.cru.problemas_p3": {
        "es": "En la cuenta: {saldo} sin pagar hace {dias} días, con plazo de {plazo}.",
        "en": "On the account: {saldo} unpaid for {dias} days, on {plazo}-day terms."},
    "core.cru.problemas_i": {"es": "{n} veces cerrado", "en": "shut {n} times"},
    "core.cru.problemas_chat": {
        "es": "¿qué hago con {cliente} antes de mandarle otro pedido?",
        "en": "what should I do about {cliente} before sending another order?"},

    # 6 · notas × depósito × compras
    "core.cru.espacio_t": {"es": "No entra más nada en {ubicacion} y viene un pedido",
                            "en": "Nothing else fits in {ubicacion}, and an order is coming"},
    "core.cru.espacio_r": {
        "es": "El equipo lo dijo {n} veces esta semana y la orden {orden} sigue abierta.",
        "en": "The team said it {n} times this week and order {orden} is still open."},
    "core.cru.espacio_p1": {
        "es": "{n} avisos del equipo ({quienes}) sobre {ubicacion}.",
        "en": "{n} heads-ups from the team ({quienes}) about {ubicacion}."},
    "core.cru.espacio_p2": {"es": "Hoy hay {lotes} lotes cargados en {ubicacion}.",
                             "en": "There are {lotes} lots currently in {ubicacion}."},
    "core.cru.espacio_p3": {
        "es": "La orden {orden} a {proveedor} sigue abierta con {n} renglones por entrar.",
        "en": "Order {orden} to {proveedor} is still open with {n} lines to come in."},
    "core.cru.espacio_p4": {
        "es": "Y ahí mismo hay {n} lote(s) por vencer: {plata} que conviene sacar antes.",
        "en": "And right there sit {n} lot(s) about to expire: {plata} worth clearing first."},
    "core.cru.espacio_i": {"es": "orden {orden} abierta", "en": "order {orden} open"},
    "core.cru.espacio_i2": {"es": "{cantidad} por entrar", "en": "{cantidad} to come in"},
    "core.cru.espacio_chat": {
        "es": "¿cómo hago lugar en {ubicacion} antes de que llegue el pedido?",
        "en": "how do I make room in {ubicacion} before the order lands?"},

    "core.opn.f_ventas10a": {"es": "10 años de ventas", "en": "10 years of sales"},
    "core.opn.f_stock": {"es": "stock actual", "en": "current stock"},
    "core.opn.f_costos": {"es": "costos y precios", "en": "costs and prices"},
    "core.opn.f_lista": {"es": "lista del proveedor", "en": "supplier price list"},
    "core.opn.f_ipc": {"es": "IPC (INDEC)", "en": "CPI (INDEC)"},
    "core.opn.f_rank": {"es": "ranking de facturación", "en": "revenue ranking"},
    "core.opn.f_estacion": {"es": "estacionalidad por categoría", "en": "seasonality by category"},
    "core.opn.f_lead": {"es": "tiempo de reposición del proveedor", "en": "supplier lead time"},
    # P38·D — sobrecompra: la oferta cruzada contra la rotación real
    "core.opn.sobre_t": {"es": "{proveedor} te ofrece {producto} con {desc}% off — ojo con la cantidad",
                          "en": "{proveedor} is offering {producto} at {desc}% off — mind the quantity"},
    "core.opn.sobre_monto_label": {"es": "que ibas a tirar", "en": "you'd have thrown out"},
    "core.opn.sobre_r": {"es": "Tardarías {meses} meses en venderlo y el lote vence en {dias} días. Te conviene comprar {sug}.",
                          "en": "It'd take you {meses} months to sell and the batch expires in {dias} days. You're better off buying {sug}."},
    "core.opn.sobre_chat": {"es": "¿cuánto de {producto} me conviene comprar en esta oferta?",
                             "en": "how much {producto} should I actually buy on this deal?"},
    "core.opn.sobre_piezas": {"es": " (≈{n} piezas)", "en": " (≈{n} pieces)"},
    "core.opn.sobre_q1": {"es": "{proveedor} te ofrece {oferta} de {producto} con {desc}% de descuento.",
                           "en": "{proveedor} is offering {oferta} of {producto} at {desc}% off."},
    "core.opn.sobre_q2": {"es": "Vendés ~{u} {unidad} por mes: esa cantidad son {meses} meses de venta, y el lote que te ofrecen vence en {dias} días.",
                           "en": "You sell ~{u} {unidad} a month: that quantity is {meses} months of sales, and the batch they're offering expires in {dias} days."},
    "core.opn.sobre_q3": {"es": "O sea que {sobrante} {unidad} se te vencerían en el depósito: {tirar} a la basura, con descuento y todo.",
                           "en": "Which means {sobrante} {unidad} would expire in your warehouse: {tirar} in the bin, discount and all."},
    "core.opn.sobre_q3_lbl": {"es": "Valor a pérdida: {sobrante} {unidad} que vencerían sin vender",
                               "en": "Value at risk: {sobrante} {unidad} that would expire unsold"},
    "core.opn.sobre_q4": {"es": "Comprando {sug} aprovechás el descuento en todo lo que SÍ vas a vender: {ahorro} de ahorro real, sin tirar nada.",
                           "en": "Buying {sug} you get the discount on everything you WILL sell: {ahorro} of real savings, nothing wasted."},
    "core.opn.sobre_q4_lbl": {"es": "Ahorro por comprar {sug} aprovechando el descuento",
                               "en": "Savings from buying {sug} at the discount"},
    "core.opn.sobre_g": {"es": "La oferta contra lo que vendés ({unidad})", "en": "The offer against what you sell ({unidad})"},
    "core.opn.sobre_g_oferta": {"es": "Te ofrecen", "en": "Offered"},
    "core.opn.sobre_g_vendible": {"es": "Vendés antes del vto.", "en": "You sell before expiry"},
    "core.opn.sobre_g_stock": {"es": "Ya tenés", "en": "Already in stock"},
    "core.opn.sobre_s1": {"es": "Supuesto: el lote ofrecido vence el {fecha} (dato del proveedor).",
                           "en": "Assumption: the offered batch expires on {fecha} (supplier's data)."},
    "core.opn.sobre_prop_t": {"es": "Pedir sólo lo que se vende", "en": "Order only what sells"},
    "core.opn.sobre_prop_d": {"es": "Orden de {sug} de {producto} a {proveedor}, en vez de las {oferta} que te empujan.",
                               "en": "Order {sug} of {producto} from {proveedor}, instead of the {oferta} they're pushing."},

    # --- core/patrones.py — continuous learning: patterns nobody asked to have calculated --
    "core.pat.combo_t": {
        "es": "{a} y {b} viajan juntos casi siempre",
        "en": "{a} and {b} almost always travel together"},
    "core.pat.combo_r_falta": {
        "es": "{pct}% de los pedidos con {a} también llevan {b} — pero {n} no, y ahí se está perdiendo una venta cruzada.",
        "en": "{pct}% of the orders with {a} also carry {b} — but {n} didn't, and that's a missed cross-sell."},
    "core.pat.combo_r_conjunto": {
        "es": "{pct}% de los pedidos con {a} también llevan {b}: un combo tácito que nadie armó todavía.",
        "en": "{pct}% of the orders with {a} also carry {b}: an unofficial combo nobody's set up yet."},
    "core.pat.combo_rate_lbl": {
        "es": "Tasa de coocurrencia del combo",
        "en": "Combo co-occurrence rate"},
    "core.pat.combo_monto_label_potencial": {
        "es": "venta cruzada sin aprovechar", "en": "unrealized cross-sell"},
    "core.pat.combo_monto_label_conjunto": {
        "es": "facturación conjunta ya detectada", "en": "combined revenue already detected"},
    "core.pat.combo_chat": {
        "es": "Contame más sobre el combo de {a} y {b}.",
        "en": "Tell me more about the {a} and {b} combo."},
    "core.pat.combo_q1": {
        "es": "Crucé los {n} pedidos de los últimos {clientes} clientes que llevaron {a}: {pct}% de esas veces, {b} viajó en el mismo pedido. Eso no es casualidad — nadie lo cargó como combo, pero el patrón está en los datos.",
        "en": "I crossed the {n} orders from the {clientes} customers who bought {a}: {pct}% of those times, {b} rode along in the same order. That's not chance — nobody set it up as a combo, but the pattern is right there in the data."},
    "core.pat.combo_q2_falta": {
        "es": "Las {n} veces que faltó, es plata que se dejó arriba del mostrador: armar el combo (o simplemente ofrecerlo al cerrar el pedido) puede cerrar esa brecha.",
        "en": "The {n} times it was missing, that's money left on the counter: setting up the combo (or just offering it when closing the order) can close that gap."},
    "core.pat.combo_q2_conjunto": {
        "es": "Hoy esa plata ya entra, pero entra como dos ventas sueltas: empaquetarla (o negociarla junta con el proveedor) puede subir el ticket promedio de quien ya compra los dos.",
        "en": "That money already comes in today, but as two separate sales: bundling it (or negotiating it jointly with the supplier) can lift the average ticket for whoever already buys both."},
    "core.pat.combo_i_falta": {
        "es": "se llevó {a} el {fecha} sin {b}", "en": "bought {a} on {fecha} without {b}"},
    "core.pat.combo_i_conjunto": {
        "es": "{fecha}: se llevó los dos juntos", "en": "{fecha}: bought both together"},
    "core.pat.combo_s1": {
        "es": "Supuesto: cruce sobre los pedidos abiertos en renglones (qué se lleva cada cliente), no sobre el total facturado.",
        "en": "Assumption: crossed over itemized orders (what each customer takes home), not over total billing."},
    "core.pat.combo_g": {"es": "Pedidos con {a}", "en": "Orders with {a}"},
    "core.pat.combo_g_con": {"es": "con {b}", "en": "with {b}"},
    "core.pat.combo_g_sin": {"es": "sin {b}", "en": "without {b}"},
    "core.pat.combo_amount_ev": {"es": "Monto combinado de la pareja de productos",
                                "en": "Combined amount for the product pair"},

    "core.pat.caja_t": {
        "es": "Cada {dia} la caja falta mucho más que el resto de la semana",
        "en": "Every {dia} the till comes up short far more than the rest of the week"},
    "core.pat.caja_r": {
        "es": "Faltó en el {pct}% de los cierres de {dia} (vs {pct_resto}% el resto), {total} acumulado en {n} cierres.",
        "en": "Came up short in {pct}% of {dia} closes (vs {pct_resto}% the rest of the week), {total} accumulated over {n} closes."},
    "core.pat.caja_r_lbl": {
        "es": "Faltante los {dia} vs. el resto de la semana ({total} en {n} cierres)",
        "en": "Shortfall rate on {dia}s vs. the rest of the week ({total} across {n} closes)"},
    "core.pat.caja_chat": {
        "es": "¿Por qué falta tanto la caja los días {dia}?",
        "en": "Why does the till come up short so often on {dia}s?"},
    "core.pat.caja_q1": {
        "es": "De los últimos {n} cierres de {dia}, {faltan} tuvieron faltante — {pct}% de las veces, contra {pct_resto}% el resto de los días de la semana.",
        "en": "Of the last {n} {dia} closes, {faltan} came up short — {pct}% of the time, against {pct_resto}% the rest of the week."},
    "core.pat.caja_q2": {
        "es": "Nadie lo comparó día por día antes: el promedio general de la semana lo tapa. Sumado, son {total} que se fueron sin explicación los días {dia} de este período.",
        "en": "Nobody compared it day-by-day before: the week's overall average hides it. Added up, that's {total} that went unexplained on {dia}s in this period."},
    "core.pat.caja_s1": {
        "es": "Supuesto: compara el faltante promedio de cada día de la semana contra el resto, sobre el historial de cierres disponible.",
        "en": "Assumption: compares each weekday's average shortfall against the rest, over the available close history."},
    "core.pat.caja_i": {
        "es": "{fecha}: faltaron {monto}", "en": "{fecha}: short by {monto}"},
    "core.pat.caja_g": {"es": "Faltante por cierre", "en": "Shortfall per close"},
    "core.pat.shortfall_total_ev": {"es": "Total de faltantes de caja ese día",
                                   "en": "Total cash shortfall on that day"},
    "core.pat.caja_hyp": {
        "es": "Parece algo propio del {dia} — un problema de proceso ese día puntual, no ruido repartido entre toda la semana.",
        "en": "It looks like something specific to {dia}s — a process gap on that particular day, not noise spread across the week."},
    "core.pat.caja_alt1": {
        "es": "Puede ser un tema de quién atiende ese día, no del día en sí: si suele cerrar caja la misma persona los {dia}, el patrón podría seguir a quien trabaja, no a la fecha.",
        "en": "It might be about who's working that day, not the day itself: if the same person usually closes the till on {dia}s, the pattern could be tracking the employee, not the date."},
    "core.pat.caja_baseline": {
        "es": "% de faltante el resto de la semana", "en": "% short the rest of the week"},

    # --- structured insight (Task 9): pattern/hypothesis/alternatives for the combo card --
    "core.pat.combo_pattern": {
        "es": "En los últimos {n} pedidos de los {clientes} clientes que llevaron {a}, {b} viajó en el mismo pedido el {pct}% de las veces — {lift}× más seguido de lo que explicaría el azar.",
        "en": "Across the last {n} orders from the {clientes} customers who bought {a}, {b} rode along in the same order {pct}% of the time — {lift}× more often than chance would explain."},
    "core.pat.combo_hyp_falta": {
        "es": "Eso no es casualidad: parece demanda complementaria real, y las {n} veces que faltó son venta cruzada que se está dejando sobre el mostrador.",
        "en": "That's not chance: it looks like real complementary demand, and the {n} times it was missing are cross-sell being left on the counter."},
    "core.pat.combo_hyp_conjunto": {
        "es": "Eso no es casualidad: parece demanda complementaria real que hoy ya entra, pero como dos ventas sueltas en vez de un combo armado.",
        "en": "That's not chance: it looks like real complementary demand that already comes in today, but as two separate sales instead of a bundled one."},
    "core.pat.combo_alt1": {
        "es": "Puede que los dos productos simplemente vendan más en la misma época del año, sin que exista una relación real de compra conjunta entre clientes.",
        "en": "The two products may simply sell more during the same time of year, with no real joint-purchase relationship between customers."},
    "core.method.combo_cooccurrence": {
        "es": "Tasa de coocurrencia en pedidos: pedidos con ambos productos ÷ pedidos con el producto ancla.",
        "en": "Order co-occurrence rate: orders with both products ÷ orders with the anchor product."},
    "core.method.combo_gap_amount": {
        "es": "Pedidos sin la pareja × el monto promedio que agrega la pareja cuando sí aparece.",
        "en": "Orders missing the partner × the average amount the partner adds when it does appear."},
    "core.method.combo_combined_amount": {
        "es": "Suma de lo facturado por ambos productos en los pedidos donde viajaron juntos.",
        "en": "Sum of what both products billed in the orders where they traveled together."},
    "core.method.weekday_shortfall_rate": {
        "es": "% de cierres de ese día de la semana con faltante, contra el % del resto de los días.",
        "en": "% of that weekday's closes that came up short, against the % for the rest of the week."},
    "core.method.weekday_shortfall_total": {
        "es": "Suma de los faltantes de ese día de la semana en el historial analizado.",
        "en": "Sum of that weekday's shortfalls over the analyzed history."},

    # P38·C — los grupos del canal MOSTRADOR (locales propios). El mismo fiambre
    # feteado o entero son dos negocios distintos: por eso son dos grupos.
    # P38·H — vencimientos gestionados (no un campo que nadie mira)
    "core.venc.sin_deposito": {
        "es": "Todavía no tengo el detalle del depósito con lotes y vencimientos. "
              "Se carga con el export del sistema de depósito por «Cargar datos».",
        "en": "I don't have the warehouse detail with batches and expiry dates yet. "
              "It loads from your warehouse system's export via \"Load data\".",
    },
    "core.venc.prop_t": {"es": "Armar una promoción para {producto}",
                          "en": "Set up a promo for {producto}"},
    "core.venc.prop_d": {"es": "Sacarte {sobrante} de encima antes de que venzan, en {dias} días: promoción en el mostrador o mandarlo a los locales que sí lo rotan.",
                          "en": "Move {sobrante} before it expires, in {dias} days: a counter promo or send it to the stores that actually rotate it."},
    "core.venc.n_unidades": {"es": "{n} unidades", "en": "{n} units"},
    "core.margen.grupo_feteado": {"es": "Fiambrería feteada", "en": "Deli, sliced"},
    "core.margen.grupo_pieza_entera": {"es": "Fiambrería en pieza entera", "en": "Deli, whole pieces"},
    "core.margen.grupo_congelados": {"es": "Congelados", "en": "Frozen"},
    "core.margen.grupo_lacteos": {"es": "Lácteos", "en": "Dairy"},
    "core.margen.grupo_almacen": {"es": "Almacén", "en": "Dry goods"},
    "core.margen.grupo_galletitas": {"es": "Galletitas y golosinas", "en": "Cookies & candy"},
    "core.margen.grupo_bebidas": {"es": "Bebidas", "en": "Drinks"},
    "core.margen.grupo_limpieza": {"es": "Limpieza y perfumería", "en": "Cleaning & toiletries"},
    "core.opn.f_oferta": {"es": "oferta del proveedor", "en": "supplier offer"},
    "core.opn.f_vida_util": {"es": "vencimiento del lote ofrecido", "en": "expiry of the offered batch"},
    "core.opn.f_cierres": {"es": "cierres de caja por local", "en": "per-store register closings"},
    "core.opn.f_traslados": {"es": "movimientos a locales propios", "en": "movements to own stores"},
    "core.opn.f_mostrador": {"es": "ventas de mostrador", "en": "counter sales"},
    "core.opn.margen_t": {"es": "Revisar el precio de {n} productos con margen bajo",
                           "en": "Review the price of {n} low-margin products"},
    "core.opn.margen_r": {"es": "Venden con margen muy por debajo de su categoría: llevarlos al promedio es plata todos los meses.",
                           "en": "They sell well below their category's margin: bringing them to average is money every month."},
    "core.opn.margen_chat": {"es": "mostrame los productos con margen bajo y qué precio les pondrías",
                              "en": "show me the low-margin products and what price you'd set"},
    "core.opn.margen_p1": {"es": "{n} productos venden con margen anómalamente bajo vs su categoría: llevarlos al promedio suma ~{extra}/mes.",
                            "en": "{n} products sell at an anomalously low margin vs their category: bringing them to average adds ~{extra}/mo."},
    "core.opn.margen_p1_lbl": {"es": "Ganancia extra total si {n} productos vuelven al promedio",
                                "en": "Total extra profit if {n} products return to average"},
    "core.opn.margen_i": {"es": "margen {m}% vs {prom}% promedio de {cat}",
                           "en": "{m}% margin vs {cat}'s {prom}% average"},
    # P38·C — el hallazgo de margen NOMBRA al producto (un conteo no mueve a
    # nadie; "estás vendiendo X al 12% cuando su grupo deja 21%" sí).
    "core.opn.margen_t2": {"es": "Estás vendiendo {producto} con {m}% de margen",
                            "en": "You're selling {producto} at a {m}% margin"},
    "core.opn.margen_r2": {"es": "Muy por debajo del {prom}% promedio de {cat}. Hay {n} más en la misma situación.",
                            "en": "Way below the {prom}% average for {cat}. There are {n} more in the same spot."},
    "core.opn.margen_r2_solo": {"es": "Muy por debajo del {prom}% promedio de {cat}. ¿Revisamos el precio?",
                                "en": "Way below the {prom}% average for {cat}. Shall we review the price?"},
    "core.opn.margen_chat2": {"es": "¿qué precio le pondrías a {producto}?",
                               "en": "what price would you put on {producto}?"},
    "core.opn.margen_p0": {"es": "{producto} deja {m}% de margen; el promedio de {cat} es {prom}%.",
                            "en": "{producto} leaves a {m}% margin; the average for {cat} is {prom}%."},
    "core.opn.margen_p2": {"es": "Hoy lo vendés a {pvp}. A {objetivo} quedaría en el promedio de su grupo: {extra} más por mes sólo con ese producto.",
                            "en": "Today you sell it at {pvp}. At {objetivo} it'd sit at its group's average: {extra} more a month from that product alone."},
    "core.opn.margen_p2_lbl": {"es": "Vendés a {pvp}; al precio objetivo {objetivo} quedaría en el promedio de su grupo",
                                "en": "You sell at {pvp}; at the target price {objetivo} it would match its group's average"},
    "core.opn.margen_s1": {"es": "Supuesto: el volumen no cae con el ajuste (subas chicas, al promedio de la categoría).",
                            "en": "Assumption: volume holds after the adjustment (small raises, up to category average)."},
    # P24·G4 — la pantalla de revisión, re-localizada al leer (por tipo de obs)
    "core.staging.d_prod_inexistente_dep": {
        "es": "{n} lotes referencian un producto que no existe en tu inventario. No los "
              "integro a ciegas: ¿faltan dar de alta o son códigos viejos del depósito?",
        "en": "{n} lots reference a product that doesn't exist in your inventory. I won't "
              "take them in blindly: are they missing from the catalog, or old warehouse codes?",
    },
    "core.staging.d_lote_vencido": {
        "es": "{n} lotes del archivo tienen el vencimiento pasado. Los integro igual para "
              "que quede el registro, pero conviene revisarlos físicamente y darlos de baja.",
        "en": "{n} lots in the file are past their expiry date. I'll take them in so the "
              "record exists, but they should be physically checked and written off.",
    },
    "core.staging.d_entrega_atrasada": {
        "es": "{n} entregas del archivo tienen la fecha prevista pasada y no figuran como "
              "entregadas. Las integro para que Ángela las alerte.",
        "en": "{n} deliveries in the file are past their planned date and not marked as "
              "delivered. I'll take them in so Ángela can flag them.",
    },
    "core.staging.d_sin_cliente": {
        "es": "{n} envíos llegan sin cliente asignado. Sin cliente no puedo responder "
              "«¿salió el pedido de X?».",
        "en": "{n} shipments arrive with no customer assigned. Without a customer I can't "
              "answer \"did X's order go out?\".",
    },
    "core.staging.d_prod_inexistente_ventas": {
        "es": "{n} ventas referencian un producto que no existe en tu inventario. No las "
              "integro a ciegas: ¿son productos que faltan agregar o códigos viejos?",
        "en": "{n} sales reference a product that doesn't exist in your inventory. I won't "
              "take them in blindly: missing products, or old codes?",
    },
    "core.staging.d_numero_ambiguo": {
        "es": "{n} valores se pueden leer como miles (1.234 = mil doscientos treinta y "
              "cuatro) o como decimales (uno coma dos). No lo decido sola: elegí y los "
              "aplico a todos. Mientras tanto quedan sin valor — no invento números.",
        "en": "{n} values can be read as thousands (1.234 = one thousand two hundred "
              "thirty-four) or as decimals (one point two). I won't decide alone: pick one "
              "and I'll apply it to all. Until then they stay empty — I don't make up numbers.",
    },
    "core.staging.d_precio_perdida": {
        "es": "{n} productos tienen el costo más alto que el precio de venta. En el Excel "
              "esto pasa desapercibido.",
        "en": "{n} products have a cost higher than their sale price. In a spreadsheet "
              "this slips right through.",
    },
    "core.staging.d_sin_precio": {
        "es": "{n} productos llegan sin precio. ¿Les pongo uno según el costo?",
        "en": "{n} products arrive without a price. Want me to set one from cost?",
    },
    "core.staging.d_duplicado_clientes": {
        "es": "{n} clientes parecen ya existir en tu sistema con el mismo nombre.",
        "en": "{n} customers seem to already exist in your system under the same name.",
    },
    "core.staging.d_duplicado_proveedores": {
        "es": "{n} proveedores parecen ya existir en tu sistema con el mismo nombre.",
        "en": "{n} vendors seem to already exist in your system under the same name.",
    },
    "core.staging.d_duplicado": {
        "es": "{n} productos parecen ya existir en tu sistema con el mismo nombre.",
        "en": "{n} products seem to already exist in your system under the same name.",
    },
    "core.staging.d_stock_outlier": {
        "es": "{n} productos tienen un stock muy alto (más de {umbral} u). ¿Es correcto "
              "o hay un error de tipeo?",
        "en": "{n} products show very high stock (over {umbral} u). Is that right, or "
              "a typo?",
    },
    "core.staging.op_descartar": {"es": "Descartarlos", "en": "Discard them"},
    "core.staging.op_integrar_igual": {"es": "Integrarlos igual", "en": "Take them in anyway"},
    "core.staging.op_integrar_revisar": {"es": "Integrarlos y revisarlos", "en": "Take in and review"},
    "core.staging.op_integrar_alertar": {"es": "Integrarlas y alertar", "en": "Take in and alert"},
    "core.staging.op_miles": {"es": "Son miles (1.234 = 1234)", "en": "They're thousands (1.234 = 1234)"},
    "core.staging.op_decimales": {"es": "Son decimales (1.234 = 1,234)", "en": "They're decimals (1.234 = 1.234)"},
    "core.staging.op_margen": {"es": "Poner margen del {margen}%", "en": "Set a {margen}% margin"},
    "core.staging.op_margen_costo": {"es": "Margen del {margen}% sobre el costo", "en": "{margen}% margin over cost"},
    "core.staging.op_dejar_sin_precio": {"es": "Dejarlos sin precio por ahora", "en": "Leave them unpriced for now"},
    "core.staging.op_no_agregar": {"es": "No agregarlos (ya existen)", "en": "Don't add them (they exist)"},
    "core.staging.op_agregar_igual": {"es": "Agregarlos igual (son distintos)", "en": "Add them anyway (they're different)"},
    "core.staging.op_dejarlo": {"es": "Está bien, dejarlo", "en": "It's fine, keep it"},
    "core.pagos.proyeccion_supuestos": {
        "es": "Proyección sobre plazos históricos de cobro de cada cliente y "
              "vencimientos ya cargados. No incluye gastos no cargados.",
        "en": "Projected on each customer's historical payment behavior and "
              "already-loaded due dates. Doesn't include unloaded expenses.",
    },
    # P24·D6 — alertas personales por umbral (recordatorios condicionales)
    "core.rec.notif_titulo": {
        "es": "Aviso de Ángela",
        "en": "Heads-up from Ángela",
    },
    "core.rec.dormido_supera": {
        "es": "La plata dormida llegó a {monto} — pasó tu umbral de {umbral}.",
        "en": "Sleeping money hit {monto} — past your {umbral} threshold.",
    },
    "core.rec.cliente_atraso": {
        "es": "{n} cliente(s) pasaron los {dias} días sin pagar — el peor: "
              "{cliente} ({peor} días).",
        "en": "{n} customer(s) went past {dias} days without paying — worst: "
              "{cliente} ({peor} days).",
    },
    "fb.lista_revertida": {
        "es": "Listo, revertí la lista de precios del backup #{backup}: los costos "
              "volvieron exactamente como estaban, y el margen y el inmovilizado se "
              "recalcularon solos.",
        "en": "Done, I reverted the price list from backup #{backup}: costs are back "
              "exactly as they were, and margin and tied-up capital recalculated on "
              "their own.",
    },
    "fb.lista_sin_backup": {
        "es": "No hay ninguna lista de precios aplicada para revertir.",
        "en": "There's no applied price list to revert.",
    },
    "fb.consulta_sugerencias": {
        "es": "¿Quisiste decir {lista}?",
        "en": "Did you mean {lista}?",
    },
    "fb.widget_no_encontrado": {
        "es": "No encontré esa card entre las que me pediste. Decime cuál "
              "(el título o una parte) y la toco.",
        "en": "I couldn't find that card among the ones you asked for. Tell me "
              "which one (its title or part of it) and I'll change it.",
    },
    "fb.vista_join": {"es": " y ", "en": " and "},
    "fb.vista_listo": {
        "es": "Listo, {partes}. Lo dejé así para la próxima también.",
        "en": "Done, {partes}. I kept it that way for next time too.",
    },
    # fb: saneamiento
    "fb.san_manual": {
        "es": "Tenés {n} en esa categoría, pero {extra}: no la puedo corregir sola sin "
              "arriesgarme. ¿Te llevo a verlos?",
        "en": "You have {n} in that category, but it {extra}: I can't fix it on my own "
              "without taking a risk. Want me to take you there?",
    },
    "fb.san_extra_conteo": {
        "es": "necesita un conteo físico",
        "en": "needs a physical count",
    },
    "fb.san_extra_precios": {
        "es": "necesita que cargues los precios",
        "en": "needs you to load the prices",
    },
    "fb.san_det_fantasma": {
        "es": "{n} productos que el sistema tiene como inexistentes pero que tienen "
              "stock físico real",
        "en": "{n} products the system marks as nonexistent that still have real "
              "physical stock",
    },
    "fb.san_det_balanza": {
        "es": "{n} balanzas mal calibradas: {impacto} en stock que no se está "
              "cobrando bien",
        "en": "{n} miscalibrated scales: {impacto} in stock that isn't being "
              "charged right",
    },
    "fb.san_encontre": {
        "es": "Encontré {detalle}. Puedo resolverlo de varias formas — elegí, o pedime "
              "algo distinto. Siempre guardo un backup por si querés revertir.",
        "en": "I found {detalle}. I can solve it a few ways — pick one, or ask me for "
              "something else. I always keep a backup in case you want to revert.",
    },
    # fb: análisis P7
    "fb.rot_resumen": {
        "es": "Tenés {inmovilizado} en stock, rotando cada "
              "{dias} días en promedio — eso está sano. Lo que miraría: "
              "{dormido} ({pct}%) están DORMIDOS "
              "(más de 60 días sin rotar o sin una venta en el año).",
        "en": "You have {inmovilizado} in stock, turning over every "
              "{dias} days on average — that's healthy. What I'd look at: "
              "{dormido} ({pct}%) is SLEEPING "
              "(over 60 days without turning, or no sale all year).",
    },
    "fb.rot_rota_cada": {
        "es": "rota cada {dias} días",
        "en": "turns over every {dias} days",
    },
    "fb.rot_sin_venta": {
        "es": "no tuvo una venta en el año",
        "en": "didn't have a single sale all year",
    },
    "fb.rot_top": {
        "es": "El que más pesa: {producto} — {inmovilizado} y {dias}.",
        "en": "The heaviest one: {producto} — {inmovilizado} and {dias}.",
    },
    "fb.rot_lista": {
        "es": "¿Querés la lista completa de dormidos?",
        "en": "Want the full list of sleepers?",
    },
    "fb.est_analice": {
        "es": "Analicé {n} años completos de tus ventas (el año en curso no cuenta hasta cerrarse).",
        "en": "I analyzed {n} full years of your sales (the current year doesn't count until it closes).",
    },
    "fb.est_categoria": {
        "es": "{cat}: todos los {mes} vende {indice}× el mes promedio.",
        "en": "{cat}: every {mes} it sells {indice}× the average month.",
    },
    "fb.est_accionable": {
        "es": "Lo accionable ya: {aviso}",
        "en": "Actionable right now: {aviso}",
    },
    "fb.est_sin_picos": {
        "es": "En los próximos 60 días no viene ningún pico fuerte: buen momento para "
              "ordenar stock.",
        "en": "No big peak coming in the next 60 days: good moment to tidy up stock.",
    },
    "fb.pp_push": {
        "es": "Conviene empujarlos: {lista}",
        "en": "Worth promoting: {lista}",
    },
    "fb.pp_pull": {
        "es": "Los que se venden solos: {lista}. Ahí la jugada es no quedarte "
              "sin stock.",
        "en": "The ones that sell on their own: {lista}. There the play is to "
              "never run out of stock.",
    },
    "fb.pp_lista": {
        "es": "¿Te armo la lista completa?",
        "en": "Want me to build the full list?",
    },
    "fb.obj_propongo": {
        "es": "Con todo lo que veo en tus datos, te propongo estos objetivos — vos decidís "
              "cuáles adoptar. {partes}",
        "en": "With everything I see in your data, I propose these objectives — you decide "
              "which to adopt. {partes}",
    },
    # fb: evolución
    "fb.evo_sin_datos": {
        "es": "Para compararte contra el año pasado necesito tus ventas históricas — el "
              "mismo CSV que activa la rotación y las alertas de stock. Se carga por "
              "«Cargar datos»; apenas esté, te digo cómo venís de verdad, ajustado por "
              "inflación para que compares parejo.",
        "en": "To compare you against last year I need your historical sales — the "
              "same CSV that unlocks turnover and stock alerts. It loads via \"Load "
              "data\"; the moment it's in, I'll tell you how you're really doing, "
              "inflation-adjusted so you compare apples to apples.",
    },
    "fb.evo_interanual": {
        "es": "En {mes} facturaste {nominal}: contra "
              "{mes_anterior} es {var_nominal}% en pesos "
              "corrientes, pero ajustado por inflación —para que compares parejo— da "
              "{var_real}% real.",
        "en": "In {mes} you billed {nominal}: against "
              "{mes_anterior} that's {var_nominal}% in current "
              "pesos, but inflation-adjusted —so you compare apples to apples— it's "
              "{var_real}% real.",
    },
    "fb.evo_ytd": {
        "es": "El acumulado {anio} va {var_real}% real contra "
              "el mismo tramo del año pasado ({var_nominal}% nominal).",
        "en": "The {anio} year-to-date is running {var_real}% real against "
              "the same stretch last year ({var_nominal}% nominal).",
    },
    "fb.evo_demo": {
        "es": "(Ojo: estás viendo datos de demostración.)",
        "en": "(Heads up: you're looking at demo data.)",
    },
    "fb.evo_serie": {
        "es": "Te dejo la serie completa en Evolución.",
        "en": "The full series is waiting for you in Evolution.",
    },
    # fb: plata / navegación
    "fb.plata_en": {
        "es": "En {prod} tenés {monto} parados "
              "({unidades} unidades en {coincidencias} artículos). ¿Querés el desglose?",
        "en": "In {prod} you have {monto} sitting idle "
              "({unidades} units across {coincidencias} items). Want the breakdown?",
    },
    "fb.plata_total": {
        "es": "Tenés {monto} inmovilizados en total. "
              "Decime qué producto o categoría querés mirar (ej: manteca, queso, leche).",
        "en": "You have {monto} tied up in total. "
              "Tell me which product or category to look at (e.g.: manteca, queso, leche).",
    },
    "fb.nav_te_llevo": {
        "es": "Te llevo. Ahí están, tocá cualquiera para corregirlo.",
        "en": "I'll take you there. There they are — tap any one to fix it.",
    },
    # fb: cuentas corrientes
    "fb.cta_sin_datos": {
        "es": "Todavía no tengo las cuentas corrientes de verdad: lo que hay es el "
              "seed de fábrica y no te voy a contestar con eso como si fuera tuyo. "
              "Se activa cargando el export de cuentas por «Cargar datos»; apenas "
              "esté te digo quién te debe, cuánto y hace cuántos días.",
        "en": "I don't have your real customer accounts yet: what's loaded is the "
              "factory seed and I won't answer with that as if it were yours. "
              "It activates when you load the accounts export via “Load data”; as "
              "soon as it's in, I'll tell you who owes you, how much and for how long.",
    },
    "fb.cta_al_dia": {
        "es": "Por ahora nadie está en mora. Tus clientes vienen al día.",
        "en": "Nobody's overdue for now. Your customers are keeping up.",
    },
    "fb.cta_morosos": {
        "es": "Tenés {n} clientes en mora por {total} en total. "
              "El más urgente: {nombre} debe {saldo} hace {dias} "
              "días (está {atraso}% más tarde que su promedio). ¿Le mando un recordatorio?",
        "en": "You have {n} customers overdue for {total} in total. "
              "The most urgent: {nombre} owes {saldo}, {dias} days "
              "now (running {atraso}% later than their average). Shall I send a reminder?",
    },
    "fb.cta_cobro": {
        "es": "Te propongo este mensaje para {cliente}:\n\n«{mensaje}»\n\nLo mando por "
              "WhatsApp si me das el ok.",
        "en": "Here's the message I propose for {cliente}:\n\n\"{mensaje}\"\n\nI'll send "
              "it via WhatsApp if you give me the ok.",
    },
    "fb.cta_estado": {
        "es": "Te armé el estado de cuenta de {nombre}. Revisalo y generás el PDF.",
        "en": "I put together {nombre}'s account statement. Review it and generate the PDF.",
    },
    # fb: caja
    "fb.caja_cierre": {
        "es": "Cerré la caja del día: total {total}.",
        "en": "I closed today's register: total {total}.",
    },
    "fb.caja_estado": {
        "es": "En caja tenés {total} ahora mismo "
              "(arrancaste con {inicial}). ¿Querés cerrarla?",
        "en": "You have {total} in the register right now "
              "(you started with {inicial}). Want to close it?",
    },
    # fb: documentos
    "fb.doc_orden": {
        "es": "Te armé una orden de pedido con {n} productos que conviene reponer (los que "
              "están sin stock). Editá cantidades, proveedor y plazo, y generás el PDF. Sin ventas todavía "
              "sugiero por stock; cuando las cargues, ajusto cada cantidad con la rotación real.",
        "en": "I built a purchase order with {n} products worth restocking (the ones out "
              "of stock). Edit quantities, supplier and terms, then generate the PDF. With no sales loaded "
              "yet I suggest by stock; once you load them, I'll tune each quantity with real turnover.",
    },
    "fb.doc_resumen": {
        "es": "Te armé el resumen ejecutivo del inventario: los números clave, las anomalías con su impacto "
              "y las acciones que recomiendo. Revisalo y generás el PDF para tu contador o el banco.",
        "en": "I put together the inventory executive summary: the key numbers, the anomalies with their "
              "impact, and the actions I recommend. Review it and generate the PDF for your accountant or the bank.",
    },
    "fb.doc_cierres": {
        "es": "Listo: armé el reporte de cierres de todos los locales de esta semana, comparados "
              "contra la anterior. Es lo que se imputaba a mano al Excel todas las semanas — "
              "revisalo y generás el PDF.",
        "en": "Done: I built the closings report for every store this week, compared against the "
              "previous one. This is what used to get typed into a spreadsheet by hand every "
              "week — review it and generate the PDF.",
    },
    "fb.cierres_por_local": {
        "es": "Del {desde} al {hasta}, por local: {detalle}. Total: {total}. "
              "Sale de los cierres de caja que ya se cargan todos los días.",
        "en": "From {desde} to {hasta}, by store: {detalle}. Total: {total}. "
              "It comes from the register closings already logged every day.",
    },
    "fb.doc_carta": {
        "es": "Te dejé un borrador de la carta para que lo edites y generes el PDF. (Con el modelo conectado "
              "la redacto fina sola desde el contexto del negocio.)",
        "en": "I left you a draft of the letter to edit and turn into a PDF. (With the model connected "
              "I'll polish it myself from your business context.)",
    },
    # fb: defaults
    "fb.default_inventario": {
        "es": "Hoy tenés {monto} parados en mercadería sobre "
              "{n} artículos. Puedo corregirte los datos, armarte un gráfico, "
              "cambiar tu vista o avisar a tu equipo. ¿Por dónde arrancamos?\n\n"
              "(Modo datos: para charla libre total falta cargar ANTHROPIC_API_KEY.)",
        "en": "Today you have {monto} sitting in merchandise across "
              "{n} items. I can fix your data, build you a chart, "
              "change your view or notify your team. Where do we start?\n\n"
              "(Data mode: full free chat needs ANTHROPIC_API_KEY loaded.)",
    },
    "fb.default_area": {
        "es": "Contame qué necesitás de tu área y te ayudo con eso. "
              "(Modo datos: para charla libre total falta cargar ANTHROPIC_API_KEY.)",
        "en": "Tell me what you need from your area and I'll help with that. "
              "(Data mode: full free chat needs ANTHROPIC_API_KEY loaded.)",
    },
    # fb: labels de opciones-botones (el ENVIAR queda siempre en ES: es lo que
    # se re-inyecta al router, cuyo matching es por keywords en español)
    "fb.op_cancelar": {"es": "Cancelar", "en": "Cancel"},
    "fb.op_si_revertila": {"es": "Sí, revertila", "en": "Yes, undo it"},
    "fb.op_si_confirma": {"es": "Sí, confirmá", "en": "Yes, confirm"},
    "fb.op_en_inicio": {"es": "En el Inicio", "en": "On Home"},
    "fb.op_en_inventario": {"es": "En Inventario", "en": "In Inventory"},
    "fb.op_whatsapp": {"es": "Ya se lo mandé — anotalo", "en": "I sent it — note it down"},
    "fb.op_fant_reactivar": {"es": "Reactivarlos todos", "en": "Reactivate them all"},
    "fb.op_fant_baja": {"es": "Dar de baja los de menos de 50 unidades",
                        "en": "Retire the ones under 50 units"},
    "fb.op_fant_ver": {"es": "Verlos uno por uno", "en": "See them one by one"},
    "fb.op_bal_corregir": {"es": "Corregirlas todas", "en": "Fix them all"},
    "fb.op_bal_ver": {"es": "Verlas una por una", "en": "See them one by one"},
    # ==========================================================================
    # core.* · E9b — textos user-facing que PRODUCE core/ (el ES es byte-igual
    # al texto histórico de cada módulo; los IDs/categorías nunca se traducen).
    # ==========================================================================
    # --- core/quality.py + core/models.py · libro de calidad -------------------
    "core.calidad.fantasma": {
        "es": "Anulado con stock vivo",
        "en": "Cancelled with live stock",
    },
    "core.calidad.negativo": {
        "es": "Stock negativo (el sistema miente)",
        "en": "Negative stock (the system is lying)",
    },
    "core.calidad.sin_precio": {
        "es": "Sin precio de venta cargado",
        "en": "No sale price loaded",
    },
    "core.calidad.balanza": {
        "es": "Balanza con peso fuera de rango",
        "en": "Scale with weight out of range",
    },
    "core.calidad.costo_viejo": {
        "es": "Costo desactualizado (+1 año)",
        "en": "Outdated cost (1+ year)",
    },
    # estado_label: el texto legible del estado. El campo `estado` NO cambia
    # (es el ID que la UI usa para el color); esto es el texto para mostrar.
    "core.calidad.estado_completo": {"es": "completo", "en": "complete"},
    "core.calidad.estado_inconsistente": {"es": "inconsistente", "en": "inconsistent"},
    "core.calidad.estado_mal_configurado": {"es": "mal configurado", "en": "misconfigured"},
    "core.calidad.estado_incompleto": {"es": "incompleto", "en": "incomplete"},
    "core.calidad.estado_desactualizado": {"es": "desactualizado", "en": "outdated"},
    # --- data_store.py · grupos y salud del Inicio ------------------------------
    "core.grupo.fantasmas": {
        "es": "Productos fantasma (anulados con stock vivo)",
        "en": "Ghost products (cancelled with live stock)",
    },
    "core.grupo.negativos": {
        "es": "Stock negativo (el sistema miente)",
        "en": "Negative stock (the system is lying)",
    },
    "core.grupo.sin_pvp": {
        "es": "Sin precio de venta cargado",
        "en": "No sale price loaded",
    },
    "core.grupo.balanza": {
        "es": "Balanza con peso teórico fuera de rango",
        "en": "Scale with theoretical weight out of range",
    },
    "core.grupo.costo_viejo": {
        "es": "Costo desactualizado (más de 1 año)",
        "en": "Outdated cost (over 1 year)",
    },
    # --- core/saneamiento.py · propuestas de corrección (P14) --------------------
    "core.sane.accion_fantasma": {
        "es": "Reactivar (volver a estado activo)",
        "en": "Reactivate (back to active status)",
    },
    "core.sane.accion_balanza": {
        "es": "Resetear el peso teórico al punto medio del rango",
        "en": "Reset the theoretical weight to the midpoint of the range",
    },
    "core.sane.no_auto_motivo": {
        "es": "Esta categoría necesita un dato o un conteo físico; no la puedo corregir sola sin arriesgarme a romper algo.",
        "en": "This category needs a piece of data or a physical count; I can't fix it on my own without risking breaking something.",
    },
    # --- data_store.py · oportunidades (P14: ES verbatim al histórico) -----------
    "core.oport.sin_pvp_titulo": {
        "es": "Cargá los precios que faltan y vendé lo que hoy no podés cobrar bien",
        "en": "Load the missing prices and sell what you can't properly charge for today",
    },
    "core.oport.sin_pvp_desc": {
        "es": "Tenés {n} productos activos sin precio de venta. Son mercadería que está en góndola pero sin precio firme: se vende a ojo y se desincroniza entre locales.",
        "en": "You have {n} active products without a sale price. That's merchandise on the shelf with no firm price: it sells by eye and drifts apart between stores.",
    },
    "core.oport.sin_pvp_impacto": {
        "es": "en stock sin precio firme",
        "en": "in stock without a firm price",
    },
    "core.oport.sin_pvp_accion": {
        "es": "Cargar los precios faltantes",
        "en": "Load the missing prices",
    },
    "core.oport.balanza_titulo": {
        "es": "Corregí las balanzas y dejá de regalar fiambre",
        "en": "Fix the scales and stop giving away deli meat",
    },
    "core.oport.balanza_desc": {
        "es": "Hay {n} balanzas con el peso teórico fuera de rango (muchas con el default 3,00). El sistema no está cobrando lo que corresponde: es el origen del robo de fiambre feteado.",
        "en": "There are {n} scales with the theoretical weight out of range (many at the 3.00 default). The system isn't charging what it should: that's where the sliced-deli theft comes from.",
    },
    "core.oport.balanza_impacto": {
        "es": "en stock mal pesado",
        "en": "in badly weighed stock",
    },
    "core.oport.balanza_accion": {
        "es": "Corregir el peso teórico",
        "en": "Fix the theoretical weight",
    },
    "core.oport.ventana_titulo": {
        "es": "Ventana de compra por contexto económico",
        "en": "Buying window from the economic context",
    },
    "core.oport.ventana_desc": {
        "es": "Para detectar cuándo conviene adelantar una compra antes de un aumento, necesito el contexto económico de la semana (dólar, inflación) y las listas de precios de proveedores.",
        "en": "To spot when it pays to bring a purchase forward before a price hike, I need the week's economic context (dollar, inflation) and the suppliers' price lists.",
    },
    "core.oport.ventana_falta": {
        "es": "contexto económico + listas de precios",
        "en": "economic context + price lists",
    },
    "core.oport.rotacion_titulo": {
        "es": "Qué dejar de comprar (plata parada que no rota)",
        "en": "What to stop buying (idle money that doesn't turn)",
    },
    "core.oport.rotacion_desc": {
        "es": "Para decirte qué productos comprás de más, necesito el export de ventas históricas. Con eso cruzo tu stock parado contra lo que realmente vendés.",
        "en": "To tell you which products you over-buy, I need the sales history export. With that I cross your idle stock against what you actually sell.",
    },
    "core.oport.rotacion_falta": {
        "es": "ventas históricas",
        "en": "sales history",
    },
    "core.oport.credito_titulo": {
        "es": "Líneas de crédito y subsidios que te aplican",
        "en": "Credit lines and subsidies that apply to you",
    },
    "core.oport.credito_desc": {
        "es": "Para matchearte con líneas BICE/Nación/provincia, necesito el contexto legal/financiero cargado.",
        "en": "To match you with BICE/national/provincial credit lines, I need the legal/financial context loaded.",
    },
    "core.oport.credito_falta": {
        "es": "contexto legal/financiero",
        "en": "legal/financial context",
    },
    "core.salud.requiere_accion": {
        "es": "Requiere acción urgente",
        "en": "Needs urgent action",
    },
    "core.salud.atencion": {"es": "Atención requerida", "en": "Attention required"},
    "core.salud.en_orden": {"es": "En orden", "en": "In order"},
    # --- core/analisis.py · los cruces (P7) --------------------------------------
    "core.analisis.sin_ventas": {
        "es": "Todavía no hay ventas cargadas. Este análisis se despierta con el archivo de ventas.",
        "en": "No sales loaded yet. This analysis wakes up with the sales file.",
    },
    "core.analisis.sin_validar": {
        "es": "Las ventas están cargadas pero falta confirmar los montos (validador). Hasta ahí no muestro cruces.",
        "en": "The sales are loaded but the amounts still need confirming (validator). Until then I don't show cross-analysis.",
    },
    "core.analisis.est_aviso": {
        "es": "Todos los {mes} {cat} vende {indice}× el mes promedio: conviene stockearse antes.",
        "en": "Every {mes}, {cat} sells {indice}× the average month: better stock up beforehand.",
    },
    "core.analisis.pp_pull_motivo": {
        "es": "Rota cada {dias} días: la demanda lo mueve sola. Reponé y no lo toques.",
        "en": "Turns over every {dias} days: demand moves it on its own. Restock and don't touch it.",
    },
    "core.analisis.pp_push_margen": {
        "es": "Margen {margen}% y rota lento{extra}: conviene empujarlo (oferta, punta de góndola, preventista).",
        "en": "{margen}% margin and slow turnover{extra}: worth promoting (deal, end-cap, sales rep).",
    },
    "core.analisis.pp_push_temporada": {
        "es": " — y su temporada viene ahora ({temporada}×)",
        "en": " — and its season is coming right now ({temporada}×)",
    },
    "core.analisis.pp_push_estacional": {
        "es": "Su temporada arranca ya ({temporada}× el mes promedio): ganale al pico stockeando y empujando ahora.",
        "en": "Its season starts now ({temporada}× the average month): beat the peak by stocking up and promoting it now.",
    },
    "core.analisis.obj_morosos_titulo": {
        "es": "Cobrar los {n} clientes en mora",
        "en": "Collect from the {n} overdue customers",
    },
    "core.analisis.obj_morosos_detalle": {
        "es": "{monto} vencidos más allá del plazo. "
              "Un recordatorio por semana hasta regularizar.",
        "en": "{monto} past due beyond terms. "
              "One reminder a week until it's settled.",
    },
    "core.analisis.obj_dormido_titulo": {
        "es": "Despertar {monto} de stock dormido",
        "en": "Wake up {monto} of sleeping stock",
    },
    "core.analisis.obj_dormido_detalle": {
        "es": "Más de 60 días de rotación o sin una venta en el año. "
              "{top}Oferta, combo o devolución al proveedor.",
        "en": "Over 60 days of turnover, or not one sale all year. "
              "{top}Deal, bundle, or return to the supplier.",
    },
    "core.analisis.obj_dormido_top": {
        "es": "El que más pesa: {producto} ({monto}). ",
        "en": "The heaviest one: {producto} ({monto}). ",
    },
    "core.analisis.obj_pico_titulo": {
        "es": "Stockear {categoria} antes de {mes}",
        "en": "Stock up on {categoria} before {mes}",
    },
    "core.analisis.obj_pico_detalle": {
        "es": "{aviso} Confirmar pedidos con el proveedor 3 semanas antes.",
        "en": "{aviso} Confirm orders with the supplier 3 weeks ahead.",
    },
    "core.analisis.obj_crec_titulo": {
        "es": "Sostener el crecimiento: {crec}% en volumen interanual",
        "en": "Sustain the growth: {crec}% in year-over-year volume",
    },
    "core.analisis.obj_crec_detalle": {
        "es": "Se vendieron {u12} unidades en los últimos 12 meses contra "
              "{u12_prev} de los 12 anteriores (unidades, no pesos: la inflación no ensucia). {cierre}",
        "en": "{u12} units sold in the last 12 months against "
              "{u12_prev} in the 12 before (units, not pesos: inflation doesn't muddy it). {cierre}",
    },
    "core.analisis.obj_crec_bien": {
        "es": "Va bien: no aflojar con la reposición de los que rotan rápido.",
        "en": "Going well: don't ease up on restocking the fast movers.",
    },
    "core.analisis.obj_crec_mal": {
        "es": "Está cayendo: mirar los que se venden solos de siempre y los morosos.",
        "en": "It's slipping: look at the products that usually sell on their own and the overdue accounts.",
    },
    # --- core/evolucion.py · comparaciones ajustadas por IPC ---------------------
    "core.evolucion.sin_datos": {
        "es": "Se activa al cargar las ventas históricas (el mismo CSV que "
              "despierta rotación, margen y quiebre de stock).",
        "en": "It switches on when you load your historical sales (the same CSV "
              "that wakes up turnover, margin and stock-outs).",
    },
    "core.evolucion.aviso_indice": {
        "es": "El INDEC no respondió: muestro sólo valores nominales, "
              "sin ajuste por inflación. No invento deflactores.",
        "en": "INDEC didn't answer: I'm showing nominal values only, "
              "no inflation adjustment. I don't make up deflators.",
    },
    "core.evolucion.etiqueta_base": {
        "es": "a precios de hoy ({mes_base}), según IPC INDEC",
        "en": "at today's prices ({mes_base}), per INDEC CPI",
    },
    "core.evolucion.sin_indice": {
        "es": "sin índice IPC disponible",
        "en": "no CPI index available",
    },
    "core.evolucion.alerta_caida_titulo": {
        "es": "Caída real de facturación",
        "en": "Real drop in revenue",
    },
    "core.evolucion.alerta_caida_detalle": {
        "es": "En {mes} facturaste {caida}% menos en términos reales que en {mes_anterior} "
              "(ajustado por inflación; en pesos corrientes figura {nominal}%).",
        "en": "In {mes} you billed {caida}% less in real terms than in {mes_anterior} "
              "(inflation-adjusted; in current pesos it shows {nominal}%).",
    },
    # --- core/ventas.py · validador de montos ------------------------------------
    # OJO: el punto tras «cargaste» reproduce el .replace(",", ".") histórico
    # sobre el string entero (byte-igual al texto que el piloto ya vio).
    "core.ventas.pregunta": {
        "es": "Con lo que cargaste. calculo que en {mes} facturaste "
              "{total} (pesos de ese momento). ¿Se parece a lo que "
              "facturaste de verdad ese mes?",
        "en": "From what you loaded, I calculate {mes} billed "
              "{total} (pesos of that moment). Does that look like what "
              "you actually billed that month?",
    },
    "core.ventas.nada_para_validar": {
        "es": "No hay ventas cargadas para validar.",
        "en": "There are no sales loaded to validate.",
    },
    "core.ventas.esperado_o_confirma": {
        "es": "Decime el monto esperado o confirmá.",
        "en": "Tell me the expected amount or confirm.",
    },
    "core.ventas.dif_motivo": {
        "es": "El total calculado difiere {pct}% de lo que esperabas.{pista}",
        "en": "The calculated total differs {pct}% from what you expected.{pista}",
    },
    "core.ventas.pista_inflados": {
        "es": " Pinta que la columna de monto trae el TOTAL de la fila y la "
              "estamos multiplicando por la cantidad (números inflados).",
        "en": " Looks like the amount column carries the row TOTAL and we're "
              "multiplying it by the quantity (inflated numbers).",
    },
    "core.ventas.pista_miniatura": {
        "es": " Pinta que la columna de monto es el precio UNITARIO y no lo "
              "estamos multiplicando (números en miniatura).",
        "en": " Looks like the amount column is the UNIT price and we're not "
              "multiplying it (miniature numbers).",
    },
    "core.ventas.motivo_sin_ventas": {
        "es": "faltan ventas históricas",
        "en": "historical sales are missing",
    },
    "core.ventas.motivo_sospechoso": {
        "es": "los montos están marcados como mal interpretados; revisá la carga",
        "en": "the amounts are flagged as misread; check the upload",
    },
    "core.ventas.motivo_sin_confirmar": {
        "es": "falta que el dueño confirme el total de un mes (validador de montos)",
        "en": "the owner still has to confirm one month's total (amount validator)",
    },
    "core.ventas.nota_margen": {
        "es": "costo actual, no histórico (se afina con el CSV real)",
        "en": "current cost, not historical (it sharpens with the real CSV)",
    },
    # --- core/cuentas.py · scoring, cobro y estado de cuenta ---------------------
    "core.cuentas.score_confiable": {"es": "buen historial", "en": "good track record"},
    "core.cuentas.score_atencion": {"es": "viene atrasado", "en": "running late"},
    "core.cuentas.score_riesgoso": {"es": "alto riesgo", "en": "high risk"},
    # el id crudo del score, legible (el ES es el valor histórico tal cual)
    "core.cuentas.score_id_confiable": {"es": "confiable", "en": "reliable"},
    "core.cuentas.score_id_atencion": {"es": "atencion", "en": "watch"},
    "core.cuentas.score_id_riesgoso": {"es": "riesgoso", "en": "risky"},
    "core.cuentas.scoring_desconocido": {
        "es": "No tengo historial de «{nombre}». Para arrancar, mejor efectivo o un "
              "límite bajo hasta ver cómo paga.",
        "en": "I have no history for «{nombre}». To start, better cash or a low "
              "limit until you see how they pay.",
    },
    "core.cuentas.scoring_supera": {
        "es": "{nombre} tiene {disp} disponibles de límite y querés venderle "
              "{monto}. Eso supera su límite: necesito que lo autorice el dueño.",
        "en": "{nombre} has {disp} of credit available and you want to sell them "
              "{monto}. That's over their limit: I need the owner to authorize it.",
    },
    "core.cuentas.scoring_ok": {
        "es": "{nombre} ({detalle}) tiene {disp} disponibles de límite. "
              "Le podés vender hasta eso.",
        "en": "{nombre} ({detalle}) has {disp} of credit available. "
              "You can sell them up to that.",
    },
    # OJO: «Hola.» reproduce el .replace(",", ".") histórico sobre el mensaje
    # entero (byte-igual a lo que hoy sale por WhatsApp).
    "core.cuentas.cobro_mensaje": {
        "es": "Hola. te escribo de {empresa}. Te recuerdo que tenés un saldo pendiente de "
              "{saldo} con {dias} días.{extra} ¿Coordinamos el pago? "
              "Gracias.",
        "en": "Hi, this is {empresa}. Just a reminder that you have an outstanding balance of "
              "{saldo}, {dias} days now.{extra} Shall we arrange the payment? "
              "Thanks.",
    },
    "core.cuentas.cobro_extra": {
        "es": " Históricamente pagás a los {prom} días; hoy estás {atraso}% "
              "más tarde.",
        "en": " You usually pay within {prom} days; right now you're {atraso}% "
              "later than that.",
    },
    "core.cuentas.ec_titulo": {
        "es": "Estado de cuenta · {nombre}",
        "en": "Account statement · {nombre}",
    },
    "core.cuentas.ec_kpi_saldo": {"es": "Saldo adeudado", "en": "Balance due"},
    "core.cuentas.ec_kpi_vencido": {"es": "Vencido", "en": "Past due"},
    "core.cuentas.ec_kpi_al_dia": {"es": "Al día", "en": "Current"},
    "core.cuentas.ec_lectura_atraso": {
        "es": "Viene pagando a {prom} días en promedio; el atraso actual ({pct}% por encima "
              "de su propio histórico) es inusual para este cliente.",
        "en": "They usually pay in {prom} days on average; the current delay ({pct}% above "
              "their own history) is unusual for this customer.",
    },
    "core.cuentas.ec_lectura_tolerancia": {  # E2·pieza 1 — reencuadre vs tolerancia de Aldo
        "es": "Vos le tolerás {tol} días: los {dias} de ahora son {exceso} más que tu límite.",
        "en": "You allow it {tol} days: the current {dias} are {exceso} over your limit.",
    },
    "core.cuentas.ec_lectura_normal": {
        "es": "Viene pagando a {prom} días en promedio y el saldo actual está dentro de su "
              "comportamiento habitual.",
        "en": "They usually pay in {prom} days on average and the current balance is within "
              "their normal behavior.",
    },
    "core.cuentas.ec_lectura_al_dia": {
        "es": "Cliente al día: sin saldo pendiente.",
        "en": "Customer is current: no outstanding balance.",
    },
    "core.cuentas.ec_kpi_dias": {"es": "Días sin pagar", "en": "Days without paying"},
    "core.cuentas.ec_kpi_limite": {"es": "Límite disponible", "en": "Available credit"},
    "core.cuentas.ec_movimientos": {"es": "Movimientos", "en": "Transactions"},
    "core.cuentas.ec_col_fecha": {"es": "Fecha", "en": "Date"},
    "core.cuentas.ec_col_tipo": {"es": "Tipo", "en": "Type"},
    "core.cuentas.ec_col_monto": {"es": "Monto", "en": "Amount"},
    "core.cuentas.ec_nota": {
        "es": "Comportamiento: {score}. Plazo acordado: {plazo} días.",
        "en": "Behavior: {score}. Agreed terms: {plazo} days.",
    },
    # --- core/caja.py · nota de Ángela en cierres inusuales ----------------------
    "core.caja.nota_diferencia": {
        "es": "El cierre tiene una diferencia de {dif} contra lo declarado. "
              "Conviene revisar los movimientos del día.",
        "en": "The closing shows a {dif} difference against what was declared. "
              "Worth reviewing the day's movements.",
    },
    "core.caja.nota_promedio": {
        "es": "El total de hoy ({total}) está bastante {signo} del promedio de la semana "
              "({prom}). ¿Querés que revise qué cambió?",
        "en": "Today's total ({total}) is well {signo} the week's average "
              "({prom}). Want me to check what changed?",
    },
    "core.caja.por_encima": {"es": "por encima", "en": "above"},
    "core.caja.por_debajo": {"es": "por debajo", "en": "below"},
    # --- core/deposito.py y core/logistica.py · sin datos (tool results) ---------
    "core.deposito.sin_datos": {
        "es": "Todavía no hay datos de depósito cargados. Se cargan por "
              "'Cargar datos' con el export del sistema de depósito.",
        "en": "No warehouse data loaded yet. It loads via "
              "'Load data' with your warehouse system's export.",
    },
    "core.logistica.sin_datos": {
        "es": "Todavía no hay datos de envíos cargados. Se cargan por "
              "'Cargar datos' con el export del sistema de reparto.",
        "en": "No shipping data loaded yet. It loads via "
              "'Load data' with your delivery system's export.",
    },
    # --- core/normalizacion.py · Nivel 1 en criollo -------------------------------
    "core.norm.regla_separadores_es_ar": {
        "es": "números con miles y decimales (1.234,50)",
        "en": "numbers with thousands and decimals (1.234,50)",
    },
    "core.norm.regla_coma_decimal": {"es": "decimales con coma", "en": "comma decimals"},
    "core.norm.regla_puntos_miles": {"es": "puntos de miles", "en": "thousands dots"},
    "core.norm.regla_formato_numero": {
        "es": "símbolos y espacios en números",
        "en": "symbols and spaces in numbers",
    },
    "core.norm.regla_fecha_iso": {"es": "formatos de fecha", "en": "date formats"},
    "core.norm.regla_espacios": {"es": "espacios sobrantes", "en": "extra spaces"},
    "core.norm.regla_mayusculas": {
        "es": "mayúsculas y minúsculas",
        "en": "upper and lower case",
    },
    "core.norm.regla_encoding": {
        "es": "caracteres rotos (encoding)",
        "en": "broken characters (encoding)",
    },
    "core.norm.resumen": {
        "es": "Normalicé sola {total} valores en {filas} filas: {partes}. "
              "Nada que cambie el significado; el original quedó guardado y podés revertir.",
        "en": "I normalized {total} values across {filas} rows on my own: {partes}. "
              "Nothing that changes the meaning; the original is saved and you can revert.",
    },
    "core.norm.ambiguos": {
        "es": " Aparté {n} números ambiguos para que los decidas vos.",
        "en": " I set aside {n} ambiguous numbers for you to decide.",
    },
    # --- core/staging.py · zona de revisión ---------------------------------------
    "core.staging.obs_producto_inexistente_ventas": {
        "es": "Ventas de productos que no están en tu catálogo",
        "en": "Sales of products that aren't in your catalog",
    },
    "core.staging.obs_producto_inexistente_deposito": {
        "es": "Lotes de productos que no están en tu catálogo",
        "en": "Batches of products that aren't in your catalog",
    },
    "core.staging.obs_lote_vencido": {
        "es": "Lotes que ya están vencidos",
        "en": "Batches already expired",
    },
    "core.staging.obs_entrega_atrasada": {
        "es": "Entregas que ya vienen atrasadas",
        "en": "Deliveries already running late",
    },
    "core.staging.obs_sin_cliente": {
        "es": "Envíos sin cliente",
        "en": "Shipments without a customer",
    },
    "core.staging.obs_numero_ambiguo": {
        "es": "Números que se pueden leer de dos formas",
        "en": "Numbers that can be read two ways",
    },
    "core.staging.obs_precio_perdida": {
        "es": "Productos que se venden a pérdida",
        "en": "Products selling at a loss",
    },
    "core.staging.obs_sin_precio": {
        "es": "Productos sin precio de venta",
        "en": "Products without a sale price",
    },
    "core.staging.obs_duplicado": {
        "es": "Posibles duplicados",
        "en": "Possible duplicates",
    },
    "core.staging.obs_stock_outlier": {
        "es": "Stock anormalmente alto",
        "en": "Abnormally high stock",
    },
    "core.staging.integrar_apartado": {
        "es": "Listo. Creé el apartado {nombre} con {n} registros.{rel}{activado}{extra}",
        "en": "Done. I created the {nombre} section with {n} records.{rel}{activado}{extra}",
    },
    "core.staging.integrar_rel": {
        "es": " Lo conecté con tu {lista}.",
        "en": " I connected it with your {lista}.",
    },
    "core.staging.integrar_activa": {
        "es": " Con eso se activa: {lista}.",
        "en": " That switches on: {lista}.",
    },
    "core.staging.integrar_validador": {
        "es": " ANTES de mostrarte números: {pregunta}",
        "en": " BEFORE I show you numbers: {pregunta}",
    },
    "core.staging.integrar_productos": {
        "es": "Listo. Integré {n} productos al sistema. Guardé un backup por si querés revertir.",
        "en": "Done. I merged {n} products into the system. I saved a backup in case you want to revert.",
    },
    "core.staging.join_y": {"es": " y ", "en": " and "},
    "core.staging.sin_normalizaciones": {
        "es": "No hay normalizaciones automáticas en la zona de revisión.",
        "en": "There are no automatic normalizations in the review area.",
    },
    "core.staging.nivel1_deshecho": {
        "es": "Nivel 1 deshecho: el archivo volvió a como vino.",
        "en": "Level 1 undone: the file is back to how it arrived.",
    },
    # --- core/esquema.py · plan de integración (nombres y qué activa) ------------
    "core.esquema.producto": {"es": "Inventario", "en": "Inventory"},
    "core.esquema.venta": {"es": "Ventas", "en": "Sales"},
    "core.esquema.cliente": {"es": "Clientes", "en": "Customers"},
    "core.esquema.proveedor": {"es": "Proveedores", "en": "Suppliers"},
    "core.esquema.cuenta_corriente": {"es": "Cuentas corrientes", "en": "Customer accounts"},
    "core.esquema.deposito": {"es": "Depósito", "en": "Warehouse"},
    "core.esquema.logistica": {"es": "Logística", "en": "Logistics"},
    "core.esquema.ordenes_compra": {"es": "Órdenes de compra", "en": "Purchase orders"},
    "core.esquema.recepciones": {"es": "Recepciones", "en": "Receipts"},
    "core.esquema.compras": {"es": "Compras", "en": "Purchases"},
    "core.esquema.entregas": {"es": "Entregas", "en": "Deliveries"},
    "core.esquema.pagos": {"es": "Pagos", "en": "Payments"},
    "core.esquema.activa_venta_0": {"es": "rotación por producto", "en": "turnover per product"},
    "core.esquema.activa_venta_1": {"es": "margen real por producto", "en": "real margin per product"},
    "core.esquema.activa_venta_2": {"es": "alertas de quiebre de stock", "en": "stock-out alerts"},
    "core.esquema.activa_venta_3": {"es": "stock excedente liberable", "en": "excess stock you can free up"},
    "core.esquema.activa_cliente_0": {"es": "ranking de clientes por volumen", "en": "customer ranking by volume"},
    "core.esquema.activa_cliente_1": {"es": "cuentas corrientes con nombre", "en": "customer accounts with names"},
    "core.esquema.activa_proveedor_0": {"es": "costo de reposición por proveedor", "en": "replacement cost per supplier"},
    "core.esquema.activa_proveedor_1": {"es": "órdenes de pedido por proveedor", "en": "purchase orders per supplier"},
    "core.esquema.activa_cuenta_corriente_0": {"es": "identificación de morosos (nombre, monto, días)",
                                               "en": "overdue customers identified (name, amount, days)"},
    "core.esquema.activa_cuenta_corriente_1": {"es": "alertas de cobro", "en": "collection alerts"},
    "core.esquema.activa_deposito_0": {"es": "consultas de ubicación por producto", "en": "location lookups per product"},
    "core.esquema.activa_deposito_1": {"es": "alertas de vencimiento próximo", "en": "upcoming expiry alerts"},
    "core.esquema.activa_deposito_2": {"es": "discrepancias entre stock contable y físico",
                                       "en": "differences between book and physical stock"},
    "core.esquema.activa_logistica_0": {"es": "estado de envío por cliente", "en": "shipment status per customer"},
    "core.esquema.activa_logistica_1": {"es": "alertas de entregas atrasadas", "en": "late delivery alerts"},
    "core.esquema.activa_logistica_2": {"es": "resumen del día de reparto", "en": "delivery day summary"},
    "core.esquema.activa_ordenes_compra_0": {"es": "control remito ↔ orden de compra al recibir mercadería",
                                              "en": "delivery-note vs. purchase-order matching on receipt"},
    "core.esquema.activa_entregas_0": {"es": "entregas parciales y backorders abiertos",
                                       "en": "partial deliveries and open backorders"},
    "core.esquema.activa_compras_0": {"es": "cuenta corriente del proveedor (cuánto le debés y cuándo vence)",
                                      "en": "supplier account (what you owe and when it is due)"},
    "core.esquema.activa_recepciones_0": {"es": "mercadería que entra al stock con control contra lo pedido",
                                          "en": "goods received matched against what was ordered"},
    "core.esquema.activa_pagos_0": {"es": "pagos reales conciliados contra facturas y residuales",
                                    "en": "real payments reconciled against invoices and residuals"},
    # --- core/fase.py · la etapa del negocio --------------------------------------
    "core.fase.titulo_puesta": {"es": "Puesta a punto", "en": "Getting set up"},
    "core.fase.titulo_operacion": {"es": "En operación", "en": "Up and running"},
    "core.fase.msj_saneamiento": {
        "es": "Antes de arrancar a full, ordenemos tu sistema: tenés {issues} cosas para "
              "corregir en tus datos. Empezá por ahí y después cargamos tus ventas para que "
              "te muestre el margen real y las alertas de tu negocio.",
        "en": "Before going full speed, let's tidy up your system: you have {issues} things to "
              "fix in your data. Start there, and then we load your sales so I can show you "
              "real margins and your business alerts.",
    },
    "core.fase.msj_cargar": {
        "es": "Tu catálogo ya está limpio. El próximo paso es cargar tus ventas históricas "
              "para desbloquear el margen por producto y las alertas de quiebre.",
        "en": "Your catalog is already clean. The next step is loading your historical sales "
              "to unlock per-product margin and stock-out alerts.",
    },
    "core.fase.msj_operacion": {
        "es": "Tu sistema está al día. Te voy avisando lo que necesita tu atención.",
        "en": "Your system is up to date. I'll flag whatever needs your attention.",
    },
    # --- core/macro.py · fuente caída ---------------------------------------------
    "core.macro.no_respondio": {
        "es": "la fuente no respondió ({error})",
        "en": "the source didn't answer ({error})",
    },
    # --- core/documentos.py · títulos y labels (el contenido de datos no) ---------
    "core.doc.resumen_titulo": {
        "es": "Resumen ejecutivo del inventario",
        "en": "Inventory executive summary",
    },
    "core.doc.kpi_inmovilizado": {"es": "Plata inmovilizada", "en": "Money tied up"},
    "core.doc.kpi_articulos": {"es": "Artículos", "en": "Items"},
    "core.doc.kpi_problemas": {
        "es": "Productos con problemas de dato",
        "en": "Products with data issues",
    },
    "core.doc.tabla_top": {
        "es": "Top 10 productos por plata parada",
        "en": "Top 10 products by idle money",
    },
    "core.doc.col_producto": {"es": "Producto", "en": "Product"},
    "core.doc.col_stock": {"es": "Stock", "en": "Stock"},
    "core.doc.col_plata": {"es": "Plata parada", "en": "Idle money"},
    "core.doc.accion_perdida": {
        "es": "Corregir el precio de {n} productos que se venden a pérdida "
              "({monto} en juego).",
        "en": "Fix the price of {n} products selling at a loss "
              "({monto} at stake).",
    },
    "core.doc.accion_conteo": {
        "es": "Conteo físico de {n} productos en stock negativo.",
        "en": "Physical count of {n} products in negative stock.",
    },
    "core.doc.accion_cargar": {
        "es": "Cargar las ventas históricas para activar rotación, margen real y alertas de quiebre.",
        "en": "Load the historical sales to switch on turnover, real margin and stock-out alerts.",
    },
    # --- core/pdf.py · etiquetas del PDF real (P17·E1) -------------------------
    "core.pdf.pedido_por": {"es": "Pedido por", "en": "Requested by"},
    "core.pdf.generado_por": {
        "es": "Generado por PolPilot / Ángela",
        "en": "Generated by PolPilot / Ángela",
    },
    "core.pdf.destinatario": {"es": "Destinatario", "en": "To"},
    "core.pdf.proveedor": {"es": "Proveedor", "en": "Supplier"},
    "core.pdf.plazo": {"es": "Plazo de pago", "en": "Payment terms"},
    "core.pdf.col_producto": {"es": "Producto", "en": "Product"},
    "core.pdf.col_cantidad": {"es": "Cantidad", "en": "Quantity"},
    "core.pdf.col_motivo": {"es": "Motivo", "en": "Reason"},
    "core.pdf.col_costo": {"es": "Costo unit.", "en": "Unit cost"},
    "core.pdf.issues_titulo": {"es": "Qué corregir", "en": "What to fix"},
    "core.pdf.col_problema": {"es": "Problema", "en": "Issue"},
    "core.pdf.col_items": {"es": "Productos", "en": "Products"},
    "core.pdf.col_riesgo": {"es": "$ en riesgo", "en": "$ at risk"},
    "core.pdf.acciones_titulo": {"es": "Próximas acciones", "en": "Next actions"},
    "core.pdf.disclaimer": {
        "es": "Generado por PolPilot el {fecha}. Datos del sistema del cliente.",
        "en": "Generated by PolPilot on {fecha}. Data from the client's system.",
    },
    # --- P18·B · el resumen que ANALIZA (pirámide: veredicto → hallazgos → acciones) ---
    "core.doc.veredicto_rot": {
        "es": "Tu inventario está {salud}, pero tenés {dormido} frenados en productos que no rotan "
              "({pct}% del stock). Liquidando los 5 peores recuperás {top5}.",
        "en": "Your inventory is {salud}, but you have {dormido} stuck in products that don't turn "
              "({pct}% of your stock). Clearing the worst 5 gets you {top5} back.",
    },
    "core.doc.veredicto_base": {
        "es": "Tu inventario está {salud}, con {inmovilizado} de capital inmovilizado. "
              "Con las ventas cargadas, este resumen pasa a decirte qué liquidar y cuánto recuperás.",
        "en": "Your inventory is {salud}, with {inmovilizado} tied up. Once sales are loaded, "
              "this summary starts telling you what to clear and how much you get back.",
    },
    "core.doc.h_dormido_sin_venta": {
        "es": "El {pct}% de tu capital está en productos sin venta en 60+ días. El más pesado, "
              "{producto}, lleva un año sin una sola venta y tiene {monto} parados: devolución "
              "al proveedor o liquidación.",
        "en": "{pct}% of your capital sits in products with no sales in 60+ days. The heaviest, "
              "{producto}, hasn't sold once in a year and has {monto} stuck: return it to the "
              "supplier or run it out on offer.",
    },
    "core.doc.h_dormido_lento": {
        "es": "El {pct}% de tu capital está en productos que rotan lento. El más pesado, "
              "{producto}, tarda {dias} días en venderse y tiene {monto} parados: oferta, "
              "combo o devolución.",
        "en": "{pct}% of your capital sits in slow-turning products. The heaviest, {producto}, "
              "takes {dias} days to sell through and has {monto} stuck: deal, bundle or return.",
    },
    "core.doc.h_pico": {
        "es": "{mes} te multiplica ×{indice} las ventas de {cat} (histórico multi-año). "
              "Conviene confirmar los pedidos con el proveedor unas 3 semanas antes para no "
              "comprar el pico a precio de apuro.",
        "en": "{mes} multiplies your {cat} sales by ×{indice} (multi-year history). Confirm "
              "supplier orders about 3 weeks ahead so you don't buy the peak at rush prices.",
    },
    "core.doc.h_morosos": {
        "es": "{n} clientes concentran {total} vencidos. El más pesado, {nombre}, está pagando "
              "un {atraso}% más tarde que su propio promedio histórico: el recordatorio a tiempo "
              "es la palanca más barata que tenés.",
        "en": "{n} customers hold {total} past due. The heaviest, {nombre}, is paying {atraso}% "
              "later than their own historical average: a timely reminder is your cheapest lever.",
    },
    "core.doc.acc_liquidar": {
        "es": "Liquidar los 5 productos más dormidos (oferta, combo o devolución): recuperás {monto}.",
        "en": "Clear the 5 most dormant products (deal, bundle or return): you recover {monto}.",
    },
    "core.doc.acc_recordatorio": {
        "es": "Mandar el recordatorio de cobro a los {n} morosos ({monto} vencidos). "
              "Puedo dejarte el mensaje listo con tu OK.",
        "en": "Send the payment reminder to the {n} overdue customers ({monto} past due). "
              "I can have the message ready with your OK.",
    },
    "core.doc.acc_balanzas": {
        "es": "Corregir el peso teórico de las {n} balanzas mal calibradas: {monto} de stock "
              "cobrándose mal en cada corte.",
        "en": "Fix the theoretical weight on the {n} miscalibrated scales: {monto} of stock "
              "mischarged on every slice.",
    },
    "core.doc.acc_pvp": {
        "es": "Cargar el precio de venta de los {n} productos que no lo tienen: {monto} en "
              "góndola vendiéndose a ojo.",
        "en": "Load the sale price on the {n} products missing one: {monto} on the shelf "
              "selling by eye.",
    },
    "core.doc.v_balanzas": {
        "es": "{n} balanzas con peso teórico fuera de rango (el origen de la merma en fiambres).",
        "en": "{n} scales with theoretical weight out of range (where deli shrinkage comes from).",
    },
    "core.doc.v_costos": {
        "es": "{n} productos con costo de más de un año: ese margen no es confiable hasta actualizarlo.",
        "en": "{n} products with costs over a year old: that margin isn't reliable until updated.",
    },
    "core.doc.v_negativos": {
        "es": "{n} productos en stock negativo: el sistema dice tener menos que cero.",
        "en": "{n} products in negative stock: the system claims less than zero on hand.",
    },
    "core.doc.resumen_nota": {
        "es": "Generado por PolPilot desde el núcleo de verdad del negocio. Compartible con tu contador o banco.",
        "en": "Generated by PolPilot from the business's core of truth. Shareable with your accountant or bank.",
    },
    "core.doc.orden_titulo": {
        "es": "Orden de pedido a proveedor",
        "en": "Purchase order to supplier",
    },
    "core.doc.orden_proveedor": {"es": "(a completar)", "en": "(to fill in)"},
    "core.doc.orden_plazo": {"es": "(a definir)", "en": "(to define)"},
    "core.doc.orden_sin_stock": {"es": "sin stock", "en": "out of stock"},
    "core.doc.orden_negativo": {"es": "stock negativo", "en": "negative stock"},
    "core.doc.orden_cobertura": {
        "es": "cubre ~{dias} días de venta",
        "en": "covers ~{dias} days of sales",
    },
    "core.doc.orden_total": {"es": "Total estimado", "en": "Estimated total"},
    "core.pdf.hallazgos_titulo": {"es": "Lo que importa", "en": "What matters"},
    "core.pdf.vigilar_titulo": {"es": "Para vigilar", "en": "Watch list"},
    "core.pdf.anexo_titulo": {"es": "Anexo de datos", "en": "Data appendix"},
    # P38·E — el reporte de cierres por local (el Excel que alguien hace a mano)
    "core.doc.cierres_titulo": {
        "es": "Reporte de cierres por local",
        "en": "Register closings by store",
    },
    "core.doc.cierres_veredicto": {
        "es": "En los últimos {dias} días los locales hicieron {total}, {var} contra "
              "los {dias} días anteriores. {mejor} creció {mejor_pct} y {peor} cayó "
              "{peor_pct}: ahí está la diferencia.",
        "en": "Over the last {dias} days the stores did {total}, {var} against the "
              "previous {dias} days. {mejor} grew {mejor_pct} and {peor} fell "
              "{peor_pct}: that's where the difference is.",
    },
    "core.doc.cierres_veredicto_simple": {
        "es": "En los últimos {dias} días los locales hicieron {total}, {var} contra "
              "los {dias} días anteriores.",
        "en": "Over the last {dias} days the stores did {total}, {var} against the "
              "previous {dias} days.",
    },
    "core.doc.cierres_h_local": {
        "es": "{local}: {total} ({pct} vs el período anterior).",
        "en": "{local}: {total} ({pct} vs the previous period).",
    },
    "core.doc.cierres_kpi_total": {"es": "Total del período", "en": "Period total"},
    "core.doc.cierres_kpi_previo": {"es": "Período anterior", "en": "Previous period"},
    "core.doc.cierres_kpi_var": {"es": "Variación", "en": "Change"},
    "core.doc.cierres_tabla": {
        "es": "Cierre por local · {desde} → {hasta}",
        "en": "Closings by store · {desde} → {hasta}",
    },
    "core.doc.cierres_col_local": {"es": "Local", "en": "Store"},
    "core.doc.cierres_col_actual": {"es": "Este período", "en": "This period"},
    "core.doc.cierres_col_previo": {"es": "Período anterior", "en": "Previous period"},
    "core.doc.cierres_col_var": {"es": "Variación", "en": "Change"},
    "core.doc.cierres_acc_peor": {
        "es": "Pasar por {local} y entender la caída de {pct}: es la única boca que "
              "se mueve en contra del resto.",
        "en": "Stop by {local} and understand the {pct} drop: it's the only store "
              "moving against the rest.",
    },
    "core.doc.cierres_acc_mejor": {
        "es": "Ver qué está haciendo {local} para replicarlo en las otras bocas.",
        "en": "See what {local} is doing and replicate it at the other stores.",
    },
    "core.doc.cierres_acc_auto": {
        "es": "Este reporte lo tenés listo cuando quieras: los cierres ya están "
              "cargados, no hace falta imputarlos a mano.",
        "en": "This report is ready whenever you want it: the closings are already "
              "loaded, nobody needs to key them in by hand.",
    },
    "core.doc.cierres_nota": {
        "es": "Comparado contra el período {desde} → {hasta}. Sale de los cierres "
              "diarios de cada boca, tal como se cargaron.",
        "en": "Compared against the {desde} → {hasta} period. Built from each "
              "store's daily closings, exactly as they were loaded.",
    },
    "core.doc.orden_nota": {
        "es": "Cantidades sugeridas en base al stock actual. Cuando carguemos las ventas, ajusto "
              "cada cantidad con la rotación real de cada producto. Editá lo que quieras antes de generar.",
        "en": "Quantities suggested from the current stock. Once we load the sales, I'll tune "
              "each quantity with each product's real turnover. Edit whatever you want before generating.",
    },
    "core.doc.carta_titulo": {"es": "Carta", "en": "Letter"},
    "core.doc.carta_destinatario": {"es": "(destinatario)", "en": "(recipient)"},
    "core.doc.carta_nota": {
        "es": "Borrador base. Editalo y generá el PDF, o pedile a Ángela que lo ajuste.",
        "en": "Base draft. Edit it and generate the PDF, or ask Ángela to tweak it.",
    },
    # --- core/recordatorios.py · detalle del disparo -------------------------------
    "core.rec.venc_deposito": {
        "es": "{n} lotes del depósito vencen en menos de {dias} días. "
              "El más urgente: {producto} (lote {lote}, "
              "{restantes} días).",
        "en": "{n} warehouse batches expire in less than {dias} days. "
              "Most urgent: {producto} (batch {lote}, "
              "{restantes} days).",
    },
    "core.rec.entrega_pendiente": {
        "es": "La entrega de {cliente} (pedido {pedido}) "
              "sigue sin salir: está «{estado}».",
        "en": "The delivery for {cliente} (order {pedido}) "
              "still hasn't gone out: it shows «{estado}».",
    },
    "core.rec.llego_batch": {
        "es": "Llegó «{nombre}» ({tipo}).",
        "en": "«{nombre}» arrived ({tipo}).",
    },

    # --- Bloque F · el registro de auditoría, en idioma de persona -------------
    # Una línea por acción auditada. El slug es el identificador (no se traduce);
    # esto es lo que el dueño LEE. Si mañana se audita algo nuevo y no entra acá,
    # cae en `audit.acc.generico` con el slug legible — se ve, no se esconde.
    "audit.acc.generico": {"es": "{accion}", "en": "{accion}"},
    "audit.acc.sanear": {"es": "Limpió «{cat}» en el catálogo",
                         "en": "Cleaned up «{cat}» in the catalog"},
    "audit.acc.sanear_fantasma_custom": {
        "es": "Dio de baja productos fantasma elegidos a mano",
        "en": "Retired hand-picked phantom products"},
    "audit.acc.cobranza_recordado": {"es": "Mandó el recordatorio de cobro",
                                     "en": "Sent the payment reminder"},
    "audit.acc.cobranza_promesa": {"es": "Anotó que el cliente prometió pagar",
                                   "en": "Logged the customer's promise to pay"},
    "audit.acc.cobranza_pagado": {"es": "Registró el pago del cliente",
                                  "en": "Logged the customer's payment"},
    "audit.acc.cobranza_sin_respuesta": {"es": "Anotó que el cliente no contestó",
                                         "en": "Logged that the customer didn't reply"},
    "audit.acc.cobranza_pendiente": {"es": "Volvió la gestión a pendiente",
                                     "en": "Put the collection back to pending"},
    "audit.acc.corregir_precio_perdida": {"es": "Corrigió un precio que vendía a pérdida",
                                          "en": "Fixed a price that was selling at a loss"},
    "audit.acc.aplicar_lista_precios": {"es": "Aplicó una lista de precios nueva",
                                        "en": "Applied a new price list"},
    "audit.acc.cargar_remito": {"es": "Cargó un remito desde la foto",
                                "en": "Logged a delivery note from the photo"},
    "audit.acc.cargar_factura": {"es": "Cargó una factura desde la foto",
                                 "en": "Logged an invoice from the photo"},
    "audit.acc.cargar_recibo": {"es": "Cargó un recibo desde la foto",
                                "en": "Logged a receipt from the photo"},
    "audit.acc.cargar_orden_compra": {"es": "Cargó una orden de compra",
                                      "en": "Logged a purchase order"},
    "audit.acc.integrar_staging": {"es": "Integró un archivo a los datos del negocio",
                                   "en": "Merged a file into the business data"},
    "audit.acc.crear_apartado": {"es": "Abrió un apartado de datos nuevo",
                                 "en": "Opened a new data section"},
    "audit.acc.validacion_montos_ventas": {"es": "Validó los montos de ventas contra el sistema",
                                           "en": "Checked sales amounts against the system"},
    "audit.acc.normalizacion_nivel1": {
        "es": "Normalizó el archivo al entrar (mayúsculas, espacios, separadores)",
        "en": "Normalized the file on the way in (case, spacing, separators)"},
    "audit.acc.revertir_normalizacion_nivel1": {"es": "Deshizo la normalización de un archivo",
                                                "en": "Undid a file's normalization"},
    "audit.acc.revertir_version": {"es": "Volvió los datos a una versión anterior",
                                   "en": "Rolled the data back to an earlier version"},
    "audit.acc.restaurar_version": {"es": "Restauró una versión guardada de los datos",
                                    "en": "Restored a saved version of the data"},
    "audit.acc.preparar_orden_compra": {"es": "Preparó una orden de compra para aprobar",
                                        "en": "Prepared a purchase order for approval"},
    "audit.acc.crear_ubicacion": {"es": "Creó una ubicación de depósito",
                                  "en": "Created a warehouse location"},
    "audit.acc.editar_ubicacion": {"es": "Editó una ubicación de depósito",
                                   "en": "Edited a warehouse location"},
    "audit.acc.eliminar_ubicacion": {"es": "Eliminó una ubicación de depósito",
                                     "en": "Deleted a warehouse location"},
    "audit.acc.crear_proveedor": {"es": "Dio de alta un proveedor",
                                  "en": "Added a vendor"},
    "audit.acc.editar_proveedor": {"es": "Editó la ficha de un proveedor",
                                   "en": "Edited a vendor's record"},
    "audit.acc.eliminar_proveedor": {"es": "Eliminó un proveedor",
                                     "en": "Deleted a vendor"},
    "audit.acc.upsert_proveedores_conector": {"es": "Actualizó proveedores desde un conector",
                                              "en": "Updated vendors from a connector"},
    "audit.acc.crear_lote": {"es": "Dio de alta un lote de depósito",
                             "en": "Added a warehouse lot"},
    "audit.acc.editar_lote": {"es": "Editó un lote de depósito",
                              "en": "Edited a warehouse lot"},
    "audit.acc.eliminar_lote": {"es": "Eliminó un lote de depósito",
                                "en": "Deleted a warehouse lot"},
    "audit.acc.crear_articulo": {"es": "Dio de alta un producto",
                                 "en": "Added a product"},
    "audit.acc.editar_articulo": {"es": "Editó un producto", "en": "Edited a product"},
    "audit.acc.eliminar_articulo": {"es": "Eliminó un producto", "en": "Deleted a product"},
    "audit.acc.crear_articulo_conector": {"es": "Dio de alta un producto desde un conector",
                                          "en": "Added a product from a connector"},
    "audit.acc.actualizar_articulo_conector": {"es": "Actualizó un producto desde un conector",
                                               "en": "Updated a product from a connector"},
    "audit.acc.crear_orden_compra": {"es": "Creó una orden de compra manual",
                                     "en": "Created a manual purchase order"},
    "audit.acc.cambiar_estado_orden_compra": {"es": "Cambió el estado de una orden de compra",
                                              "en": "Changed a purchase order's status"},
    "audit.acc.upsert_ordenes_compra_conector": {"es": "Actualizó órdenes de compra desde un conector",
                                                 "en": "Updated purchase orders from a connector"},
    "audit.acc.upsert_ventas_conector": {"es": "Actualizó ventas desde un conector",
                                         "en": "Updated sales from a connector"},
    "audit.acc.upsert_deposito_conector": {"es": "Actualizó el depósito desde un conector",
                                           "en": "Updated warehouse positions from a connector"},
    "audit.acc.upsert_recepciones_conector": {"es": "Actualizó recepciones desde un conector",
                                              "en": "Updated receipts from a connector"},
    "audit.acc.reportar_faltante": {"es": "Reportó un faltante en el depósito",
                                    "en": "Reported a shortage in the warehouse"},
    "audit.acc.marcar_conteo": {"es": "Cargó un conteo de stock",
                                "en": "Logged a stock count"},
    "audit.acc.confirmar_entrega": {"es": "Confirmó una entrega",
                                    "en": "Confirmed a delivery"},
    "audit.acc.pedir_reposicion": {"es": "Pidió reposición de un producto",
                                   "en": "Requested a restock"},
    "audit.acc.registrar_pedido": {"es": "Registró un pedido del mostrador",
                                   "en": "Logged an order from the counter"},
    "audit.acc.registrar_presupuesto": {"es": "Registró un presupuesto por WhatsApp",
                                        "en": "Logged a WhatsApp quote request"},
    "audit.acc.resolver_reporte_piso": {"es": "Resolvió un reporte del piso",
                                        "en": "Closed a floor report"},
    "audit.acc.solicitar_modulo": {"es": "Pidió acceso a un módulo",
                                   "en": "Requested access to a module"},
    "audit.acc.resolver_solicitud_modulo": {"es": "Resolvió un pedido de acceso",
                                            "en": "Resolved an access request"},
    "audit.acc.cambiar_modulo_empleado": {"es": "Cambió los módulos de una persona",
                                          "en": "Changed a person's modules"},
    "audit.acc.cambiar_autonomia_angela": {"es": "Cambió cuánto puede hacer Ángela sola",
                                           "en": "Changed how much Ángela can do alone"},
    "audit.acc.editar_descripcion_perfil": {"es": "Editó la descripción de su perfil",
                                            "en": "Edited their profile description"},
    "audit.acc.cambiar_foto_perfil": {"es": "Cambió su foto de perfil",
                                      "en": "Changed their profile photo"},
    "audit.acc.cambiar_idioma": {"es": "Cambió su idioma", "en": "Changed their language"},
    "audit.acc.consulta_angela": {"es": "Consulta a Ángela", "en": "Question to Ángela"},
    "audit.acc.reset_demo_publico": {"es": "Reinició el demo público",
                                     "en": "Reset the public demo"},

    # --- Bloque F · autonomía graduada ---------------------------------------
    "autonomia.clase_plata": {"es": "Plata: cobranzas y precios",
                              "en": "Money: collections and prices"},
    "autonomia.clase_stock": {"es": "Stock: compras y depósito",
                              "en": "Stock: purchasing and warehouse"},
    "autonomia.clase_permisos": {"es": "Permisos: quién ve qué",
                                 "en": "Permissions: who sees what"},
    "autonomia.clase_datos": {"es": "Datos: limpieza reversible",
                              "en": "Data: reversible cleanups"},
    "autonomia.nivel_pide_ok": {"es": "Te pide el OK de a una",
                                "en": "Asks you one by one"},
    "autonomia.nivel_pide_ok_det": {
        "es": "Ángela te muestra cada propuesta por separado y espera.",
        "en": "Ángela shows you each proposal separately and waits."},
    "autonomia.nivel_agrupa": {"es": "Te pide el OK todo junto",
                               "en": "Asks you all at once"},
    "autonomia.nivel_agrupa_det": {
        "es": "Ángela junta lo rutinario en una sola aprobación. Seguís decidiendo vos, "
              "pero te interrumpe una vez en vez de ocho.",
        "en": "Ángela bundles the routine work into a single approval. You still decide, "
              "but she interrupts you once instead of eight times."},
    "autonomia.candado_plata": {
        "es": "Nada que toque plata sale sin tu OK. No se puede cambiar.",
        "en": "Nothing that touches money goes out without your OK. This can't be changed."},
    "autonomia.candado_stock": {
        "es": "Nada que mueva stock o compras sale sin tu OK. No se puede cambiar.",
        "en": "Nothing that moves stock or purchasing goes out without your OK. "
              "This can't be changed."},
    "autonomia.candado_permisos": {
        "es": "Los accesos los das vos. No se puede cambiar.",
        "en": "You grant access yourself. This can't be changed."},
    "autonomia.ya_hace_sola": {
        "es": "Lo único que Ángela hace hoy sin preguntarte: acomodar el formato de un "
              "archivo al entrar — mayúsculas, espacios, separadores de miles. No toca "
              "ningún número ni ningún precio, queda con respaldo y lo deshacés con un click.",
        "en": "The only thing Ángela does today without asking: tidy a file's formatting "
              "on the way in — case, spacing, thousand separators. It touches no number "
              "and no price, it's backed up, and you undo it with one click."},
    "autonomia.proximo_paso": {
        "es": "Más adelante vas a poder dejarle hacer sola alguna tarea de bajo riesgo y "
              "revisarla después, acá mismo. Todavía no: primero queremos que mires este "
              "registro un par de semanas y decidas con datos, no con una promesa.",
        "en": "Later on you'll be able to let her handle a low-risk task on her own and "
              "review it afterwards, right here. Not yet: first we want you to watch this "
              "log for a couple of weeks and decide on evidence, not on a promise."},

    # --- Prioridades inbox (chips + leftover alerts not covered by oportunidades) --
    "core.prio.chip_cobrar": {"es": "Cobrar", "en": "Collect"},
    "core.prio.chip_liquidar": {"es": "Liquidar", "en": "Liquidate"},
    "core.prio.chip_precio": {"es": "Precio", "en": "Price"},
    "core.prio.chip_comprar": {"es": "Comprar", "en": "Buy"},
    "core.prio.chip_vender": {"es": "Vender", "en": "Sell"},
    "core.prio.chip_planificar": {"es": "Planificar", "en": "Plan"},
    "core.prio.chip_riesgo": {"es": "Riesgo", "en": "Risk"},
    "core.prio.chip_reponer": {"es": "Reponer", "en": "Restock"},
    "core.prio.chip_pagar": {"es": "Pagar", "en": "Pay"},
    "core.prio.chip_deposito": {"es": "Depósito", "en": "Warehouse"},
    "core.prio.chip_equipo": {"es": "Tu equipo", "en": "Your team"},
    "core.prio.chip_ver": {"es": "Mirar", "en": "Watch"},
    "core.prio.chip_revisar": {"es": "Revisar", "en": "Review"},
    # --- Prioridades evidence labels (short claims — value/unit carry the number) --
    "core.prio.overdue_total_ev": {"es": "Saldo vencido total", "en": "Total overdue balance"},
    "core.prio.stockout_count_ev": {"es": "Artículos sin stock", "en": "Items out of stock"},
    "core.prio.payables_overdue_ev": {"es": "Total vencido a proveedores",
                                     "en": "Total overdue to suppliers"},
    "core.prio.payables_week_ev": {"es": "A pagar esta semana", "en": "Due this week"},
    "core.prio.checks_total_ev": {"es": "Total en cheques en cartera",
                                 "en": "Total value of checks on hand"},
    "core.prio.expired_lots_ev": {"es": "Valor de los lotes vencidos",
                                 "en": "Value of the expired lots"},
    "core.prio.expiring_lots_ev": {"es": "Valor de los lotes por vencer",
                                  "en": "Value of the lots about to expire"},
    "core.prio.discrepancy_count_ev": {"es": "Diferencias entre el físico y el sistema",
                                      "en": "Differences between physical count and system"},
    "core.prio.at_risk_value_ev": {"es": "Plata en riesgo por vencimiento",
                                  "en": "Value at risk from expiration"},
    "core.prio.stale_cost_value_ev": {"es": "Valor inmovilizado por costo desactualizado",
                                     "en": "Value stuck due to a stale cost"},
    "core.prio.cash_today_ev": {"es": "Caja de hoy", "en": "Today's till"},
    "core.prio.f_cuentas": {"es": "Cuentas corrientes", "en": "Receivables"},
    "core.prio.f_stock": {"es": "Stock", "en": "Stock"},
    "core.prio.f_ventas": {"es": "Ventas", "en": "Sales"},
    "core.prio.f_finanzas": {"es": "Pagos a proveedores", "en": "Vendor payments"},
    "core.prio.f_deposito": {"es": "Depósito", "en": "Warehouse"},
    "core.prio.f_costos": {"es": "Costos", "en": "Costs"},
    "core.prio.f_caja": {"es": "Caja del día", "en": "Today's till"},
    "core.prio.morosos_t": {"es": "Clientes en mora", "en": "Overdue customers"},
    "core.prio.morosos_r": {
        "es": "{n} clientes, {monto} trabado.",
        "en": "{n} customers, {monto} stuck."},
    "core.prio.morosos_p": {
        "es": "{n} clientes en mora por {monto}.",
        "en": "{n} overdue customers for {monto}."},
    "core.prio.morosos_chat": {
        "es": "Ayudame a cobrar a los que están en mora.",
        "en": "Help me collect from the overdue customers."},
    "core.prio.atraso_t": {
        "es": "{nombre} viene mucho más lento que de costumbre",
        "en": "{nombre} is paying much slower than usual"},
    "core.prio.atraso_r": {
        "es": "{dias} días sin pagar, {atraso}% más que su promedio.",
        "en": "{dias} days without paying, {atraso}% above their average."},
    "core.prio.atraso_r_lbl": {
        "es": "Días sin pagar vs. su promedio",
        "en": "Days unpaid vs. their average"},
    "core.prio.atraso_p": {
        "es": "{nombre} lleva {dias} días; su promedio era {prom}.",
        "en": "{nombre} is at {dias} days; their average was {prom}."},
    "core.prio.atraso_chat": {
        "es": "¿Qué hago con {nombre}, que se atrasó de más?",
        "en": "What should I do about {nombre}, who is later than usual?"},
    "core.prio.atraso_i": {"es": "sin pagar hace {dias} días", "en": "unpaid for {dias} days"},
    "core.prio.quiebre_t": {"es": "Productos que se están por acabar",
                            "en": "Products about to run out"},
    "core.prio.quiebre_r": {"es": "{n} SKU debajo de la cobertura de reposición.",
                           "en": "{n} SKUs below restock coverage."},
    "core.prio.quiebre_p": {"es": "Hay {n} productos activos con demanda que no llegan a la próxima reposición.",
                           "en": "{n} active products with demand will not last until the next restock."},
    "core.prio.quiebre_chat": {"es": "¿Qué tengo que reponer ya?",
                              "en": "What do I need to restock now?"},
    "core.prio.quiebre_i": {"es": "{dias} días de cobertura",
                            "en": "{dias} days of coverage"},
    "core.method.mora_total": {
        "es": "Suma de saldos vencidos de clientes con al menos un comprobante impago pasada su fecha.",
        "en": "Sum of overdue balances for clients with at least one unpaid invoice past its due date.",
    },
    "core.method.dias_mora": {
        "es": "Días entre la última cobranza registrada del cliente y hoy.",
        "en": "Days between the client's last recorded payment and today.",
    },
    "core.method.prom_pago": {
        "es": "Promedio de días entre cobranzas de ese cliente en su historia.",
        "en": "That client's historical average days between payments.",
    },
    "core.method.quiebre_conteo": {
        "es": "Artículos cuya cobertura proyectada, al ritmo de venta actual, es menor al lead time del proveedor.",
        "en": "Items whose projected coverage at the current sales rate is below supplier lead time.",
    },
    "core.prio.morosos_hyp": {
        "es": "La mora está concentrada: son pocos clientes, no una caída general de la cobranza.",
        "en": "The overdue balance is concentrated — a few clients, not a general collections slump.",
    },
    "core.prio.atraso_hyp": {
        "es": "{nombre} cambió su comportamiento de pago, no necesariamente su capacidad.",
        "en": "{nombre}'s payment behaviour changed — not necessarily their ability to pay.",
    },
    "core.prio.atraso_alt": {
        "es": "Puede haber un pago hecho y todavía no registrado.",
        "en": "There may be a payment made but not yet recorded.",
    },
    "core.prio.atraso_fals": {
        "es": "Un comprobante de pago posterior a la última cobranza registrada.",
        "en": "A payment receipt dated after the last recorded collection.",
    },
    "core.prio.mora_sup": {
        "es": "Asumo que no hubo pagos en efectivo sin registrar.",
        "en": "I assume there were no unrecorded cash payments.",
    },
    "core.prio.mora_sup_if": {
        "es": "La mora real sería menor.",
        "en": "The real overdue figure would be lower.",
    },
    "core.prio.quiebre_hyp": {
        "es": "El faltante es de reposición, no de demanda: se vende igual que siempre.",
        "en": "This is a restocking gap, not a demand drop — sales are unchanged.",
    },
    "core.prio.quiebre_risk": {
        "es": "Venta perdida mientras el artículo no esté en góndola.",
        "en": "Lost sales for as long as the item is off the shelf.",
    },
    "core.prio.mora_risk": {
        "es": "Capital inmovilizado en la calle.",
        "en": "Working capital stuck with customers.",
    },
    "core.prio.pago_vencido_t": {"es": "Pagos a proveedores ya vencidos",
                                "en": "Vendor payments already due"},
    "core.prio.pago_vencido_r": {"es": "{n} pagos, {monto}.",
                                "en": "{n} payments, {monto}."},
    "core.prio.pago_vencido_p": {"es": "Hay {n} pagos vencidos.",
                                "en": "There are {n} overdue payments."},
    "core.prio.pago_vencido_chat": {"es": "Mostrame los pagos vencidos a proveedores.",
                                   "en": "Show me the overdue vendor payments."},
    "core.prio.pago_vencido_g": {"es": "Facturas vencidas por monto", "en": "Overdue bills by amount"},
    "core.prio.pago_vencido_i": {"es": "vencida hace {dias} días", "en": "overdue by {dias} days"},
    "core.prio.pago_semana_t": {"es": "A pagar esta semana",
                               "en": "Due this week"},
    "core.prio.pago_semana_r": {"es": "{monto} de acá a 7 días.",
                               "en": "{monto} in the next 7 days."},
    "core.prio.pago_semana_p": {"es": "Vencen esta semana {monto} en facturas de proveedores.",
                                "en": "{monto} in vendor bills are due this week."},
    "core.prio.pago_semana_g": {"es": "Por pagar esta semana, por monto", "en": "Due this week, by amount"},
    "core.prio.pago_semana_i": {"es": "vence en {dias} días", "en": "due in {dias} days"},
    "core.prio.pago_semana_chat": {"es": "¿Qué tengo que pagar esta semana?",
                                  "en": "What do I have to pay this week?"},
    "core.prio.cheques_t": {"es": "Cheques en cartera",
                           "en": "Cheques on hand"},
    "core.prio.cheques_r": {"es": "{n} cheques, {monto}.",
                           "en": "{n} cheques, {monto}."},
    "core.prio.cheques_p": {"es": "Tenés {n} cheques en cartera por {monto}.",
                            "en": "You have {n} checks in hand worth {monto}."},
    "core.prio.cheques_g": {"es": "Cheques en cartera por monto", "en": "Checks in hand by amount"},
    "core.prio.cheques_i": {"es": "banco {banco}", "en": "bank {banco}"},
    "core.prio.cheques_chat": {"es": "¿Cómo están los cheques en cartera?",
                              "en": "How do the cheques on hand look?"},
    "core.prio.dep_vencidos_t": {"es": "Lotes ya vencidos",
                                "en": "Lots already expired"},
    "core.prio.dep_vencidos_r": {"es": "{n} lotes pasaron la fecha.",
                                "en": "{n} lots are past date."},
    "core.prio.dep_vencidos_chat": {"es": "¿Qué lotes ya vencieron?",
                                   "en": "Which lots have already expired?"},
    "core.prio.dep_porvencer_t": {"es": "Lotes por vencer",
                                 "en": "Lots about to expire"},
    "core.prio.dep_porvencer_r": {"es": "{n} lotes en la ventana de alerta.",
                                 "en": "{n} lots in the alert window."},
    "core.prio.dep_porvencer_chat": {"es": "¿Qué vence pronto en el depósito?",
                                    "en": "What expires soon in the warehouse?"},
    "core.prio.dep_vencidos_p": {
        "es": "{n} lotes, {monto}, ya pasaron su fecha de vencimiento.",
        "en": "{n} lots, {monto}, are already past their expiration date."},
    "core.prio.dep_vencidos_g": {"es": "Lotes vencidos por valor", "en": "Expired lots by value"},
    "core.prio.dep_vencidos_i": {"es": "vencido hace {dias} días", "en": "expired {dias} days ago"},
    "core.prio.dep_vencidos_s": {"es": "Valor calculado al costo con IVA cargado en el catálogo.",
                                 "en": "Value computed at the catalog's costo_iva."},
    "core.prio.dep_porvencer_p": {
        "es": "{n} lotes entran en la ventana de vencimiento próximo.",
        "en": "{n} lots are entering the upcoming-expiration window."},
    "core.prio.dep_porvencer_g": {"es": "Lotes por vencer por valor", "en": "Expiring lots by value"},
    "core.prio.dep_porvencer_i": {"es": "vence en {dias} días", "en": "expires in {dias} days"},
    "core.prio.dep_discrep_t": {"es": "El físico no cierra con el sistema",
                               "en": "Physical count doesn't match the system"},
    "core.prio.dep_discrep_r": {"es": "{n} diferencias stock físico vs contable.",
                               "en": "{n} physical vs book differences."},
    "core.prio.dep_discrep_chat": {"es": "Mostrame las discrepancias de depósito.",
                                  "en": "Show me the warehouse discrepancies."},
    "core.prio.venc_riesgo_t": {"es": "{n} lotes que no llegás a vender",
                               "en": "{n} lots you won't sell in time"},
    "core.prio.venc_riesgo_r": {
        "es": "{producto} vence en {dias} días. {monto} en riesgo.",
        "en": "{producto} expires in {dias} days. {monto} at risk."},
    "core.prio.venc_riesgo_p": {
        "es": "{n} lotes, {monto}, no se venden al ritmo actual antes de vencer.",
        "en": "{n} lots, {monto}, won't sell at the current pace before they expire."},
    "core.prio.venc_riesgo_chat": {"es": "¿Qué lotes no llego a vender antes de que venzan?",
                                  "en": "Which lots won't I sell before they expire?"},
    "core.prio.venc_riesgo_g": {"es": "Lotes en riesgo por plata expuesta",
                                "en": "At-risk lots by exposed value"},
    "core.prio.venc_riesgo_i": {"es": "vence en {dias} días", "en": "expires in {dias} days"},
    "core.prio.venc_riesgo_s": {"es": "Ritmo de venta = unidades de los últimos 12 meses / 365.",
                                "en": "Sale pace = last 12 months' units / 365."},
    "core.prio.dep_discrep_p": {
        "es": "{n} artículo(s) tienen diferencia entre el stock del sistema y el del depósito.",
        "en": "{n} item(s) differ between system stock and warehouse stock.",
    },
    "core.method.dep_discrep": {
        "es": "Comparación entre la existencia registrada y el último conteo de depósito.",
        "en": "Recorded stock compared against the latest warehouse count.",
    },
    "core.prio.dep_porvencer_hyp": {
        "es": "Es un problema de rotación, no de compra de más: el lote entró y no salió a tiempo.",
        "en": "A turnover problem, not over-buying — the lot came in and did not move in time.",
    },
    "core.method.payables_overdue": {
        "es": "Suma de facturas de proveedores en estado pendiente cuya fecha de vencimiento ya pasó.",
        "en": "Sum of pending vendor bills whose due date has already passed.",
    },
    "core.method.payables_week": {
        "es": "Suma de facturas de proveedores en estado pendiente que vencen dentro de los próximos 7 días.",
        "en": "Sum of pending vendor bills due within the next 7 days.",
    },
    "core.method.checks": {
        "es": "Suma de cheques recibidos que todavía no fueron cobrados.",
        "en": "Sum of received checks not yet collected.",
    },
    "core.method.expired_lots": {
        "es": "Lotes de depósito cuya fecha de vencimiento ya pasó, valuados al costo con IVA del catálogo.",
        "en": "Warehouse lots past their expiration date, valued at the catalog's cost including VAT.",
    },
    "core.method.expiring_lots": {
        "es": "Lotes de depósito que vencen dentro de la ventana de alerta, valuados al costo con IVA del catálogo.",
        "en": "Warehouse lots expiring within the alert window, valued at the catalog's cost including VAT.",
    },
    "core.method.at_risk": {
        "es": "Lotes cuyo ritmo de venta actual no alcanza para agotarlos antes de vencer.",
        "en": "Lots whose current sale pace won't clear them before they expire.",
    },
    "core.prio.pago_vencido_risk": {
        "es": "Intereses o corte de suministro del proveedor si no se paga.",
        "en": "Interest charges or a supplier cutting off supply if left unpaid.",
    },
    "core.prio.pago_semana_risk": {
        "es": "Quiebre de caja si el pago no se planifica con anticipación.",
        "en": "A cash crunch if the payment isn't planned for ahead of time.",
    },
    "core.prio.cheques_risk": {
        "es": "Plata en cartera hasta la fecha de cobro de cada cheque.",
        "en": "Money held up until each check's collection date.",
    },
    "core.prio.dep_vencidos_risk": {
        "es": "Mercadería vencida que ya no se puede vender.",
        "en": "Expired merchandise that can no longer be sold.",
    },
    "core.prio.dep_porvencer_risk": {
        "es": "Se pierde si no rota antes de la fecha de vencimiento.",
        "en": "Lost if it doesn't turn over before its expiration date.",
    },
    "core.prio.venc_riesgo_risk": {
        "es": "Plata inmovilizada en lotes que no llegan a venderse a tiempo.",
        "en": "Money tied up in lots that won't sell in time.",
    },
    "core.prio.costo_viejo_t": {"es": "Costos sin actualizar hace más de un año",
                               "en": "Costs not updated in over a year"},
    "core.prio.costo_viejo_r": {"es": "{n} productos con costo viejo. El margen que ves no es real.",
                               "en": "{n} products with a stale cost. The margin you see isn't real."},
    "core.prio.costo_viejo_chat": {"es": "¿Qué costos tengo que actualizar?",
                                  "en": "Which costs do I need to update?"},
    "core.prio.costo_viejo_p": {"es": "{n} productos tienen su costo cargado hace más de un año.",
                                "en": "{n} products have a cost loaded over a year ago."},
    "core.prio.costo_viejo_g": {"es": "Costo desactualizado por plata parada",
                                "en": "Outdated cost by immobilized value"},
    "core.prio.costo_viejo_i": {"es": "costo cargado hace {dias} días",
                                "en": "cost loaded {dias} days ago"},
    "core.prio.caja_t": {"es": "La caja del día está fuera de lo habitual",
                        "en": "Today's till is off the usual range"},
    "core.prio.caja_r": {"es": "Hoy {total} contra un promedio de {prom}.",
                        "en": "Today {total} vs an average of {prom}."},
    "core.prio.caja_chat": {"es": "¿Por qué la caja de hoy está rara?",
                           "en": "Why does today's till look unusual?"},
    "core.prio.caja_g": {"es": "Total de caja, últimos cierres", "en": "Cash total, recent closes"},
    "core.prio.caja_hoy": {"es": "Hoy", "en": "Today"},
    "core.prio.caja_p": {"es": "El cierre de hoy ({total}) se desvía {pct}% del promedio de los últimos cierres ({prom}).",
                         "en": "Today's close ({total}) deviates {pct}% from the recent average ({prom})."},
    "core.prio.caja_s": {"es": "Promedio de los últimos cierres con caja positiva.",
                         "en": "Average of recent closes with a positive cash total."},
    "core.prio.caida_chat": {"es": "Explícame la caída interanual de la venta real.",
                            "en": "Explain the year-over-year drop in real sales."},
    "core.prio.caida_g": {"es": "Facturación real, mes a mes", "en": "Real revenue, month by month"},
    "core.prio.caida_s": {"es": "Deflactado con el IPC del último mes disponible.",
                          "en": "Deflated using the latest available CPI month."},
    "core.prio.pico_t": {"es": "Se viene un pico de compra",
                        "en": "A buying peak is coming"},
    "core.prio.pico_p": {"es": "En {mes} pega {cat}.",
                        "en": "{cat} spikes in {mes}."},
    "core.prio.pico_chat": {"es": "¿Cómo me preparo para el pico de {cat}?",
                           "en": "How do I prepare for the {cat} peak?"},
    "core.prio.costo_viejo_hyp": {
        "es": "El precio quedó viejo frente al costo, no es un problema de demanda.",
        "en": "The price fell behind the cost — this isn't a demand problem.",
    },
    "core.prio.caja_hyp": {
        "es": "Un movimiento puntual, no un cambio de nivel.",
        "en": "A one-off movement, not a level shift.",
    },
    "core.prio.caida_hyp": {
        "es": "La caída es de volumen, no de precio.",
        "en": "The drop is in volume, not price.",
    },
    "core.prio.yoy_change_lbl": {
        "es": "Variación interanual real",
        "en": "Real year-over-year change",
    },
    "core.prio.peak_multiplier_lbl": {
        "es": "Multiplicador de pico estacional",
        "en": "Seasonal peak multiplier",
    },
    "core.method.stale_cost_value": {
        "es": "Suma del valor inmovilizado (cantidad × costo) de los productos con costo cargado hace más de un año.",
        "en": "Sum of the immobilized value (quantity × cost) of products whose cost was loaded over a year ago.",
    },
    "core.method.stale_cost_rows": {
        "es": "Productos con costo cargado hace más de un año, ordenados por valor inmovilizado.",
        "en": "Products with a cost loaded over a year ago, sorted by immobilized value.",
    },
    "core.method.stale_cost_chart": {
        "es": "Valor inmovilizado por producto con costo desactualizado, de mayor a menor.",
        "en": "Immobilized value per product with a stale cost, highest to lowest.",
    },
    "core.method.cash_today": {
        "es": "Total de caja del cierre de hoy.",
        "en": "Today's closing cash total.",
    },
    "core.method.cash_history": {
        "es": "Total de caja de los últimos cierres con caja positiva, en orden cronológico.",
        "en": "Cash total of recent closes with a positive balance, in chronological order.",
    },
    "core.method.yoy_change": {
        "es": "Variación interanual de la facturación real (deflactada por IPC) del último mes contra el mismo mes del año anterior.",
        "en": "Year-over-year change in real (CPI-deflated) revenue for the latest month vs the same month last year.",
    },
    "core.method.yoy_series": {
        "es": "Facturación real mensual, deflactada por IPC, mes a mes.",
        "en": "Monthly real revenue, CPI-deflated, month by month.",
    },
    "core.method.peak_multiplier": {
        "es": "Índice de estacionalidad de la categoría para el mes: veces la venta promedio de un mes normal.",
        "en": "The category's seasonality index for the month: multiple of an average month's sales.",
    },
    # --- conciliación depósito (conteo vs sistema) --------------------------------
    "conc.hip.conteo_incompleto": {
        "es": "Este lote se contó, pero {n} lote(s) del mismo producto todavía no. Hasta completar el conteo no se puede explicar el hueco.",
        "en": "This lot was counted, but {n} other lot(s) of the same product were not. Until the count is complete the gap can't be explained.",
    },
    "conc.hip.tara": {
        "es": "La diferencia es {pct}%: por debajo del umbral de desvío de balanza ({umbral}%).",
        "en": "The gap is {pct}% — under the scale-drift threshold ({umbral}%).",
    },
    "conc.hip.venta_sin_bajar_stock": {
        "es": "Una venta de {qty} unidades el {fecha} cierra con el faltante: puede que el stock no se haya bajado.",
        "en": "A sale of {qty} units on {fecha} matches the shortage; stock may not have been reduced.",
    },
    "conc.hip.recepcion_sin_cargar": {
        "es": "Una recepción de {qty} unidades el {fecha} cierra con el sobrante: puede que no se haya cargado.",
        "en": "A receipt of {qty} units on {fecha} matches the surplus; it may not have been booked.",
    },
    "conc.hip.en_transito": {
        "es": "Hay {qty} unidades en tránsito ({lado}). Todavía no conviene aceptar el conteo.",
        "en": "{qty} units are in the pipeline ({lado}). Don't accept the count yet.",
    },
    "conc.hip.cantidad_mal_tipeada": {
        "es": "Contado {counted} contra sistema {cantidad}: parece un error de tipeo ×10.",
        "en": "Counted {counted} vs system {cantidad} looks like a ×10 typing error.",
    },
    "conc.hip.lote_vencido": {
        "es": "El lote venció el {vencimiento}; el faltante puede ser merma para dar de baja.",
        "en": "The lot expired on {vencimiento}; the shortage may be a write-off.",
    },
    "conc.hip.sin_explicacion": {
        "es": "No hay una venta, recepción, tránsito ni vencimiento que explique este hueco.",
        "en": "No matching sale, receipt, pipeline or expiry explains this gap.",
    },
    "conc.pipeline_in": {"es": "entrando", "en": "incoming"},
    "conc.pipeline_out": {"es": "saliendo", "en": "outgoing"},
    "core.stock_viz.aging_sin_fecha": {
        "es": "Los lotes no tienen fecha de ingreso, así que no puedo decir hace cuánto está la mercadería.",
        "en": "Lots have no inbound date, so I can't tell how long the merchandise has been sitting.",
    },
    "core.stock_viz.lead_sin_ordenes": {
        "es": "Todavía no hay órdenes de compra para cruzar contra las recepciones.",
        "en": "There are no purchase orders yet to match against receipts.",
    },
    "core.stock_viz.lead_sin_pares": {
        "es": "Hay recepciones, pero ninguna está atada a una orden con fecha. Sin ese cruce no puedo decir si el camión llega cuando promete.",
        "en": "There are receipts, but none are tied to a dated purchase order. Without that match I can't tell if the truck arrives when it promises.",
    },
    "core.stock_viz.burn_sin_sku": {
        "es": "No encuentro ese producto en el catálogo.",
        "en": "I can't find that product in the catalog.",
    },
    "core.stock_viz.burn_sin_ritmo": {
        "es": "Este producto no tiene ventas en el año: no hay ritmo para proyectar cuándo se acaba.",
        "en": "This product has no sales in the year, so there's no rate to project a stockout.",
    },
    "core.confidence.data_high": {
        "es": "Basado en {points} puntos de historia y {records} registros.",
        "en": "Based on {points} data points and {records} records.",
    },
    "core.confidence.data_medium": {
        "es": "Basado en {points} puntos y {records} registros — alcanza para la señal, no para el detalle.",
        "en": "Based on {points} points and {records} records — enough for the signal, not the detail.",
    },
    "core.confidence.data_low": {
        "es": "Poca evidencia detrás: {points} puntos, {records} registros.",
        "en": "Thin evidence behind this: {points} points, {records} records.",
    },
    "core.confidence.hyp_high": {
        "es": "No apoya en supuestos: la lectura sale directo de los datos.",
        "en": "Rests on no assumptions — the reading comes straight from the data.",
    },
    "core.confidence.hyp_medium": {
        "es": "Apoya en {assumptions} supuesto(s) y {alternatives} explicación(es) alternativa(s).",
        "en": "Rests on {assumptions} assumption(s) with {alternatives} alternative explanation(s).",
    },
    "core.confidence.hyp_low": {
        "es": "Lectura frágil: {assumptions} supuesto(s) y {alternatives} explicación(es) alternativa(s).",
        "en": "Fragile reading: {assumptions} assumption(s) and {alternatives} alternative explanation(s).",
    },
}


# Nombres de mes (1..12) por idioma. El ES es la lista histórica de
# analisis.MESES_ES; acá vive la versión bilingüe para todo el backend.
MESES = {
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
           "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
}


def mes_nombre(numero: int, lang: str | None = None) -> str:
    """Nombre del mes 1..12 en el idioma pedido (default el del tenant)."""
    lang = lang if lang in paths.IDIOMAS else paths.DEFAULT_LANG
    return MESES.get(lang, MESES["es"])[numero - 1]


# Weekday names (0=Monday..6=Sunday, same index as datetime.date.weekday())
# — for findings that call out ONE specific day (core/patrones.py: the cash
# shortfall pattern that repeats on a fixed weekday).
WEEKDAYS = {
    "es": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
}


def weekday_name(weekday: int, lang: str | None = None) -> str:
    """Name of weekday 0=Monday..6=Sunday (`datetime.date.weekday()`) in the
    requested language (defaults to the tenant's)."""
    lang = lang if lang in paths.IDIOMAS else paths.DEFAULT_LANG
    return WEEKDAYS.get(lang, WEEKDAYS["es"])[weekday]


# Rubros del dataset (los 8 `tipo` finitos). El valor crudo español es la clave
# interna (round-trip a consulta-serie); esto traduce SOLO el display, espejo del
# tCat del frontend. Cualquier hallazgo que inyecte una categoría debe pasarla
# por acá antes de meterla en un template (si no, se cuela español con app en EN).
CATEGORIAS_EN = {
    "aceites y aderezos": "Oils & dressings",
    "almacén seco": "Dry goods",
    "bebidas": "Beverages",
    "congelados": "Frozen",
    "fiambres y quesos (balanza)": "Cold cuts & cheese (scale)",
    "galletitas y golosinas": "Cookies & candy",
    "limpieza y perfumería": "Cleaning & toiletries",
    "lácteos": "Dairy",
}


def categoria(cat: str | None, lang: str | None = None) -> str:
    """El nombre de un rubro para el DISPLAY, traducido si la app está en EN.
    Sin match (nombre propio, SKU) devuelve el valor tal cual — no se traduce."""
    lang = lang if lang in paths.IDIOMAS else paths.DEFAULT_LANG
    if lang == "en":
        return CATEGORIAS_EN.get((cat or "").strip().lower(), cat or "")
    return cat or ""


def pesos(n: float, lang: str | None = None) -> str:
    """EL formateador de plata del backend — único, consciente del idioma.
    ES: $45.337.100 (punto para miles, como siempre). EN: $45,337,100
    (agrupación en-US: un reviewer yanqui lee $1.234 como un dólar con
    centavos). La moneda sigue siendo ARS; el sufijo lo decide el texto."""
    lang = lang if lang in paths.IDIOMAS else paths.DEFAULT_LANG
    crudo = f"{round(n or 0):,}"
    return "$" + (crudo if lang == "en" else crudo.replace(",", "."))


def t(key: str, lang: str | None = None, **params) -> str:
    lang = lang if lang in paths.IDIOMAS else paths.DEFAULT_LANG
    entrada = CATALOGO.get(key)
    if not entrada:
        return key  # que el bug se vea, no que se esconda
    texto = entrada.get(lang) or entrada.get("es") or key
    try:
        return texto.format(**params) if params else texto
    except (KeyError, IndexError):
        return texto
