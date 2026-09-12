# Los cuatro de ellos contra los cuatro nuestros

Todo lo de acá está verificado contra `main` de `agustindelmonti/polpilot-app`
en `33ebb07`, leyendo el código y el dataset. Cada afirmación lleva el archivo y
la línea. Donde digo "no existe", es que busqué y no está.

Semáforo: 🟢 lo tenemos y se defiende · 🟡 lo tenemos a medias, hay que decir
hasta dónde · 🔴 no lo tenemos.

---

## 1. «Un registro que se llena solo desde donde ocurre la información» — 🟡

### Lo que sí

**Los caminos de entrada están construidos y son reales, no maquetas.**

- `core/voz.py` — audio del piso → intención → propuesta estructurada. El LLM
  interpreta el lenguaje; **el código valida los números contra
  `core/validacion`**, el mismo peaje que un remito. El módulo lo dice en su
  propia cabecera: "ocho" y "ochocientos" suenan parecido por teléfono y la
  diferencia son dos ceros en el stock.
- `core/extraccion.py` — el único punto por donde una foto se vuelve datos. Dos
  caminos: comprobante de muestra reconocido por sha256 de los bytes → extracción
  canónica determinista sin red; cualquier otra imagen → visión real. El
  pipeline de abajo (chequeos, cruce contra la orden de compra, confirmación,
  stock, audit) es idéntico por los dos caminos, y `origen` viaja en la
  respuesta para que la UI lo diga en vez de esconderlo.
- `core/piso.py` — ocho clases de reporte del piso (faltante, conteo, entrega,
  reposición, pedido, presupuesto, pregunta, costo), cada uno atribuido a la
  persona.
- `backend/whatsapp_bot.py` + `core/whatsapp_channel.py` — un canal de WhatsApp
  de cara al cliente, con credenciales, envío, y registro de pedidos como
  reportes de piso. Sesión de tool-use chica y aparte, con cuatro herramientas.

### Lo que no, y hay que decirlo

**Las 31 notas del equipo que alimentan el grafo y los cruces son datos
sintéticos sembrados, y `core/notas.py` no tiene API de escritura.** Está
declarado en el propio docstring del módulo, con todas las letras: *"Es DATA
SINTÉTICA del demo… NO es un canal externo: NO hay WhatsApp conectado, y ninguna
pantalla dice lo contrario."*

