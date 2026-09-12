# Los ejemplos

Todos verificados contra el dataset del tenant `demo`. Cada uno lleva el archivo
y la fila. **El "hoy" del demo está congelado en `2026-07-07`**
(`POLPILOT_DEMO_TODAY`, `start_demo.py:71`): todas las cuentas de días de este
documento salen de ahí.

Recordatorio de lo que declara el propio repo: el dataset es 100% ficticio,
generado con semilla fija por `data-demo/generar.py`. Es un mundo consistente,
no una empresa real.

---

# Parte 1 · Los tres que pediste

## Ejemplo 1 — El insumo de plazo largo

### El problema, primero

**El caso tal como está escrito no existe en el dataset.** El plazo de
reposición más largo de todo `proveedores_condiciones.json` es **21 días**
(Limpieza Total SA, "el más lento de todos: hay que pedirle con tres semanas de
anticipación"). No hay ningún proveedor de tres meses, no hay nada importado, y
el default es de 10 días.

Si se cuenta el ejemplo del insumo importado con tres meses de plazo, **hay que
agregar un proveedor al dataset**. Eso es legítimo —el dataset es sintético y
está para eso— pero hay que decidirlo a propósito, no descubrirlo en la sala.

### La buena noticia: la misma forma ya existe, con números reales

**El yogur bebible de Tierra Roja.** Los datos:

| Dato | Valor | Dónde |
|---|---|---|
| Producto | YOGUR BEBIBLE TIERRA ROJA 900G (X6U), código 1228 | `inventory.json` |
| Stock | 304 unidades · $2.010.890 inmovilizado | `inventory.json` |
| Lote | L-2026-309, Pasillo 1 · Rack A | `apartados.json` → `deposito` |
| **Vence** | **2026-07-14 — faltan 7 días** | ídem |
| Proveedor | Alimentos del Paraná SA | `inventory.json` |
| **Plazo de reposición** | **9 días** — "reparte por zona; el camión de esta zona pasa cada semana y media" | `proveedores_condiciones.json` |
| Señal de demanda | Vanesa, chat, **2026-07-02**: *"Tres clientes preguntaron por el yogur bebible de Tierra Roja esta semana. Les dije que había, pero el que quedaba tenía fecha corta."* | `notas_equipo.json` → `nt06` |

**La cadena de consecuencias, y es exacta:**

> El lote vence en 7 días. El proveedor tarda 9 en traer más. **El reemplazo
> llega después del quiebre, hagas lo que hagas — salvo que pidas hoy.** Y hay
> demanda: tres clientes preguntaron esta semana, y esa demanda no está en
> ningún sistema porque quien la escuchó fue Vanesa en el mostrador.

Eso **no es una predicción**. Es una resta entre dos fechas y un dato de
condiciones comerciales, más una nota de una persona. Se verifica en la sala en
diez segundos. Y tiene la ventaja sobre el insumo importado de que **está en los
datos de hoy**.

Si además se quiere el caso con plazo largo, la forma limpia es agregar un
proveedor de importación al `proveedores_condiciones.json` —tres meses, mínimo de
compra— y colgarle un producto. Es una fila de JSON, no una feature.

## Ejemplo 2 — La devolución de mercadería

**Estado: diseñado entero, construido nada.** El documento
`design/mobile/01-DEVOLUCIONES-Y-RECLAMOS.md` (rama `design/mobile-roles`) tiene
el flujo pantalla por pantalla, la cuenta de toques, y —lo más importante— el
relevamiento técnico de dónde vive.

### Lo que el diseño resolvió bien y hay que respetar

El conocimiento de qué exige cada proveedor **entra en `core/conocimiento.py` sin
forzar nada**, y el documento lo prueba: `params` ya es un dict libre que cada
motor lee con su propia clave, y eso ya está en producción en cinco lugares
(`cuentas.py:111` lee `tolerancia_dias`, `deposito.py:152` lee `umbral_pct`,
`conciliacion.py:73`, `carpeta.py:183`, `oportunidades_neg.py:391` lee
`evitar_dia`). La pieza sembrada `k09` es literalmente un `protocolo` de ámbito
`proveedor` con `params: {"umbral_suba_pct": 15}`.

> *«A Campo Alegre mandale siempre foto del lote» tiene la misma forma que «A
> Doña Elsa tolerale hasta 45 días».*

### Lo único que falta en el backend

**Un valor en el catálogo `EFECTOS`** de `conocimiento.py:47`. Hoy son cinco:
`ajusta_umbral`, `suprime_alerta`, `genera_alerta`, `contexto_para_angela`,
`requiere_aprobacion`. Ninguno describe "cambia lo que la app le pide a una
persona". El diseño propone `exige_evidencia`: **una línea en un `frozenset`.**
Verificado hoy contra `main`: sigue sin estar.

No hace falta tabla nueva, ni `tenant_tables.py`, ni endpoint de escritura:
`POST /api/conocimiento` y el flujo `crear` → `pendiente` → `aprobar` ya existen
y ya están auditados.

### El caso concreto que está en los datos

**Mortadela Santa Clara.** Dos personas, dos canales, el mismo lote:

- `wa04` · Osmar · **WhatsApp** · 2026-06-30: *"Las 3 cajas de fiambre vinieron
  falladas, las separé. No las cargué al camión."*
- `ft03` · Brian · **foto** · 2026-07-01: *"Foto de las cajas de mortadela
  falladas, para el reclamo al proveedor."*

Producto: MORTADELA SANTA CLARA (PLANCHA), código 1316, proveedor **Frigorífico
La Ribera**, 124,7 kg en **Cámara de frío 2**, lote L-2027-444.

**Brian ya sacó la foto "para el reclamo", y el reclamo no existe.** Ésa es la
frase del ejemplo, y está literalmente escrita en el dataset.

### Lo que sí está construido y sirve

- `core/voz.py` — la frase que colapsa pasos ("ocho cajas de manteca Santa Clara
  vinieron rotas, del lote L-2026-368") ya devuelve transcripción, candidatos de
  producto, `avisos[]` y `bloqueado[]`, y el número pasa por `core/validacion`.
- `core/piso.py` — el reporte de `faltante` ya existe, atribuido a la persona.
- `core/carpeta.py` — la procedencia `valor`/`fuente`/`estado` por campo, que es
  exactamente la forma que necesita "lo que pide este proveedor, ya completado
  hasta donde se pudo".
- `core/mis_avisos.py` — el círculo cerrado: destinatario, acuse, y el resultado
  que vuelve.

**Estimación honesta para tenerlo funcionando de punta a punta: una jornada
larga**, y sólo si se acepta el camino del diseño (una pieza de conocimiento, un
efecto nuevo, y reusar el flujo de aviso dirigido que ya cierra).

## Ejemplo 3 — El pasillo 4

**Construido y es el mejor que tenemos** — `deposito.explicaciones()`, probado en
`test_diferencia_explicada.py`.

| | |
|---|---|
| Lo que dice el ERP | faltan 6,5 unidades de leche · $53.646 |
| Ubicación | Pasillo 4 · Rack B |
| Nota 1 | `nt12` · **Kevin** · **voz** · 2026-07-06: *"Me mandaron a buscar leche al pasillo 4 y estaba en otro rack. Lo dejé donde decía el sistema para no romper nada."* |
| Nota 2 | `wa05` · **Nahuel** · **WhatsApp** · 2026-07-06: *"Corrí las cajas del pasillo 4 para hacer lugar. Quedó todo del lado de la pared, avisen antes de buscar algo ahí."* |

**El mismo día. Dos canales. Nadie los juntó.**

Una decisión de diseño del módulo que conviene saber defender: *"La nota NO
decide nada: es contexto para el que decide. Por eso viaja con la diferencia y no
la borra de la lista."* Si un jurado pregunta "¿y si las notas están mal?", la
respuesta ya está construida: el sistema no borra la diferencia, la explica.

### ⚠ El problema que hay que arreglar antes de mostrarlo

**Este caso no tiene camino en el grafo.** Ver `04-GRAFO...`, §2.5. Vive en
`deposito.explicaciones()` y `grafo.caminos()` no lo ve. **Media jornada** para
escribirlo como el séptimo cruce de `cruces.py`, que es donde pertenece.

---

# Parte 2 · Los que encontré en el dataset

Cinco. Todos con la misma forma: dos o tres fuentes que no se hablan, y una
consecuencia que ninguna tenía sola. Ordenados por qué tan buenos me parecen en
una sala.

## Nuevo 1 — ⭐ La oferta que hay que rechazar

**Por qué es el mejor: el sistema dice que no a una oportunidad que parece
buena.** Todos los demás equipos van a mostrar algo que encuentra oportunidades.
Nosotros mostramos una que las descarta con fundamento.

| Fuente | Qué dice | Dónde |
|---|---|---|
| **1. El proveedor** | Oferta `of-2026-071`: Frigorífico La Ribera, pallet completo de 25 planchas de SALAME MILAN LA RIBERA, **689 kg**, **18% de descuento**, la oferta **vence el 2026-07-17** | `proveedores_condiciones.json` → `ofertas` |
| **2. El depósito** | Ya hay **65,6 kg de SALAME MILAN MONTE CHICO** (cód. 1286), lote L-2026-522, **en Cámara de frío 2**, que **vence el 2026-07-18** — en 11 días. $945.431 inmovilizado | `apartados.json` → `deposito` + `inventory.json` |
| **3. La regla de la casa** | `k15`: *"Fiambres: nunca más de 15 días de stock, se vencen."* Aplicada 4 veces | `conocimiento_negocio.json` |
| **4. La voz del piso** | `nt08` Ramón (voz, 29/06) y `wa01` Ramón (WhatsApp, 02/07) y `ft02` Tomás (**foto**, 06/07): **la cámara de frío 2 no entra un pallet más** | `notas_equipo.json` |
| **5. El calendario del proveedor** | `em03` Celeste (email, 04/07): *"La Ribera confirmó la orden de fiambres para el 9. Pidieron que les avisemos si no hay lugar en cámara."* | ídem |

**La consecuencia que ninguna fuente tenía sola:**

> No compres el pallet con 18% de descuento. Tenés 65 kg del mismo tipo de
> fiambre venciendo en 11 días en la cámara donde iría, la regla de la casa dice
> que fiambres nunca más de 15 días de stock, la cámara está llena según tres
> personas por tres canales distintos, y el 9 llega otra orden de fiambres del
> mismo proveedor que ya pidió que le avisemos si no hay lugar.

**Cinco fuentes, cinco canales, cuatro personas, una regla de la casa.** El
descuento del 18% es real y el sistema igual dice que no. **Verificable fila por
fila.** Éste es el que yo pondría de segundo en el pitch, después del pasillo 4.

## Nuevo 2 — ⭐ La regla más aplicada de la casa, rota, y nadie se enteró

| Fuente | Qué dice | Dónde |
|---|---|---|
| **1. La regla** | `k11`: *"GASEOSA COLA LA RIBERA nunca puede quebrar: trae gente al local."* **`veces_aplicada: 9` — la más aplicada de las 22** | `conocimiento_negocio.json` |
| **2. La persona** | `nt13` · Norma · **chat** · 2026-06-28: *"En la Sucursal Norte la góndola de gaseosa cola quedó vacía el sábado a la tarde. Es el fin de semana que más se vende."* | `notas_equipo.json` |
| **3. Los traslados** | El último envío de gaseosa cola (cód. 1161) a **Sucursal Norte** fue el **2026-06-15**, 54 unidades. **No hubo otro.** Al 07/07: 22 días | `traslados_internos.json` (2.640 filas) |
| **4. El depósito central** | Hay **282 unidades**, Pasillo 2 · Rack B, vencen 2026-10-07. **No falta mercadería: falta que baje al local** | `apartados.json` → `deposito` |
| **5. El proveedor** | La Ribera repone en **3 días** pero *"exige el pedido en firme"* | `proveedores_condiciones.json` |

**La consecuencia:**

> La regla que más veces se aplicó en esta empresa dice que este producto nunca
> puede quebrar. Quebró, en la Sucursal Norte, el sábado que más se vende. El
> ERP no lo vio porque el ERP mira el depósito central, y ahí hay 282 unidades.
> La única persona que lo supo fue Norma, y lo dijo por chat.

**Por qué es fuerte:** es el caso donde **la regla aprendida y la realidad se
contradicen**, y el sistema lo nota. No es "el sistema aprende"; es "el sistema
usa lo que aprendió para detectar que se incumplió". Es el paso siguiente y casi
nadie lo tiene.

## Nuevo 3 — ⭐ El reclamo que cuatro personas están armando sin saberlo

Éste el documento interno ya lo tenía anotado (7.7). Lo confirmo y lo cierro con
las filas exactas.

**Un solo hecho — Lácteos Campo Alegre entregó la mitad — contado por cuatro
personas, por cuatro canales, en cinco días:**

| # | Quién | Canal | Fecha | Qué dijo |
|---|---|---|---|---|
| `nt16` | **Ramón** | voz | 02/07 | *"Campo Alegre entregó incompleto otra vez: faltaron dos pallets de yogur y los trajeron al otro día."* |
| `em02` | **Marta** | email | 03/07 | *"La factura de Campo Alegre vino por el total de la orden, pero entregaron la mitad. No la pago hasta que la corrijan."* |
| `wa02` | **Brian** | WhatsApp | 03/07 | *"Llegaron 40 cajas y la orden decía 80. El chofer dice que el resto viene la semana que viene."* |
| `ft01` | **Nahuel** | **foto** | 03/07 | *"Foto del remito de Campo Alegre: dice 40 bultos, no 80. Queda la constancia por si después discuten."* |

Y del otro lado, el dato estructurado que ninguno de los cuatro miró:

> **OC-2026-0847**, Lácteos Campo Alegre, **2026-07-02**, estado **abierta**,
> incluye 60 unidades del código 1215 (LECHE ENTERA CAMPO ALEGRE 1L).
> — `apartados.json` → `ordenes_compra`

**La consecuencia:**

> Hay un reclamo armado entre cuatro personas que no saben que lo están armando.
> Ramón tiene el antecedente ("otra vez"), Brian tiene la cantidad, Nahuel tiene
> la evidencia, Marta tiene la palanca (la factura sin pagar), y el sistema tiene
> la orden abierta. **Ninguno de los cinco pedazos alcanza solo. Los cinco
> juntos son un reclamo con foto, número y plata retenida.**

**Y hay una contradicción de verdad adentro**, que es lo que lo hace mejor que
una simple agregación: Ramón dice *"los trajeron al otro día"*; Brian dice *"el
resto viene la semana que viene"*. **No coinciden.** El sistema tiene que
marcarlo, no elegir una versión. Ésa es la idea 7.7 del documento, y acá está el
dato para construirla.

## Nuevo 4 — El producto que se vence en el depósito es el que piden en el mostrador

| Fuente | Qué dice | Dónde |
|---|---|---|
| **1. Depósito** | `nt10` · Brian · **reporte** · 04/07: *"El salame de Monte Chico que está en la cámara tiene fecha para este mes y todavía hay un montón. Nadie lo pidió esta semana."* | `notas_equipo.json` |
| **2. Mostrador** | `wa07` · Vanesa · **WhatsApp** · 01/07: *"Me preguntaron dos veces por el salame Monte Chico en el mostrador."* Y `nt14` · Vanesa · **chat** · 05/07: *"Si me dejan bajarle el precio lo saco en dos días; la gente lo pide feteado."* | ídem |
| **3. El dato duro** | 65,6 kg, lote L-2026-522, **vence 2026-07-18** (11 días), $945.431 inmovilizado, pvp $18.123,85, costo $11.910,79 | `inventory.json` + `apartados.json` |
| **4. La regla de la casa** | `k16`: *"Los precios de fiambres los revisa Vanesa antes de aplicarlos."* | `conocimiento_negocio.json` |

**La consecuencia, y tiene un remate:**

> El depósito dice que no se mueve. El mostrador dice que lo piden. Son la misma
> semana y los dos tienen razón: se pide feteado y está en plancha. La palanca
> existe —bajar el precio— y hay margen para hacerlo. **Y la regla de la casa
> dice que ese precio lo revisa Vanesa… que es justo la que lo está pidiendo.**

Ese último giro es lo que lo hace memorable: el sistema no sólo cruza el dato,
sabe **quién tiene que aprobar** y resulta que es la misma persona que levantó la
señal. Eso no está en ningún ERP.

## Nuevo 5 — La cuenta morosa que el sistema defiende

**Por qué vale: el sistema contradice a su propio reporte de morosos.**

| Fuente | Qué dice | Dónde |
|---|---|---|
| **1. La cuenta corriente** | Despensa Doña Elsa figura en mora | `cuentas.json` |
| **2. La regla de la casa** | `k01`: *"A Despensa Doña Elsa tolerale hasta 45 días — es cliente desde 2011 y nunca me falló."* `efecto: ajusta_umbral`, `params: {tolerancia_dias: 45, desde_anio: 2011}`, **`veces_aplicada: 7`**, `efecto_profundo: true` | `conocimiento_negocio.json` |
| **3. Lo que vio el repartidor** | `wa06` · Walter · **WhatsApp** · 05/07: *"Pasé por lo de Doña Elsa. Está abierta y trabajando bien, me dijo que la semana que viene se pone al día."* | `notas_equipo.json` |
| **4. Lo que pidió la oficina** | `nt07` · Lucía · **chat** · 26/06: *"Doña Elsa me pidió si le podemos hacer una entrega chica sin factura nueva, para no seguir sumando a la cuenta hasta que cobre."* | ídem |
| **5. El protocolo** | `k03`: *"Si un moroso pasa los 60 días, prepará la intimación pero NO la mandes sin mi OK."* | `conocimiento_negocio.json` |

**La consecuencia:**

> El listado de morosos dice que la intimes. La regla de la casa dice 45 días
> porque es cliente desde 2011. El repartidor la vio abierta y trabajando el
> viernes pasado. Y ella misma pidió una entrega chica para no seguir sumando —
> que es lo que hace alguien que piensa pagar, no alguien que se va. **El sistema
> no te dice que la intimes: te dice que no la intimes todavía, y te dice por
> qué, con nombre y fecha.**

Esto contrasta directo con el argumento de Lightfield sobre el registro que se
llena solo: acá el dato que cambia la decisión **no existe en ningún canal
digital.** Lo vio un tipo manejando una camioneta.

---

# Parte 3 · Cuál usaría, y en qué orden

| Momento | Ejemplo | Por qué |
|---|---|---|
| **El aha (0:40–1:40)** | **Pasillo 4** | Quince segundos, dos canales, el mismo día. Ya construido. **Requiere el cruce nuevo para tener camino en el grafo.** |
| **La profundidad (1:40–2:20)** | **La oferta que hay que rechazar** | Cinco fuentes. El sistema dice que no a un 18% de descuento y se lo puede probar. Es donde el jurado ve que hay motor |
| **El golpe humano (2:50–3:30)** | **Doña Elsa**, o el reclamo de Campo Alegre | El primero si el jurado es de negocio; el segundo si es técnico |
| **De reserva, si preguntan** | Yogur Tierra Roja (cadena de consecuencias), Gaseosa Cola (regla rota), Salame Monte Chico (depósito vs mostrador) | Cada uno se cuenta en veinte segundos y todos se verifican |

**Los cinco nuevos usan fuentes distintas entre sí**, lo que sirve para una cosa
concreta: si un jurado pregunta "¿esto es un caso armado?", se pueden mostrar
cinco casos con cinco formas distintas, sobre el mismo dataset, sin repetir el
truco.
