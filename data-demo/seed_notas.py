"""
Siembra de las NOTAS DEL EQUIPO — lo que la gente sabe y nunca entra a un ERP.

QUÉ ES ESTO, SIN VUELTAS: son las notas e interacciones del equipo — lo que
dictan por voz desde el piso (`core/voz.py`), lo que cargan en un reporte de
faltante o conteo (`mobile/ReporteForm.jsx`), lo que le comentan a Ángela en el
chat, y —desde el mapa de la operación— lo que entra POR AFUERA: el grupo de
WhatsApp del depósito, el mail de los proveedores y la foto del remito.

SOBRE LOS TRES CANALES DE AFUERA, PARA QUE NO SE MALINTERPRETEN: son el ORIGEN
de la información, no una integración viva. NO hay un WhatsApp Business
conectado ni una casilla siendo leída (ese canal existe aparte y se configura
por tenant, ver core/whatsapp_channel.py). Estas notas son sintéticas como el
resto del dataset, y describen lo que en un cliente real alguien reenvía o
transcribe. Son la mitad de la información de una PyME y el mapa las muestra
como lo que son: lo que el ERP no captura.

Como el resto del demo, el contenido es SINTÉTICO: personas, clientes y
situaciones inventadas para "Distribuidora del Litoral", coherentes con el mismo
dataset (los 24 clientes reales del archivo, los productos del catálogo, las
ubicaciones del depósito, los empleados del seed) y con fechas ≤ 2026-07-07.

POR QUÉ IMPORTA: es la única fuente del dataset que NO es estructurada. Un ERP
sabe que un cliente debe $42M; no sabe que el repartidor pasó dos veces y estaba
cerrado. Cruzar las dos cosas es lo que separa un chatbot sobre un ERP de algo
que entiende el negocio (ver core/cruces.py, que las usa).

Idempotente y determinista (ids fijos nt01…nt17, wa01…wa07, em01…em04,
ft01…ft03): si el archivo existe, no se
toca — start_demo compara byte a byte contra el snapshot commiteado.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(HERE, "notas_equipo.json")

# Por dónde entró la nota. Tres son superficies del producto y tres son de
# AFUERA — y esa división es justamente lo que el mapa de la operación muestra
# en su banda "Lo que entra desde afuera" (core/mapa_operacion.DE_AFUERA):
#   voz      — el botón de hablar de "Mi día" / Depósito (core/voz.py)
#   reporte  — el formulario de faltante / conteo / entrega del piso
#   chat     — lo que le escribieron a Ángela
#   whatsapp — el grupo del depósito: lo que alguien tira mientras trabaja
#   email    — lo que mandan los proveedores, que vive en una casilla
#   foto     — el remito sacado con el celular al recibir
CANALES = ("voz", "reporte", "chat", "whatsapp", "email", "foto")

# id, autor (username del seed), fecha, canal, tipo, texto/texto_en y las
# entidades que la nota menciona (nombres tal cual el dataset, para que el
# cruce las resuelva sin adivinar).
NOTAS = [
    # --- lo que ve el que entrega -------------------------------------------
    {"id": "nt01", "autor": "walter", "fecha": "2026-06-24", "canal": "voz",
     "tipo": "observacion_campo", "cliente": "Almacén San Martín",
     "texto": "Pasé por el Almacén San Martín y estaba cerrado, persiana baja. "
              "Es la segunda vez esta semana; los vecinos me dijeron que abre salteado.",
     "texto_en": "I stopped at Almacén San Martín and it was shut, blinds down. "
                 "Second time this week; the neighbours told me he opens on and off."},
    {"id": "nt02", "autor": "walter", "fecha": "2026-07-01", "canal": "voz",
     "tipo": "observacion_campo", "cliente": "Almacén San Martín",
     "texto": "Otra vez cerrado San Martín. Me llevé el pedido de vuelta al depósito.",
     "texto_en": "San Martín closed again. I brought the order back to the warehouse."},
    {"id": "nt03", "autor": "osmar", "fecha": "2026-06-27", "canal": "reporte",
     "tipo": "incidencia_entrega", "cliente": "Rotisería Avenida",
     "texto": "En Rotisería Avenida me rechazaron dos cajas: llegaron golpeadas del viaje. "
              "El dueño estaba caliente, dijo que es la segunda vez en el mes.",
     "texto_en": "Rotisería Avenida turned down two boxes: they arrived dented. "
                 "The owner was angry, said it's the second time this month."},
    {"id": "nt17", "autor": "osmar", "fecha": "2026-07-04", "canal": "reporte",
     "tipo": "incidencia_entrega", "cliente": "Supermercado El Puente",
     "texto": "En El Puente el encargado me hizo esperar dos horas para recibir y me marcó "
              "que la mitad de las cajas venían mal apiladas. Pidió hablar con alguien.",
     "texto_en": "At El Puente the manager kept me waiting two hours to unload and pointed out "
                 "half the boxes were badly stacked. He asked to speak to someone."},
    {"id": "nt04", "autor": "walter", "fecha": "2026-07-03", "canal": "voz",
     "tipo": "observacion_campo", "cliente": "Autoservicio 9 de Julio",
     "texto": "El de 9 de Julio me pidió que no le lleve más hasta que hable con Aldo. "
              "Dice que está complicado este mes.",
     "texto_en": "The 9 de Julio guy asked me not to deliver again until he talks to Aldo. "
                 "Says this month is tight for him."},

    # --- lo que ve el que atiende --------------------------------------------
    {"id": "nt05", "autor": "diego", "fecha": "2026-06-30", "canal": "chat",
     "tipo": "queja_cliente", "cliente": "Proveeduría La Rural",
     "texto": "La Rural me dijo que está comprando gaseosa en otro lado porque se la dejan "
              "más barata. Me pidió precio por cantidad.",
     "texto_en": "La Rural told me they're buying soda elsewhere because someone quotes them "
                 "cheaper. They asked me for a volume price."},
    {"id": "nt06", "autor": "vanesa", "fecha": "2026-07-02", "canal": "chat",
     "tipo": "queja_cliente", "producto": "YOGUR BEBIBLE TIERRA ROJA 900G (X6U)",
     "texto": "Tres clientes preguntaron por el yogur bebible de Tierra Roja esta semana. "
              "Les dije que había, pero el que quedaba tenía fecha corta.",
     "texto_en": "Three customers asked for the Tierra Roja drinkable yogurt this week. "
                 "I said we had it, but what's left is close to its date."},
    {"id": "nt07", "autor": "lucia", "fecha": "2026-06-26", "canal": "chat",
     "tipo": "pedido_cliente", "cliente": "Despensa Doña Elsa",
     "texto": "Doña Elsa me pidió si le podemos hacer una entrega chica sin factura nueva, "
              "para no seguir sumando a la cuenta hasta que cobre.",
     "texto_en": "Doña Elsa asked whether we can do a small delivery without a new invoice, "
                 "so her account stops growing until she gets paid."},

    # --- lo que ve el que está en el galpón ----------------------------------
    {"id": "nt08", "autor": "ramon", "fecha": "2026-06-29", "canal": "voz",
     "tipo": "estado_deposito", "ubicacion": "Cámara de frío 2",
     "texto": "No entra más nada en la cámara de frío 2. Si llega el pedido grande de "
              "fiambres no sé dónde lo pongo.",
     "texto_en": "Nothing else fits in cold room 2. If the big cold-cuts order lands "
                 "I don't know where to put it."},
    {"id": "nt09", "autor": "nahuel", "fecha": "2026-07-01", "canal": "voz",
     "tipo": "estado_deposito", "ubicacion": "Cámara de frío 2",
     "texto": "Estamos apilando cajas en el pasillo porque la cámara 2 está llena.",
     "texto_en": "We're stacking boxes in the aisle because cold room 2 is full."},
    {"id": "nt10", "autor": "brian", "fecha": "2026-07-04", "canal": "reporte",
     "tipo": "estado_deposito", "producto": "SALAME MILAN MONTE CHICO (PLANCHA)",
     "texto": "El salame de Monte Chico que está en la cámara tiene fecha para este mes y "
              "todavía hay un montón. Nadie lo pidió esta semana.",
     "texto_en": "The Monte Chico salami in the cold room is dated for this month and there's "
                 "still a lot of it. Nobody ordered any this week."},
    {"id": "nt11", "autor": "tomas", "fecha": "2026-06-25", "canal": "reporte",
     "tipo": "estado_deposito", "producto": "JAMON COCIDO EL PARANA (HORMA)",
     "texto": "Conté el jamón cocido de El Paraná y hay más de lo que dice el sistema. "
              "Igual la fecha está justa.",
     "texto_en": "I counted the El Paraná cooked ham and there's more than the system says. "
                 "The date is tight anyway."},
    {"id": "nt12", "autor": "kevin", "fecha": "2026-07-06", "canal": "voz",
     "tipo": "estado_deposito", "ubicacion": "Pasillo 4 - Rack B",
     "texto": "Me mandaron a buscar leche al pasillo 4 y estaba en otro rack. Lo dejé donde "
              "decía el sistema para no romper nada.",
     "texto_en": "They sent me to fetch milk from aisle 4 and it was on another rack. I left it "
                 "where the system said so nothing breaks."},

    # --- lo que ve la que maneja una boca ------------------------------------
    {"id": "nt13", "autor": "norma", "fecha": "2026-06-28", "canal": "chat",
     "tipo": "estado_local", "producto": "GASEOSA COLA LA RIBERA 2.25L (X6U)",
     "texto": "En la Sucursal Norte la góndola de gaseosa cola quedó vacía el sábado a la "
              "tarde. Es el fin de semana que más se vende.",
     "texto_en": "At the North branch the cola shelf was empty on Saturday afternoon. That's "
                 "the weekend when it sells the most."},
    {"id": "nt14", "autor": "vanesa", "fecha": "2026-07-05", "canal": "chat",
     "tipo": "estado_local", "producto": "SALAME MILAN MONTE CHICO (PLANCHA)",
     "texto": "Si me dejan bajarle el precio al salame de Monte Chico lo saco en dos días en "
              "el mostrador; la gente lo pide feteado.",
     "texto_en": "If you let me drop the price on the Monte Chico salami I'll clear it in two "
                 "days at the counter; people ask for it sliced."},

    # --- lo que se cuenta del proveedor ---------------------------------------
    {"id": "nt15", "autor": "celeste", "fecha": "2026-06-23", "canal": "chat",
     "tipo": "nota_proveedor", "proveedor": "Frigorífico La Ribera",
     "texto": "La Ribera me avisó que en agosto le cambian el reparto de esta zona. No me "
              "confirmaron si mantienen los 3 días de entrega.",
     "texto_en": "La Ribera warned me they're changing this area's route in August. They didn't "
                 "confirm whether the 3-day delivery holds."},
    {"id": "nt16", "autor": "ramon", "fecha": "2026-07-02", "canal": "voz",
     "tipo": "nota_proveedor", "proveedor": "Lácteos Campo Alegre",
     "texto": "Campo Alegre entregó incompleto otra vez: faltaron dos pallets de yogur y los "
              "trajeron al otro día.",
     "texto_en": "Campo Alegre delivered short again: two pallets of yogurt were missing and "
                 "they brought them the next day."},

    # --- WhatsApp · el grupo del depósito ------------------------------------
    # Lo que alguien tira mientras trabaja, con guantes puestos, sin entrar a
    # ningún sistema. Es el canal del pitch: no es que al ERP le falte el campo,
    # es que nadie se lo va a llenar.
    {"id": "wa01", "autor": "ramon", "fecha": "2026-07-02", "canal": "whatsapp",
     "tipo": "estado_deposito", "ubicacion": "Cámara de frío 2",
     "texto": "Muchachos, no entra más nada en la cámara 2. Si llega algo hoy "
              "lo dejo en el pasillo y después vemos.",
     "texto_en": "Guys, nothing else fits in cold room 2. If anything arrives "
                 "today I'll leave it in the aisle and we'll sort it out later."},
    {"id": "wa02", "autor": "brian", "fecha": "2026-07-03", "canal": "whatsapp",
     "tipo": "incidencia_entrega", "proveedor": "Lácteos Campo Alegre",
     "texto": "Llegaron 40 cajas y la orden decía 80. El chofer dice que el "
              "resto viene la semana que viene.",
     "texto_en": "40 boxes arrived and the order said 80. The driver says the "
                 "rest is coming next week."},
    {"id": "wa03", "autor": "ramon", "fecha": "2026-07-04", "canal": "whatsapp",
     "tipo": "nota_proveedor", "proveedor": "Frigorífico La Ribera",
     "texto": "El camión de La Ribera llega mañana temprano. ¿Dónde lo bajamos "
              "si la cámara 2 está llena?",
     "texto_en": "The La Ribera truck arrives early tomorrow. Where do we "
                 "unload it if cold room 2 is full?"},
    {"id": "wa04", "autor": "osmar", "fecha": "2026-06-30", "canal": "whatsapp",
     "tipo": "incidencia_entrega", "producto": "MORTADELA SANTA CLARA (PLANCHA)",
     "texto": "Las 3 cajas de fiambre vinieron falladas, las separé. No las "
              "cargué al camión.",
     "texto_en": "The 3 boxes of cold cuts came damaged, I set them aside. I "
                 "didn't load them onto the truck."},
    {"id": "wa05", "autor": "nahuel", "fecha": "2026-07-06", "canal": "whatsapp",
     "tipo": "estado_deposito", "ubicacion": "Pasillo 4 - Rack B",
     "texto": "Corrí las cajas del pasillo 4 para hacer lugar. Quedó todo del "
              "lado de la pared, avisen antes de buscar algo ahí.",
     "texto_en": "I moved the boxes in aisle 4 to make room. Everything's "
                 "against the wall now — give me a heads-up before looking there."},
    {"id": "wa06", "autor": "walter", "fecha": "2026-07-05", "canal": "whatsapp",
     "tipo": "observacion_campo", "cliente": "Despensa Doña Elsa",
     "texto": "Pasé por lo de Doña Elsa. Está abierta y trabajando bien, me "
              "dijo que la semana que viene se pone al día.",
     "texto_en": "I stopped by Doña Elsa's. She's open and doing fine, she told "
                 "me she'll settle up next week."},
    {"id": "wa07", "autor": "vanesa", "fecha": "2026-07-01", "canal": "whatsapp",
     "tipo": "pedido_cliente", "producto": "SALAME MILAN MONTE CHICO (PLANCHA)",
     "texto": "Me preguntaron dos veces por el salame Monte Chico en el "
              "mostrador. Si hay que sacarlo pronto, avisen y lo empujo.",
     "texto_en": "I was asked twice about the Monte Chico salami at the "
                 "counter. If it needs to move soon, tell me and I'll push it."},

    # --- Mail · lo que mandan los proveedores --------------------------------
    # Estructurado por fuera, muerto por dentro: vive en una casilla y no toca
    # el sistema hasta que alguien lo tipea a mano.
    {"id": "em01", "autor": "celeste", "fecha": "2026-07-02", "canal": "email",
     "tipo": "nota_proveedor", "proveedor": "Distrib. Mayorista Guaraní",
     "texto": "Guaraní mandó lista de precios nueva, rige desde el 15. Suben "
              "gaseosas y galletitas; el resto queda igual.",
     "texto_en": "Guaraní sent a new price list, effective from the 15th. Soft "
                 "drinks and biscuits go up; the rest stays the same."},
    {"id": "em02", "autor": "marta", "fecha": "2026-07-03", "canal": "email",
     "tipo": "nota_proveedor", "proveedor": "Lácteos Campo Alegre",
     "texto": "La factura de Campo Alegre vino por el total de la orden, pero "
              "entregaron la mitad. No la pago hasta que la corrijan.",
     "texto_en": "The Campo Alegre invoice came for the full order, but they "
                 "delivered half. I'm not paying it until they fix it."},
    {"id": "em03", "autor": "celeste", "fecha": "2026-07-04", "canal": "email",
     "tipo": "nota_proveedor", "proveedor": "Frigorífico La Ribera",
     "texto": "La Ribera confirmó la orden de fiambres para el 9. Pidieron que "
              "les avisemos si no hay lugar en cámara.",
     "texto_en": "La Ribera confirmed the cold-cuts order for the 9th. They "
                 "asked us to let them know if there's no room in the cold store."},
    {"id": "em04", "autor": "celeste", "fecha": "2026-06-29", "canal": "email",
     "tipo": "nota_proveedor", "proveedor": "Golosinas Costa Dulce SRL",
     "texto": "Costa Dulce avisa que el reparto de la próxima semana se corre "
              "un día por feriado.",
     "texto_en": "Costa Dulce says next week's delivery moves one day because "
                 "of the holiday."},

    # --- Foto · el remito sacado con el celular al recibir -------------------
    {"id": "ft01", "autor": "nahuel", "fecha": "2026-07-03", "canal": "foto",
     "tipo": "incidencia_entrega", "proveedor": "Lácteos Campo Alegre",
     "texto": "Foto del remito de Campo Alegre: dice 40 bultos, no 80. Queda "
              "la constancia por si después discuten.",
     "texto_en": "Photo of the Campo Alegre delivery note: it says 40 units, "
                 "not 80. Keeping the proof in case they argue later."},
    {"id": "ft02", "autor": "tomas", "fecha": "2026-07-06", "canal": "foto",
     "tipo": "estado_deposito", "ubicacion": "Cámara de frío 2",
     "texto": "Foto de cómo quedó la cámara 2 después de acomodar. No entra un "
              "pallet más.",
     "texto_en": "Photo of how cold room 2 ended up after reorganising. Not one "
                 "more pallet fits."},
    {"id": "ft03", "autor": "brian", "fecha": "2026-07-01", "canal": "foto",
     "tipo": "incidencia_entrega", "producto": "MORTADELA SANTA CLARA (PLANCHA)",
     "texto": "Foto de las cajas de mortadela falladas, para el reclamo al "
              "proveedor.",
     "texto_en": "Photo of the damaged mortadella boxes, for the supplier claim."},
]


def sembrar() -> bool:
    """Crea notas_equipo.json si falta. True si lo creó, False si ya existía."""
    if os.path.exists(DESTINO):
        return False
    notas = []
    for n in NOTAS:
        notas.append({
            "id": n["id"], "autor": n["autor"], "fecha": n["fecha"],
            "canal": n["canal"], "tipo": n["tipo"],
            "texto": n["texto"], "texto_en": n["texto_en"],
            # las entidades que la nota nombra (None si no aplica)
            "cliente": n.get("cliente"), "producto": n.get("producto"),
            "proveedor": n.get("proveedor"), "ubicacion": n.get("ubicacion"),
        })
    with open(DESTINO, "w", encoding="utf-8") as f:
        json.dump({
            "_nota": "Notas e interacciones del equipo — la capa NO estructurada del dataset "
                     "demo. Seis canales: WhatsApp, mail y foto del remito entran DE AFUERA "
                     "(ahí vive la mitad de la información de una PyME); voz, chat y reporte "
                     "son superficies del producto. Sintéticas como todo el resto del demo: "
                     "describen el ORIGEN de la información, no una integración conectada.",
            "canales": list(CANALES),
            "notas": notas,
        }, f, ensure_ascii=False, indent=2)
    return True


if __name__ == "__main__":
    creado = sembrar()
    print(f"notas: {'sembradas (%d)' % len(NOTAS) if creado else 'ya existían'}")
