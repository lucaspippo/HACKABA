# Lo disruptivo, ordenado por impacto

Criterio de admisión, el tuyo: construible de verdad, demostrable en menos de un
minuto, sin humo, defendible si aprietan. Todo lo que no lo cumple está al final,
en "descartadas".

Costos en jornadas de una persona. Cada ficha dice **qué existe hoy** y **qué hay
que escribir**, porque esa distinción es la que evita que una estimación se
triplique.

---

## 1. ⭐ El jurado conecta su propio cliente de IA a nuestro negocio — **coste ~0**

**Lo nuestro, y no estaba en la lista.**

El servidor MCP ya está construido, montado en `/mcp`, probado y documentado
(`backend/mcp_server.py`, `backend/MCP.md`). 28 herramientas de sólo lectura,
autenticadas con el mismo token del login, con los permisos del rol re-chequeados
del lado del servidor en cada llamada.

**La demo:** se le pide a alguien del jurado que abra su Claude Desktop o su
Cursor, se le pasa la URL y un token, y **le pregunta al negocio desde su propia
herramienta**. "¿Cuánta plata tengo parada en stock?" "¿Quién me debe?" El
número que sale es byte-idéntico al de la pantalla, porque las dos rutas pasan
por el mismo `angela._run_tool`.

**Por qué gana:** es la única forma de demostrar "plataforma abierta" que no es
una diapositiva. Y con Cognition entre los sponsors, hablarle a un jurado en el
idioma de los agentes que consumen sistemas de registro es exactamente el tiro.

**Qué hay que escribir:** nada. **Qué hay que preparar:** un token válido (TTL
12 h — hay que sacarlo el mismo día), la URL del deploy, y probarlo con un
cliente real antes, porque `MCP.md` mismo advierte que los clientes reales son
más quisquillosos que el SDK con redirecciones y negociación de `Accept`.

**Riesgo:** depende de la red del lugar. Tener un cliente propio ya conectado
como plan B.

**Costo: 0 de construcción, 1 hora de preparación y prueba.**

---

## 2. ⭐ El contrafáctico: que el jurado rompa el sistema — **media jornada**

Tu idea 7.1, y sigo pensando que es la mejor de las tuyas.

**Por qué funciona:** un chatbot no se rompe cuando le sacás un dato. Sigue
contestando con la misma seguridad. El nuestro se apaga. Eso prueba causalidad en
cinco segundos y deja al jurado con la sensación de haber tocado el motor.

**Lo que existe:** `caminos()` es determinista y recalculable; `cruces.cards()`
tiene la regla escrita de que *"si falta el dato, el cruce no sale: no hay
hallazgo a medias"*; `analisis_cache.datos_cambiaron()` invalida todo desde un
solo punto.

**Lo que hay que escribir:** un parámetro de exclusión (`sin_notas=[ids]`) que
viaje por `cruces.cards()` y `grafo.completo()`, y un botón "quitar este dato"
al lado de cada evidencia. **No hay que borrar nada de la base** — y eso es
importante, porque un botón que borre datos en vivo delante de un jurado es una
mala idea por razones obvias.

**El remate:** al quitar la nota de Kevin, el camino se apaga, el número vuelve a
rojo, y **la card dice "faltante, $53.646"**. Al devolverla, vuelve a explicarse.

**Costo: media jornada.**

---

## 3. ⭐ El punto ciego por persona — **media jornada, y es el reemplazo honesto del "conocimiento en riesgo"**

**Éste hay que leerlo entero porque corrige el guion.**

El Momento 3 tal como está escrito —*"si Ramón se va, la empresa pierde siete
reglas que sólo él sabe"*— **es falso contra los datos de hoy**: las 22 piezas de
`conocimiento_negocio.json` tienen `origen.quien = "aldo"`. Las 22. Nadie más
enseñó nada.

**Pero hay una versión que es verdadera, está en los datos reales, y es mejor.**

Las 31 notas del equipo sí tienen autor, y 13 personas distintas. Calculé qué
entidades del negocio tienen **una sola fuente humana**:

| Entidad | Su única fuente |
|---|---|
| Almacén San Martín (cliente) | **Walter** — 2 notas |
| Autoservicio 9 de Julio (cliente) | **Walter** |
| Rotisería Avenida (cliente) | **Osmar** |
| Supermercado El Puente (cliente) | **Osmar** |
| Proveeduría La Rural (cliente) | **Diego** |
| Yogur Bebible Tierra Roja | **Vanesa** |
| Jamón Cocido El Paraná | **Tomás** |
| Gaseosa Cola La Ribera | **Norma** |
| Distrib. Mayorista Guaraní (proveedor) | **Celeste** |
| Golosinas Costa Dulce SRL (proveedor) | **Celeste** |

