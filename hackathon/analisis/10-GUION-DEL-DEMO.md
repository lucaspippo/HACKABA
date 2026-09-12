# El guion del demo, cronometrado

Escrito **antes** de terminar de construir, como corresponde. Cuatro minutos.

Todo lo que está acá se apoya en algo que existe en
`HACKABA/polpilot-hackcba`. Lo que todavía no se verificó corriendo va marcado
**[verificar]** — y verificarlo es parte del ensayo, no del pitch.

---

## Antes de subir

| | Qué | Por qué |
|---|---|---|
| ☐ | **Correr `py backend/scripts/run_evals.py`** | Sin corrida, el panel dice "todavía no corrió". Es honesto pero no es lo que queremos mostrar |
| ☐ | **Mirar los números que salieron** y ajustar el guion a ellos | Si una suite da 5 de 7, se dice 5 de 7 |
| ☐ | **Abrir el cerebro y tocar el hallazgo de la oferta** | Confirmar que el cruce emite y que el camino enciende post-its |
| ☐ | **Activar "Proyectar" y mirar desde el fondo de la sala** | Lo que se lee en un monitor no se lee en un proyector |
| ☐ | **Token de MCP nuevo** (TTL 12 h) y las dos ventanas ya conectadas | No se configura un conector delante de un jurado |
| ☐ | **Video del demo grabado** | Plan B si se cae la red |
| ☐ | **La prueba de los tres minutos** con alguien de afuera | Si no lo puede explicar, el jurado tampoco |

---

## 0:00 – 0:20 · El problema universal

> "En toda empresa hay información que existe y no llega. Alguien la sabe,
> alguien la dijo, y la decisión igual se toma sin ella. Nosotros la juntamos.
> Se lo mostramos en una distribuidora porque ahí se ve la plata."

**Pantalla:** nada todavía, o el cerebro quieto. **No hablar de remitos, lotes,
conciliación ni ERP.** Ni una vez en los primeros noventa segundos.

## 0:20 – 0:40 · La distinción que les enseñamos

> "Una **alerta** mira UNA fuente y avisa un umbral. Cualquier ERP con un chat
> encima lo hace, y por eso no prueba nada. Un **cruce** junta fuentes que no se
> hablan entre sí y encadena una consecuencia que nadie tenía a la vista."

**Por qué va acá y no al final:** a partir de este momento el jurado tiene un
criterio nuevo para juzgar a los otros equipos — y todos los demás van a estar
mostrando alertas.

## 0:40 – 1:50 · La oferta que hay que rechazar · **el aha**

**Pantalla:** cerebro → "Proyectar" activado → tocar el hallazgo
**"El 18% de descuento de Frigorífico La Ribera conviene rechazarlo"** →
**Reproducir el camino**.

La animación corre sola en cuatro segundos: silencio, se encienden las semillas
(los post-its, con el texto de lo que dijo cada uno), viajan las ramas,
converge.

**El texto, mientras corre:**

> "El proveedor te ofrece un pallet de salame con **18% de descuento**. La
> oferta vence el 17. Parece una buena compra."
>
> *(pausa)*
>
> "El sistema dice que no."
>
> "Vendés 1,44 kg por día. El lote vence en 100 días. Podés absorber 88 kilos.
> La oferta son 689."
>
> **"El descuento te ahorra $163.675 y te hace tirar $5.038.657."**
>
> "Y además, el mismo proveedor ya tiene una orden de fiambres llegando el 9, a
> una cámara que **tres personas dijeron por tres canales distintos que está
> llena** — uno de ellos con una foto. Él mismo pidió que le avisemos si no hay
> lugar."

**[verificar]** Los dos montos salen de replicar a mano la aritmética de
`_card_sobrecompra` sobre el dataset. **Hay que leerlos de la pantalla antes de
decirlos en una sala.** Si la card muestra otra cosa, se dice lo que muestra la
card.

**Lo que hay que señalar con el dedo mientras se ve:**
- Los post-its con **borde discontinuo**: eso entró de afuera del sistema.
- El **glifo adentro**: onda = voz, burbuja = WhatsApp, cámara = foto.
- Los **chips de dominios**: cuatro fuentes que no se hablan entre sí.

