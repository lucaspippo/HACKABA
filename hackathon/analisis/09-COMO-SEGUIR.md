# Cómo seguir

11 de septiembre de 2026 · versión 3 del plan. Reemplaza al documento de trabajo
(ver §6).

---

# 0. Tu pregunta: ¿hace falta portar el pasillo 4?

**No. Ahorrate esas tres horas, y te explico por qué es mejor de lo que pensabas.**

Fui a verificar si el ejemplo de la oferta ya vive en el grafo, y encontré algo
que no sabíamos: **la card ya está construida.** `_card_sobrecompra` en
`backend/core/oportunidades_neg.py:1096`, id `sobrecompra`. Su propio docstring
dice:

> *"el error más caro del rubro: entrar a una oferta del proveedor sin mirar la
> rotación. El descuento es real; el problema es la cantidad… El resto no es
> stock: es mercadería que vas a tirar con 18% de descuento."*

Corrí su cálculo a mano contra el dataset, con el `hoy` congelado del demo
(2026-07-07). **Los números:**

| | |
|---|---|
| Producto | SALAME MILAN LA RIBERA (PLANCHA), cód. 1282, Frigorífico La Ribera |
| La oferta | 689 kg · **18% de descuento** · la oferta vence el **17/07** · el lote vence el **15/10** |
| Rotación real | **524,2 kg en 12 meses** = 1,44 kg/día (sobre 10.776 filas de venta) |
| Vida del lote | **100 días** desde hoy |
| Stock actual | 54,8 kg |
| Lo que podés absorber | **88,8 kg** |
| **Sobrante** | **600,2 kg** |
| **Plata que tirás** | **$5.038.657** |
| **Ahorro real del descuento** | **$163.675** |

**El descuento te ahorra $163 mil y te hace tirar $5 millones. Treinta y una
veces más.** Ése es el titular, y sale de una resta, no de un modelo.

## Lo que falta, y cuánto cuesta

`sobrecompra` **no tiene camino en el grafo**, por la misma razón que el pasillo
4: `CARDS_QUE_CRUZAN` (`grafo.py:614`) sólo tiene `cliente_frio` y
`ventana_compra`. Pero acá el arreglo es mucho más barato, porque su `datos` ya
trae `producto` y `proveedor` como strings, que es exactamente lo que
`grafo.caminos()` resuelve como semilla.

**Tres opciones, y recomiendo la B:**

| | Qué | Costo | Qué te da |
|---|---|---|---|
| **A** | Agregar `"sobrecompra"` a `CARDS_QUE_CRUZAN` | **15 min** | Camino en el grafo. **Pero sin notas**: las semillas serían producto y proveedor, no gente |
| **B** ✅ | **Un cruce nuevo en `cruces.py`** que junta la oferta con las notas de la cámara, citando el cálculo de `_card_sobrecompra` sin recalcularlo | **2 h** | 4 dominios, `no_estructurado=True`, **las notas como semilla** → el camino enciende post-its con nombre y canal |
| **C** | Portar el pasillo 4 | 3 h | El ejemplo viejo |

**B es el que queremos** y la razón es la tesis: si el camino no enciende una
nota de una persona, estamos mostrando un buen cálculo de ERP. Con las notas
adentro, estamos mostrando lo que nadie más tiene.

**Regla dura al construirlo:** el cruce nuevo **no recalcula un solo número**.
Llama a `oportunidades_neg` y cita. Es The Counting Rule y es la clase de cosa
que se rompe a las 3 de la mañana.

## Y una corrección de honestidad sobre mi propio ejemplo

En `05-EJEMPLOS.md` conté la oferta rechazada como "cinco fuentes". Verifiqué
fila por fila y **una de las cinco es una inferencia mía, no un dato**:

- ✅ La oferta, la rotación, la vida del lote y el stock: **están**, y son los
  números de arriba.
- ✅ La Cámara de frío 2 tiene **41 lotes**, y tres personas dijeron por tres
  canales distintos que no entra más nada (Ramón por voz el 29/06 y por WhatsApp
  el 02/07, Nahuel por voz el 01/07, Tomás con **foto** el 06/07).
- ✅ `em03`, Celeste, email, 04/07: **La Ribera confirmó una orden de fiambres
  para el 9** y pidió que le avisemos si no hay lugar en cámara. Mismo proveedor
  que la oferta.
- ❌ **Que el pallet de la oferta iría a la Cámara de frío 2 no está en los
  datos.** El código 1282 no tiene fila en el export del depósito (hay 380
  códigos con ubicación sobre 430 del catálogo). Es un fiambre de balanza y en
  esa cámara hay otros tres salames milán, así que es razonable — **pero es una
  inferencia y no se dice como dato.**

**Cómo se cuenta sin mentir:** *"El mismo proveedor ya tiene una orden de
fiambres llegando el 9 a una cámara que tres personas dicen que está llena, y él
mismo pidió que le avisemos."* Eso es todo verdad y pega igual.

---

# 1. Qué construir, en qué orden

