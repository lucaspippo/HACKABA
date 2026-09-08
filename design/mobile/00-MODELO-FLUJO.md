# Modelo de flujo de la información — mobile por rol

**Estado: propuesta, pendiente de confirmación.** Nada de esto se diseña ni se
construye hasta que Lucas confirme las cinco respuestas de la sección 5.

Relevado contra `main` en `0778dda3`. Cada afirmación cita el archivo y la
línea. Todo lo que no salga del código está marcado **[SUPUESTO]**.

---

## 1. Las cinco palabras, contra el código

Resumen. El detalle de cada una, abajo.

| Palabra | Dónde vive hoy | Persiste | Tiene destinatario | Tiene estado | Quién la crea | Quién la cierra |
|---|---|---|---|---|---|---|
| **Aviso / nota** | `core/notas.py` | sí (sembrada) | **no** | **no** | **nadie — no hay API de escritura** | nadie |
| *(otro sentido)* «aviso» | `core/notificaciones.py` | sí | sí (`para`) | `leida` | sólo el sistema | el que la lee |
| **Reporte de piso** | `core/piso.py` | sí | **no** | `nuevo → resuelto` | cualquiera del piso | **sólo el dueño** |
| **Hallazgo** | `core/mapa_operacion.py` | **no** (recalculado) | no | no | el cálculo | nadie |
| **Prioridad** | `core/priorities.py` | **no** (cache de proceso) | no (se filtra por *features*) | derivado (`action_taken`) | la composición | quien aprueba la propuesta |
| **Objetivo** | `core/objetivos.py` | sí | `responsable` (texto libre) | `pendiente / en_proceso / listo` | cualquier usuario logueado | cualquier usuario logueado |
| **Tarea asignada** | `core/recordatorios.py` | sí | sí (`para`) | `latente / activo / disparado / hecho` | cualquiera **para sí mismo**; sólo el dueño para otro | su destinatario o el dueño |
| **Tarea derivada** | `lib/piso.js` | **no** | no | no | el front, del `/api/inicio` | la persona (2 de 4 tipos) |

### 1.1 Aviso / nota — hay dos cosas distintas con el mismo nombre

**(a) `core/notas.py` — la capa no estructurada.** 31 notas en el demo
(`data-demo/notas_equipo.json`), por 6 canales: `voz` 7, `whatsapp` 7, `chat` 6,
`reporte` 4, `email` 4, `foto` 3. Los tres «de afuera» (`whatsapp`, `email`,
`foto`, `mapa_operacion.py:113`) suman **14**: ése es el "14 de 31" de la banda
del mapa (`mapa_operacion.py:437` `canales_de_entrada`).

Campos: `id, autor, fecha, canal, tipo, texto, texto_en, cliente, producto,
proveedor, ubicacion` (`notas.py:32`, `TIPOS` de 7 valores).

Lo decisivo: **el módulo no tiene API de escritura**. Su propio docstring lo
dice — es data sembrada, se lee y se cruza, no se crea. No hay endpoint
`POST /api/notas`. Y no tiene `destinatario` ni `estado`.

> Una nota, hoy, nace sembrada, no llega a nadie y no se cierra nunca.

**(b) `core/notificaciones.py` — el evento de entrega.** `{id, para, titulo,
cuerpo, tipo, ref, leida, fecha}` (`notificaciones.py:47`). Sí tiene
destinatario y sí tiene «visto». Pero sólo la emite el sistema (un recordatorio
que se dispara, un cambio de perfil); no hay camino persona → persona. Destino
`panel` activo, `whatsapp` registrado y **apagado a propósito**
(`notificaciones.py:30`).

### 1.2 Reporte de piso — `core/piso.py`

Seis tipos (`piso.py:50`): `faltante, conteo, entrega, reposicion, pedido,
presupuesto`. Registro: `{id, tipo, actor, cuando, fecha, estado, datos,
adjunto?}` (`piso.py:111`). Regla escrita en el módulo: **reportar no toca stock
ni ERP** — el reporte es un hecho, y lo que sale de cruzarlo es una propuesta.