**La frase de cierre del momento:**

> "Todos los que están acá hoy van a mostrar algo que encuentra oportunidades.
> Esto descarta una, y les puede decir exactamente por qué."

## 1:50 – 2:30 · El contrafáctico · **que lo rompa el jurado**

> "Sáquenle un dato."

Se le pasa el mouse. Debajo del hallazgo hay una fila de evidencias: *Ramón ·
voz*, *Nahuel · voz*, *Tomás · foto*. Tocan una. El grafo se vuelve a pedir sin
ella, el post-it desaparece del mapa, la rama se apaga.

> "Un chatbot no se rompe cuando le sacás un dato. Sigue contestando con la
> misma seguridad, porque lo que produce es redacción. Esto se apaga, porque lo
> que produce es una consecuencia."

Se toca **"Devolver el dato"** y vuelve.

> "No borramos nada. Es un parámetro de lectura: la nota sigue ahí, con su autor
> y su fecha."

**Acá va la frase de arquitectura**, que es la que un jurado técnico está
esperando:

> "Lo que ven lo calcula código, no el modelo. El modelo pone las palabras. Si
> el modelo alucina un número, el código lo frena — toda cantidad se valida
> contra catálogo antes de entrar."

## 2:30 – 3:00 · El MCP y el determinismo, juntos

**Pantalla partida:** PolPilot a la izquierda, Claude Desktop a la derecha, ya
conectado a `/mcp`.

Misma pregunta en las dos: *"¿cuánta plata tengo parada en stock?"*

> "A la izquierda, nuestro producto. A la derecha, Claude Desktop hablando con
> el mismo negocio por MCP, con el login del usuario y los permisos de su rol.
> **No es la misma pregunta contestada dos veces: es el mismo cálculo citado dos
> veces.** El número no lo pone el modelo. Si lo pusiera, serían distintos."

**El remate de quince segundos**, si el tiempo lo permite: cerrar sesión, entrar
como rol de depósito, volver a listar herramientas.

> "`estado_caja` ya no está. Un rol de depósito no ve la caja en la app; tampoco
> la ve un agente que entre con su token. Y no es que se la escondemos del
> menú: si la llama igual, el servidor la rechaza."

## 3:00 – 3:35 · El punto ciego · **el golpe**

**Pantalla:** cerebro → el bloque "El punto ciego" → tocar **Walter**.

Dos clientes se apagan en el mapa.

> "Walter maneja una camioneta. Es la única persona de esta empresa que pisa
> estos dos clientes.
>
> Si Walter se toma vacaciones, la empresa no pierde los datos — los datos
> siguen ahí. **Deja de saber lo que no está en ningún dato:** que uno abre
> salteado, que el otro pidió hablar con el dueño antes de que le lleven más."

**Por qué esta versión y no la de las reglas:** es verdad contra el dataset. Las
22 reglas de la casa las enseñó el dueño, así que un mapa de riesgo sobre eso
diría "si se va el dueño se pierde todo", que es cierto y no sirve. Sobre las
notas del equipo hay 13 autores reales.

## 3:35 – 3:50 · Los evals

**Pantalla:** "Qué tan seguido acierta".

> "Medimos esto. No es una promesa: es una corrida grabada, con fecha, sobre
> conjuntos de casos con nombre. Cada puntaje muestra el tamaño de su conjunto
> al lado — **24 de 24**, no '100%'.
>
> Y la que más nos importa: **cuántas veces el sistema dijo que no sabe y tenía
> razón.** Es el único número que un sistema que contesta siempre no puede
> reportar."

**[verificar]** Los números concretos salen de la corrida. Decir los que estén.

## 3:50 – 4:00 · Cierre

> "Todos muestran una salida. Nosotros mostramos el camino.
> Todos muestran que funciona; nosotros mostramos qué pasa si sacás una pieza.
> Todos hablan con confianza; nosotros declaramos cuándo no sabemos.
> Y todos usan datos de ejemplo: nosotros usamos una empresa entera, con catorce
> personas que se contradicen entre sí."

---

