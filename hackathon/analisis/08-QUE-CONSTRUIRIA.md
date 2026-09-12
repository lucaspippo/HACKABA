# Qué construiría, en qué orden, y cuánto lleva

Ordenado por lo que gana la hackathon, no por lo que completa el producto — como
pediste.

Hay dos planes porque hay dos cronogramas posibles y no se puede decidir sin
confirmar cuál rige (ver `00-LEEME-PRIMERO.md`, §1).

---

# Antes de construir nada — 30 minutos

Cuatro cosas, en este orden, y ninguna es código.

1. **Entrar a la zona de participantes y confirmar por escrito:** horario real,
   mecánica de asignación de track, **el texto exacto de la regla de código**, si
   se pueden consumir servicios propios preexistentes, y si hay rubric publicado.
   Sin esto, la mitad de las decisiones de abajo son a ciegas.
2. **Decidir la política de repo** con esa información (`07-MUDANZA-DEL-REPO.md`).
   Mi recomendación: repo nuevo vacío, sólo lo de la hackathon adentro, PolPilot
   declarado aparte.
3. **Sacar del pitch, de las slides y de cualquier pantalla:** el funcionamiento
   sin conexión (no existe, re-verificado hoy) y la frase de las siete reglas de
   Ramón (falso: las 22 piezas son de `aldo`). Sustituto verdadero y mejor: el
   punto ciego por persona, `06-DISRUPTIVO.md` §3.
4. **Sacar un token de MCP** y probar el conector desde un cliente real. TTL 12
   horas, así que hay que sacarlo el mismo día que se usa.

---

# Plan A — si rige el cronograma del sitio (24 horas, entrega mañana 16:00)

Ésta es la versión que creo que va a regir. Son aproximadamente **19 horas de
hackeo** contando la noche, para un equipo de hasta cuatro personas. La regla
número uno acá es la que ya está escrita en el documento de trabajo: **apilar
cosas a medio terminar se lee como inconcluso.**

## Bloque 1 — Sin esto no hay demo · **~5 horas**

| # | Qué | Costo | Por qué primero |
|---|---|---|---|
| 1 | **El pasillo 4 como séptimo cruce de `cruces.py`**, con el shape estándar, para que `grafo.caminos()` lo resuelva | 3 h | **El mejor ejemplo que tenemos es el único que el cerebro no puede encender hoy.** Sin esto el momento 1 no existe |
| 2 | **Modo presentación del grafo**: tipografía ×2,2, aristas ×2,5, y sobre todo **recortar el lienzo al camino + 2 saltos** (20–40 nodos en vez de 570) | 2 h | Proyectado, hoy son manchas de color. El recorte es un filtro sobre `graphData`, no un cambio de dibujo |

Con estas dos, el momento 1 del guion funciona y se ve desde el fondo de la sala.

## Bloque 2 — Lo que nos separa · **~5 horas**

| # | Qué | Costo | Prueba |
|---|---|---|---|
| 3 | **El camino como secuencia animada** de cuatro etapas, 4 segundos (`04`, §3.2). El dato ya existe en `caminos().semillas` | 4 h | Que hay un recorrido, no un resultado |
| 4 | **Determinismo demostrado**: misma consulta dos veces, números idénticos, y qué sí varía | 1 h | Que el número no lo pone el modelo |

## Bloque 3 — El golpe · **~4 horas**

| # | Qué | Costo | Prueba |
|---|---|---|---|
| 5 | **El contrafáctico**: el jurado quita un dato y el cruce se rompe en vivo. Parámetro de exclusión, sin borrar nada de la base | 4 h | Causalidad, en cinco segundos |

## Bloque 4 — Si sobra tiempo, **de a uno y terminado** · **4 h cada uno**

En este orden:

| # | Qué | Por qué en este orden |
|---|---|---|
| 6 | **Punto ciego por persona** (`06` §3) | Es el ángulo con el que ganaron los dos premios grandes de la hackathon de GitLab, y funciona con datos reales de hoy |
| 7 | **Glifos de canal en las notas** + borde discontinuo para lo que entra de afuera (`04` §3.1) | Hace visible la tesis: qué lo dijo una persona y por qué canal |
| 8 | **Panel de evals con tasa de abstención** | Nadie más va a medir nada. Pero es lo primero que se cae si queda a medias |

## Lo que NO haría en 24 horas

- **La entrada en vivo (momento 2 del guion).** Requiere abrir escritura en
  `core/notas.py`, conectar `piso.reportar` al grafo, invalidar cache y refrescar
  la vista. Es una jornada bien hecha y **es el punto donde más fácil se rompe en
  vivo**. Con la voz ya construida (`core/voz.py`) se puede mostrar el camino
  audio → propuesta estructurada, que es la mitad del efecto con un décimo del
  riesgo.
- **El eje temporal del grafo.** Una jornada. Es lo que más rinde de todo el
  documento y **no entra**.
- **Devoluciones y reclamos.** Diseñado entero, construido nada. Una jornada
  larga.