La consecuencia práctica, que es la que importa para la demo: **hoy, si alguien
manda un reporte de piso en vivo, ese reporte NO se convierte en un nodo `nota`
del grafo.** El camino existe hasta `piso.reportar`; de ahí al grafo no hay
puente. El Momento 2 del guion ("el jurado habla, aparece un nodo nuevo y se
conecta solo") **no está construido.**

La buena noticia: el andamio para construirlo sí está. `team_notes_repo.save_data`
existe (se usa para sembrar), y `analisis_cache.datos_cambiaron()` es el hook
único de invalidación que ya usan todos los puntos de persistencia. Escribir la
nota, bumpear la generación y volver a pedir `/api/grafo` es un camino corto.

### Cómo decirlo sin mentir

> "Capturamos desde donde ocurre: voz, foto, formulario del piso, WhatsApp. En
> la demo, la capa de notas del equipo está sembrada con datos sintéticos, como
> todo el dataset — está escrito en el código."

---

## 2. «Un modelo del mundo del negocio: grafo que conecta cada interacción y preserva cómo cambió en el tiempo» — 🟡

### La mitad que tenemos, y es fuerte

`core/grafo.py` construye un grafo de **entidades reales**, no de dominios:
producto, cliente, proveedor, rubro, local, remito, cuenta, y **nota** — el tipo
de nodo que no sale de ninguna tabla.

Las relaciones son diez: `pertenece`, `provee`, `vende`, `coventa`, `debe`,
`compra`, `afinidad`, `entrega`, `ordena`, `pide`, `traslado`, `menciona`.

Y hay una decisión que un jurado técnico va a valorar si se la contamos: el
módulo **declara en `meta.derivados` qué es dato crudo y qué calculó él**. La
co-venta producto↔producto se calcula con **lift ≥ 1,15 sobre canastas diarias
(fecha × boca), mínimo 3 canastas, top 3 por producto**, sobre 10.776 filas de
venta. La arista `afinidad` cliente↔rubro viaja marcada `inferida: true` y se
dibuja punteada, y **existe sólo de respaldo** para el cliente que todavía no
tiene pedidos abiertos en renglones. Eso es un grafo que declara su propia
incertidumbre, y no conozco otro proyecto de hackathon que lo haga.

`grafo.caminos()` ya guarda, por cada hallazgo, **los nodos y las aristas que lo
produjeron**, más las semillas. Las notas del equipo entran como **semilla y no
como vecina**, con un comentario en el código que explica por qué: si entraran
sólo por expansión, un proveedor con 70 productos las tapa y se pierde justo la
parte que prueba que el cruce tocó lo no estructurado.

### La mitad que no tenemos

**No hay eje temporal. El grafo es una foto.** `construir()` toma `hoy()` y una
ventana de 12 meses y devuelve el estado actual. Ningún nodo ni arista lleva
`desde`/`hasta`, no hay versiones, no hay historial.

Los datos para hacerlo **sí existen** y están sin usar: cada nota tiene `fecha`
(el dataset va del 2026-06-23 al 2026-07-06), cada pieza de conocimiento tiene
`origen.cuando` (del 2026-06-05 al 2026-07-06), hay lotes con vencimiento y
órdenes con fecha. La propuesta concreta está en `04`.

### Cómo decirlo sin mentir

> "Tenemos el grafo de entidades y el camino de cada hallazgo guardado. Lo que
> hoy es una foto del estado actual; el eje del tiempo es lo que estamos
> agregando."

---

## 3. «Un arnés determinístico: SDK, sandbox de código, y evals continuos» — 🔴 / 🟢 partido

Este punto hay que partirlo porque juntos dan una respuesta falsa.

### 3a · Determinismo: 🟢 y es de lo mejor que tenemos

No es una promesa, es un invariante de arquitectura escrito en `PRODUCT.md` y
sostenido por el código:

> *"Ángela es un orquestador LLM con tool-calling que narra y cita la salida de
> `core/` — nunca debe calcular, recordar ni reformatear un número por sí misma.
> Esto es un invariante arquitectónico duro, no una preferencia de estilo."*

Y hay pruebas concretas de que se sostiene:

- `core/cruces.py`: *"acá se DETECTA y se CALCULA. Cada número sale de los
  módulos que ya son la verdad del negocio. Si falta el dato, el cruce no sale:
  no hay hallazgo a medias."*
- `core/extraccion.py`: la extracción canónica se reconoce **por sha256 de los
  bytes, no por nombre de archivo ni por un flag del cliente**, porque esos dos
  se falsifican desde el navegador. Eso es pensar en el adversario.
- **The Counting Rule**: `mostrador.costos_viejos()` no tiene campo total **a
  propósito**, porque sumar el inmovilizado de esas filas daría un número que
  parece plata en juego y no lo es. Está respetada en `ficha.py`, `parada.py`,
  `vencimientos.py`, y protegida por tests (`test_costo_viejo.py`,
  `test_montos_canonicos.py`, `test_parada.py`).

**Dato menor pero conviene saberlo antes de que lo encuentre otro: "The Counting
Rule" se cita en 14 archivos y su definición ya no está en `PRODUCT.md`.** Se
perdió en alguna reescritura. La regla está viva en el código; el documento la
dejó colgando.

### 3b · Evals: 🔴 — **no tenemos evals. Tenemos tests.**

Esto es lo que preguntaste y la respuesta honesta es que no es lo mismo, y un
jurado técnico lo va a saber.

**Lo que hay:** 159 archivos `test_*.py` en el backend y 37 en el frontend. Dos
de ellos se acercan mucho a un eval:

- `tests/test_matriz_consultas.py` — genera **programáticamente la matriz
  completa** fuente × métrica × agrupación × filtro con las categorías reales del
  dataset y una muestra representativa de productos (grandes, chicos, sin
  ventas, cancelados) y clientes. Cada celda válida debe devolver una serie sana;
  las combinaciones que por diseño no existen deben devolver su error honesto —
  **y eso también es un PASS**. Esa última decisión es lo más parecido a un eval
  de abstención que tenemos.
- `tests/test_bateria_nl.py` — 24 frases (12 en inglés, 12 en español) por la
  **misma ruta que usa el modelo**. Criterio por frase: resuelve en ≤2 pasos de
  herramienta, termina en la respuesta correcta, nunca necesita un menú.

**Por qué no son evals:** devuelven verde o rojo, no una métrica. No hay
precisión, no hay recall, no hay falsos positivos contados, no hay una línea de
base contra la cual comparar una corrida con la siguiente, y no hay ninguna
superficie del producto que muestre un número de calidad. Un eval responde
"¿cuánto de bien?"; un test responde "¿se rompió?".

**La distancia entre lo que hay y un eval presentable es corta** —media jornada—
porque el conjunto de casos ya existe y ya corre. Lo que falta es puntuar en vez
de afirmar, y mostrarlo. Es la mejor relación impacto/costo de toda la lista.

### 3c · SDK y sandbox: 🔴

No existen, y hay que ser claro en por qué eso no es una carencia sino una
arquitectura distinta. Lightfield mete al agente en un sandbox porque **el agente
escribe el código que calcula**. Nosotros no necesitamos sandbox porque **el
modelo nunca calcula**: el cálculo ya está escrito, revisado y testeado en
`core/`. Son dos soluciones al mismo problema. La nuestra es más rígida y más
barata de verificar; la de ellos es más flexible.

Eso **sí** se puede decir en una sala, y es una buena respuesta.

---

## 4. «Plataforma abierta: todo legible y escribible por API, MCP y CLI» — 🟡, y mejor de lo que el documento interno decía

El documento interno dice "ellos tienen API, MCP y CLI abiertos, nosotros no".
**Eso está desactualizado.**

### Lo que sí tenemos

**Hay un servidor MCP real, construido, montado y testeado.** `backend/mcp_server.py`,
documentado en `backend/MCP.md` (un documento de 200 líneas que es de lo mejor
escrito del repo), montado en la misma app de FastAPI en `/mcp`, hablando
Streamable HTTP estándar. **28 herramientas de sólo lectura**, cada una un
envoltorio fino sobre `angela._run_tool` — el mismo punto de entrada al borde
determinístico, así que un número que llega por MCP es el mismo número que diría
Ángela y mostraría la app.

Y la parte que un jurado técnico va a respetar:

- La identidad viene del `Authorization: Bearer` con el mismo token que devuelve
  `POST /api/login`. **No hay credencial de MCP aparte que provisionar o
  filtrar.**
- **El gate de permisos se re-chequea del lado del servidor en cada llamada**, no
  se confía en que el cliente pida sólo lo que se le mostró. Un cliente que
  llame una herramienta que nunca vio igual recibe un rechazo.
- Cada herramienta se anuncia con `annotations.readOnlyHint = True`, y hay un
  test (`test_mcp_server.py::test_every_tool_is_marked_read_only`) que **hace
  fallar la suite si alguien agrega una herramienta de escritura a la lista
  equivocada**. Eso es la clase de bug que no puede nacer, que es exactamente el
  argumento del campo `total` que no existe.
- Cómo se testeó está escrito: Postgres real, tenant descartable, login real,
  la app real de FastAPI manejada por el SDK real de MCP sobre
  `httpx.ASGITransport`. Y **qué NO cubre también está escrito**: un cliente real
  de Claude Desktop contra un deploy real por red.

Hay además API REST completa (`backend/main.py`) con autenticación y permisos
por rol.

### Lo que no

- **No hay CLI.** Costo estimado: dos a cuatro horas contra la API que ya está.
- **El MCP es estrictamente de sólo lectura.** Nada que corrija datos, cierre la
  caja, mande un mensaje de cobranza o fije un widget. El plan de cómo abrirlo
  está escrito en `MCP.md` (propose→apply, `destructiveHint`, elicitation, token
  propio revocable, auditoría con actor distinguible, límites de tasa). Es una a
  dos jornadas y no lo haría para esto.
- **No hay SDK.**

### Cómo decirlo sin mentir

> "Cualquier LLM puede consultar el negocio por MCP con el mismo login del
> usuario y los mismos permisos de su rol. De sólo lectura, a propósito: lo que
> escribe pasa por una persona. Está documentado por qué, y hay un test que
> rompe si alguien se olvida."

**Y hay una jugada acá que el documento no vio:** los sponsors incluyen a
Cognition, y el jurado de una hackathon de IA en 2026 probablemente usa Claude
Desktop o Cursor. **Conectar nuestro MCP en vivo, delante de ellos, y hacer que
su propio cliente le pregunte al negocio** es una demostración de plataforma
abierta que cuesta cero construir porque ya está hecha. Riesgo: depende de la
red del lugar y del TTL de 12 horas del token.

---

## Cuadro final

| | Lightfield | PolPilot hoy | En una frase |
|---|---|---|---|
| **1. Registro que se llena solo** | 🟢 mail, calendario, llamadas, Slack, LinkedIn | 🟡 los canales existen (voz, foto, piso, WhatsApp); las notas del grafo son sintéticas y no hay escritura | Tenemos el canal más difícil (el que no tiene computadora) y no tenemos el puente al grafo |
| **2. Modelo del mundo con grafo temporal** | 🟢 temporal context graph | 🟡 grafo de entidades con caminos guardados y derivaciones declaradas, **sin eje temporal** | Tenemos el grafo, nos falta el tiempo |
| **3a. Determinismo** | 🟢 sandbox + SDK | 🟢 invariante de arquitectura, sostenido por tests | Distinta solución, mismo resultado |
| **3b. Evals** | 🟢 continuos | 🔴 **son tests, no evals** | Media jornada de distancia |
| **3c. SDK / sandbox** | 🟢 | 🔴 | No los necesitamos con esta arquitectura |
| **4. Plataforma abierta** | 🟢 API + MCP + CLI, lectura y escritura | 🟡 **API + MCP de sólo lectura, construido y testeado.** Sin CLI, sin SDK | Mejor de lo que creíamos |
| **5. Procedencia por dato** | 🔴 no publicado | 🟢 `valor`/`fuente`/`estado` en `carpeta.py`; `fuentes` y `dominios` en cada cruce; `meta.derivados` en el grafo | **Acá estamos adelante** |
| **6. Confianza en dos ejes** | 🔴 no publicado | 🟢 `core/confidence.py`: datos e hipótesis por separado, porque pueden discrepar y esa discrepancia *es* la información | **Acá estamos adelante** |

---

# Anexo · Qué de los dos documentos ya está construido

Contra el repositorio, no contra el PDF.

## Construido y verificado

| Cosa | Dónde |
|---|---|
| Motor de cruces determinísticos, 6 cruces, cada uno 3+ dominios | `core/cruces.py`, 590 líneas |
| Memoria de reglas de la casa con efecto verificable en el producto | `core/conocimiento.py` · 22 piezas, 97 aplicaciones, efectos `ajusta_umbral`/`suprime_alerta`/`genera_alerta`/`contexto_para_angela`/`requiere_aprobacion` con `params` que los motores leen |
| Grafo de entidades, layout de fuerzas, camino por hallazgo | `core/grafo.py` + `desktop/sections/CerebroNegocio.jsx` (994 líneas) |
| Mapa de la operación física en tres capas | `core/mapa_operacion.py` + `MapaNegocio.jsx` (2.391 líneas) |
| Banda de canales de entrada, con los tres de afuera primero | `mapa_operacion.canales_de_entrada()` · whatsapp, email, foto marcados `de_afuera` |
| Procedencia campo/valor/fuente/estado | `core/carpeta.py` |
| Confianza en dos ejes | `core/confidence.py` |
| El caso del pasillo 4 | `deposito.explicaciones()` + `test_diferencia_explicada.py` |
| Círculo cerrado del aviso dirigido | `core/mis_avisos.py` + `test_circulo_cerrado.py` |
| Servidor MCP de sólo lectura | `backend/mcp_server.py` + `backend/MCP.md` |
| Buscador global, prioridades, superficie mobile por oficio | `core/buscador.py`, `core/priorities.py`, `core/avisos_oficio.py` |
| Forecast determinista de demanda | `core/forecast.py` |

## A medias

| Cosa | Qué falta |
|---|---|
| **El camino del pasillo 4 en el grafo** | El caso vive en `deposito.explicaciones()`. `grafo.caminos()` sólo resuelve los 6 cruces de `cruces.py` más `cliente_frio` y `ventana_compra`. **El mejor ejemplo que tenemos es el único que el cerebro no puede encender** |
| Animación del camino | Hay partículas direccionales (`linkDirectionalParticles`) y encuadre automático. No hay secuencia por etapas ni dos caminos convergiendo |
| Contradicción entre canales | Los datos están (Campo Alegre: cuatro relatos por cuatro canales). No hay motor que la detecte ni superficie que la muestre |
| Devoluciones y reclamos | Diseñado entero en `design/mobile/01-DEVOLUCIONES-Y-RECLAMOS.md`, con la pieza de conocimiento concreta escrita. Falta un valor en `EFECTOS` (`exige_evidencia`) y la superficie. **No está construido** |
| Conocimiento en riesgo | Los efectos y el contador están. **Las 22 piezas tienen `origen.quien = "aldo"`**; no hay conocimiento distribuido que apagar |

## No existe

- Funcionamiento sin conexión. **Re-verificado hoy contra el repo:** no hay
  service worker, ni manifest, ni IndexedDB, ni workbox en `frontend/`. El
  documento tiene razón y la corrección sigue siendo obligatoria.
- Evals presentables (ver 3b).
- Eje temporal en el grafo.
- Pantalla "Cómo lo supe".
- Contrafáctico interactivo.
- CLI, SDK, MCP de escritura.
- Modelos probabilísticos de predicción. Confirmado: lo único que hay es
  `core/forecast.py`, determinista.
- Cruce con datos macro de la economía como motor. Existe `core/macro.py` con
  indicadores oficiales (tipo de cambio, IPC) con fuente y fecha, usado para
  deflactar en `core/evolucion.py` — que es otra cosa y es la correcta.