## Los ejemplos de reserva

De a uno, veinte segundos, sólo si preguntan.

1. **El pasillo 4.** El ERP dice que faltan 6,5 unidades de leche, $53.646. No
   faltan: Kevin las fue a buscar y estaban en otro rack, Nahuel corrió las
   cajas para hacer lugar. El mismo día, por canales distintos, y nadie los
   juntó. *(Se muestra como card, no como grafo: vive en
   `deposito.explicaciones()` y no tiene camino.)*
2. **Doña Elsa.** El listado de morosos dice que la intimes. La regla de la casa
   dice 45 días porque es cliente desde 2011. El repartidor la vio abierta y
   trabajando el viernes. Ella misma pidió una entrega chica para no seguir
   sumando. **El sistema te dice que no la intimes todavía, y por qué.**
3. **El reclamo de Campo Alegre.** Cuatro personas, cuatro canales, cinco días,
   un solo hecho. Y dos se contradicen: Ramón dice que lo trajeron al otro día,
   Brian que viene la semana que viene.
4. **La gaseosa.** La regla más aplicada de la casa (9 veces) dice que ese
   producto nunca puede quebrar. Quebró en la Sucursal Norte el sábado que más
   se vende. Hay 282 unidades en el depósito central: no falta mercadería,
   falta que baje.
5. **El yogur.** El lote vence en 7 días. El proveedor tarda 9 en traer más. El
   reemplazo llega después del quiebre, hagas lo que hagas — salvo que pidas
   hoy.

---

## Las respuestas que hay que tener listas

| Si preguntan | Se contesta |
|---|---|
| ¿Funciona sin conexión? | "Está diseñado y es lo próximo que construimos." **No decir que sí.** |
| ¿El grafo muestra la evolución en el tiempo? | "Hoy es una foto. Guardamos cuándo y de quién aprendimos cada cosa, así que el eje del tiempo es lo próximo. No está construido." |
| ¿Esto se llenó solo? | "Los canales están construidos: voz, foto, formulario del piso, WhatsApp. Las 31 notas de esta demo son datos sintéticos, como todo el dataset — está escrito en el código del módulo." |
| ¿Puedo hablarle y que aparezca en el grafo? | "La voz está construida y convierte lo que decís en una propuesta estructurada, validada contra catálogo. Que ese reporte se vuelva un nodo del grafo en vivo es el puente que estamos terminando." |
| ¿Tienen API abierta? | "API REST y un servidor MCP construido y probado, de sólo lectura. No tenemos CLI ni SDK." |
| ¿Por qué el MCP no escribe? | "A propósito. Lo que escribe pasa por una persona. Hay un test que rompe la suite si alguien mete una herramienta de escritura en la lista equivocada." |
| ¿Son evals o son tests? | "Hasta ayer eran tests: 159 archivos que dan verde o rojo. Esto puntúa dos conjuntos que ya corrían más uno que etiquetamos a mano. Digo el tamaño de cada uno porque importa." |
| ¿Predice la demanda? | "Hay un pronóstico determinista. No hay modelos probabilísticos y no hacemos pronósticos que no podamos explicar." |
| ¿Ya tienen clientes? | "Producto funcionando, un piloto realizado no pago, cero clientes pagos hoy." |
| ¿Esto lo construyeron acá? | "No, y lo decimos: PolPilot es un producto que venimos construyendo. Lo de estas horas es el cruce nuevo, la animación del camino, el panel de evals, el contrafáctico y el mapa de punto ciego." |
| ¿El dataset es real? | "Cien por ciento ficticio, generado con semilla fija. Está declarado en el repositorio." |

**La regla que las cubre a todas: lo que el jurado no pueda verificar en la
sala, mejor no prometerlo.**

---

## Reparto en la sala

- **Quien habla:** uno solo. El guion es de una voz.
- **Quien maneja la pantalla:** otro. Nunca la misma persona — buscar un botón
  mientras se habla mata el ritmo.
- **Quien contesta preguntas técnicas:** el que escribió el motor. Se presenta
  al final, no al principio.
- **Nunca empezar por el equipo, los premios o la arquitectura.**
