"""
Siembra de las NOTAS DEL EQUIPO — lo que la gente sabe y nunca entra a un ERP.

QUÉ ES ESTO, SIN VUELTAS: son las notas e interacciones que los empleados YA le
dejan a Ángela dentro de PolPilot — lo que dictan por voz desde el piso
(`core/voz.py`), lo que cargan en un reporte de faltante o conteo
(`mobile/ReporteForm.jsx`) y lo que le comentan en el chat. Es data del producto,
no un canal externo: NO hay ningún WhatsApp conectado, y en pantalla se dice así
("lo que el equipo le contó a Ángela").

Como el resto del demo, el contenido es SINTÉTICO: personas, clientes y
situaciones inventadas para "Distribuidora del Litoral", coherentes con el mismo
dataset (los 24 clientes reales del archivo, los productos del catálogo, las
ubicaciones del depósito, los empleados del seed) y con fechas ≤ 2026-07-07.

POR QUÉ IMPORTA: es la única fuente del dataset que NO es estructurada. Un ERP
sabe que un cliente debe $42M; no sabe que el repartidor pasó dos veces y estaba
cerrado. Cruzar las dos cosas es lo que separa un chatbot sobre un ERP de algo
que entiende el negocio (ver core/cruces.py, que las usa).

Idempotente y determinista (ids fijos nt01…nt16): si el archivo existe, no se
toca — start_demo compara byte a byte contra el snapshot commiteado.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(HERE, "notas_equipo.json")

# Por dónde entró la nota. Los tres son superficies REALES del producto:
#   voz     — el botón de hablar de "Mi día" / Depósito (core/voz.py)
#   reporte — el formulario de faltante / conteo / entrega del piso
#   chat    — lo que le escribieron a Ángela
CANALES = ("voz", "reporte", "chat")

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
            "_nota": "Notas e interacciones del equipo con Ángela (voz, reportes del piso y "
                     "chat) — la capa NO estructurada del dataset demo. Sintéticas, como todo "
                     "el resto del demo. NO son un canal externo: no hay WhatsApp conectado.",
            "canales": list(CANALES),
            "notas": notas,
        }, f, ensure_ascii=False, indent=2)
    return True


if __name__ == "__main__":
    creado = sembrar()
    print(f"notas: {'sembradas (%d)' % len(NOTAS) if creado else 'ya existían'}")