Y del otro lado, lo que sí está cubierto por varios: Cámara de frío 2 (Ramón,
Nahuel, Tomás), Lácteos Campo Alegre (Ramón, Brian, Nahuel, Marta), Pasillo 4
(Kevin, Nahuel).

**La demo:** los nodos del grafo coloreados por cuántas fuentes humanas tienen.
Se apaga a Walter y **se apagan dos clientes enteros**. Se apaga a Celeste y **se
apagan dos proveedores**. Y la frase:

> "Si Walter se toma vacaciones, esta empresa deja de saber qué pasa en dos de
> sus clientes. No porque no tenga los datos: los datos siguen ahí. Deja de
> saber **lo que no está en ningún dato.**"

**Por qué es mejor que la versión del guion:** (a) es verdad hoy, sin tocar el
dataset; (b) es sobre gente del piso, no sobre el dueño, que es más sentido; (c)
es el ángulo con el que ganó *lore* el Grand Prize en la hackathon de GitLab, y
*graphdev* el de Anthropic — conocimiento que se va con la persona, sobre un
grafo.

**Lo que hay que escribir:** un cálculo de cobertura por autor sobre
`notas.listar()` (una función de veinte líneas), un campo por nodo, y un modo de
color en el lienzo con un selector de persona.

**Si además se quiere la versión del conocimiento:** hay que repartir los autores
de las 22 piezas en el seed. Es una decisión sobre el dataset, no una feature, y
es defendible mientras se diga que el dataset es sintético. Pero **no hace
falta**: la versión de las notas es más fuerte.

**Costo: media jornada.**

---

## 4. ⭐ La contradicción entre canales — **media jornada, y los datos ya están**

Tu idea 7.7. La confirmo: el caso existe y es mejor de lo que decía el documento.

Cuatro personas describen la **misma** entrega de Lácteos Campo Alegre por
cuatro canales en cinco días (detalle completo en `05-EJEMPLOS.md`, nuevo 3), y
**dos de ellas se contradicen de verdad**:

- Ramón (voz, 02/07): *"faltaron dos pallets de yogur y **los trajeron al otro
  día**"*.
- Brian (WhatsApp, 03/07): *"Llegaron 40 cajas y la orden decía 80. El chofer
  dice que **el resto viene la semana que viene**"*.

**El sistema no elige.** Muestra las dos, con autor, canal y fecha, y dice: *hay
dos versiones incompatibles de lo mismo; antes de reclamar, alguien tiene que
decidir cuál.*

**Por qué gana:** en una sala llena de sistemas que sintetizan, el que señala que
no puede sintetizar es el único que está diciendo la verdad. Y **cierra con
acción**, que es la regla de la casa: la contradicción va a la persona que puede
resolverla, por el círculo cerrado que ya existe (`core/mis_avisos.py`).

**Lo que hay que escribir:** un detector chico —notas del mismo `proveedor` o la
misma `ubicacion`, en una ventana de días, cuyos campos declarados no coincidan—
y la superficie. **No hace falta NLP**: para el caso de Campo Alegre alcanza con
que dos notas hablen del mismo hecho y el humano vea los dos textos enfrentados.
Si se intenta detectar la contradicción semánticamente con el modelo, se rompe la
regla de la casa y se vuelve indefendible.

**Costo: media jornada.** Y hay que decir en voz alta que la contradicción se
**señala**, no se **resuelve**.

---

## 5. La regla aprendida que se incumplió — **media jornada, y no está en ninguna lista**

**Lo nuestro.** Es el paso que sigue a "el sistema aprende", y casi nadie lo
tiene: **el sistema usa lo que aprendió para detectar que se rompió.**

El caso, verificado (detalle en `05-EJEMPLOS.md`, nuevo 2):

- `k11`: *"GASEOSA COLA LA RIBERA nunca puede quebrar: trae gente al local."*
  **`veces_aplicada: 9` — la regla más aplicada de las 22.**
- Norma, por chat, 28/06: la góndola de la Sucursal Norte quedó vacía el sábado.
- El último traslado a esa sucursal fue el **15/06**. Veintidós días.
- En el depósito central hay 282 unidades. **No falta mercadería: falta que
  baje.**

