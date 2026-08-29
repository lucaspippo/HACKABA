"""
usuarios_demo.py · El equipo de "Distribuidora del Litoral" (100% FICTICIO).

Organigrama realista de una distribuidora de alimentos mediana (~$750M/mes,
3 bocas, 2 camiones propios): 1 dueño, 2 de oficina, 1 compras, 1 encargado
de depósito + 4 de depósito (uno de ellos recién entrado), 2 choferes,
2 preventistas, 1 encargada de sucursal, 1 mostrador — y el equipo PolPilot.
Personas INVENTADAS.

Campos opcionales del perfil (los usa el que recién entra, ver
core/onboarding.py): `ingreso` (fecha de alta → antigüedad y chip "Nuevo") y
`puesto` (sector, turno, mentor, contrato). Quien no los declara sigue igual
que siempre: son aditivos.

Las descripciones usan el formato de BLOQUES del perfil (P6): "Mi función: …
Me encargo de: … Todos los días miro: … Decido sobre: …" — así el demo
muestra el flujo real de perfiles autoadministrados, y el sugeridor de
módulos trabaja sobre texto con la estructura que el producto propone.

BILINGÜE: cada descripción viaja también en inglés (`descripcion_en`, con los
marcadores de bloque en inglés: "My role / I take care of / Every day I look at
/ I decide on"). El demo se muestra en inglés y un párrafo entero en castellano
adentro de una pantalla en inglés se lee como un descuido. Mismo mecanismo que
el resto del contenido del dataset (conocimiento, notas del equipo): el dato
nace en los dos idiomas y la pantalla elige.

El CASTELLANO sigue siendo la fuente: `perfiles.sugerir_modulos` matchea
palabras clave sobre `descripcion`, y lo que una persona reescribe de su propio
perfil se guarda tal cual (sin traducir) y se muestra igual en los dos idiomas —
son SUS palabras.

Se selecciona con POLPILOT_TENANT=demo (ver core/paths.py y auth.py).
"""

