# El grafo y el mapa, medidos en la demo en vivo

Extraído de `https://polpilot-demo.onrender.com` el 11 de septiembre de 2026,
entrando como `aldo`, leyendo `/api/grafo` y `/api/mapa-operacion` desde la
consola y usando las dos pantallas como las usaría un jurado.

**Ese deploy es `main` de `agustindelmonti/polpilot-app`** — no tiene nada de lo
que construí (modo proyectar, animación, contrafáctico, punto ciego, cruce de la
oferta). Es la línea de base, que es justo lo que hacía falta medir.

---

# 1 · La estructura de datos del grafo

**567 nodos · 1.889 aristas.**

## Nodos por tipo

| Tipo | Cantidad | % |
|---|---|---|
| **producto** | **427** | **75,3%** |
| remito | 37 | 6,5% |
| **nota** | **31** | **5,5%** |
| cliente | 24 | 4,2% |
| cuenta | 23 | 4,1% |
| rubro | 8 | 1,4% |
| conocimiento | 8 | 1,4% |
| proveedor | 6 | 1,1% |
| local | 3 | 0,5% |

## Aristas por relación

| Relación | Cantidad | % | Qué une |
|---|---|---|---|
| **coventa** | **615** | **32,6%** | producto ↔ producto (lift ≥ 1,15) |
| **pertenece** | **427** | **22,6%** | producto → rubro |
| **provee** | **427** | **22,6%** | proveedor → producto |
| compra | 144 | 7,6% | cliente → producto |
| vende | 120 | 6,4% | local → producto |
| traslado | 49 | 2,6% | local → producto |
| entrega | 33 | 1,7% | remito → cliente |
| **menciona** | **25** | **1,3%** | **nota → entidad** |
| debe | 23 | 1,2% | cliente → cuenta |
| pide | 14 | 0,7% | orden → producto |
| aplica_a | 8 | 0,4% | conocimiento → entidad |
| ordena | 4 | 0,2% | proveedor → orden |

### El número que resume todo

**`coventa` + `pertenece` + `provee` = 1.469 aristas = el 77,8% del grafo.**
Las tres son relaciones estructurales masivas de producto que no explican
ningún hallazgo.

**`menciona` —la relación que ES nuestra tesis— es el 1,3%.**

---

# 2 · Lo no estructurado está desconectado

## Seis notas tienen grado 0

De las 31 notas, **6 no tienen una sola arista**. Y son exactamente las de los
dos casos que queremos contar:

| Nota | Autor | Canal | Qué dice | Grado |
|---|---|---|---|---|
| `nt12` | kevin | voz | "me mandaron a buscar leche al pasillo 4 y estaba en otro rack" | **0** |
| `wa05` | nahuel | whatsapp | "corrí las cajas del pasillo 4 para hacer lugar" | **0** |
| `nt08` | ramon | voz | "no entra más nada en la cámara de frío 2" | **0** |
| `wa01` | ramon | whatsapp | "no entra más nada en la cámara 2" | **0** |
| `nt09` | nahuel | voz | "estamos apilando cajas en el pasillo" | **0** |
| `ft02` | tomas | **foto** | "foto de cómo quedó la cámara 2" | **0** |

**La causa es estructural:** esas notas hablan de una **ubicación** (Pasillo 4,
Cámara de frío 2) y **el grafo no tiene nodos de ubicación**. `grafo.construir`
sólo resuelve `cliente`, `producto` y `proveedor`. Una nota sobre un lugar no
tiene con qué conectarse.

Las otras 25 notas tienen **grado 1**: una sola arista cada una. Ninguna nota del
grafo tiene más de una conexión.

## El camino del hallazgo estrella no toca ninguna nota

`cruce_espacio_camara` — "No entra más nada en Cámara de frío 2 y viene un
pedido":

| | |
|---|---|
| Nodos del camino | **41** |
| Semillas | 9 (4 notas + 4 productos + 1 proveedor) |
| Traídos por expansión | **32** — de los cuales **26 son productos** |
| Aristas del camino | **54** |
| **Aristas que tocan una nota** | **0** |

Las 54 aristas se reparten así: 19 `provee`, 17 `coventa`, 7 `compra`,
5 `pertenece`, 5 `pide`, 1 `ordena`.

**El camino que prueba que lo no estructurado cruzó está compuesto enteramente
por relaciones producto-proveedor.** Las cuatro notas están adentro del conjunto
de nodos, pero flotando, sin una línea.

## El producto lo confiesa en pantalla

