# Qué quedó en main, qué no construí, y qué falta decidir

*Cierre de la tanda de mobile. Escrito el 2026-09-09, contra `main` en `8f754b0`.*

Los diez puntos están mergeados, cada uno con su PR y CI verde. Este documento
es el cierre: lo que hay, lo que deliberadamente no hay, y las decisiones que no
son mías.

---

## 1. Lo que quedó en main

Doce PRs, del #57 al #68.

| # | PR | Qué cambió, en una línea |
|---|---|---|
| 1 | [#57](https://github.com/agustindelmonti/polpilot-app/pull/57) | El depósito dejó de ser un rol y pasó a ser los **cinco oficios** que es. Brian tenía «cargar remito» como acción destacada, que es el trabajo del que recibe. |
| — | [#58](https://github.com/agustindelmonti/polpilot-app/pull/58) | Vencimientos dejó de **prometerle la misma venta a dos lotes** del mismo producto (asignación FEFO). El test que lo expone falla en el commit anterior. |
| 2 | [#59](https://github.com/agustindelmonti/polpilot-app/pull/59) · [#60](https://github.com/agustindelmonti/polpilot-app/pull/60) | **C5**: la deuda que cada camión se lleva arriba antes de salir. **$111.800.000**, deduplicada por cliente. |
| 3 | [#61](https://github.com/agustindelmonti/polpilot-app/pull/61) · [#62](https://github.com/agustindelmonti/polpilot-app/pull/62) | **El círculo cerrado**: un reporte nace dirigido, se acusa recibo y el resultado vuelve al que lo originó. Y con el **nombre** de la persona, no su usuario. |
| 4 | [#63](https://github.com/agustindelmonti/polpilot-app/pull/63) | **C7**: la diferencia de stock le llega a quien la decide **con la explicación adentro**. |
| 5 | [#64](https://github.com/agustindelmonti/polpilot-app/pull/64) | **C2**: la parada enriquecida. Una parada por pantalla, tres preguntas: ¿debe? ¿alguien dijo algo? ¿compra algo de lo que se vence? |
| 6 | [#65](https://github.com/agustindelmonti/polpilot-app/pull/65) | El **armado de pedidos** de Brian, con lo que el ERP no manda dicho en pantalla. |
| 7 | [#66](https://github.com/agustindelmonti/polpilot-app/pull/66) | Los **dos gratuitos**: el costo de 535 días donde alguien puede hacer algo, y «preguntarle a Ramón». |
| 8 | [#67](https://github.com/agustindelmonti/polpilot-app/pull/67) | La **superficie por oficio**: tres destinos + botón de carga, y los avisos del oficio como botones que llegan a alguien. |
| 9 y 10 | [#68](https://github.com/agustindelmonti/polpilot-app/pull/68) | La **búsqueda** (caja abajo, Ángela como fila) y la **ficha** del producto. |

### Dos reglas nuevas en `PRODUCT.md`

- **Record Rule** — lo que se reporta vuelve al que lo reportó, o no sirvió.
- **The Counting Rule** — un número canónico se cita, no se recalcula. Nació de
  que el mismo doble conteo apareció **dos veces**: los $168,7M que en realidad
  eran $111,8M. «Dos veces no es mala suerte: es un patrón.»

La Counting Rule está aplicada donde más duele: `oportunidades_neg.exposicion()`
**no tiene campo `total`**, a propósito, para que esa clase de bug no pueda
nacer. Lo mismo en `parada.de()` y en `ficha.producto()`.

---

## 2. Lo que NO construí, y por qué

### Lo que pediste explícitamente que no

| No construido | Por qué |
|---|---|
| **Offline** | No hay motor. Sería una pantalla muerta que promete algo que no pasa. |
| **El escalado del aviso no visto** | Requiere una política de tiempos que nadie definió. |
| **Cualquier cosa que toque authz** | No se decide en una rama de pantallas. |

### Lo que se chocó con el código y frené, en vez de resolverlo solo

**a · El picking renglón por renglón no se puede construir.**
`apartados.logistica` trae `{pedido, cliente, direccion, estado,
fecha_prevista, transporte}` y **nada une un pedido de entrega con sus
productos**. `ventas_por_cliente` sí tiene renglones, pero son los de la cuenta
corriente y no comparten clave con el `P-44xx`; `ordenes_compra` tiene ítems,
pero son órdenes a proveedores. La pantalla lo dice (mismo criterio que el
bloque FIFO del depósito) en vez de simularlo. **Hace falta que el ERP exporte
los renglones del pedido de entrega**: es una decisión de integración, no de
pantalla.

**b · `preventista_del_cliente` no se puede resolver.**
El dataset no une un cliente con su preventista, y elegir entre Diego y Lucía
sería inventarlo. El único aviso que lo usa —«El cliente no estaba», de los
choferes— vuelve con el destinatario vacío y cae en la propuesta por tipo. La
pantalla lo dice: *«Vas a elegir a quién le llega.»*

**c · El de piso con vista de oficio perdió la solapa «Insights».**
Tres destinos + carga es el techo de la barra. Sus señales —fantasma, balanza,
negativos— **ya le llegan como tareas en «Mi día»**, así que era la misma
información por dos puertas. Sigue alcanzable por Ángela y por URL. **Si
preferís que se quede, es una línea.**

**d · El escaneo no escanea todavía.**
El botón comparte la caja de búsqueda, como pide el diseño, pero enfoca el campo
en vez de abrir un lector. No hay lector cableado y fingirlo sería el tipo de
comportamiento falso que este producto no hace.

**e · «La recepción del día» de Nahuel no se puede armar.**
`ordenes_compra` no tiene fecha de llegada esperada —sólo la fecha en que se
creó la orden— así que **el dataset no sabe qué entra hoy**. Lo más cercano que
existe es la orden abierta, que no es lo mismo: saber que hay una orden viva no
es saber que el camión llega esta mañana. El bloque «lo que sigue» de Nahuel
queda sin construir, declarado.

**f · «PolPilot recomienda» no tiene texto en ninguna card.**
Ninguna de las diez cards de oportunidades trae `insight.recommendation.detail`.
Lo único que hay es `accion_chat`, que es el prompt que se le **manda** a Ángela
(«ayudame a cobrarles a los que están atrasados»). Rotularlo «PolPilot
recomienda» sería ponerle en la boca un consejo que no dio. La banda quedó con
dos modos —la recomendación de verdad cuando existe, «Preguntarle a Ángela»
cuando no— y hoy todas caen en el segundo. **Llenar `recommendation.detail` es
trabajo de backend**, en `core/insight.py`, y no lo inventé.

**g · Los pasteles de la imagen de referencia no se pueden usar.**
La imagen pinta cada acción rápida de un color distinto, y eso es color
decorativo: el celeste del escáner no significa nada distinto del verde de la
cámara. `DESIGN.md` lo prohíbe dos veces (One Meaning Rule, y el azul es
exclusivamente de Ángela). Se copió la composición entera y el relleno va en
`papel-hondo` con el ícono en `tinta`: el ritmo de la fila lo dan la forma y el
espaciado. La única alternativa que no rompe la regla es `hielo-claro` para los
seis por igual —un tono, que es superficie y no código de color—.

**h · La ficha no tiene deep-link.**
El router mobile es `/:section`, así que el código del producto vive en estado.
Se llega por búsqueda o por tarea, que es como se llega de verdad; un link
directo a una ficha es deseable y no existe.

---

## 3. Lo que falta decidir — y no lo decido yo

Estos tres son de Agustín, no míos. Los tres están construidos «como si el
permiso existiera», sin tocar `authz`.

**1 · ¿El chofer ve el saldo del cliente que va a visitar?**
Hoy **no**: ver saldos es `cuentas` y el chofer tiene `logistica`. La parada le
llega sin el bloque de deuda y con las otras dos preguntas completas. El recorte
va **del lado del servidor** (`deuda_oculta: true`) — mandarlo y esconderlo en
el front sería regalarlo en la respuesta. Darle el saldo del cliente que tiene
enfrente es probablemente correcto —es la plata que puede cobrar— pero **cambia
qué ve un rol**.

**2 · ¿Ramón necesita un tercer nivel de authz?**
Un encargado asigna trabajo. Hoy sólo el dueño puede poner `para` en un
recordatorio. «Pedir un conteo a alguien» está diseñado y no construido.

**3 · ¿Ramón necesita `mapa` en mobile?**
Es el que decide dónde entra la mercadería, y el mapa es donde eso se ve.

---

## 4. Lo que falta construir, en orden de lo que devuelve

Todo esto tiene motor o le falta poco. Ninguno estaba en los diez puntos.

| Qué | Para quién | Estado del motor |
|---|---|---|
| **Rendir la caja del día**, con la diferencia explicada por quien la vio | Vanesa, Norma | Los 153 cierres ya están sembrados (`core/mostrador.py`); falta la pantalla |
| **C1 completo**: el salame que se vence × lo que Vanesa puede empujar | Vanesa, Aldo | Parcial — la ficha ya junta las piezas; falta la propuesta |
| **C10**: «no me lleves más» × un pedido en curso | Diego, Lucía | Filtro sobre C5, que ya existe |
| **C12**: el jamón de Tomás — notas de conteo × vencimientos | Ramón | No, pero las dos fuentes están |
| **Progreso personal** («contaste 14 de 21 ubicaciones») | todo el piso | No. **Nunca comparación entre compañeros** |
| **La ficha de cliente** como pantalla propia | preventa, mostrador | Existe como `parada.de()`; falta la entrada por búsqueda |
| **El lector de código de barras** | depósito | No hay nada |
| **`recommendation.detail` en las cards** | todos | El campo existe y viene vacío — ver §2·f |
| **Fecha de llegada esperada en las órdenes** | Nahuel | No está en el dataset — ver §2·e |

---

## 5. Lo que hay que recordar de todo esto

**Tres cosas que aprendí a los golpes en esta tanda y que valen más que el
código:**

1. **Un número que ya falló una vez no se mergea sin la suite corrida.** El
   doble conteo apareció dos veces y las dos veces se veía razonable.
2. **Un test que pasa solo y rompe al de al lado es un test roto.** El tenant
   demo lo comparte media suite; todo lo que escribe, limpia.
3. **Cuando el diseño choca con el dato, se dice.** Cuatro veces en esta tanda
   preferí una pantalla que declara lo que no sabe antes que una que lo inventa.
   Es lo único que hace que se le pueda creer al resto.

---

*Todo lo que dice «supuesto» en `02-ROLES-Y-SUPERFICIE.md` y
`03-CRUCES.md` sigue siendo supuesto: PolPilot no tiene usuarios activos. La
única lista de avisos que **no** es hipótesis es la de recepción, cuyos cuatro
motivos ya los validaba `core/piso.py`.*
