# El grafo: diagnóstico y propuesta

---

# Parte 1 · Cómo está construido hoy

## Qué lo alimenta

`core/grafo.py::construir()` lee **siete fuentes** y arma un grafo de entidades.
No hay ninguna capa de NLP en el medio: cada relación sale de una fila o de un
campo declarado.

| Fuente | Qué aporta |
|---|---|
| `store.raw_actual()` | 430 productos (427 activos) |
| `cuentas.listar()` | 24 clientes y sus cuentas corrientes |
| `esquema.filas("venta")` | 10.776 filas, 12 meses, para facturación por entidad y canastas |
| `ventas_cliente.por_cliente()` | qué se lleva cada cliente, renglón por renglón |
| `esquema.filas("logistica" / "ordenes_compra" / "recepciones")` | remitos, órdenes, quién entregó de verdad |
| `traslados._load()` | movimientos a locales propios |
| `notas.listar()` | **31 notas del equipo** — el único tipo de nodo que no sale de una tabla |
| `conocimiento.listar()` | las 22 reglas, colgadas de la entidad que nombran |

**Tamaño estimado: entre 550 y 600 nodos.**

## Los nodos

Ocho tipos, cada uno con **forma propia** dibujada a mano en `dibujarForma()` —
no es sólo color:

| Tipo | Forma | Color |
|---|---|---|
| producto | círculo | hielo `#4aa8bf` |
| cliente | cuadrado redondeado | salvia `#5fbf8f` |
| proveedor | rombo | ocre `#c98a3c` |
| rubro | hexágono | neutro `#8b8fa8` |
| local | triángulo (el techo de la casa) | papel `#d7cfc0` |
| remito | hoja de papel vertical | violeta `#9d8bc4` |
| cuenta | círculo **hueco** (es un saldo, no una cosa) | salvia clara |
| **nota** | **post-it con la esquina doblada** | **amarillo `#e8c86a`** |

Tres señales más por nodo: **tamaño** = peso (facturación 12m, saldo, compras),
**anillo rojo** = problema real, **anillo ámbar** = para mirar.

## Las aristas

Doce relaciones. La que sostiene el núcleo denso es `coventa`
(producto↔producto), calculada con **lift ≥ 1,15 sobre canastas diarias
(fecha × boca), mínimo 3 canastas, top 3 por producto**. La arista `afinidad`
(cliente↔rubro) es **la única inferida**, se dibuja **punteada**, y existe sólo
de respaldo para el cliente sin pedidos abiertos.

## El layout

Force-directed (`react-force-graph-2d` + `d3-force-3d`): atracción por arista,
repulsión, y gravedad proporcional al grado. El comentario del archivo lo dice
mejor de lo que yo podría: *"la posición NO se decide, se gana… El núcleo denso
no está dibujado: emerge."* Eso es cierto y es defendible.

## Los caminos

`grafo.caminos(g, cards)` — determinista, sin heurística:

1. **Semillas**: resuelve por nombre las entidades que la card ya nombra
   (`datos.producto/cliente/proveedor`, `datos.clientes/productos`, los records
   de la evidencia) **más las notas que dispararon el hallazgo**.
2. **Un salto**: por cada semilla, hasta 14 vecinos. Los locales quedan afuera
   salvo que la semilla sea el propio local — son hubs de todo y arrastran medio
   grafo.
3. Devuelve `{semillas, nodos, aristas, dominios, tipos, porque}`.

Sobre eso, la vista enciende el camino en azul-Ángela, atenúa el resto a 13% de
opacidad, pone **partículas direccionales viajando** por las aristas del camino,
y hace `zoomToFit` sobre los nodos del camino. Hay un panel debajo con el
resumen, los dominios cruzados, el porqué, y las entidades recorribles una por
una.

---

# Parte 2 · El diagnóstico

## 2.1 · Qué no se entiende a primera vista

**a) Qué estoy mirando.** El grafo se abre con ~570 nodos y la primera lectura es
"una nube". El núcleo emerge, sí, pero emerger tarda 220 ticks de simulación y
el que mira no sabe que tiene que esperar. **No hay un estado inicial que
enseñe.** El primer segundo es el que decide si el jurado se engancha o si
piensa "otro grafo bonito", y hoy ese segundo lo gasta una nube.

**b) La leyenda es un diccionario, no una explicación.** Ocho formas y doce
relaciones es más de lo que alguien puede aprender mirando. Ninguna forma tiene
un rótulo permanente en el lienzo: hay que ir a la leyenda, memorizar, volver.

**c) El camino se enciende, pero no se entiende *en qué orden*.** Las partículas
viajan todas a la vez, en las dos direcciones, por todas las aristas del camino.
Ver el resultado no es ver el razonamiento: hay que ver **la secuencia**.