Al tocar la nota de Ramón, el panel lateral dice, textual:

> **CRUCES CON EL RESTO: 0**
> **Sus relaciones (0) — Sin relaciones registradas todavía**

Si un jurado toca esa nota durante la demo, lee que la evidencia humana del
hallazgo no está conectada a nada.

---

# 3 · Fricciones de uso, una por una

Lo que hice y lo que pasó.

### F1 · El lienzo arranca debajo del fold

**Qué hice:** encendí el camino de la cámara.
**Qué pasó:** el panel de texto creció y empujó el lienzo hacia abajo. Medido:
viewport 1920×912, el canvas empieza en **y = 713**. Quedan **199 px de grafo
visibles** de 515 que mide. Hay que scrollear para ver lo que es el centro del
demo.

### F2 · La rueda scrollea la página en vez de hacer zoom

**Qué hice:** rodé la rueda sobre el lienzo para acercarme.
**Qué pasó:** scrolleó la página y **perdí el grafo de vista**. Tuve que volver a
bajar. En un escenario, esto es el presentador perdiendo la pantalla en vivo.

### F3 · No hay pantalla completa

Busqué en todos los botones de la página: `["Toda la red", "Soltar el foco",
"Apagar el camino", …]` — **no hay ninguno de pantalla completa.**
`document.fullscreenEnabled` es `true`: la API está disponible y sin usar.
"Toda la red" es un `zoomToFit`, no un modo de pantalla.

### F4 · Tocar un nodo destruye el encuadre

**Qué hice:** con el camino encendido, toqué el chip de la nota de Ramón.
**Qué pasó:** el grafo hizo zoom hasta ese nodo, que quedó **solo en un lienzo
negro vacío**. Se perdió el camino de vista. Para volver hay que tocar "Toda la
red" y rearmar el encuadre a mano.

### F5 · Los nodos son intocables

**Qué hice:** intenté clickear el nodo del proveedor en el centro de la maraña.
**Qué pasó:** nada. Los nodos miden 2–3 px al zoom de entrada. Erré dos veces
seguidas.

### F6 · El grafo entra como una nube y se sigue moviendo

Al abrir, ~567 puntos ocupan un círculo de unos 250×250 px en el centro de un
lienzo de 1649×515: **más del 70% del lienzo está vacío** y el contenido está
comprimido. La simulación sigue corriendo y **el grafo se mueve solo** mientras
uno mira. Ninguna etiqueta es legible.

### F7 · Las notas aisladas se ven como basura flotando

Los 6 nodos de grado 0 quedan lejos del núcleo, como puntitos amarillos sueltos
en los bordes del lienzo. Visualmente leen como error de render.

### F8 · La lista de 41 chips es ruido puro

Con el camino encendido aparece "Las 41 entidades del cruce". Los chips, en
orden real:

> Almacén San Martín · Granja Los Álamos · Hostería Costanera · Panadería El
> Trigal · **tomas · 07-06** · **ramon · 06-29** · **nahuel · 07-01** ·
> **ramon · 07-02** · MAYONESA LA RIBERA 500G · MAYONESA MONTE CHICO 500G ·
> MAYONESA EL LITORAL 500G · VINAGRE COSTA DULCE 1L · LENTEJAS DON TIMOTEO 400G
> · YERBA COSTA DULCE X1KG · ALFAJOR TRIPLE LA RIBERA · TURRON COSTA DULCE ·
> VINO TINTO MONTE CHICO · LECHE ENTERA TIERRA ROJA · … (23 productos más)

**Las cuatro personas que avisaron están enterradas entre mayonesas y lentejas.**

---

# 4 · El mapa de la operación — el inventario textual

Este sí está bien, y conviene decirlo.

## Los cuatro titulares

| Valor | Etiqueta | Pie | Estado |
|---|---|---|---|
| **8** | Vencen en 30 días | plata que se tira si no sale | dudoso |
| **290** | Bultos sin confirmar | 4 pedidos salieron y nadie avisó | error |
| **20** | Pedidos sin salir | esperando en la playa de carga | — |
| **$311M** | Por cobrar | Despensa Doña Elsa lleva 66 días | dudoso |

## Los seis hallazgos (chips bajo el título)

1. "El depósito avisó 4 veces que Cámara de frío 2 está llena — y hay una orden
   de compra abierta que llega justo ahí." → camino de **7 nodos**, y acá **sí**
   incluye `nota_ft02, nota_wa01, nota_nt09, nota_nt08` + `oc_oc_2026_0863` +
   `zona_camara_de_frio_2` + `lote_l_2026_522`