- Lo crea cualquiera con el *feature* del tipo (`main.py:1230`).
- `estado`: `nuevo → resuelto`, y **cerrarlo requiere `require_admin`**
  (`main.py:1323`).
- El cruce: `piso.propuestas()` agrupa los faltantes sin resolver por proveedor,
  valoriza con el costo del catálogo y busca la OC abierta (`piso.py:227`).
  También `require_admin` (`main.py:1348`).
- El reporte **no tiene destinatario**. Va a un pozo común que sólo el dueño ve.

### 1.3 Hallazgo — `core/mapa_operacion.py`

`hallazgos(lang)` (`mapa_operacion.py:2027`, calculado en `:1225`) cruza nodos
del mapa: zona + notas del equipo + orden de compra abierta. Es el ejemplo
insignia — "el depósito avisó dos veces que la cámara está llena y hay una OC
que entra justo ahí".

No persiste, no tiene id estable fuera del cálculo, no tiene estado, no tiene
dueño. Se recalcula por idioma vía `analisis_cache`. **Y sólo `aldo` tiene el
*feature* `mapa`** (`main.py:3067`, `require_feature("mapa")`): nadie más ve un
hallazgo del mapa, ni siquiera el encargado de depósito que lo produjo.

### 1.4 Prioridad — `core/priorities.py`

`inbox()` (`priorities.py:306`) compone cuatro fuentes: oportunidades
(`oportunidades_neg`), patrones (`patrones`), alertas de negocio, y **reportes de
piso** (`_piso_items`, `priorities.py:483`). Deduplica, parte en `act` / `watch`,
rankea y filtra por *features* del que mira (`visibles_para`, `:298`).

- No es del dueño: **todos tienen `alertas`** salvo el usuario interno, así que
  todos ven una porción. Lo que cambia es el tamaño de la porción.
- El «cerrado» es derivado, no guardado: `with_action_taken` (`:336`) pregunta a
  `proposal_state.for_proposal` si la propuesta ya produjo un registro real. Hoy
  **hay un solo resolver**: orden de compra (`proposal_state.py:38`).
- La otra forma de que una prioridad desaparezca es que el dueño le dé feedback
  al patrón (`pattern_feedback`, usado en `priorities.py:414`).
- `PRODUCT.md` es explícito: el ciclo de vida del insight (`New / Confirmed /
  Acted upon / Resolved / Proven wrong / Still monitored`) **está diseñado y no
  implementado**.

### 1.5 Objetivo — `core/objetivos.py`

`{id, nombre, responsable, fecha, estado, creado_por}`, estados `pendiente /
en_proceso / listo` (`objetivos.py:15`). Nace de "Adoptar como objetivo" en
`Prioridades.jsx:257` y `OportunidadesNegocio.jsx:140`.

Dos cosas que llaman la atención:

- `responsable` es **texto libre**, no un `username`. Un objetivo asignado a
  "Ramón" no aparece en ninguna pantalla de Ramón. No hay ninguna consulta por
  responsable en el código.
- `POST /api/objetivos` y el cambio de estado **no piden admin**
  (`main.py:408`, `:417`): cualquier usuario logueado crea y cierra objetivos de
  cualquiera. Probablemente no sea intencional.

Aparte y sin relación: `core/objetivos_medidos.py` — los 7 objetivos que Ángela
**mide** contra datos reales. Ésos no se crean ni se adoptan; se calculan.
Comparten la palabra y nada más.

### 1.6 Tarea — hay tres cosas distintas

**(a) Tarea asignada = recordatorio.** `core/recordatorios.py:56`. Es lo que
`MiDia.jsx:185` muestra como "Lo que te asignaron" y lo que la persona marca
hecho (`MiDia.jsx:65`). Tiene `para`, `creado_por`, estado real y condiciones que
se evalúan contra datos vivos.
**Restricción clave:** `main.py:1372` — `para = req.para if (u.es_admin and
req.para) else creado_por`. **Una persona de piso no le puede dejar una tarea a
nadie.** Sólo a sí misma.