**d) Ningún camino empieza en la nota y termina en la plata.** El camino es un
conjunto, no una narración. Nada dice "esto empezó acá".

## 2.2 · ¿Se distingue lo no estructurado dentro del grafo? — **Sí, y es de lo mejor que tiene**

Esto lo preguntaste explícitamente y la respuesta es mejor de lo que esperabas.

**En el cuerpo del grafo, sí se nota**, y por tres vías a la vez:

- **Forma propia**: post-it con esquina doblada, la única forma no geométrica.
- **Color propio**: el amarillo del post-it, deliberadamente fuera de la paleta
  de las entidades del sistema. El comentario del código lo dice: *"es lo único
  acá que no salió de una tabla."*
- **Arista propia**: `menciona`, en el mismo amarillo.

**Lo que falta no es distinguir la nota: es distinguir el canal.** Una nota de
voz de Kevin y un mail de Celeste son hoy **el mismo post-it amarillo**. El
canal existe en el dato (`nota.canal`: voz, whatsapp, chat, reporte, email,
foto) y está usado en la banda de canales del otro mapa —donde `whatsapp`,
`email` y `foto` van marcados `de_afuera` y de primeros— **pero no llega al
cuerpo del grafo**. Ahí está el pedido tuyo de los glifos de canal, y es
correcto: hoy se ve "esto lo dijo una persona", no se ve "esto lo dijo hablando".

**Y falta la transformación.** El nodo `nota` y el nodo `producto` están unidos
por `menciona`, pero el momento en que "corrí las cajas del pasillo 4" se vuelve
un registro con ubicación, fecha y autor **no tiene representación**. La nota ya
llega estructurada al grafo (el reporte del piso pide producto y motivo), así que
el grafo nunca ve el antes. Ésa es nuestra tesis entera y hoy es invisible.

## 2.3 · ¿Se ve la evolución en el tiempo? — **No. Es una foto.**

`construir()` toma `hoy()` y una ventana de 12 meses y devuelve el estado actual.
Ningún nodo ni arista lleva `desde`/`hasta`. No hay versiones ni historial.

**Pero los datos están, sin usar:**

- 31 notas con `fecha`, del **2026-06-23 al 2026-07-06**.
- 22 piezas de conocimiento con `origen.cuando`, del **2026-06-05 al 2026-07-06**,
  más `veces_aplicada`.
- Lotes con vencimiento, órdenes con fecha, recepciones con fecha, 12 meses de
  venta.

Eso alcanza para un eje temporal honesto de **32 días**, que es exactamente el
tramo donde ocurren todos nuestros casos. No hace falta inventar historia.

## 2.4 · ¿Se lee proyectado, desde lejos? — **No.**

Números concretos del código:

| Parámetro | Valor actual | Qué pasa en un proyector |
|---|---|---|
| Tipografía de etiqueta | `max(2.6, 4.1/√escala)` px en unidades del grafo | Prácticamente ilegible a tres metros |
| Grosor de arista normal | `0.55` | Desaparece |
| Grosor de arista del camino | `1.7` | Se ve, apenas |
| Nodos atenuados | `globalAlpha = 0.13` | En un proyector con poco contraste, **desaparecen del todo** — lo que puede ser bueno |
| Etiquetas visibles sin foco | sólo si `escala > 2.2`, o nodo grande y `escala > 0.7` | Con el mapa entero encuadrado no se ve ningún nombre |
| Fondo | `#0f1113` sobre lienzo oscuro | Correcto para proyector; el contraste de los colores de tipo sobre negro ya está corrido en luminosidad |

**El diagnóstico honesto: el grafo está diseñado para trabajar de cerca, con
mouse, en un monitor.** Está bien diseñado *para eso*. Proyectado, un jurado a
cuatro metros ve manchas de color moviéndose.

## 2.5 · El hallazgo más importante del diagnóstico

**El pasillo 4 no tiene camino en el grafo.**

El caso vive en `deposito.explicaciones()` y sale como prioridad `dep_discrep` y
como aviso dirigido en `mis_avisos`. Pero `grafo.completo()` sólo calcula caminos
para los **seis cruces de `cruces.py`** más dos cards de Oportunidades
(`cliente_frio`, `ventana_compra`).

**El mejor ejemplo que tenemos, el aha de quince segundos del guion, es el único
que el cerebro no puede encender.** Si mañana se toca el botón del pasillo 4
esperando ver el camino, no hay camino.

Arreglarlo no es difícil: o se escribe el pasillo 4 como un séptimo cruce en
`cruces.py` con el shape estándar (que es donde conceptualmente pertenece —cruza
depósito × notas × ERP—), o se lo agrega a `CARDS_QUE_CRUZAN`. **Lo primero es lo
correcto** y es media jornada.

---

# Parte 3 · La propuesta de diseño

Dirección, no especificación cerrada. Ordenada por relación impacto/costo.