> "Ésta es la regla que más veces se aplicó en esta empresa. Se incumplió hace
> nueve días. El ERP no lo vio porque mira el depósito, y ahí hay 282. La única
> que lo supo fue Norma."

**Lo que existe:** `conocimiento.aplicables()` y el contador; las notas con
autor y fecha; los 2.640 traslados con destino y fecha.

**Lo que hay que escribir:** un cruce nuevo en `cruces.py` con el shape estándar.
Es el séptimo del set.

**Costo: media jornada.**

---

## 6. El determinismo demostrado — **dos horas**

Tu idea 7.4. La confirmo sin cambios y subo su prioridad, porque es la más barata
de todas las que prueban algo.

La misma consulta dos veces, resultado idéntico carácter por carácter en los
números; después se muestra qué **sí** varía (la redacción de Ángela) y qué
**nunca** varía (la cifra).

**Lo que existe:** la arquitectura entera. `PRODUCT.md` lo declara como
invariante duro, `analisis_cache` documenta que *"un hit es byte-igual a
recomputar"*, y `extraccion.py` reconoce el comprobante de muestra **por sha256 de
los bytes, no por nombre de archivo ni por un flag del cliente, porque esos dos se
falsifican desde el navegador**.

**Ese detalle del sha256 conviene decirlo tal cual.** Es la clase de decisión que
un jurado técnico reconoce como "esta persona pensó en el adversario".

**Costo: dos horas.**

---

## 7. El panel de evals — **media jornada, y vale más de lo que parece**

Tu idea 4 / momento 4. La confirmo con una corrección importante que está
desarrollada en `03-NUESTROS-CUATRO-DIFERENCIADORES.md`, §3b: **hoy no tenemos
evals, tenemos tests.** Hay 159 archivos de test en el backend y dos de ellos
—`test_matriz_consultas.py` y `test_bateria_nl.py`— son casi evals: la matriz
completa fuente × métrica × agrupación × filtro, y 24 frases en dos idiomas por
la misma ruta que usa el modelo.

Lo que les falta para ser evals es puntuar en vez de afirmar. **El conjunto de
casos ya existe y ya corre**; hay que reportar precisión, falsos positivos, y
contra qué conjunto, y mostrarlo en una pantalla.

**Y hay una métrica que sólo nosotros podemos mostrar:** la tasa de abstención.
`test_matriz_consultas.py` ya trata "la combinación que por diseño no existe
devuelve su error honesto" **como un PASS**. Medir eso y llamarlo por su nombre
—cuántas veces el sistema dijo "no sé" y tenía razón— es un número que ningún
otro equipo va a tener.

**Costo: media jornada.**

---

## 8. El "¿por qué?" recursivo — **media jornada**

Tu idea 7.3. La confirmo.

**Lo que existe:** `core/carpeta.py` ya guarda por campo el triple
`valor` / `fuente` / `estado`, con la regla escrita de que la fuente **nunca**
puede ser "el sistema" — tiene que ser "pedido P-4401", "cuenta corriente de
Autoservicio 9 de Julio", "regla de la casa k01". Cada cruce declara `fuentes`,
`dominios` y `drill.porque`. El grafo declara `meta.derivados`.

**Lo que hay que escribir:** la recursión de la superficie. Los datos están; lo
que falta es que cada respuesta se pueda volver a preguntar.

**El remate, si sale:** bajar cuatro niveles en vivo hasta la nota original de
una persona con nombre, fecha y canal. Responde de antemano "¿cómo sé que no lo
inventó?".

**Costo: media jornada.**

---

## 9. La línea de tiempo del conocimiento — **media jornada**

Tu idea 7.5. La confirmo, con el dato de que **se puede construir hoy**: las 22
piezas tienen `origen.cuando` entre el **2026-06-05 y el 2026-07-06**, y
`veces_aplicada` sembrado con historia real que suma **97**.

Es el mismo eje temporal que propongo para el grafo (`04`, §3.5) y conviene
construirlos juntos: es un solo control deslizante sobre dos capas.

**El remate honesto:** *"esto es lo que el sistema no sabía hace un mes."*

**Costo: media jornada si ya se hizo el eje temporal del grafo; una jornada si
no.**

---

## 10. La entrada adversarial — **cuatro horas**

Tu idea 7.2. La confirmo con una advertencia.