Horas por ítem. **La línea de corte está marcada.** Todo lo que está debajo no
entra en una noche, y meterlo a medias baja la nota más de lo que sube.

## Bloque 1 — Los evals, primero · **4 h**

Va primero porque vos lo pediste y porque tenés razón: es el único de los cuatro
diferenciadores de Lightfield que nos falta y que podemos tener hoy.

**Qué se construye:** `backend/scripts/evals.py`, que corre los conjuntos que ya
existen y emite un JSON con métricas; y una pantalla que lo lee.

**Las cinco métricas, todas sobre conjuntos que ya corren:**

| Métrica | De dónde sale | Por qué importa |
|---|---|---|
| **Cobertura de la matriz** | `test_matriz_consultas.py` genera la matriz completa fuente × métrica × agrupación × filtro con categorías reales. Celdas válidas que devuelven una serie sana / total | Es el eje "¿contesta bien?" |
| **Tasa de abstención correcta** | La misma matriz: combinaciones que **por diseño no existen** y devuelven su error honesto / total de inválidas. **Eso ya es un PASS en el test de hoy** | **Ésta es la métrica que nadie más va a tener.** Es "¿sabe cuándo no sabe?" puesto en número |
| **Batería de lenguaje natural** | `test_bateria_nl.py`: 24 frases (12 ES + 12 EN) por la misma ruta que usa el modelo. Resueltas en ≤2 pasos de herramienta / 24 | Es el eje "¿entiende cómo pregunta un dueño?" |
| **Cruces sobre casos conocidos** | Hay que escribir el conjunto etiquetado: los 6 cruces de `cruces.py` + `sobrecompra` + `ventana_compra` + `cliente_frio`. Detectados / esperados, y falsos positivos | Es el eje "¿el motor acierta?" |
| **Determinismo** | Correr la misma consulta N veces y comparar byte a byte | Es el eje "¿da lo mismo siempre?" |

**Las tres reglas de honestidad, y no son negociables:**

1. **El panel lee un JSON de una corrida real.** Ningún número escrito a mano.
2. **Cada métrica dice el tamaño del conjunto**, al lado del porcentaje. "24 de
   24 frases" y no "100%". Un jurado que ve un 100% pelado piensa que es
   decorativo; uno que ve "24 de 24" sabe que alguien contó.
3. **El panel muestra la fecha y hora de la última corrida.** Si no corrió hoy,
   lo dice.

**Desglose:** 1 h el script que corre y emite; 1 h el conjunto etiquetado de
cruces; 1,5 h la pantalla; 0,5 h la corrida y la revisión de que los números no
sean vergonzosos. **Si algún número sale mal, se muestra igual** — un eval que
sólo se enseña cuando da bien no es un eval.

## Bloque 2 — Sin esto no hay demo · **5 h**

| # | Qué | Horas |
|---|---|---|
| 2.1 | **El cruce de la oferta** (opción B de §0): oferta × rotación × vida del lote × notas de la cámara. Cita, no recalcula | **2 h** |
| 2.2 | **Modo presentación del grafo**: tipografía ×2,2, aristas ×2,5, y sobre todo **recortar el lienzo al camino + 2 saltos** — 20 a 40 nodos en vez de ~570 | **2 h** |
| 2.3 | **Agregar `"sobrecompra"` a `CARDS_QUE_CRUZAN`** como respaldo, por si 2.1 no sale | **15 min** |
| 2.4 | Arreglar el bug de "Tu trabajo" repitiendo el mismo archivo cuatro veces | **45 min** |

El recorte del lienzo (2.2) es un filtro sobre `graphData`, no un cambio de
dibujo. Es lo más barato y lo que más cambia lo que se ve desde el fondo de la
sala.

## Bloque 3 — El camino como secuencia · **4 h**

La animación de cuatro etapas (`04-GRAFO...`, §3.2), cronometrada en cuatro
segundos: semillas una por una con el texto de la nota, después las ramas, después
la convergencia, después los dominios cruzados.

El dato ya existe: `caminos()` devuelve `semillas`, `nodos` y `aristas`. **No hay
que calcular nada nuevo, hay que temporizar el dibujo.**

## Bloque 4 — El conocimiento en riesgo, versión notas · **3 h**

La versión que es verdad: **13 autores, 10 entidades con una sola fuente
humana.**

| Entidad | Su única fuente |
|---|---|
| Almacén San Martín · Autoservicio 9 de Julio | **Walter** |
| Rotisería Avenida · Supermercado El Puente | **Osmar** |
| Proveeduría La Rural | **Diego** |
| Distrib. Mayorista Guaraní · Golosinas Costa Dulce | **Celeste** |
| Yogur Bebible Tierra Roja | **Vanesa** |
| Jamón Cocido El Paraná | **Tomás** |
| Gaseosa Cola La Ribera | **Norma** |

Y lo que sí está cubierto: Cámara de frío 2 (Ramón, Nahuel, Tomás), Campo Alegre
(cuatro personas), Pasillo 4 (Kevin, Nahuel).