## 3.1 · De dónde vino cada cosa: el glifo de canal — **barato**

Hoy toda nota es un post-it amarillo. Propongo **mantener la forma de post-it
como género** —sigue diciendo "esto lo dijo una persona"— y **meterle adentro un
glifo de canal**, dibujado en el canvas con trazo, no con emoji:

| Canal | Glifo | De afuera |
|---|---|---|
| voz | tres barras de onda | — |
| whatsapp | burbuja de chat | **sí** |
| foto | rectángulo con esquina y punto | **sí** |
| email | sobre | **sí** |
| chat | burbuja punteada | — |
| reporte | tilde en recuadro | — |

Y **una sola distinción visual fuerte**: los tres canales que vienen **de
afuera** (`whatsapp`, `email`, `foto` — la constante `DE_AFUERA` ya existe en
`mapa_operacion.py`) llevan **un borde discontinuo**. Es la lectura que importa:
lo que entró desde afuera del sistema contra lo que el sistema ya sabía.

**Por qué así y no con más colores:** ya hay ocho colores de tipo. Un noveno eje
de color rompe la lectura. La forma ya está ocupada por el tipo. El interior del
glifo es el único canal libre.

**Costo: 2–3 horas.** El dato ya viaja en el nodo (`metricas` trae `canal`);
hay que exponerlo como campo de primer nivel y dibujar seis glifos.

## 3.2 · El camino como secuencia, no como conjunto — **medio**

Reemplazar el "todo se enciende a la vez" por **cuatro etapas cronometradas**,
disparadas por un botón de reproducir:

```
  t=0.0s   fondo al 8%. Nada encendido. Sólo la silueta.
  t=0.4s   se encienden LAS SEMILLAS, una por una, 150 ms de diferencia.
           Si son notas: aparece el texto de la nota como globo, con autor,
           canal y fecha. "Kevin · voz · 6 jul". Se lee.
  t=1.6s   viajan las partículas DESDE cada semilla, por su rama, una rama
           por vez. Las ramas llegan en orden.
  t=2.8s   converge: el nodo de la consecuencia crece, pulsa una vez,
           y aparece el número.
  t=3.4s   se dibuja el pie: qué dominios se cruzaron (los chips que ya
           existen) y la frase del hallazgo.
```

**Cuatro segundos.** Es el aha del guion, cronometrado.

Lo que lo hace barato: **el dato ya existe**. `caminos()` devuelve `semillas`
(ordenables por fecha de la nota) y `nodos` y `aristas`. La secuencia es
recorrer semillas → BFS de un salto desde cada una → nodo final. No hay que
calcular nada nuevo, hay que temporizar el dibujo.

**Costo: media jornada** (la animación por etapas sobre el canvas existente).

## 3.3 · La transformación visible — **medio, y es la tesis**

Éste es el que pediste y el que más vale.

Cuando una nota es semilla de un camino, al encenderse **se abre en dos mitades
sobre el lienzo**:

```
   ┌─────────────────────┐        ┌─────────────────────┐
   │  ◍ voz · Kevin      │   →    │  ubicación  Pasillo 4 · Rack B
   │  6 jul, 07:41       │        │  producto   Leche entera 1L
   │                     │        │  tipo       estado_depósito
   │  "me mandaron a     │        │  autor      kevin
   │   buscar leche al   │        │  fecha      2026-07-06
   │   pasillo 4 y       │        │  canal      voz
   │   estaba en otro    │        │
   │   rack"             │        │  → se conecta con: Pasillo 4 · Rack B
   └─────────────────────┘        └─────────────────────┘
     LO QUE ALGUIEN DIJO            LO QUE EL SISTEMA ENTENDIÓ
```

La flecha se dibuja, los campos aparecen uno por uno, y recién entonces la nota
se cierra de vuelta en su post-it y la arista `menciona` se dibuja hacia la
entidad.

**Un aviso de honestidad que hay que respetar:** en el dataset de hoy la nota ya
llega con sus campos resueltos —el reporte del piso pide producto y motivo, y
`notas.py` lo dice explícitamente: *"las entidades NO se adivinan con NLP"*. Así
que este panel **muestra la estructura que el formulario ya capturó**, no una
extracción mágica. Si un jurado pregunta, la respuesta es buena: *"el campo lo
pide el formulario del piso, no lo adivina un modelo. Lo que adivinaría un
modelo es lo que después no podés auditar."* **Lo que no se puede decir es "el
sistema leyó el audio y sacó esto"** salvo que se conecte por `core/voz.py`,
donde sí ocurre de verdad.

**Costo: media jornada** si es un panel superpuesto; **una jornada** si se dibuja
dentro del canvas.

## 3.4 · Dos caminos que convergen — **medio**