- **El costo de no saber.** Es la idea con más chance de producir un número
  inflado bajo presión.
- **La entrada adversarial abierta.** Hacerla ensayada por nosotros, sí. Invitar
  al jurado a romperlo, no: en un producto de 65.000 líneas con un LLM adentro
  hay un camino donde afirma de más, y encontrarlo en vivo cuesta más de lo que
  gana.

## Reparto para cuatro personas

- **Una en el backend:** items 1 y 5 (el cruce y el contrafáctico). Es el camino
  crítico y el que más conoce `cruces.py` tiene que estar acá.
- **Una en el grafo:** items 2 y 3. Es trabajo de canvas, aislado, no bloquea.
- **Una en el guion y el ensayo:** el demo escrito y cronometrado **antes** de
  que termine de construirse, la prueba de los tres minutos con alguien de
  afuera, el video de respaldo, y el token de MCP probado. Esto no es trabajo de
  relleno: es lo que más peso tiene en la nota y es lo que siempre se deja para
  las dos de la mañana.
- **Una flotante:** item 4, después 6, después 7. Y el arreglo del bug de "Tu
  trabajo" repitiendo el mismo archivo cuatro veces, que es barato y es lo
  primero que ve alguien que abre el producto.

---

# Plan B — si de verdad hay varios días

Entonces el orden cambia, porque entra lo caro.

| Orden | Qué | Costo | Por qué en ese lugar |
|---|---|---|---|
| 1 | Todo el Bloque 1 y 2 del Plan A | 10 h | Es la base |
| 2 | **El eje del tiempo en el grafo** (`04` §3.5): control de 32 días, las notas apareciendo en su fecha, **el cruce que no existía ayer** | 1 j | **Es lo que más rinde de todo el documento.** Es literalmente el proyecto que ganó el Grand Prize de Anthropic en GitLab, aplicado a una PyME |
| 3 | El contrafáctico | ½ j | |
| 4 | **La transformación visible** (`04` §3.3): la nota que se abre en dos mitades, lo que alguien dijo contra lo que el sistema entendió | ½ j | Es la tesis, y hoy es invisible |
| 5 | Punto ciego por persona | ½ j | El golpe del cierre |
| 6 | **La entrada en vivo**, bien hecha: escritura en `notas`, puente desde `piso.reportar`, invalidación, refresco | 1 j | Con tiempo para probarla, deja de ser un riesgo y pasa a ser el momento más impactante |
| 7 | Panel de evals con tasa de abstención | ½ j | |
| 8 | Contradicción entre canales (Campo Alegre) | ½ j | |
| 9 | Regla aprendida incumplida (la gaseosa) | ½ j | |
| 10 | Línea de tiempo del conocimiento | ½ j | Casi gratis si ya está el punto 2 |
| 11 | "¿Por qué?" recursivo | ½ j | |
| 12 | Glifos de canal | 3 h | |

**Total del plan B: entre seis y siete jornadas.**

---

# La decisión que me parece más importante de todas

Si tuviera que quedarme con una sola cosa de todo este análisis, es ésta:

**El grafo no gana por ser bonito. Gana por ser el único lugar donde se puede ver
que el sistema piensa, y hoy le faltan tres cosas chicas para que eso se vea:**

1. que el mejor ejemplo tenga camino (3 horas),
2. que el camino sea una secuencia y no un conjunto (4 horas),
3. que se pueda leer desde el fondo de la sala (2 horas).

**Nueve horas.** Todo lo demás de este documento es mejora sobre esa base. Nada
de lo demás la reemplaza.

---

# Lo que hay que decir, y lo que no

Una última pasada sobre el guion, con lo verificado:

| Se puede decir | No se puede decir |
|---|---|
| "Cualquier LLM puede consultar este negocio por MCP, con el login del usuario y los permisos de su rol" | "Tenemos API, MCP y CLI abiertos" — no hay CLI, y el MCP es de sólo lectura |
| "Toda cantidad se valida contra código, nunca contra el modelo. Está escrito como invariante en el repositorio" | "Tenemos evals" — son tests. Media jornada de distancia |
| "Hay una función que a propósito no tiene campo total, porque dos indicadores comparten clientes" | "El sistema aprende de cada corrección" sin aclarar que la memoria de reglas hoy tiene un solo autor |
| "Si Walter se toma vacaciones, la empresa deja de saber qué pasa en dos de sus clientes" | "Si Ramón se va se pierden siete reglas" — falso contra el dataset |
| "Está diseñado y es lo próximo que construimos" (offline) | "Funciona sin conexión" |
| "El grafo declara qué es dato crudo y qué calculó él, con el umbral" | "El grafo muestra la evolución en el tiempo" — hoy es una foto |
| "Producto funcionando, un piloto no pago, cero clientes pagos" | cualquier otra cosa sobre clientes |

**Y la regla que las cubre a todas, que ya está en el documento de trabajo y es
la correcta: todo lo que el jurado no pueda verificar en la sala, mejor no
prometerlo.**