**Qué se escribe:** una función de ~20 líneas sobre `notas.listar()` que cuenta
autores por entidad, un campo por nodo, y un modo de color en el lienzo con un
selector de persona. **Apagás a Walter y se apagan dos clientes.**

**Horas:** 1 h el cálculo, 2 h el modo de color y el selector.

## Bloque 5 — El contrafáctico · **4 h**

Un parámetro de exclusión (`sin_notas=[ids]`) que viaje por `cruces.cards()` y
`grafo.completo()`, y un botón "quitar este dato" al lado de cada evidencia.
**No se borra nada de la base** — un botón que borre datos en vivo delante de un
jurado es mala idea por razones obvias.

## Bloque 6 — Determinismo demostrado · **1 h**

La misma consulta dos veces, números idénticos, y mostrar qué **sí** varía (la
redacción) y qué **nunca** varía (la cifra). Se hace junto con el MCP (§5) y sale
casi gratis.

---

## ✂️ LA LÍNEA DE CORTE

**Arriba: 21 horas de trabajo.** Con cuatro personas y reparto paralelo entra en
una noche con margen para ensayar. **Con dos personas, se corta el Bloque 5.**

Todo lo de abajo **no entra**, y quiero que quede escrito para que no se discuta
a las 4 de la mañana:

| Qué | Costo real | Por qué no |
|---|---|---|
| **La entrada en vivo (voz → nodo nuevo en el grafo)** | 1 jornada | Requiere abrir escritura en `core/notas.py`, puentear `piso.reportar`, invalidar cache y refrescar. **Es el punto donde más fácil se rompe delante del jurado.** Sustituto: mostrar el camino audio → propuesta estructurada con `core/voz.py`, que ya existe — mitad del efecto, décimo del riesgo |
| **El eje temporal del grafo** | 1 jornada | Es lo que más rinde de todo el análisis y **no entra**. Duele y es así |
| **La transformación visible** (la nota que se abre en dos mitades) | ½ jornada | Es la tesis y es lo primero que construiría si aparecieran seis horas más |
| **Devoluciones y reclamos** | 1 jornada larga | Diseñado entero, construido nada |
| **Contradicción entre canales** | ½ jornada | Los datos están (Campo Alegre). Queda para después |
| **Glifos de canal en las notas** | 3 h | Lo primero que agregaría si sobran 3 h |
| **El costo de no saber** | ½ jornada | La idea con más chance de producir un número inflado bajo presión |
| **"¿Por qué?" recursivo** | ½ jornada | |

## Reparto para cuatro

- **Backend A:** Bloque 1 (evals, 4 h) → Bloque 5 (contrafáctico, 4 h).
- **Backend B:** Bloque 2.1 y 2.3 (el cruce de la oferta, 2,25 h) → Bloque 4
  cálculo (1 h) → apoyo.
- **Frontend:** Bloque 2.2 (modo presentación, 2 h) → Bloque 3 (animación, 4 h) →
  Bloque 4 superficie (2 h).
- **Guion y ensayo:** el demo escrito y cronometrado **antes** de que termine de
  construirse, la prueba de los tres minutos con alguien de afuera, el video de
  respaldo, el token de MCP sacado y probado, y el arreglo del bug 2.4. **Esto no
  es relleno: es lo que más pesa en la nota y es lo que siempre se deja para las
  dos de la mañana.**

---

# 2. Qué tomar de Lightfield

Analicé su arquitectura publicada. Lo ordeno como pediste: adoptable ahora, caro
pero interesante, y no aplica.

## 2.1 · Cómo representan la evolución en el tiempo, y qué copiar

**Lo que ellos declaran** (documentación, fuente primaria): el grafo de contexto
captura *"tanto el estado actual de los objetos como la historia de **cómo,
cuándo y por qué** cambiaron"*. El post de a16z lo llama *"un grafo de contexto
temporal que captura **el porqué** detrás de cada negocio"*.

**El patrón real, despojado del marketing:** el eje del tiempo no es sobre el
estado del mundo. Es sobre **el acto de aprender**. Guardan cuándo el sistema se
enteró de algo y por qué. Un campo no es "vale X"; es "vale X desde que esta
llamada del martes lo dijo".

**Y acá está la parte que nos sirve: eso nosotros ya lo tenemos, y no lo estamos
mostrando.**

- Cada nota tiene `autor`, `fecha` y `canal`.
- Cada pieza de conocimiento tiene `origen: {quien, cuando}` y `veces_aplicada`.
- Cada campo de documento tiene `valor` / `fuente` / `estado`, con la regla
  escrita de que la fuente **nunca** puede ser "el sistema".
- El log de auditoría tiene `actor`, `accion`, `antes`, `despues`, `cuando`.

**Lo que no tenemos es el eje puesto en pantalla.** Lo caro no es el dato: es la
superficie.

**Qué adoptar ahora, en horas: la versión honesta y barata del eje temporal.**
No versionar el grafo entero —eso es una pieza de días y el dataset no tiene con
qué llenarla, sería un eje temporal falso—. Sí: **un control deslizante de 32
días sobre el aprendizaje**. Las notas aparecen en su fecha, las piezas de
conocimiento se prenden en su `origen.cuando`, y los cruces aparecen el día en
que sus dos notas ya existen. El remate es una sola frase:

> **"Este cruce no existía ayer."**

El cruce del pasillo 4 no existe el 5 de julio y existe el 6, porque ese día
Nahuel mandó el suyo. Eso es verificable y es exactamente lo que ganó el Grand
Prize de Anthropic en la hackathon de GitLab (*graphdev*: mapea relaciones y
muestra cómo el sistema cambia en el tiempo).

**Pero son 8 horas y están debajo de la línea de corte.** Lo digo igual porque
es lo primero de la lista de "la semana que viene", y porque conviene decir en el
pitch que es lo próximo: *"guardamos cuándo y de quién aprendimos cada cosa;
ponerlo en un eje es lo que sigue."* Eso se puede decir sin mentir, porque el
dato está.

## 2.2 · Cómo estructuran lo no estructurado, y qué copiar

**Lo que ellos declaran:** capturan mails y transcripciones **como datos no
estructurados**, y esos datos quedan **dentro del mismo grafo** junto a los
estructurados. Los agentes *"razonan sobre los dos juntos **y escriben de
vuelta**"*: actualizan campos y crean registros.

**Lo que NO publican, y busqué:** qué campos extraen exactamente, el algoritmo de
resolución de entidades, y qué hacen cuando hay ambigüedad. No está en el sitio,
ni en la documentación, ni en la prensa.

**Los tres patrones, separados:**

**(a) Lo no estructurado vive en el mismo grafo, no en un almacén aparte.**
**Ya lo tenemos.** El nodo `nota` es un tipo de primera clase, con forma propia
(post-it con esquina doblada), color propio (el amarillo que el código comenta
como *"lo único acá que no salió de una tabla"*) y arista propia (`menciona`).
Un camino puede ir de un cliente a lo que el repartidor vio en la calle. **No hay
nada que adoptar: hay que contarlo mejor.**

**(b) La resolución de entidades.** Ellos la hacen automática y no cuentan cómo.
Nosotros hacemos lo contrario a propósito y está escrito en `notas.py`: *"las
entidades NO se adivinan con NLP: cada nota declara a qué se refiere"*, porque el
reporte del piso ya pide producto y motivo.

**Eso no es una carencia nuestra, es una postura, y hay que decirla como tal:**

> "Ellos infieren a qué se refiere un mail. Nosotros se lo preguntamos a la
> persona en el momento, con un formulario de un toque. Lo que infiere un modelo
> después no lo podés auditar; lo que declaró la persona sí."

**Cuidado con una tentación concreta:** en la demo, el panel de "la nota que se
convierte en dato" muestra la estructura **que el formulario ya capturó**. No se
puede decir "el sistema leyó el audio y sacó esto" salvo que se entre por
`core/voz.py`, que es donde sí ocurre de verdad. Si se quiere esa frase, la demo
tiene que pasar por la voz.

**(c) ⭐ El "escriben de vuelta" — esto sí vale adoptarlo, y es barato.**

Éste es el patrón suyo que más me interesa y el que menos estamos aprovechando.
Su arco completo es: interacción no estructurada → grafo → el agente razona →
**escribe de vuelta al registro**. En su caso lo escribe el agente solo.

**Nosotros tenemos el mismo arco, pero pasa por una persona** — `piso.reportar`
→ propuesta → aprobación → dato modificado → `audit` → y el resultado vuelve al
que lo originó (`core/mis_avisos.py`, el círculo cerrado).

Y **ya está construida la banda que lo muestra**: `mapa_operacion.vuelve_al_sistema()`
lee el log de auditoría y arma los chips de qué se escribió de vuelta en los
últimos 30 días. Con una honestidad que conviene señalar en voz alta, porque está
en el docstring:

> *"Si esto está vacío el círculo NO se cierra, y el mapa tiene que decirlo. Un
> tilde verde fijo sería decoración — y la primera pregunta de «¿esto actualizó
> de verdad?» no tendría respuesta."*

**Qué adoptar, en 30 minutos: decirlo.** El arco ya existe y ya se muestra; lo
que falta es la frase que lo nombra:

> "Lightfield deja que el agente escriba de vuelta al registro. Nosotros
> escribimos de vuelta también — pero la firma la pone una persona, y queda en el
> log con nombre y hora. En una PyME donde el dueño responde con su patrimonio,
> ésa no es una limitación: es el requisito."

## 2.3 · El cuadro completo

### Adoptable en las horas que tenemos

| Patrón | Costo | Qué es |
|---|---|---|
| **Declarar la arquitectura públicamente, con nombre** | 0 | Ellos publican sus cuatro diferenciadores. Nosotros tenemos equivalentes y no los contamos: el motor de cruces, la procedencia por campo, la validación de cantidades contra código, la memoria de reglas con su fuente, el MCP de sólo lectura |
| **Evals como parte del producto, no como prueba interna** | 4 h | Bloque 1 |
| **El arco de "escribir de vuelta", nombrado** | 30 min | §2.2(c). Ya construido, sin contar |
| **El encuadre de "sistema de registro para la era de los agentes"** | 0 | La frase de Rampell es el mejor marco que hay para explicar por qué existe la oportunidad ahora |
| **Enseñar el MCP en vivo** | 1 h de preparación | §5 |