**(b) Tarea derivada.** `lib/piso.js:21` `derivarTareas(ini)` — cuatro tipos
armados en el navegador desde `/api/inicio`: `fantasma`, `balanza` (cerrables,
aplican `saneamiento` real y quedan auditadas a nombre de la persona,
`MiDia.jsx:105`), `negativo` y `entrada` (sólo lectura → abren Ángela). No
persisten, no se asignan, no tienen dueño.

**(c) El reporte de piso**, que en la práctica se comporta como una tarea del
dueño: entra con `estado: nuevo` y espera que él lo resuelva.

---

## 2. Dónde se pisan

1. **«Aviso» significa dos cosas opuestas.** La nota (`notas.py`) tiene contenido
   y no tiene destinatario; la notificación (`notificaciones.py`) tiene
   destinatario y no tiene contenido propio. **La pieza que falta es exactamente
   la intersección de las dos.**

2. **Reporte de piso y nota son el mismo hecho por dos rieles.** `canal:
   "reporte"` es uno de los seis canales de `notas.py`, y `piso.reportar` produce
   justamente eso. Pero son tablas distintas, con esquemas distintos, y no se
   hablan: un `faltante` de `piso` no aparece en `notas.listar()` ni cuenta en la
   banda "14 de 31". **Recomendación: `piso` es la nota con estructura; la nota
   es el reporte sin campos. Deberían ser un solo objeto con dos niveles de
   estructura, no dos objetos.**

3. **Hallazgo y prioridad son la misma cosa en dos lugares.** El hallazgo del
   mapa y la card de Prioridades tienen la misma forma (`insight`), el mismo
   origen (cruces deterministas) y ningún estado. La diferencia es de qué
   pantalla cuelgan y qué *feature* las gatea (`mapa` para uno, `alertas` para el
   otro). **Recomendación: hallazgo = prioridad vista desde el mapa. Un solo
   objeto, dos entradas.**

4. **Objetivo y tarea asignada se pisan de frente.** Ambos: texto, un
   responsable, un estado de tres valores, persistidos. El objetivo asigna por
   nombre y no llega a nadie; el recordatorio asigna por `username` y sí llega.
   **Recomendación: el objetivo es una tarea del dueño con horizonte largo. Debe
   asignar por `username` y aterrizar en el "Mi día" del responsable — si no, es
   un post-it privado.**

5. **`estado` no es un vocabulario, son cinco.** `nuevo/resuelto` (piso),
   `latente/activo/disparado/hecho` (recordatorios), `pendiente/en_proceso/listo`
   (objetivos), `action_taken` derivado (prioridades), y nada (hallazgos).

---

## 3. El ciclo de vida, y dónde se corta

```
   ┌─ 1 NACE ──────► 2 SE INTERPRETA ──► 3 SE DECIDE ──► 4 SE EJECUTA ─┐
   │                                                                    │
   └──── 6 VUELVE AL CIRCUITO ◄──── 5 QUEDA AUDITADO ◄──────────────────┘
```

**1 · Nace.** ✅ **Funciona.** Voz (`core/voz.py`), formulario
(`ReporteForm.jsx`), foto/remito (`cargar`), o detección del sistema. Nace con
`actor`, `cuando`, `fecha` (`piso.py:111`).
⚠️ **Falla en un punto:** nace **sin destinatario**. Ni el reporte ni la nota
tienen a quién. Y la nota, directamente, no se puede crear.

**2 · Se interpreta.** ✅ **Funciona, y es lo mejor que hay.** `voz.proponer`
(`voz.py:210`) separa bien las aguas: el LLM interpreta el lenguaje, el código
valida el número contra `core/validacion` — el mismo peaje que un remito. Los
candidatos de producto se **proponen**, no se eligen; un empate bloquea y lo
desempata una persona (`voz.py:243`). Devuelve `bloqueado[]` y `avisos[]`.
⚠️ **Falla:** las cinco intenciones (`voz.py:58`) son todas de depósito y
reparto. No hay intención para "el cliente pidió algo que no tenemos", "me
rechazó parte del pedido", "no pudo pagar". Y ninguna intención produce un
destinatario.