**Lo que existe:** el comportamiento. Ángela no calcula, el código valida toda
cantidad (`core/validacion`), no hay modelos probabilísticos, `voz.py` devuelve
`bloqueado[]` cuando no puede resolver, y `cruces.py` no emite hallazgos a
medias.

**La advertencia:** invitar al jurado a romperlo es una apuesta. Si encuentra un
camino donde el sistema **sí** afirma algo que no puede sostener —y en un
producto de 65.000 líneas, con un LLM en el medio, ese camino probablemente
existe— se pierde más de lo que se gana.

**La versión segura, que es igual de fuerte:** **nosotros** hacemos los dos o tres
intentos, ensayados, y se invita al jurado a proponer el cuarto. Si el cuarto
sale mal, la respuesta ya está preparada: *"ahí interpretó de más; el número no
lo inventó, pero la frase se fue. Eso es lo que miden los evals."* Eso también
suma.

**Costo: cuatro horas de guionado y ensayo, cero de construcción.**

---

## 11. El costo de no saber — **media jornada, con condición**

Tu idea 7.8. La confirmo **con la condición que vos mismo escribiste**, y la
repito porque es la que más veces se rompió: distinguir plata que se ahorra de
plata que está a la vista, y **nunca sumar dos indicadores que comparten
clientes**.

**Lo que ya protege esto:** The Counting Rule está viva en el código
(`mostrador.costos_viejos()` no tiene campo total a propósito) y protegida por
`test_costo_viejo.py`, `test_montos_canonicos.py` y `test_parada.py`.

**Aviso de higiene, chico pero conviene:** la definición de The Counting Rule
**ya no está en `PRODUCT.md`**, aunque 14 archivos la citan por nombre. Se perdió
en una reescritura. Si un jurado sigue la referencia, no llega a nada.

**Costo: media jornada.** Y si no da el tiempo, **no se hace**: es la idea con
más probabilidad de producir un número inflado bajo presión.

---

## 12. El diff de la semana — **una jornada**

Tu idea 7.6. Buena idea de producto, floja idea de hackathon: necesita una
ventana de tiempo que el dataset de 32 días no da con holgura, y compite por el
mismo espacio que la línea de tiempo del conocimiento (#9), que es más barata y
más vistosa.

**Recomendación: no para Córdoba.** Para después.

---

# Descartadas

| Idea | Por qué |
|---|---|
| **Cruzar con datos macro de la economía** | El documento ya lo cerró bien. `core/macro.py` existe y sirve para deflactar con IPC oficial en `core/evolucion.py`, que es el uso correcto y honesto. Como motor predictivo, no hay con qué contestar "¿con qué serie? ¿con qué modelo?" |
| **Modelos probabilísticos de predicción** | Confirmado por tercera vez contra el repo: no existen. Lo único que hay es `core/forecast.py`, determinista |
| **Integraciones y conectores como diferencial** | Existen (`core/conectores.py`, Odoo por XML-RPC) pero no diferencian: todo el mundo tiene conectores |
| **Sandbox de código para el agente** | Semanas, y nuestra arquitectura resuelve el mismo problema al revés |
| **Funcionamiento sin conexión** | **No existe.** Re-verificado hoy: no hay service worker, ni manifest, ni IndexedDB, ni workbox en `frontend/`. Sacar toda mención, como ya estaba decidido |

---

# El orden

| # | Qué | Costo | Prueba qué |
|---|---|---|---|
| 1 | MCP en vivo con el cliente del jurado | ~0 | Plataforma abierta |
| 6 | Determinismo demostrado | 2 h | Que el número no lo pone el modelo |
| 2 | Contrafáctico | ½ j | Causalidad |
| 3 | Punto ciego por persona | ½ j | Que el conocimiento vive en gente |
| 4 | Contradicción entre canales | ½ j | Honestidad |
| 5 | Regla aprendida incumplida | ½ j | Que lo aprendido se usa |
| 7 | Panel de evals + tasa de abstención | ½ j | Rigor |
| 8 | "¿Por qué?" recursivo | ½ j | Trazabilidad |
| 9 | Línea de tiempo del conocimiento | ½ j | Evolución |
| 10 | Adversarial (ensayado) | 4 h guion | Que dice "no sé" |
| 11 | El costo de no saber | ½ j, condicional | Plata |

**Las tres primeras suman menos de una jornada y prueban tres cosas distintas.**
Si el tiempo es el que dice el sitio del evento —una noche—, ésas tres y nada
más.