### Interesante pero caro

| Patrón | Costo | Comentario |
|---|---|---|
| **Eje temporal del grafo** | 1 jornada | Lo que más rinde. Debajo de la línea de corte, primero de la lista que sigue |
| **Modelo de datos que se arma solo desde el canal** | Semanas | Es el corazón de su producto. Nuestro esquema es fijo |
| **MCP de escritura** | 1–2 jornadas | Hay un plan escrito en `backend/MCP.md`: propose→apply, `destructiveHint`, elicitation, token revocable propio, auditoría con actor distinguible, límites de tasa. No para una hackathon |
| **CLI** | 2–4 h | Barato, pero no mueve la aguja de un jurado. Después |
| **SDK por lenguaje** | 2–3 jornadas cada uno | No |

### No aplica a nuestro caso

| Patrón | Por qué no |
|---|---|
| **Sandbox de código para el agente** | Ellos lo necesitan porque **el agente escribe el código que calcula**. Nosotros no, porque **el modelo nunca calcula**: el cálculo ya está escrito, revisado y testeado en `core/`. Son dos soluciones al mismo problema; la nuestra es más rígida y más barata de verificar. **Esto se puede decir en la sala y es una buena respuesta** |
| **Migración asistida y sync en dos vías** | Ellos reemplazan a Salesforce. Nosotros nos montamos encima del ERP a propósito: nadie cambia el sistema donde factura |
| **Ingesta de mail / calendario / Slack / LinkedIn** | Son canales que **ya son datos digitales**. Nuestro problema es el opuesto y más difícil: el dato no existe hasta que alguien lo dice. Por eso todo nuestro producto está armado alrededor de la voz, la foto y la gente sin escritorio |
| **Llamarnos "el Lightfield de LatAm"** | Nos convierte en la copia regional de algo que ya tiene 47 millones |

---

# 3. El guion del demo, minuto a minuto

Cuatro minutos. El orden final de los ejemplos cambió respecto del documento
viejo: **la oferta rechazada pasa al centro.**

## La regla de la apertura, que no cambia

Nadie en esa sala sintió nunca una diferencia de stock en una distribuidora.
**Nada de "remito", "lote", "conciliación" ni "ERP" en los primeros noventa
segundos.** El nicho no cambia; lo que tiene que ser universal es el sentimiento.

## El guion

| Tiempo | Qué | Qué se dice |
|---|---|---|
| **0:00–0:20** | **El problema universal** | "En toda empresa hay información que existe y no llega. Alguien la sabe, alguien la dijo, y la decisión igual se toma sin ella. Nosotros la juntamos. Se lo mostramos en una distribuidora porque ahí se ve la plata." |
| **0:20–0:40** | **La distinción que les enseñamos** | "Una **alerta** mira UNA fuente y avisa un umbral. Cualquier ERP con un chat encima lo hace, y por eso no prueba nada. Un **cruce** junta fuentes que no se hablan entre sí y encadena una consecuencia que nadie tenía a la vista." **Decirla tal cual y temprano: a partir de ahí el jurado tiene un criterio nuevo para juzgar a todos los demás equipos — y todos los demás van a estar mostrando alertas.** |
| **0:40–1:40** | **⭐ La oferta que hay que rechazar** — el aha | En pantalla: la card. "El proveedor te ofrece un pallet de salame con **18% de descuento**. La oferta vence el 17. Parece una buena compra." Pausa. "El sistema dice que no." Se enciende el camino en el grafo. "Vendés 1,44 kg por día. El lote vence en 100 días. Podés absorber 88 kilos. La oferta son 689." Y el remate: **"El descuento te ahorra $163.675 y te hace tirar $5.038.657."** Y después la parte que no es cálculo: "Y además, el mismo proveedor ya tiene una orden de fiambres llegando el 9, a una cámara que **tres personas dijeron por tres canales distintos que está llena** — uno con una foto. Él mismo pidió que le avisemos si no hay lugar." |
| **1:40–2:20** | **El contrafáctico** | "Sáquenle un dato." El jurado quita la nota de Ramón. El camino se apaga, el hallazgo pierde una pata. Se devuelve y vuelve. **"Un chatbot no se rompe cuando le sacás un dato. Sigue contestando igual de seguro."** Acá va la frase de qué es determinístico y qué usa el modelo. |
| **2:20–2:50** | **El MCP y el determinismo, juntos** | Ver §5. Dos ventanas, la misma pregunta, el mismo número. Y el gesto de los permisos. |
| **2:50–3:30** | **El conocimiento en riesgo** — el golpe | Los nodos coloreados por cuántas fuentes humanas tienen. Se apaga a Walter. **"Si Walter se toma vacaciones, esta empresa deja de saber qué pasa en dos de sus clientes. No porque no tenga los datos: los datos siguen ahí. Deja de saber lo que no está en ningún dato."** |
| **3:30–3:50** | **Los evals** | El panel. "Medimos esto: 24 de 24 frases, N de N celdas, y —la que más nos importa— cuántas veces el sistema dijo *no sé* y tenía razón." |
| **3:50–4:00** | **Cierre** | "Todos muestran una salida. Nosotros mostramos el camino. Todos muestran que funciona; nosotros mostramos qué pasa si sacás una pieza. Todos hablan con confianza; nosotros declaramos cuándo no sabemos." |