USUARIOS = {
    "aldo": {
        "username": "aldo", "nombre": "Aldo", "rol": "Dueño", "es_admin": True,
        "telefono": "+5493410000001", "color": "#e0241b",
        "superficies": ["desktop", "mobile"],
        "descripcion": (
            "Mi función: fundé la distribuidora hace 22 años con una camioneta y tres "
            "clientes; hoy soy el dueño y la cabeza del negocio. "
            "Me encargo de: la relación con los proveedores grandes, los precios, las "
            "compras fuertes y todo lo que sea plata — firmo yo. "
            "Todos los días miro: dónde está parada la plata, quién me debe, qué se "
            "vence en el depósito y qué está haciendo cada uno del equipo. "
            "Decido sobre: precios, compras grandes, crédito a clientes y la gente."
        ),
        "descripcion_en": (
            "My role: I started this distributor 22 years ago with one pickup truck and "
            "three customers; today I own it and I'm the head of the business. "
            "I take care of: the relationship with the big suppliers, the prices, the "
            "large purchases and anything involving money — I sign that myself. "
            "Every day I look at: where the money is parked, who owes me, what's about to "
            "expire in the warehouse and what everyone on the team is up to. "
            "I decide on: prices, big purchases, customer credit and the people."
        ),
        "features": [
            "panel", "mapa", "inventario", "saneamiento", "finanzas", "cuentas", "caja", "deposito",
            "logistica", "evolucion", "alertas", "oportunidades", "equipo", "gestion_equipo",
            "cargar", "documentos", "cobranzas", "auditoria", "conectores",
            "perfil", "angela",
        ],
    },
    "marta": {
        "username": "marta", "nombre": "Marta", "rol": "Administración", "es_admin": False,
        "telefono": "+5493410000002", "color": "#e8a317",
        "superficies": ["desktop", "mobile"],
        "descripcion": (
            "Mi función: administración — estoy en la oficina hace 14 años, soy la que "
            "ordena el papelerío. "
            "Me encargo de: cargar las facturas de compra, emitir las de venta, "
            "conciliar la caja y pelearme con el banco cuando algo no cierra. "
            "Todos los días miro: la caja del día, los vencimientos de pago a "
            "proveedores y las cuentas corrientes de los que compran a plazo. "
            "Decido sobre: qué pago sale primero cuando la plata no alcanza para todo; "
            "los montos grandes los consulto con Aldo."
        ),
        "descripcion_en": (
            "My role: admin — I've been in the office for 14 years, I'm the one who keeps "
            "the paperwork in order. "
            "I take care of: entering purchase invoices, issuing the sales ones, "
            "reconciling the register and arguing with the bank when something doesn't add up. "
            "Every day I look at: the day's till, what we owe suppliers and when, and the "
            "accounts of everyone who buys on terms. "
            "I decide on: which payment goes out first when there isn't enough for all of "
            "them; the big amounts I check with Aldo."
        ),
        "features": ["panel", "administracion", "cuentas", "caja", "saneamiento", "documentos",
                     "evolucion", "cargar", "alertas", "equipo", "perfil", "angela"],
    },
    "celeste": {
        "username": "celeste", "nombre": "Celeste", "rol": "Compras y proveedores", "es_admin": False,
        "telefono": "+5493410000003", "color": "#15727e",
        "superficies": ["desktop", "mobile"],
        "descripcion": (
            "Mi función: compras — hablo con los proveedores todos los días. "
            "Me encargo de: pasar los pedidos de reposición, negociar bonificaciones, "
            "cargar las listas de precios nuevas que llegan por WhatsApp (dos o tres "
            "por semana) y avisar cuando un aumento nos rompe el margen. "
            "Todos los días miro: el stock de los que más rotan, los quiebres que "
            "avisa el depósito y las listas que mandaron los proveedores. "
            "Decido sobre: cuánto pedir de cada cosa dentro del presupuesto; los "
            "precios de venta los decide Aldo."
        ),
        "descripcion_en": (
            "My role: purchasing — I talk to the suppliers every single day. "
            "I take care of: placing the restock orders, negotiating discounts, loading the "
            "new price lists that come in over WhatsApp (two or three a week) and flagging "
            "it when an increase breaks our margin. "
            "Every day I look at: the stock of the fast movers, the shortages the warehouse "
            "reports and the lists the suppliers sent. "
            "I decide on: how much to order of each thing within budget; the selling prices "
            "are Aldo's call."
        ),
        "features": ["panel", "inventario", "saneamiento", "cargar", "documentos", "alertas",
                     "evolucion", "oportunidades", "equipo",
                     "oportunidades", "perfil", "angela"],
    },
    "ramon": {
        "username": "ramon", "nombre": "Ramón", "rol": "Encargado de depósito", "es_admin": False,
        "telefono": "+5493410000004", "color": "#3e7d63",
        "superficies": ["mobile", "desktop"],
        "descripcion": (
            "Mi función: encargado del depósito central — 9 años acá adentro. "
            "Me encargo de: la recepción de mercadería contra remito, el orden de los "
            "pasillos y las cámaras de frío, los lotes y vencimientos, y que los "
            "pedidos del reparto salgan armados a las 6 de la mañana. "
            "Todos los días miro: qué entra, qué sale, qué está por vencer y si el "
            "stock físico coincide con lo que dice el sistema. "
            "Decido sobre: la ubicación de la mercadería y el orden de armado; las "
            "devoluciones a proveedor las consulto con Celeste."
        ),
        "descripcion_en": (
            "My role: manager of the central warehouse — 9 years inside these walls. "
            "I take care of: receiving goods against the delivery note, keeping the aisles "
            "and the cold rooms in order, the lots and expiry dates, and making sure the "
            "delivery orders are picked and ready by six in the morning. "
            "Every day I look at: what comes in, what goes out, what's about to expire and "
            "whether the physical stock matches what the system says. "
            "I decide on: where the goods go and the picking order; returns to a supplier I "
            "check with Celeste."
        ),
        "features": ["panel", "deposito", "logistica", "inventario", "saneamiento", "cargar",
                     "alertas", "equipo", "perfil", "angela"],
    },
    "brian": {
        "username": "brian", "nombre": "Brian", "rol": "Depósito · armado de pedidos", "es_admin": False,
        "telefono": "+5493410000005", "color": "#6b6457",
        "superficies": ["mobile"],
        "descripcion": (
            "Mi función: armo los pedidos en el depósito. "
            "Me encargo de: juntar la mercadería de cada pedido con el picking que me "
            "pasa Ramón, armar los pallets por reparto y cargar los camiones. "
            "Todos los días miro: la lista de pedidos del día y de qué pasillo sale "
            "cada cosa. "
            "Decido sobre: el orden en que armo; si falta algo, le aviso a Ramón."
        ),
        "descripcion_en": (
            "My role: I pick the orders in the warehouse. "
            "I take care of: gathering the goods for each order from the picking list Ramón "
            "hands me, building the pallets by route and loading the trucks. "
            "Every day I look at: the day's order list and which aisle each thing comes from. "
            "I decide on: the order I pick in; if something's missing, I tell Ramón."
        ),
        "features": ["deposito", "logistica", "alertas", "perfil", "angela"],
    },
    "nahuel": {
        "username": "nahuel", "nombre": "Nahuel", "rol": "Depósito · recepción", "es_admin": False,
        "telefono": "+5493410000006", "color": "#0e5560",
        "superficies": ["mobile", "desktop"],
        "descripcion": (
            "Mi función: recibo la mercadería que llega de los proveedores. "
            "Me encargo de: controlar los remitos contra lo que baja del camión, "
            "cargar las entradas al sistema, etiquetar lotes y fechas de vencimiento. "
            "Todos los días miro: qué proveedores caen hoy y las diferencias entre lo "
            "pedido y lo recibido. "
            "Decido sobre: si acepto un bulto dañado o lo rechazo en el momento."
        ),
        "descripcion_en": (
            "My role: I receive the goods that come in from the suppliers. "
            "I take care of: checking the delivery notes against what comes off the truck, "
            "entering the incoming stock, labelling lots and expiry dates. "
            "Every day I look at: which suppliers are due today and the gaps between what "
            "was ordered and what actually arrived. "
            "I decide on: whether I accept a damaged pallet or turn it away on the spot."
        ),
        "features": ["deposito", "saneamiento", "cargar", "alertas", "perfil", "angela"],
    },
    "tomas": {
        "username": "tomas", "nombre": "Tomás", "rol": "Depósito · conteos", "es_admin": False,
        "telefono": "+5493410000007", "color": "#8a5a2b",
        "superficies": ["mobile"],
        "descripcion": (
            "Mi función: reposición y conteos en el depósito. "
            "Me encargo de: los conteos cíclicos (cada semana cuento una parte del "
            "depósito), reponer las puntas de góndola de Casa Central y avisar cuando "
            "el sistema dice una cosa y el estante dice otra. "
            "Todos los días miro: la hoja de conteo del día y los productos con stock "
            "negativo o raro. "
            "Decido sobre: nada solo — reporto las diferencias y Ramón define."
        ),
        "descripcion_en": (
            "My role: restocking and stock counts in the warehouse. "
            "I take care of: the cycle counts (every week I count a part of the warehouse), "
            "restocking the end caps at Casa Central and speaking up when the system says "
            "one thing and the shelf says another. "
            "Every day I look at: the day's count sheet and the products with negative or "
            "odd-looking stock. "
            "I decide on: nothing on my own — I report the gaps and Ramón calls it."
        ),
        # "inventario" es de LECTURA: habilita las preguntas del de a pie a Ángela
        # (cuánto stock de X, qué está en negativo). El último remito lo cubre
        # "cargar". No suma nada del dueño (finanzas/cuentas/equipo quedan fuera).
        "features": ["deposito", "inventario", "saneamiento", "cargar", "alertas", "perfil", "angela"],
    },
    "kevin": {
        "username": "kevin", "nombre": "Kevin", "rol": "Depósito · ayudante general",
        "es_admin": False,
        "telefono": "+5493410000014", "color": "#5c6f8a",
        "superficies": ["mobile"],
        # P·onboarding — EL EMPLEADO NUEVO. `ingreso` es un dato del perfil, no
        # una etiqueta cosmética: de ahí sale la antigüedad ("1 semana"), el chip
        # "Nuevo" de la lista del equipo y el apartado donde Ángela le enseña el
        # laburo. Con la fecha del demo congelada (POLPILOT_DEMO_TODAY=2026-07-07)
        # arrancó hace exactamente 7 días.
        "ingreso": "2026-06-30",
        # Más ficha que la mínima: dónde trabaja, en qué turno y a quién le
        # pregunta cuando no sabe. `mentor` es un username REAL del equipo.
        "puesto": {
            "sector": "Depósito central",
            "sector_en": "Central warehouse",
            "turno": "Mañana · 6 a 14",
            "turno_en": "Morning · 6 to 14",
            "mentor": "ramon",              # username: el NOMBRE propio no se traduce
            "contrato": "Efectivo · período de prueba",
            "contrato_en": "Permanent · probation period",
        },
        "descripcion": (
            "Mi función: entré hace una semana al depósito, como ayudante general. "
            "Me encargo de: lo que me pida Ramón — bajar la mercadería del camión, "
            "acomodarla en su lugar, ayudar en el armado de pedidos y avisar cuando "
            "algo no coincide. "
            "Todos los días miro: las tareas que me dejan y dónde va cada cosa, que "
            "todavía no me sé el depósito de memoria. "
            "Decido sobre: nada solo todavía — pregunto antes de mover algo."
        ),
        "descripcion_en": (
            "My role: I started a week ago in the warehouse, as a general hand. "
            "I take care of: whatever Ramón needs — getting the goods off the truck, putting "
            "them where they go, helping pick the orders and speaking up when something "
            "doesn't match. "
            "Every day I look at: the tasks they leave me and where each thing goes, because "
            "I don't know the warehouse by heart yet. "
            "I decide on: nothing on my own yet — I ask before I move anything."
        ),
        # MISMAS features que el resto del depósito de a pie (las de Tomás): el
        # onboarding es un PLUS, no un usuario capado ni uno con permisos de más.
        "features": ["deposito", "inventario", "saneamiento", "cargar", "alertas", "perfil", "angela"],
    },
    "walter": {
        "username": "walter", "nombre": "Walter", "rol": "Reparto · camión 1", "es_admin": False,
        "telefono": "+5493410000008", "color": "#b01910",
        "superficies": ["mobile"],
        "descripcion": (
            "Mi función: chofer del camión 1 — la zona centro y la costanera. "
            "Me encargo de: salir a las 7 con la hoja de ruta, entregar los pedidos, "
            "cobrar lo que está al contado y traer los remitos firmados. "
            "Todos los días miro: mi hoja de ruta, qué cliente rechaza mercadería y "
            "quién me dice 'pasá la semana que viene' con la plata. "
            "Decido sobre: el orden del recorrido; si un cliente no paga, aviso."
        ),
        "descripcion_en": (
            "My role: driver of truck 1 — downtown and the riverfront. "
            "I take care of: heading out at seven with the route sheet, delivering the "
            "orders, collecting what's cash on delivery and bringing back the signed notes. "
            "Every day I look at: my route sheet, which customer turns goods away and who "
            "tells me 'come back next week' about the money. "
            "I decide on: the order of the run; if a customer doesn't pay, I flag it."
        ),
        "features": ["logistica", "deposito", "alertas", "perfil", "angela"],
    },
    "osmar": {
        "username": "osmar", "nombre": "Osmar", "rol": "Reparto · camión 2", "es_admin": False,
        "telefono": "+5493410000009", "color": "#4a4238",
        "superficies": ["mobile"],
        "descripcion": (
            "Mi función: chofer del camión 2 — ruta 11 y los pueblos del norte. "
            "Me encargo de: las entregas de la zona norte (menos paradas, más "
            "kilómetros) y de los comedores y hoteles que piden en cantidad. "
            "Todos los días miro: la hoja de ruta y el estado de los caminos cuando "
            "llueve — si no entro, la entrega se reprograma. "
            "Decido sobre: reprogramar una entrega si el camino no da; aviso siempre."
        ),
        "descripcion_en": (
            "My role: driver of truck 2 — route 11 and the towns up north. "
            "I take care of: the deliveries out north (fewer stops, more miles) and the "
            "canteens and hotels that order in bulk. "
            "Every day I look at: the route sheet and the state of the roads when it rains — "
            "if I can't get through, the delivery gets rescheduled. "
            "I decide on: rescheduling a delivery when the road won't allow it; I always "
            "let people know."
        ),
        "features": ["logistica", "deposito", "alertas", "perfil", "angela"],
    },
    "diego": {
        "username": "diego", "nombre": "Diego", "rol": "Preventista · zona centro", "es_admin": False,
        "telefono": "+5493410000010", "color": "#7c3aed",
        "superficies": ["mobile"],
        "descripcion": (
            "Mi función: preventista — visito los comercios de la zona centro. "
            "Me encargo de: levantar los pedidos para el reparto del día siguiente, "
            "cobrar el fiado de los clientes chicos y avisar cuando un cliente viene "
            "flojo de pago antes de tomarle otro pedido grande. "
            "Todos los días miro: la cuenta corriente de cada cliente que visito y "
            "qué producto le falta en la góndola. "
            "Decido sobre: hasta cuánto le tomo de pedido a uno que debe; los "
            "límites de crédito los pone Aldo."
        ),
        "descripcion_en": (
            "My role: sales rep — I visit the shops downtown. "
            "I take care of: taking the orders for next day's delivery, collecting from the "
            "small accounts and flagging a customer who's getting shaky on payments before "
            "I take another big order from them. "
            "Every day I look at: the account of every customer I visit and what's missing "
            "from their shelves. "
            "I decide on: how much of an order I'll take from someone who owes; the credit "
            "limits are set by Aldo."
        ),
        "features": ["panel", "cobranzas", "cuentas", "documentos", "alertas", "perfil", "angela"],
    },
    "lucia": {
        "username": "lucia", "nombre": "Lucía", "rol": "Preventista · zona sur", "es_admin": False,
        "telefono": "+5493410000011", "color": "#be185d",
        "superficies": ["mobile"],
        "descripcion": (
            "Mi función: preventista de la zona sur — arranqué hace 8 meses. "
            "Me encargo de: abrir clientes nuevos (kioscos y despensas), levantar "
            "pedidos y cobrar el contado de mi cartera. "
            "Todos los días miro: qué clientes de mi ruta hace mucho no compran y "
            "qué ofertas puedo ofrecer para entrar. "
            "Decido sobre: a qué comercio nuevo le doy los primeros pedidos al "
            "contado; el crédito lo autoriza Aldo."
        ),
        "descripcion_en": (
            "My role: sales rep for the south side — I started 8 months ago. "
            "I take care of: opening new accounts (kiosks and corner shops), taking orders "
            "and collecting cash from my book. "
            "Every day I look at: which customers on my route haven't bought in a while and "
            "what deals I can offer to get in the door. "
            "I decide on: which new shop gets its first orders cash up front; the credit is "
            "authorised by Aldo."
        ),
        "features": ["panel", "cobranzas", "cuentas", "documentos", "alertas", "perfil", "angela"],
    },
    "norma": {
        "username": "norma", "nombre": "Norma", "rol": "Encargada · Sucursal Norte", "es_admin": False,
        "telefono": "+5493410000012", "color": "#0f766e",
        "superficies": ["desktop", "mobile"],
        "descripcion": (
            "Mi función: encargada de la Sucursal Norte. "
            "Me encargo de: abrir y cerrar la boca, la caja de la sucursal, pedir "
            "reposición al depósito central y manejar a los dos chicos del salón. "
            "Todos los días miro: la caja, qué faltó en góndola y qué me trajo el "
            "camión contra lo que pedí. "
            "Decido sobre: la reposición chica del día a día; los precios vienen de "
            "Casa Central."
        ),
        "descripcion_en": (
            "My role: manager of the North branch. "
            "I take care of: opening and closing the shop, the branch till, ordering "
            "restocks from the central warehouse and managing the two people on the floor. "
            "Every day I look at: the till, what ran out on the shelves and what the truck "
            "brought me against what I asked for. "
            "I decide on: the small day-to-day restocking; the prices come from head office."
        ),
        "features": ["panel", "caja", "inventario", "cuentas", "saneamiento", "alertas",
                     "equipo", "perfil", "angela"],
    },
    "vanesa": {
        "username": "vanesa", "nombre": "Vanesa", "rol": "Mostrador · Casa Central", "es_admin": False,
        "telefono": "+5493410000013", "color": "#a16207",
        "superficies": ["mobile", "desktop"],
        "descripcion": (
            "Mi función: mostrador de Casa Central — atiendo a los que compran acá. "
            "Me encargo de: la venta de mostrador, cobrar (efectivo, tarjeta, QR) y "
            "el arqueo de mi caja al final del turno. "
            "Todos los días miro: la caja del turno y los precios de balanza de "
            "fiambres y quesos, que son los que más preguntan. "
            "Decido sobre: nada de plata grande — las diferencias de caja las reporto."
        ),
        "descripcion_en": (
            "My role: front counter at Casa Central — I serve whoever buys here. "
            "I take care of: counter sales, taking payment (cash, card, QR) and cashing up "
            "my till at the end of the shift. "
            "Every day I look at: the shift's till and the scale prices for deli meats and "
            "cheeses, which are what people ask about most. "
            "I decide on: nothing involving big money — I report any till differences."
        ),
        # "inventario" de LECTURA: le permite responderle a un cliente en el
        # mostrador (¿tiene precio cargado?, ¿cuánto stock hay de X?, qué falta
        # precio) preguntándole a Ángela. No abre nada del dueño.
        "features": ["panel", "cobranzas", "cuentas", "caja", "inventario", "alertas", "perfil", "angela"],
    },
    "polpilot": {
        "username": "polpilot", "nombre": "Equipo PolPilot", "rol": "PolPilot", "es_admin": True,
        "interno": True, "color": "#1b8190", "superficies": ["desktop"],
        "descripcion": "Equipo PolPilot. Carga el contexto externo (economía, legal, precios) "
                       "que alimenta a Ángela hasta conectar las APIs.",
        "descripcion_en": "PolPilot team. Loads the external context (economy, legal, prices) "
                          "that feeds Ángela until the APIs are connected.",
        "features": ["admin_contexto", "angela", "perfil"],
    },
}