Es un caso particular de 3.2 con un requisito extra: que el camino tenga **dos o
más semillas de canales distintos** y que las ramas viajen **en paralelo pero
visualmente separadas** (una arriba, una abajo) hasta el nodo común, que es donde
se encuentran.

El pasillo 4 es exactamente eso: Kevin por voz y Nahuel por WhatsApp, el mismo
día, y la diferencia de stock en el medio. **Pero requiere 2.5: el pasillo 4 hoy
no tiene camino.** Hacer el cruce primero, la animación después.

**Costo: media jornada,** encima de 3.2.

## 3.5 · El tiempo — **la pieza más cara y la que más rinde**

Propongo la versión honesta y barata, no la versión completa.

**Un control deslizante de 32 días** (del 2026-06-05 al 2026-07-06), y lo que
cambia al moverlo:

- **Las notas aparecen en su fecha.** Al principio el grafo no tiene ni un
  post-it. Al día 19 aparece el primero. Al final hay 31.
- **Las piezas de conocimiento se prenden en su `origen.cuando`.** Su entidad se
  ilumina cuando alguien le enseñó algo al sistema sobre ella.
- **Los cruces aparecen el día en que sus dos notas ya existen.** Éste es el
  golpe: el cruce del pasillo 4 **no existe el 5 de julio y existe el 6**, porque
  ese día Nahuel mandó el suyo. *"Esto no se podía saber ayer."*
- Lo estructurado (productos, clientes, proveedores) se queda quieto: es el
  fondo. **Y hay que decirlo:** el eje temporal es sobre **lo que el sistema
  aprendió**, no sobre el estado del negocio. Eso es honesto y encima es mejor
  discurso.

**Lo que NO propongo, y quiero decir por qué:** versionar el grafo entero
(guardar cómo estaba cada nodo cada día) es una pieza de ingeniería de días, no
de horas, y el dataset no tiene con qué llenarla. Sería un eje temporal falso.

**Costo: una jornada.** Backend: `construir(hasta=fecha)` filtrando notas y
conocimiento por fecha, y `caminos()` recalculado. Frontend: el control y el
redibujo.

## 3.6 · Para el proyector — **barato y obligatorio**

Un modo, activado por un botón, que cambia siete cosas:

1. **Tipografía × 2,2.** De `4.1/√escala` a `9/√escala`.
2. **Aristas × 2,5.** De 0,55 a 1,4; el camino de 1,7 a 4.
3. **Nodos × 1,4.**
4. **Recorte agresivo del lienzo:** en modo presentación, **no se muestran 570
   nodos.** Se muestran el camino más dos saltos: entre 20 y 40. El resto no se
   atenúa, **no se dibuja.**
5. **Etiqueta permanente en las semillas y en el nodo de la consecuencia**, no
   dependiente del zoom.
6. **Atenuado de 0,13 a 0,06** para lo que sí queda de contexto.
7. **Franja superior con el título del hallazgo** — ya existe, sólo hay que
   agrandarla.

El punto 4 es el que más importa y es el más barato: es un filtro sobre
`graphData`, no un cambio de dibujo. Y el guion ya lo pide ("menos nodos en
pantalla durante el demo").

**Costo: dos a tres horas.** No se sube a un escenario sin esto.

## 3.7 · Jerarquía visual: qué se muestra y qué se pliega

Hoy el lienzo compite con tres paneles (hallazgos, camino recorrible, núcleo).
Para presentar, propongo tres capas:

- **Siempre visible:** el lienzo, la franja del hallazgo activo, y el botón de
  reproducir.
- **Un toque:** los chips de dominios cruzados y el porqué (ya existen).
- **Plegado:** el buscador, el núcleo, la leyenda completa, las métricas del
  nodo. Se abren cuando alguien pregunta, que es cuando valen.

**Costo: dos horas.**

---

## Resumen de costos

| # | Qué | Costo | ¿Sin esto hay demo? |
|---|---|---|---|
| 2.5 | **El pasillo 4 como cruce de verdad, con camino** | media jornada | **No** |
| 3.6 | Modo presentación / legibilidad | 2–3 h | **No** |
| 3.2 | El camino como secuencia animada | media jornada | **No** |
| 3.1 | Glifos de canal + borde discontinuo para lo de afuera | 2–3 h | Sí, pero pierde la mitad del punto |
| 3.3 | La transformación visible | media jornada | Sí |
| 3.4 | Dos caminos convergiendo | media jornada (encima de 3.2) | Sí |
| 3.5 | El eje del tiempo | una jornada | Sí |
| 3.7 | Jerarquía / plegado | 2 h | Sí |

**Lo barato:** 3.1, 3.6, 3.7 y 2.5. Suman aproximadamente una jornada y son lo
que convierte el grafo actual en algo proyectable.

**Lo caro:** 3.5. Vale una jornada entera y es lo único de la lista que un jurado
que vio la hackathon de GitLab va a reconocer al instante.