## Los ejemplos de reserva, si preguntan

De a uno, veinte segundos cada uno, todos verificables:

1. **El pasillo 4.** El ERP dice que faltan 6,5 unidades de leche, $53.646. No
   faltan: Kevin las buscó y estaban en otro rack, Nahuel corrió las cajas. **El
   mismo día, por canales distintos.** (Está construido en
   `deposito.explicaciones()`; no tiene camino en el grafo — si se muestra, se
   muestra como card, no como grafo.)
2. **Doña Elsa.** El listado de morosos dice que la intimes. La regla de la casa
   dice 45 días porque es cliente desde 2011. El repartidor la vio abierta y
   trabajando el viernes. Ella misma pidió una entrega chica para no seguir
   sumando. **El sistema te dice que no la intimes todavía, y te dice por qué.**
3. **El reclamo de Campo Alegre.** Cuatro personas, cuatro canales, cinco días, un
   solo hecho. Y **dos de ellas se contradicen**: Ramón dice que lo trajeron al
   otro día, Brian que viene la semana que viene. El sistema marca la
   contradicción en vez de elegir.
4. **La gaseosa.** La regla más aplicada de la casa (9 veces) dice que ese
   producto nunca puede quebrar. Quebró en la Sucursal Norte el sábado que más se
   vende. Hay 282 unidades en el depósito central: **no falta mercadería, falta
   que baje.**
5. **El yogur.** El lote vence en 7 días. El proveedor tarda 9 en traer más. **El
   reemplazo llega después del quiebre, hagas lo que hagas — salvo que pidas
   hoy.**

## Tres cosas que no hay que hacer

- **Nunca empezar por el equipo, los premios o la arquitectura.**
- **No apilar.** Si el Bloque 5 no salió, el guion es de tres minutos y está
  mejor así.
- **No invitar al jurado a romper el sistema con la entrada adversarial.** Hacer
  nosotros los dos intentos, ensayados. En un producto de 65.000 líneas con un
  LLM adentro hay un camino donde afirma de más, y encontrarlo en vivo cuesta
  más de lo que gana.

---

# 4. Qué NO vamos a poder mostrar, y cómo se contesta

Guion de respuestas. La regla que las cubre a todas: **todo lo que el jurado no
pueda verificar en la sala, mejor no prometerlo.**

| Si preguntan | Se contesta | Lo que NO se dice |
|---|---|---|
| **"¿Funciona sin conexión?"** | "Está diseñado y es lo próximo que construimos." | "Sí." No hay service worker, ni manifest, ni IndexedDB, ni workbox. **Re-verificado hoy contra el repo.** |
| **"¿El grafo muestra la evolución en el tiempo?"** | "Hoy es una foto del estado actual. Guardamos cuándo y de quién aprendimos cada cosa —cada nota tiene autor, fecha y canal; cada regla tiene quién la enseñó y cuándo— así que el eje del tiempo es lo próximo. No está construido." | "Sí, es un grafo temporal." |
| **"¿Esto se llenó solo?"** | "Los canales de entrada están construidos: voz, foto, formulario del piso, WhatsApp. Las 31 notas del equipo de esta demo son datos sintéticos, como todo el dataset — está escrito en el código del módulo." | "Esto entró por WhatsApp." No hay WhatsApp conectado a las notas. |
| **"¿El jurado puede hablarle y que aparezca en el grafo?"** | "La voz está construida y convierte lo que decís en una propuesta estructurada, validada contra el catálogo. Que ese reporte se vuelva un nodo del grafo en vivo es el puente que estamos terminando." | "Sí, probá." Hoy no hay escritura en `core/notas.py`. |
| **"¿Tienen API abierta?"** | "Tenemos API REST y **un servidor MCP construido y probado**, de sólo lectura. No tenemos CLI ni SDK." | "Tenemos API, MCP y CLI." |
| **"¿Por qué el MCP no escribe?"** | "A propósito. Lo que escribe pasa por una persona. Está documentado por qué, y hay un test que rompe la suite si alguien mete una herramienta de escritura en la lista equivocada." | — |
| **"¿Qué tan preciso es?"** | Mostrar el panel de evals, con los tamaños de conjunto. Si el panel no llegó: "cada afirmación declara su fuente y su nivel de confianza, y el sistema dice cuándo no sabe." | **Nunca inventar un porcentaje.** |
| **"¿Son evals o son tests?"** | "Buena pregunta. Hasta ayer eran tests: 159 archivos que dan verde o rojo. Lo que ves acá es la conversión a métrica de dos conjuntos que ya corrían: la matriz de consultas y la batería de 24 frases. La tercera, la de cruces, la etiquetamos a mano y son N casos. Lo digo porque N importa." | "Tenemos evals continuos." |
| **"¿Predice la demanda?"** | "Hay un pronóstico **determinista** de demanda, en `core/forecast.py`. No hay modelos probabilísticos y no hacemos pronósticos que no podamos explicar." | Cualquier cosa sobre modelos predictivos. |
| **"¿Cruzan con datos macro?"** | "Usamos IPC oficial del INDEC para deflactar y comparar peras con peras, con fuente y fecha. Cruzar macro con la operación para predecir no lo hacemos: no podríamos contestar con qué serie ni con qué validación." | — |
| **"¿Ya tienen clientes?"** | "Producto funcionando, un piloto realizado no pago, cero clientes pagos hoy." | Cualquier otra cosa. **Si nos agarran inflando, se cae todo lo demás, que sí es verdad.** |
| **"¿Esto lo construyeron acá?"** | "No, y lo decimos: PolPilot es un producto que venimos construyendo. Lo que construimos en estas 24 horas es esto —el cruce nuevo, la animación del camino, el panel de evals, el mapa de conocimiento en riesgo— y está en este repo, que arrancó vacío anoche." | Nada que sugiera que el producto entero es de la hackathon. |
| **"¿Esto no lo hace un ERP?"** | "Un ERP registra lo que pasó. Nosotros juntamos lo que pasó con lo que la gente dijo por fuera del sistema, y de ahí sale algo que ninguno de los dos tenía. Y no lo reemplazamos: nos montamos encima, por eso la adopción es barata." | — |
| **"¿Por qué no lo hace un modelo solo?"** | "Porque el modelo no tiene los datos, no valida el número y no conoce las reglas de esa empresa. Validamos toda cantidad contra código. Si el modelo alucina un número, el código lo frena." | — |
| **"¿El dataset es real?"** | "Cien por ciento ficticio, generado con semilla fija. Está declarado en el repositorio y no hay datos de ningún cliente acá." | — |