2. "290 bultos salieron y nadie confirmó la entrega" → 8 nodos
3. "8 partidas vencen en los próximos 30 días" → 2 nodos
4. "2 partidas ya vencidas siguen ocupando lugar" → 2 nodos
5. "Despensa Doña Elsa · 66 días sin pagar" → 1 nodo
6. "20 pedidos sin salir" → 1 nodo

> **El mapa de la operación resuelve bien lo que el grafo resuelve mal.** Su
> camino de la cámara tiene 7 nodos y las 4 notas están adentro, conectadas a la
> zona. El grafo, para el mismo hallazgo, trae 41 nodos y 0 aristas de nota.

## Las tres capas

| id | Título | Detalle | Nodos |
|---|---|---|---|
| `origen` | **De dónde viene** | "Los proveedores y lo que ya está pedido y todavía no llegó." | 7 |
| `centro` | **Dónde está** | "El depósito por dentro: cada zona con lo que tiene guardado." | 5 |
| `destino` | **Adónde va** | "Los camiones, las bocas y los clientes que esperan." | 12 |

## Las tarjetas, textual

**Centro:**
- **Depósito Central** · Casa Central · partidas: 380 · Zonas: 21 · Vencen en 30 días: 8 [dudoso]
- **Pasillos y racks** · "18 ubicaciones · hay partidas vencidas" · partidas: 279 · Unidades: 98.670,2
- **Cámara de frío 2** · "Ocupación 100% · está llena y hay mercadería en camino" · partidas: 41 · Unidades: 4.091,5
- **Cámara de frío 1** · "Ocupación 73% · sin novedades" · partidas: 30 · Unidades: 2.906,8
- **Cámara congelados** · "Ocupación 73% · vence algo pronto" · partidas: 30 · Unidades: 2.853,9

**Origen:**
- **Distrib. Mayorista Guaraní** · "Última entrega 30/06" · recepciones: 172 · Unidades: 26.119
- **Golosinas Costa Dulce SRL** · recepciones: 148 · Unidades: 21.681
- **Lácteos Campo Alegre** · recepciones: 146 · Unidades: 21.580,2
- **Frigorífico La Ribera** · recepciones: 140 · Unidades: 18.097,6
- **Otros proveedores** · "2 proveedores" · recepciones: 246 · Unidades: 35.021,5
- **OC-2026-0847** · Lácteos Campo Alegre · bultos: 165 · Llega: 02/07 [dudoso]
- **OC-2026-0863** · Frigorífico La Ribera · bultos: 154 · Llega: 09/07

**Destino:**
- **P-4411** Despensa La Unión · 39 bultos · Prevista 07/07 [error]
- **P-4412** Comedor Escolar N°12 · 69 bultos · [error]
- **P-4413** Súper Avenida Norte · 106 bultos · [error]
- **P-4414** Bar El Muelle · 76 bultos · [error]
- **Pedidos sin salir** · "3 camiones cargando" · 20 pedidos · 1.161 bultos
- **Casa Central** · "Mismo predio · sin traslado" · 2.699 movimientos
- **Sucursales** · "2 locales propios" · 1.297 reposiciones
- **Autoservicios y súper** · "7 comercios" · 11 pedidos · 1.048 bultos
- **Gastronomía y hotelería** · "7 comercios" · 16 pedidos · 954 bultos
- **Despensas y kioscos** · "4 comercios" · 6 pedidos · 221 bultos
- **Cuentas por cobrar** · "23 clientes con saldo" · $311M
- **Despensa Doña Elsa** · "el sistema dice 30 días · el dueño le dio 45" · $19M

## Los corredores y sus etiquetas

`contiene`: 279 / 41 / 30 / 30 partidas · `corredor`: 19, 11, 10, 6, 5, 4 pedidos
`recepcion`: 140, 98, 94, 90, 168 recepciones · `orden` (punteada): 165 y 154 bultos
`transito` (punteada, roja): 39, 69, 106, 76 bultos sin confirmar
`carga`: 20 pedidos · `mostrador`: "mismo predio" · `reposicion`: 1.297 reposiciones
`reparto`: 10, 14, 5 pedidos

## La banda de canales

**"Lo que entra desde afuera" · "14 de 31 entraron por un canal que el ERP no ve"**

| Canal | Nombre | Total | Recientes | ¿De afuera? |
|---|---|---|---|---|
| whatsapp | WhatsApp | 7 | 7 | **sí** |
| email | Mail | 4 | 3 | **sí** |
| foto | Foto | 3 | 3 | **sí** |
| voz | Audio | 7 | 5 | no |
| chat | Chat | 6 | 3 | no |
| reporte | Reporte | 4 | 2 | no |