**3 · Se decide.** ⚠️ **Cuello de botella.** Resolver un reporte, ver las
propuestas del piso y ver el mapa son todos `require_admin` / `feature: mapa`, y
sólo `aldo` los tiene. **Todo lo que el piso reporta necesita al dueño.** El
encargado de depósito (`ramon`), que tiene 9 años en el galpón, no puede cerrar
el faltante que le reportó Nahuel.
✅ Lo que sí está bien resuelto: `core/autonomia.py:37` — plata, stock y permisos
clavados en `pide_ok`, sin setting que los afloje. El nivel se gradúa sólo en
`datos`.

**4 · Se ejecuta.** ⚠️ **Parcial.** Hay un solo camino completo propuesta →
registro real: la orden de compra (`proposal_state.py:38`). El resto de las
prioridades no tiene resolver, así que su «hecho» no existe.
✅ La excepción brillante: las tareas cerrables de `MiDia` (`fantasma`,
`balanza`) aplican `saneamiento` **de verdad** desde el teléfono
(`MiDia.jsx:105`). Es el único lugar del producto donde alguien del piso cambia
el sistema con un toque.

**5 · Queda auditado.** ✅ **Funciona.** `AuditLog.record(actor, ...)` en cada
`piso.reportar` (`piso.py:154`) y en cada `resolver`. `mapa_operacion.
vuelve_al_sistema` (`:549`) lo muestra y —bien— **dice cuándo está vacío** en vez
de poner un tilde verde decorativo.

**6 · Vuelve al circuito.** ❌ **ACÁ SE ROMPE EL CÍRCULO, y se rompe dos veces.**

- **El que reportó nunca ve qué pasó con su reporte.** `api.piso.reportes` existe
  en `lib/api.js:277` y **ninguna pantalla lo consume** (verificado: los únicos
  consumidores de `api.piso` son `ReporteForm` para escribir, y
  `Prioridades`/`OportunidadesNegocio` —ambas de dueño— para resolver). El
  backend hasta filtra por actor para él (`main.py:1315`) y ese dato no se
  muestra en ningún lado.
- **Resolver un reporte no notifica a nadie.** `piso.resolver` (`piso.py:174`)
  audita y no llama a `notificaciones.emitir`. El recordatorio disparado sí lo
  hace (`recordatorios.py:80`); el reporte resuelto, no.

> Nahuel reporta 8 cajas rotas. Aldo reclama al proveedor y cobra la diferencia.
> Nahuel no se entera nunca. La próxima vez lo escribe en el grupo de WhatsApp,
> porque ahí por lo menos alguien contesta.
>
> **Éste es el punto donde el producto se gana o se pierde, y hoy está abierto.**

---

## 4. Lo que el relevamiento agregó al pedido

- **Son 7 personas de superficie exclusivamente móvil, no 8**
  (`superficies == ["mobile"]`): `brian`, `tomas`, `kevin`, `walter`, `osmar`,
  `diego`, `lucia`. Otras 4 son mobile-first con desktop disponible (`ramon`,
  `nahuel`, `vanesa`, `norma`). El total de 14 personas sí es exacto.
- **`lib/roles.js` tiene 7 fichas de rol para 11 oficios distintos.** La regex
  `/dep[oó]sito/i` (`roles.js:21`) se come a **cinco personas con trabajos
  distintos**: encargado (`ramon`), recepción (`nahuel`), conteos (`tomas`),
  armado de pedidos (`brian`) y ayudante (`kevin`). Todos ven las mismas tres
  acciones: cargar remito, reportar faltante, marcar conteo. **Brian arma pedidos
  todo el día y no tiene una sola acción de picking.**
  Es la primera cosa que el diseño por rol tiene que partir.
- **La barra inferior ya es dinámica por *features*** (`MobileApp.jsx:144-154`),
  no fija de cinco. Para `brian` hoy son 4 slots (Mi día · Insights · Depósito ·
  Ángela); para `diego`, 3 (Mi día · Insights · Ángela). El problema no es que la
  barra sea rígida: es que los ítems no están elegidos por oficio.