---

# 5. El MCP en el demo

Tenías razón: que esté construido y no lo supiéramos es el mejor hallazgo del
análisis. Así lo usaría.

## Lo que hay, verificado

`backend/mcp_server.py`, montado en `/mcp` de la misma app de FastAPI, hablando
Streamable HTTP estándar. **28 herramientas de sólo lectura.** Cada una es un
envoltorio fino sobre `angela._run_tool` — el mismo punto de entrada al borde
determinístico— así que **un número que llega por MCP es byte-idéntico al que
muestra la app**. La identidad viene del mismo token que devuelve
`POST /api/login`; no hay credencial aparte. El gate de permisos se re-chequea
del lado del servidor en cada llamada.

## Los tres movimientos, en orden de valor

### ⭐ Movimiento 1 — Dos ventanas, la misma pregunta · **30 segundos**

Pantalla partida: **PolPilot a la izquierda, Claude Desktop (el nuestro, ya
conectado) a la derecha.** La misma pregunta en las dos: *"¿cuánta plata tengo
parada en stock?"*

**Sale el mismo número, carácter por carácter.**

> "A la izquierda, nuestro producto. A la derecha, Claude Desktop hablando con
> el mismo negocio por MCP. **No es la misma pregunta contestada dos veces: es el
> mismo cálculo citado dos veces.** El número no lo pone el modelo. Si lo
> pusiera, serían distintos."

**Por qué es el mejor:** demuestra **plataforma abierta y determinismo en un solo
gesto** — dos de las cuatro columnas de Lightfield, en treinta segundos. Y con
Cognition entre los sponsors, le habla directo al jurado que le importa.

### ⭐ Movimiento 2 — El permiso, en vivo · **15 segundos**

Se cierra sesión y se entra como un rol de depósito. Se vuelve a listar las
herramientas del MCP. **`estado_caja` ya no está.**

> "Un rol de depósito no ve la caja en la app. Tampoco la ve un agente que entre
> con su token. Y no es que se la escondemos del menú: si un cliente la llama
> igual, el servidor la rechaza."

**Por qué:** seguridad demostrada, no afirmada, en quince segundos. **Apostaría a
que ningún otro equipo muestra algo así**, porque casi nadie construye permisos
en una hackathon.

### Movimiento 3 — El jurado desde su propia herramienta · **si hay tiempo y red**

Se le pasa la URL y un token a alguien del jurado y pregunta desde su Claude
Desktop o su Cursor.

**Es el más impactante y el más riesgoso.** Depende de la red del lugar, y
`MCP.md` advierte que los clientes reales son más quisquillosos que el SDK con
redirecciones y negociación de `Accept`. **Sólo si sobra tiempo, y sólo con el
movimiento 1 ya hecho como respaldo.**

## Lo que hay que preparar, hoy

1. **Sacar el token el mismo día.** TTL de 12 horas
   (`POLPILOT_TOKEN_TTL_HORAS`). Un token de anoche no sirve mañana a las 16:00.
   **Sacar uno nuevo antes de subir al escenario.**