> **Un error de clasificación:** `voz` está marcado `de_afuera: false`. Un audio
> que manda alguien del depósito es exactamente lo que el ERP no ve. Con voz
> adentro serían **21 de 31**, no 14.

## Las otras bandas de contexto

- **El equipo** · "14 personas · 13 avisaron algo" · 23 avisos esta semana.
  Avatares: Celeste (Compras, 4), Ramón (Encargado de depósito, 4), Walter
  (Reparto camión 1, 4), Brian (Armado de pedidos, 3) + 10 más.
- **Reglas de tu casa** · "22 aprendidas · 97 aplicaciones". Ejemplos:
  "GASEOSA COLA LA RIBERA nunca puede quebrar: trae gente al local." · "La
  balanza 2 desvía siempre un poco: si es menos del 1%, no me alertes."
- **Vuelve a Odoo** · "por export de CSV" · "23 devoluciones en 30 días" ·
  chips: datos integrados (2), remito cargado (2), montos validados (1).

## El panel lateral de un nodo (Cámara de frío 2)

Es **la mejor pantalla del producto** y conviene decirlo:

> **¿Qué está pasando con Cámara de frío 2?**
> · Ocupación 100% — la más cargada del depósito.
> · El equipo avisó 4 veces esta semana.
> · Y la OC-2026-0863 con 154 bultos llega justo acá el 09/07.
> · 1 por vencer.
>
> **DE DÓNDE SALIÓ**
> — OC-2026-0863 · Frigorífico La Ribera · "154 bultos · llega el 09/07"
> — **Tomás · 06/07 · Foto** · "Foto de cómo quedó la cámara 2 después de acomodar. No entra un pallet más."
> — **Ramón · 02/07 · WhatsApp** · "Muchachos, no entra más nada en la cámara 2..."
> — **Nahuel · 01/07 · Audio** · "Estamos apilando cajas en el pasillo porque la cámara 2 está llena."
> — **Ramón · 29/06 · Audio** · "No entra más nada en la cámara de frío 2. Si llega el pedido grande de fiambres no sé dónde lo pongo."
>
> **QUÉ SE PUEDE HACER**
> Propuesta: "Sale primero SALAME MILAN MONTE CHICO (PLANCHA) (L-2026-522) y la entrega se reprograma."
> Botón: "Pedirle a Ángela que prepare: reprogramar la orden OC-2026-0863"
>
> Abajo: "Lo que hay guardado" — las 41 filas con lote, producto, cantidad y vencimiento.

**Ese panel tiene exactamente la historia que queremos contar: cuatro personas,
con nombre, fecha y canal, y una consecuencia con acción.** El grafo, para el
mismo caso, muestra una maraña sin notas.

---

# 5 · La UI que compite por atención

En la pantalla del cerebro, de arriba hacia abajo:

1. Breadcrumbs: "Volver al mapa de la operación" · "Volver a las fuentes"
2. Título "El cerebro de tu negocio" + bajada de dos líneas
3. Panel de hallazgos: **8 botones-píldora** con título largo + `3⨯19`
4. (con camino) Resumen del cruce: una línea
5. (con camino) Chips de dominios: 4
6. (con camino) 4 viñetas de "por qué"
7. (con camino) **41 chips de entidades** en 5 filas
8. **El lienzo** ← lo único que importa
9. Leyenda flotante sobre el lienzo: 8 tipos en 3 filas
10. Debajo: "El núcleo" + "CADA FORMA ES UN TIPO DE ENTIDAD"

**Entre el borde superior y el lienzo hay 713 px de texto.**

---

# 6 · Lo que hay que entender antes de rediseñar nada

El grafo no tiene un problema de estética. Tiene tres problemas, en este orden:

1. **De datos.** Las notas sobre lugares no se conectan porque no hay nodos de
   ubicación. Seis notas con grado 0, y son las de los dos mejores casos.
2. **De selección.** La expansión de un salto trae 26 productos por
   `coventa`/`provee` y deja el hallazgo enterrado. El 78% del grafo son tres
   relaciones que no explican nada.
3. **De presentación.** Recién tercero: tamaños, formas, encuadre, pantalla
   completa.

**Arreglar sólo el 3 no sirve.** Un grafo hermoso que muestra 26 mayonesas
alrededor de cuatro post-its desconectados sigue sin contar la tesis.