- **El dueño en mobile no aterriza en `Inicio`: aterriza en el chat de Ángela**
  (`MobileApp.jsx:81`, `defaultView = piso ? "mi_dia" : "angela"`). El `Inicio`
  de cinco lecturas que describe `PRODUCT.md` es la pantalla de desktop. En
  mobile el dueño tiene algo peor: un chat vacío.

---

## 5. Las cinco preguntas — respuesta propuesta

### P1 · Cuando alguien deja un aviso, ¿nace como información o como tarea?

**Coincido, con una corrección.** Nace como **aviso con destinatario propuesto**
— ni información suelta ni tarea. Tres estados y nada más:

```
enviado ──► visto ──► aceptado (= ahí se vuelve tarea)
   │                      │
   └──────► derivado ◄────┘   (el destinatario lo pasa a quien corresponde)
```

El fundamento contra el código: hoy la nota no tiene destinatario y por eso el
único destino real es el dueño. Si el aviso naciera como tarea de alguien,
estaríamos empujando trabajo a una persona que no dijo que sí, y el modelo del
producto es exactamente el opuesto (`piso.py`: "reportar no modifica nada; lo que
sale es una propuesta que alguien aprueba"). El aviso es el hecho; la tarea es lo
que alguien acepta hacer con el hecho.

**Lo que hace que no se pierda no es el estado: es el acuse.** Un aviso
`enviado` sin `visto` a las N horas escala solo. Sin eso, "aviso sin dueño" y
"aviso con dueño que no lo abrió" son lo mismo para el que lo dejó.

**Implicación técnica:** hay que crear un `destinatario` y un `estado` en el
objeto de piso, y unificarlo con `notas`. Es la deuda más grande que abre este
modelo.

### P2 · ¿El dueño crea tareas a mano, o sólo aprueba lo que Ángela propone?

**Coincido enteramente.** Las dos, con la asignación manual como excepción
deliberadamente incómoda: no está en la barra, no está en el botón de captura;
vive dentro de la ficha de la persona en Equipo.

Fundamento: el riel manual **ya existe y ya está gateado así**
(`main.py:1372`: sólo el admin puede poner `para`). El producto ya tomó esta
decisión; lo que falta es no ampliarla. Si "asignar tarea" se vuelve un botón de
primer nivel, PolPilot compite con Trello — y con Trello no se pierde por
funcionalidades, se pierde por precio.

**El camino principal es un tercero que ninguna de las dos opciones nombra:** el
dueño **acepta un aviso y lo dirige**. No lo inventa (lo trajo alguien) ni lo
propuso Ángela (lo propuso una persona). Ése es el volumen real.

### P3 · Cuando el de depósito cierra una tarea, ¿el dueño se entera?

**Sí, y hoy no pasa — pero el problema que importa es el inverso, y es peor.**

- Depósito → dueño: **funciona.** Todo cierre queda auditado con actor
  (`piso.py:154`, `MiDia.jsx:105`) y el dueño lo ve en Equipo y en "vuelve al
  sistema" (`mapa_operacion.py:549`).
- Dueño → depósito: **no existe.** Ver sección 3, punto 6.

Propuesta: **un aviso no se cierra en silencio nunca.** Cerrarlo emite una
notificación al que lo originó, por el riel que ya existe
(`notificaciones.emitir`), con el resultado adentro: *"Aldo reclamó a Lácteos
Campo Alegre por las 8 cajas que reportaste. $X recuperados."* Y el que reportó
tiene, en su pantalla, **"lo que reporté"** con sus reportes y su estado — que es
literalmente encender un endpoint que ya está escrito y nadie llama.

Ésta es la pieza que más recomiendo priorizar. Es barata y es la que decide si la
persona vuelve a abrir la app.

### P4 · ¿Qué queda adentro de PolPilot y qué vuelve al ERP?

Contestado con lo que hay en el código, no en abstracto. Hoy la frontera está
**muy** adentro:

**Queda adentro (todo lo que se escribe hoy):** reportes de piso
(`floor_reports`), notas del equipo, recordatorios, objetivos, conocimiento del
negocio, auditoría, feedback de patrones, órdenes de compra preparadas
(`core/ordenes.py`), correcciones de saneamiento.

**Vuelve al ERP:** **hoy, nada automático.** El conector Odoo
(`core/odoo_ingest.py`, `odoo_fx.py`, `conectores.py`) **lee**. No encontré
ningún camino de escritura al ERP en `main.py`.

Y es coherente con la doctrina escrita: `PRODUCT.md` → *"El ERP es dueño del
registro; nosotros somos dueños de la decisión"*. La regla que propongo declarar
explícitamente:

> **El ERP guarda lo que pasó. PolPilot guarda lo que alguien decidió, quién lo
> decidió y por qué.** Un hecho del piso no es un movimiento de stock: es la
> evidencia de que el stock del ERP está mal. El ajuste lo hace el ERP, cuando
> una persona lo aprueba.

Para el diseño mobile esto es liberador: **ninguna pantalla de piso tiene que
escribir en el ERP.** Todas escriben hechos y decisiones. El único punto donde
esto se va a tensar es el picking de `brian`, que naturalmente querría reservar
stock — y eso es terreno del ERP. **[SUPUESTO]**

### P5 · ¿Qué ve cada rol del circuito?

Principio: **cada uno ve el paso siguiente al suyo, y el resultado final de lo
que él originó.** Nadie ve el tablero completo salvo el dueño.

| Rol | Origina | Decide | Ve del circuito |
|---|---|---|---|
| Dueño (`aldo`) | objetivos, avisos dirigidos | **todo** | el círculo entero |
| Administración (`marta`) | avisos de oficina | su cola de pendientes | lo que entró de afuera y su estado |
| Compras (`celeste`) | reclamos a proveedor | acepta/rechaza reclamos que le llegan | los avisos que la nombran + qué pasó con el reclamo |
| Encargado depósito (`ramon`) | avisos, conteos | **debería decidir diferencias de depósito** (hoy no puede) | lo de su galpón, de punta a punta |
| Recepción (`nahuel`) | faltante, roto, vencido, no pedido | nada | **el resultado de lo que reportó** |
| Conteos (`tomas`) | diferencias de conteo | nada | si su conteo corrigió el sistema — sí o no |
| Armado (`brian`) | faltantes de picking | nada | si el pedido que armó salió |
| Sucursal (`norma`) | reposición, cierre, novedades | su local | si su pedido de reposición fue despachado |
| Mostrador (`vanesa`) | faltantes de góndola, reclamos | nada | si lo que pidió llegó |
| Preventistas (`diego`, `lucia`) | pedidos, quejas, precios | nada | si el pedido se entregó y si se cobró |
| Choferes (`walter`, `osmar`) | rechazos, no estaba, cobros | nada | si el cliente al que no pudo entregar fue recontactado |

**Lo que agrego al pedido:** el enunciado dice que el de conteos "no tiene por
qué ver la decisión del dueño, pero sí que lo que cargó sirvió". Estoy de
acuerdo, y creo que hace falta un cambio más grande: **`ramon` tiene que poder
decidir.** Es encargado, tiene 9 años en el depósito y hoy no puede cerrar ni un
faltante de su propia gente. Si toda diferencia de depósito escala al dueño, el
dueño se convierte en el cuello de botella que el producto vino a sacar. Propongo
un tercer nivel entre "piso" y "dueño": **el que decide en su dominio.**
Requiere un permiso nuevo; hoy `authz` sólo distingue `es_admin` de todo lo
demás.

---

## 6. Lo que este modelo abre como deuda técnica

Ordenado por cuánto lo va a necesitar el diseño de las pantallas:

1. **`destinatario` + `estado` en el objeto del piso**, y unificarlo con `notas`
   (P1). Sin esto, "la nota con destinatario" no se puede construir, sólo
   dibujar.
2. **Notificar al que originó, al cerrar** (P3). `notificaciones.emitir` ya
   existe; falta llamarlo desde `piso.resolver`.
3. **Consumir `api.piso.reportes` en una pantalla del piso** (P3). Endpoint
   escrito, cero consumidores.
4. **Partir el rol `deposito` en cuatro** en `lib/roles.js` (recepción, conteos,
   armado, encargado). El `match` por regex ya lo permite; hay que escribir las
   fichas.
5. **Un permiso "decide en su dominio"**, entre piso y dueño (P5).
6. **Intenciones de voz para calle y mostrador** (`voz.py:58` sólo cubre
   depósito/reparto).
7. **Offline**: no hay ninguna cola local ni service worker en el repo. Todo lo
   que se diseñe de offline es pantalla sin motor, y así lo voy a marcar.
8. **`objetivos.responsable` por `username`**, no texto libre — y admin para
   crear/cerrar (`main.py:408` hoy no lo pide).

---

## 7. Supuestos sobre el trabajador (marcados, sin dato)

PolPilot no tiene usuarios activos. Todo esto es hipótesis:

- **[S1]** Que el de piso deja de usar la app si no ve qué pasó con lo que cargó.
- **[S2]** Que nadie del piso quiere elegir un destinatario de una lista de 14.
- **[S3]** Que los avisos habituales de cada oficio son los del enunciado
  (vino de menos, vino roto, el cliente no estaba…). No están en el dataset:
  las 31 notas son de otra forma. Habría que sembrarlos si se quiere que los
  botones tengan datos reales atrás.
- **[S4]** Que el encargado de depósito quiere y puede decidir sobre su dominio.
- **[S5]** Que el picking de `brian` es un oficio distinto y no una variante de
  recepción.

---

## 8. Diccionario de entidades reales para los mockups

Nada fuera de esta lista aparece en un mockup. Cero marcas reales.

**Productos** (`data-demo/inventory.json`, 430 artículos):
`GASEOSA COLA EL PARANA 2.25L (X6U)` (cód. 1166) · `LECHE ENTERA SANTA CLARA 1L
(X12U)` (1220) · `LECHE ENTERA EL PARANA 1L (X12U)` (1216) · `MANTECA SANTA
CLARA 200G (X30U)` (1236) · `VINO TINTO LA RIBERA 750CC (X6U)` (1204) ·
`GALLETITAS SURTIDAS LA RIBERA 400G (X20U)` (1129) · `JAMON COCIDO GUARANI
(HORMA)` (1269, balanza) · `ROLLO DE COCINA GUARANI X3 (X10P)` (1428) · `PAPAS
BASTON COSTA DULCE 2.5KG (X6U)` (1351).

**Proveedores** (6): Distrib. Mayorista Guaraní · Lácteos Campo Alegre ·
Golosinas Costa Dulce SRL · Frigorífico La Ribera · Limpieza Total SA ·
Alimentos del Paraná SA.

**Clientes** (24): Autoservicio 9 de Julio · Supermercado El Puente · Almacén San
Martín · Minimercado Costanera · Despensa Doña Elsa · Rotisería Avenida ·
Proveeduría La Rural · Kiosco La Terminal · Panadería El Trigal · Súper Dos
Hermanos…

**Ubicaciones** (21): Pasillo 1–6 × Rack A/B/C · Cámara de frío 1 · Cámara de
frío 2 · Cámara congelados.

**Órdenes de compra** (4): `OC-2026-0847` (abierta, Lácteos Campo Alegre) ·
`OC-2026-0791` · `OC-2026-0812` (recibidas) · `OC-2026-0833` (cancelada).

**Pedidos / reparto**: `P-4401` … `P-4433`, con `Camión 1 - Walter`,
`Camión 2 - Osmar`, `Camión 3 - Tercerizado`.

**Lotes**: `L-2026-300` en adelante. **El "hoy" del dataset es 2026-07-07.**

**Personas**: Aldo (dueño) · Marta (administración) · Celeste (compras) · Ramón
(encargado depósito) · Nahuel (recepción) · Tomás (conteos) · Brian (armado) ·
Kevin (ayudante, entró hace una semana) · Walter y Osmar (reparto) · Diego y
Lucía (preventistas) · Norma (Sucursal Norte) · Vanesa (mostrador).