2. **Probarlo contra el deploy real** con un cliente real, no con el SDK de test.
3. **Tener las dos ventanas abiertas y la conexión hecha antes de empezar.** No
   se configura un conector delante de un jurado.
4. **Captura de pantalla de respaldo** de las dos ventanas con el mismo número,
   por si se cae la red.

---

# 6. Qué hacemos con `PolPilot_Plan_Cordoba_Hack (1).docx`

Lo leí entero. **Es un buen documento y sigue siendo la mejor fuente de
posicionamiento que tenemos.** Pero es versión 2, se escribió con un cronograma
distinto, y tiene nueve puntos que hoy son falsos o quedaron viejos.

**Mi recomendación: no lo tires ni lo edites encima. Marcalo como superado y
dejá este MD como versión 3.** Un documento con correcciones parciales es peor
que dos documentos con fechas claras — y ya nos pasó dos veces que una
afirmación vieja volviera a un deck.

## Lo que sobrevive intacto y hay que seguir usando

| Sección | Por qué |
|---|---|
| **§1 La decisión, en una página** | El argumento de que lo generado bonito es barato y una empresa entera modelada no, sigue siendo el mejor párrafo del documento |
| **§2 Los cuatro pilares** | Correctos, incluida la corrección obligatoria del pilar 2 (offline) |
| **§5 El grafo va al centro, y adentro del producto** | La decisión de no hacer una página HTML aparte es correcta y el motivo es bueno |
| **§8 Sobre cruzar con la economía** | Cerrado bien. La cadena de consecuencias sí, la predicción macro no |
| **§11 El guion del pitch** | La regla de la apertura y la distinción alerta/cruce. **Los tiempos y el orden de ejemplos se reemplazan por §3 de acá** |
| **§12 Preguntas del jurado** | La base. **Ampliado y corregido en §4 de acá** |
| **§14 Checklist antes de subir** | Todo vigente, y más urgente que nunca |

## Lo que hay que tachar

| Dónde | Qué dice | Qué pasa |
|---|---|---|
| Encabezado | "Kick-off el jueves 11 a las 10:30" | **El 11 es viernes.** El sitio dice 18:30 puertas / 20:00 apertura, 24 h, entrega sábado 16:00 |
| Encabezado | "El track se gana respondiendo una pregunta técnica" | El sitio dice que **se elige en la apertura**. Los tres retos no están revelados |
| §3 | "20% innovación, 25% implementación, 25% impacto" | No pude atribuir ese reparto a este evento. Los criterios publicados de la hackathon de GitLab son cuatro ejes parejos: técnico, diseño, impacto, idea |
| §3 | "Otro premiado ganó por explicar cada decisión que toma" | **No lo pude verificar.** Los otros dos sí: *lore* (conocimiento que se va con la persona, Grand Prize) y *graphdev* (relaciones + evolución temporal, Anthropic Grand Prize) |
| §6 Momento 2 | "La entrada en vivo: aparece como nodo nuevo y se conecta solo" | **No está construido.** `core/notas.py` no tiene API de escritura. Debajo de la línea de corte |
| §6 Momento 3 | "Si Ramón se toma vacaciones, la empresa pierde siete reglas que sólo él sabe" | **Falso.** Las 22 piezas tienen `origen.quien = "aldo"`. Sustituto verdadero y mejor: el punto ciego por persona (Bloque 4) |
| §6 Momento 1 | El pasillo 4 como el aha | **Se reemplaza por la oferta rechazada.** El pasillo 4 pasa a reserva |
| §9 fila 11 | "Integraciones y conectores — NO VA como diferencial" | Sigue siendo cierto para los conectores de ERP. **Pero el MCP sí va**, y el documento no sabía que existía |
| §10 | El plan de construcción entero | Se reemplaza por §1 de acá |

## Además, una deuda de documentación que encontré

**"The Counting Rule" se cita por nombre en 14 archivos del repo y su definición
ya no está en `PRODUCT.md`.** Se perdió en una reescritura. La regla está viva en
el código y protegida por tests; el documento la dejó colgando. **Cinco minutos
de arreglo**, y conviene hacerlo antes que un jurado siga la referencia y no
llegue a nada.

---

# El resumen en cinco líneas

1. **No portes el pasillo 4.** La card de la oferta ya existe y el número es
   $5.038.657 contra $163.675. Dos horas para darle camino **con las notas
   adentro**.
2. **Los evals primero**, cuatro horas, con el tamaño del conjunto al lado de cada
   porcentaje y la fecha de la última corrida.
3. **Veintiuna horas arriba de la línea de corte.** El eje temporal del grafo y la
   entrada en vivo quedan afuera, y está bien que queden afuera.
4. **El MCP en dos ventanas con el mismo número** prueba plataforma abierta y
   determinismo en treinta segundos, y no cuesta construir nada.
5. **El documento viejo pasa a superado.** Nueve puntos tachados, siete secciones
   que siguen valiendo.
