# Los cruces que están en el dataset

Investigación. Todo lo de acá sale de consultar el dataset del demo
(`data-demo/`, "hoy" = **2026-07-07**), no de lo que se me ocurra. Cada cruce
dice qué fuentes junta, qué aparece, a quién le sirve, dónde vive y qué cuesta.

---

## 0. Antes que nada: el motor de cruces ya existe, y llega a una sola persona

**`backend/core/cruces.py` está escrito, calcula seis cruces determinísticos y
su docstring dice exactamente lo que vos decís:**

> *«ALERTA mira UNA fuente y avisa un umbral. Cualquier ERP con un chat encima
> lo hace, y por eso no prueba nada. CRUCE junta fuentes que NO se hablan entre
> sí y encadena una consecuencia que nadie tenía a la vista.»*

Los seis, con su condición de disparo real:

| Cruce | Junta | Se dispara cuando |
|---|---|---|
| `_cruce_deuda_vencimiento` | cuentas × ventas por cliente × vencimientos | un moroso compra justo lo que se vence |
| `_cruce_proveedor_estrella` | notas de proveedor × ranking de ventas × inventario | hay ruido sobre el proveedor de un producto estrella |
| `_cruce_credito_creciente` | cuentas (historial de pagos) × ventas por cliente | paga cada vez más tarde **y** le vendemos cada vez más |
| `_cruce_queja_cliente_clave` | notas × ranking real de compra × logística | se queja uno de los que más compran |
| `_cruce_cliente_en_problemas` | notas de campo × cuentas × ventas | dos avisos de campo del mismo cliente en 30 días |
| `_cruce_espacio_camara` | notas de ubicación × depósito × órdenes abiertas | dos avisos de la misma ubicación **y** algo entrando ahí |

**Y el problema entero está en una línea:** `/api/grafo` es
`Depends(require_feature("mapa"))` (`main.py:3053`), y **el único que tiene el
feature `mapa` es Aldo**. Los consumidores de `cruces.cards()` son `angela.py`
(la herramienta de chat) y `grafo.py` → `MapaNegocio.jsx` y `CerebroNegocio.jsx`,
**las dos de escritorio**.

> El cerebro que une la empresa ya está construido. Le habla a una persona, en
> un dispositivo, en una pantalla. **Nadie del piso ve nunca que su aviso se
> cruzó con algo.**

Eso cambia el costo de casi todo lo que sigue: la mayoría no es "construir un
cruce", es **rutear un cruce que ya se calcula a la persona que puede accionarlo**.

Dos límites concretos del motor de hoy, que sí son trabajo nuevo:

1. **Ningún cruce mira la ruta futura.** `cruces.py` toca `logistica` una sola
   vez (línea 360) y para mirar entregas **pasadas** de un cliente que se quejó.
   `fecha_prevista >= hoy` no aparece en ningún lado. Todo el eje «persona ×
   dónde está parada» que pedís **no tiene motor** (§3).
2. **Cada cruce devuelve como máximo uno.** Todos hacen `mejor = ...` y se
   quedan con el de mayor plata. Sirve para el panel del dueño; no sirve para
   repartir cruces a nueve personas.

---

## 1. Cómo trabaja este equipo, leído del dataset

31 avisos, **13 autores de 14**, 6 canales: voz 7 · whatsapp 7 · chat 6 ·
reporte 4 · email 4 · foto 3. Los tres de afuera —whatsapp, email, foto— suman
**14**, que es el «14 de 31» de la banda del mapa.

Lo que salta al ordenarlos por *hecho* en vez de por autor:

**Un hecho llega por dos a cuatro canales distintos, de personas distintas, y
nadie los une.** No es una hipótesis: pasa cuatro veces en 31 notas.

| El hecho | Quiénes, por dónde |
|---|---|
| **Campo Alegre entregó la mitad** | Ramón (voz, 02/07) · Brian (whatsapp, 03/07) · Nahuel (foto del remito, 03/07) · Marta (email, 03/07) |
| **La cámara de frío 2 está llena** | Ramón (voz, 29/06) · Nahuel (voz, 01/07) · Ramón otra vez (whatsapp, 02/07) · Tomás (foto, 06/07) |
| **El salame Monte Chico no sale** | Vanesa (whatsapp, 01/07) · Brian (reporte, 04/07) · Vanesa otra vez (chat, 05/07) |
| **La mortadela vino fallada** | Osmar (whatsapp, 30/06) · Brian (foto «para el reclamo», 01/07) |

Y hay un patrón adentro del patrón: **la segunda persona casi siempre aporta la
pieza que le falta a la primera.** Osmar separó las cajas; Brian sacó la foto
*para el reclamo* — la evidencia de un reporte que él no hizo. Nahuel fotografió
el remito «por si después dicen otra cosa»; Marta frenó la factura por lo mismo,
sin saber que la foto existía.

Eso ya no es "información dispersa". Es **un reclamo armado entre cuatro
personas que no saben que lo están armando.**

---

## 2. Los cruces que están, uno por uno

Ordenados por plata. Ojo con qué clase de plata es cada una: hay cruces que
**hacen visible** deuda que ya existe y cruces que **evitan** una pérdida. La
distinción está en §6 y no es cosmética. Los montos de mercadería son **valor
del lote a costo**
(`cantidad × costo_iva`); el motor calcula algo más honesto y más chico —
`vencimientos.plata_en_riesgo` es sólo el **sobrante**, lo que no se va a vender
antes de la fecha según la velocidad de 12 meses.

---

### C1 · El salame que vence, el mostrador que lo puede vender, y la cámara que no da más

**Cruza:** notas del equipo (3, de 2 personas, 2 canales) × depósito ×
`mostrador.json` (márgenes por presentación) × reglas de la casa.

**Qué hay, verificado:**
- `SALAME MILAN MONTE CHICO (PLANCHA)`, cód. 1286 · **Cámara de frío 2** · lote
  L-2026-522 · **65,6 kg** · **vence 18/07 (11 días)** · **$945.431** a costo.
- Vanesa, 01/07, whatsapp: *«Me preguntaron dos veces por el salame Monte Chico
  en el mostrador. Si hay que sacarlo pronto, avisen y lo empujo.»*
- Brian, 04/07, reporte: *«tiene fecha para este mes y todavía hay un montón.
  Nadie lo pidió esta semana.»*
- Vanesa, 05/07, chat: *«Si me dejan bajarle el precio lo saco en dos días; la
  gente lo pide feteado.»*
- `mostrador.json`: fiambre **feteado deja 80% de recargo (44,4% de margen)**;
  en pieza entera, 30% (23,1%).
- Regla de la casa de Aldo: *«Fiambres: nunca más de 15 días de stock, se
  vencen»* — `params: {dias_max_stock: 15}`, aplicada 4 veces.

**Qué aparece que ninguna fuente sola tiene:** el producto que el depósito no
puede mover es el que el mostrador ya tiene pedido dos veces, se vende con casi
el doble de margen feteado, está fuera de la regla del propio dueño, **y ocupa
lugar en la cámara que Ramón dice cuatro veces que está llena**. Sacarlo resuelve
dos problemas con una decisión.

**A quién le sirve:** a Aldo (la decisión de bajar el precio es suya), a Vanesa
(es la que lo empuja) y a Ramón (le libera cámara).
**Dónde vive:** en «Decidir» de Aldo, como una card con las tres voces adentro.
En el mostrador de Vanesa, como «te habilitaron el salame».
**Motor:** parcial. `vencimientos` y `notas` existen; **cruzar con
`mostrador.grupos` para decir "feteado deja 80%" no lo hace ningún cruce hoy.**
**Costo:** chico. Un cruce nuevo en `cruces.py`, ~40 líneas, todas las fuentes ya
están en `_ctx`.

---

### C2 · Lo que vence esta semana × quién lo compra × a quién le vamos a golpear la puerta

**El cruce con más plata del dataset, y el que no tiene nada de motor.**

**Cruza:** depósito (vencimientos) × `ventas_por_cliente.json` × **logística
futura** (`fecha_prevista >= hoy`, `estado != entregado`).

**Qué hay, verificado:** 8 lotes vencen dentro de 15 días, **$9.242.716** a costo
entre todos. De esos, **cinco lotes por $6.825.532 los compra alguien a quien le
vamos esta semana**:

| Lote | Vence | Valor | Comprador con camión programado |
|---|---|---|---|
| `MAYONESA GUARANI 500G` | 17/07 (10d) | $1.347.738 | **cuatro, todos hoy** — Comedor Escolar N°12 (Walter, P-4412) · Panadería El Trigal (P-4416) · Hostería Costanera (Osmar, P-4415) · Comidas El Fogón (Walter, P-4418) |
| `YOGUR BEBIBLE TIERRA ROJA 900G` | 14/07 (**7d**) | $2.010.890 | Supermercado El Puente (mañana, P-4420) · Minimercado Costanera (mañana, P-4425) |
| `YOGUR BEBIBLE CAMPO ALEGRE 900G` | 18/07 (11d) | $1.645.372 | Comidas El Fogón (hoy, P-4418) |
| `SALAME MILAN MONTE CHICO` | 18/07 (11d) | $945.431 | Despensa Doña Elsa (mañana, P-4426) |
| `JAMON COCIDO EL PARANA` | 19/07 (12d) | $876.101 | Despensa Doña Elsa (mañana, P-4426) |

**Qué aparece:** el camión sale hoy hacia cuatro clientes que compran la mayonesa
que se vence en diez días. Nadie cruza esas tres tablas, así que el lote se vence
en el galpón mientras cuatro camiones pasan por la puerta de gente que lo lleva.

**A quién le sirve:** a Diego y Lucía (lo ofrecen antes de que salga el camión),
a Walter y Osmar (lo llevan de arrastre en el mismo viaje), a Aldo (autoriza el
descuento).
**Dónde vive:** en la parada del chofer y en la ficha del cliente del preventista
— **no** en un tablero. «A este cliente le podés ofrecer X, que vence en 7 días.»
**Motor:** **no.** Es el gap #1 de §0: ningún cruce mira la ruta futura.
**Costo:** medio. `logistica.de_hoy()` existe, `vencimientos.en_riesgo()` existe,
`ventas_cliente.compras_de()` existe. Falta el cruce y falta que baje al teléfono.

---

### C3 · Campo Alegre: cuatro personas, cuatro canales, la misma entrega — y una orden nueva por confirmar

**Cruza:** notas (4, de 4 personas, 4 canales) × orden de compra abierta ×
recepciones × reportes de piso.

**Qué hay, verificado:**
- **OC-2026-0847**, abierta, 02/07, Lácteos Campo Alegre, 5 renglones,
  **165 unidades pedidas y 0 recibidas** según `recepciones`.
- Ramón (voz, 02/07): *«Campo Alegre entregó incompleto otra vez: faltaron dos
  pallets de yogur.»*
- Brian (whatsapp, 03/07): *«Llegaron 40 cajas y la orden decía 80.»*
- Nahuel (foto, 03/07): *«Foto del remito: dice 40 bultos, no 80. Queda la
  constancia por si después dicen otra cosa.»*
- Marta (email, 03/07): *«La factura vino por el total de la orden, pero
  entregaron la mitad. No la pago hasta que la corrijan.»*

**Qué aparece:** cuatro personas tienen un cuarto del caso cada una. Juntas
tienen un reclamo completo con evidencia fotográfica, número de orden, y la
factura ya frenada. **Y ninguna de las cuatro sabe que las otras tres existen.**
Celeste, que es la que le compra a Campo Alegre, tiene una sola de esas cuatro
piezas.

**A quién le sirve:** a Celeste, antes de confirmarle nada más a ese proveedor.
A Marta, que descubre que su decisión de no pagar tiene respaldo fotográfico.
**Dónde vive:** en la ficha del proveedor y en «Compras» de Celeste.
**Motor:** parcial. `piso.propuestas()` agrupa faltantes por proveedor y busca la
OC abierta; **pero lee sólo los reportes de piso, no las notas.** El "otra vez"
—la reincidencia— no lo calcula nadie.
**Costo:** chico-medio. Es unir dos tablas que ya existen y que deberían ser una
(ver `00-MODELO-FLUJO.md`, §2.2).

---

### C4 · Doña Elsa: dos avisos, 66 días, la regla de la casa, y un camión tercerizado

**El caso que pediste, y está entero en el dataset.**

**Cruza:** notas (2, de 2 personas) × cuentas × conocimiento × logística futura ×
vencimientos.

**Qué hay, verificado:**
- Debe **$19.200.000**, **66 días sin pagar**, plazo del sistema 30, **paga en
  promedio a 31**. Última compra 02/05.
- Regla de la casa de Aldo: *«A Doña Elsa tolerale hasta 45 días — es cliente
  desde 2011 y nunca me falló»* (`tolerancia_dias: 45`). **Pasó los 45 del
  dueño, no sólo los 30 del sistema.**
- Lucía (chat, 26/06): *«pidió si le podemos hacer una entrega chica sin factura
  nueva, para no seguir sumando a la cuenta hasta que cobre.»*
- Walter (whatsapp, 05/07): *«Pasé por lo de Doña Elsa. Está abierta y trabajando
  bien, me dijo que la semana que viene se pone al día.»*
- Mañana 08/07 va el **P-4426 · Camión 3 - Tercerizado**.
- Y compra dos de los lotes que vencen: el salame Monte Chico y el jamón El
  Paraná (C2).

**Qué aparece:** el cliente prometió ponerse al día, se lo dijo a Walter, y la
información no llegó a nadie. Mañana pasa por su puerta **un tercero que no
puede cobrar, no escuchó la promesa y no sabe que hay dos lotes que ella compra
venciéndose.** Walter, que tiene la relación, no va. Lucía, que la conoce,
tampoco.

**A quién le sirve:** a Lucía (llamarla antes), a Aldo (decidir si sale el
pedido), y a quien vaya (aunque sea el tercerizado: al menos con la instrucción).
**Dónde vive:** en la parada de mañana y en la ficha del cliente de Lucía.
**Motor:** parcial. `_cruce_cliente_en_problemas` se dispara con dos notas de
campo del mismo cliente en 30 días — **acá hay dos, pero de tipos distintos**
(`pedido_cliente` y `observacion_campo`), y el cruce filtra por
`tipo="observacion_campo"`, así que **no las ve**. La parte de la ruta, ninguna.
**Costo:** chico para la parte de notas (ampliar el filtro de tipos), medio para
la ruta.

---

### C5 · La ruta de mañana: $111.800.000 en la calle, en un camión que no es nuestro

**Cruza:** logística futura × cuentas. Dos tablas, nada más.

> **CORRECCIÓN (al construirlo).** La primera versión de este documento decía
> **$168.700.000**, y estaba mal: sumaba **por parada** en vez de **por
> cliente**. Supermercado El Puente y Kiosco Plaza tienen dos paradas cada uno
> el 08/07, y su saldo es uno solo. El número real es **$111.800.000** — un
> tercio menos. Lo detectó el código al escribirlo, no la lectura del
> documento, que es exactamente el motivo por el que un número se construye
> antes de repetirlo. Los dos primeros tests de `test_deuda_en_ruta.py` no
> prueban otra cosa.

**Qué hay, verificado, para el 08/07:**

| Camión | Paradas | Clientes | Deuda de esas paradas |
|---|---|---|---|
| Camión 1 · Walter | 1 | 1 | $12.600.000 |
| **Camión 3 · Tercerizado** | **7** | **5** | **$111.800.000** |

$111,8M es el **36% de los $311.400.000 que la empresa tiene por cobrar**. Y una
de esas siete paradas es Doña Elsa, con 66 días — que además compra dos de los
lotes que se están venciendo (C2).

**Qué aparece:** el ERP sabe cuánto debe cada cliente y sabe qué pedido sale
mañana. Lo que no hace nadie es **la suma por camión**. Puesto así, es una
decisión de operación evidente: o el tercerizado lleva instrucciones, o algunas
paradas se reasignan.

**A quién le sirve:** a Aldo y a Ramón (reasignar), a Marta (avisarle al
tercerizado qué cobrar).
**Dónde vive:** en «Decidir» de Aldo, una vez por día, a la tarde.
**Motor: SÍ, ya construido** — `cobranza.exposicion_en_ruta()` y la tarjeta
`deuda_en_ruta` en Prioridades (rama `feat/deuda-por-camion`). Llega a mobile
sin tocar el front, porque Insights lee Prioridades. Gateado por **dos**
módulos, `logistica` **y** `cuentas`: el encargado tiene rutas y no saldos, el
preventista al revés, y ninguno de los dos ve la flota entera.
**Costo:** fue chico, como estaba estimado. Lo único que no estaba previsto es
que el número había que deduplicarlo.

---

### C6 · La cámara de frío 2 y la orden de La Ribera del 9

**Cruza:** notas de ubicación (4, de 3 personas, 3 canales) × depósito × órdenes
× notas de proveedor.

**Qué hay, verificado:** 41 lotes en Cámara de frío 2 · 4 avisos entre el 29/06 y
el 06/07 (Ramón ×2, Nahuel, Tomás con foto) · Celeste (email, 04/07): *«La Ribera
confirmó la orden de fiambres para el 9. Pidieron que les avisemos si no hay
lugar en cámara»* · Ramón (whatsapp, 04/07): *«El camión de La Ribera llega
mañana temprano. ¿Dónde lo bajamos si la cámara 2 está llena?»* · y adentro de
esa cámara está el salame de C1, venciendo el 18/07.

**Qué aparece:** el proveedor **pidió expresamente que le avisemos**, el depósito
avisó cuatro veces que no entra, y las dos mitades están en personas distintas.
La pregunta de Ramón del 04/07 sigue sin responder.

**Motor: sí.** Es literalmente `_cruce_espacio_camara`, y es el ejemplo insignia
del docstring de `mapa_operacion.py`. **Se calcula hoy y lo ve sólo Aldo, en
desktop.** Ramón, que hizo la pregunta, no ve la respuesta.
**Costo: cero de motor.** Todo el costo es de ruteo.

---

### C7 · El pasillo 4: dos avisos que explican una diferencia de $53.646

**Cruza:** notas de ubicación (2, de 2 personas) × diferencias de conteo.

**Qué hay, verificado:**
- Kevin (voz, 06/07): *«Me mandaron a buscar leche al pasillo 4 y estaba en otro
  rack. Lo dejé donde decía el sistema para no romper nada.»*
- Nahuel (whatsapp, 06/07): *«Corrí las cajas del pasillo 4 para hacer lugar.
  Quedó todo del lado de la pared, avisen antes de buscar algo ahí.»*
- Y en **Pasillo 4 · Rack B** hay una diferencia de **−6,5 unidades** de
  `LECHE ENTERA EL PARANA 1L`, **$53.646**.

**Qué aparece:** la diferencia de conteo **ya tiene explicación**, escrita el
mismo día por dos personas. Sin el cruce, alguien va a recontar, o va a ajustar
stock por una diferencia que es de acomodamiento y no de faltante.

**A quién le sirve:** a Ramón, que es el que decide la diferencia — le llega con
la explicación adentro. Y a Kevin, que es nuevo y ve que lo que dijo sirvió.
**Dónde vive:** dentro de la card de la diferencia, no en una pantalla aparte.
**Motor:** no. `notas.por_ubicacion()` existe y `deposito.discrepancias()`
existe; nadie los junta.
**Costo:** muy chico. Y es de los que mejor enseña qué es PolPilot: el ERP dice
«faltan 6,5»; nosotros decimos «no faltan, Nahuel las corrió el lunes».

---

### C8 · La góndola vacía de Norma: 282 unidades y ningún quiebre

**Cruza:** notas de local × depósito central × traslados internos × la regla de
la casa más aplicada de todas.

**Qué hay, verificado:**
- Norma (chat, 28/06): *«En la Sucursal Norte la góndola de gaseosa cola quedó
  vacía el sábado a la tarde. Es el fin de semana que más se vende.»*
- `GASEOSA COLA LA RIBERA 2.25L`, cód. 1161: **282 unidades en el depósito
  central**, Pasillo 2 · Rack B, vence recién el 07/10.
- 48 traslados internos históricos de ese código (24 a Norte, 24 a Puerto); el
  último a Norte fue el **15/06 — hace 22 días**.
- Regla de la casa: *«GASEOSA COLA LA RIBERA nunca puede quebrar: trae gente al
  local»*, `genera_alerta`, `critico: true`, **aplicada 9 veces: es la más
  aplicada de las 22**.

**Qué aparece:** para el ERP no hay quiebre — hay 282 unidades. **El quiebre es
de ubicación, no de stock**, y lo único que lo prueba es el aviso de Norma. Y la
regla dice que este producto en particular no puede faltar en el local.

**A quién le sirve:** a Norma (pedir reposición con argumento), a Ramón
(despacharla), a Aldo (ver que su regla se está incumpliendo).
**Dónde vive:** en «Mi local» de Norma, como un pedido de reposición ya armado.
**Motor:** parcial. La regla y el stock existen; los traslados internos existen
como fuente. **Nadie cruza "hay en el central + falta en el local + hay regla".**
**Costo:** chico.

---

### C9 · La mortadela: el chofer separa, el armador fotografía

**Cruza:** dos notas de dos personas × inventario × proveedor.

**Qué hay:** Osmar (whatsapp, 30/06): *«Las 3 cajas de fiambre vinieron falladas,
las separé. No las cargué al camión.»* · Brian (foto, 01/07): *«Foto de las cajas
de mortadela falladas, para el reclamo al proveedor.»* ·
`MORTADELA SANTA CLARA (PLANCHA)`, cód. 1316, proveedor **Frigorífico La Ribera**.

**Qué aparece:** el reclamo está armado entre dos personas que no se coordinaron
— **uno tiene el hecho, el otro tiene la evidencia** — y sigue sin existir como
reclamo. Y La Ribera es el mismo proveedor que entra el 9 (C6): hay un reclamo
pendiente y una orden nueva del mismo proveedor, sin que nadie los vea juntos.

**A quién le sirve:** a Celeste, antes de recibir el camión del 9.
**Motor:** no. Es el enganche natural del flujo de reclamos de
`01-DEVOLUCIONES-Y-RECLAMOS.md`.
**Costo:** cae solo si se construye el reclamo con destinatario.

---

### C10 · «No me lleves más hasta que hable con Aldo» — y hay un pedido en camino

**Cruza:** nota de campo × cuentas × logística.

**Qué hay:** Walter (voz, 03/07): *«El de 9 de Julio me pidió que no le lleve más
hasta que hable con Aldo. Dice que está complicado.»* · Autoservicio 9 de Julio
debe **$42.000.000, 58 días** (el que más debe) · y **P-4401 sigue pendiente,
previsto para el 06/07 con Camión 2 · Osmar**.

**Qué aparece:** un cliente pidió expresamente que no le lleven, se lo dijo a
Walter, y hay un pedido a su nombre en la lista de Osmar. Si sale, o vuelve, o
suma $X más a una cuenta de 58 días.

**Motor:** no.
**Costo:** muy chico. Es la misma consulta de C5, filtrada por cliente.

---

### C11 · La Rural se va por precio, y paga al día

**Cruza:** nota de queja × cuentas.

**Qué hay:** Diego (chat, 30/06): *«La Rural me dijo que está comprando gaseosa
en otro lado porque se la dejan más barata. Me pidió precio por cantidad.»* ·
Proveeduría La Rural: **saldo $0, 0 días sin pagar** — el único de los 24 sin
deuda.

**Qué aparece:** el que se está yendo por precio es **el mejor pagador de la
cartera**. La decisión de darle precio no es la misma para un moroso que para el
único que paga al contado, y esa segunda mitad no está en la queja.

**Motor: sí, casi.** `_cruce_queja_cliente_clave` cruza queja × ranking real de
compra. Lo ve Aldo, en desktop. **Diego, que la levantó, no ve la respuesta.**
**Costo:** cero de motor.

---

### C12 · El jamón que Tomás avisó hace doce días

**Cruza:** nota de conteo × depósito.

**Qué hay:** Tomás (reporte, 25/06): *«Conté el jamón cocido de El Paraná y hay
más de lo que dice el sistema. Igual la fecha está justa.»* ·
`JAMON COCIDO EL PARANA (HORMA)`: Cámara congelados, 68,7 kg, **vence el 19/07**,
$876.101 · lo compra Despensa Doña Elsa, que va mañana.

**Qué aparece:** Tomás dijo «la fecha está justa» hace doce días y sigue ahí. Es
el caso más simple y el más elocuente: **un aviso correcto, de la persona
correcta, que no llegó a nadie.**

**Motor:** no. Enganchar `notas` de conteo con `vencimientos.en_riesgo()`.
**Costo:** chico.

---

## 3. El eje que no tiene nada: persona × dónde está parada

De los doce cruces de arriba, **cinco dependen de la ruta futura (C2, C4, C5,
C10, y la mitad de C12) y ninguno tiene motor**, por la razón de §0: `cruces.py`
mira `logistica` sólo hacia atrás.

Lo que propongo, y que es una sola cosa: **la parada enriquecida.**

Cuando el chofer o el preventista abre la parada de hoy, la app ya sabe quién es
el cliente. Con eso, tres consultas que hoy nadie hace juntas:

1. **¿Debe?** → `cuentas`, con el plazo del sistema **y** el de la casa.
2. **¿Alguien dijo algo de este cliente en los últimos 30 días?** → `notas`,
   filtrado por cliente, **de cualquier autor**.
3. **¿Compra algo de lo que se me vence?** → `ventas_cliente` × `vencimientos`.

Las tres fuentes existen y están cargadas. Lo que no existe es la pregunta
"¿quién está parado frente a quién, ahora?".

Y una versión agregada, una vez por día: **la ruta de mañana con la deuda sumada
por camión** (C5). Cuatro líneas de código y $168,7M a la vista.

---

## 4. Cómo se concilia con «cada uno ve su tramo»

Tu intuición es la correcta, y la escribo como regla operable. **No es mostrarle
el tablero: es traerle el cruce puntual que él puede accionar, en el momento en
que puede accionarlo.** Tres condiciones, y las tres tienen que darse:

> **1 · Le cambia lo que va a hacer en las próximas horas.** No «es interesante»:
> le cambia el acto. A Walter, que Doña Elsa prometió ponerse al día le cambia lo
> que dice al bajar del camión. Que el margen del feteado sea 80% no le cambia
> nada.
>
> **2 · Él puede hacer algo con eso, solo.** Si la única salida es «avisale a
> otro», el cruce no es suyo: es del otro, y a él le llega el resultado, no el
> problema.
>
> **3 · Llega enganchado a lo que ya está mirando, nunca como sección aparte.**
> El cruce de la deuda vive **adentro de la parada**. El de la explicación del
> pasillo 4 vive **adentro de la card de la diferencia**. Ninguno tiene pantalla
> propia. Una sección «Cruces» sería un tablero con otro nombre.

Y una cuarta que es la contracara y la que hace que el sistema se sostenga:

> **4 · Al que lo originó le vuelve el resultado, siempre.** Aunque el cruce lo
> haya accionado otro. Kevin no necesita ver la diferencia de $53.646; necesita
> ver que lo que dijo del pasillo 4 explicó una diferencia. Ésa es la mitad que
> convierte «te miramos» en «servís».

Con esas cuatro, el mismo cruce se reparte distinto y nadie ve de más:

| C1 · el salame | Qué recibe |
|---|---|
| **Aldo** | el cruce entero: vence en 11 días, $945.431, el mostrador lo puede sacar feteado al 80%, y libera la cámara. **Decide.** |
| **Vanesa** | «te habilitaron bajarle el precio al salame, tenés 11 días» |
| **Ramón** | «si sale el salame, entran 3 pallets en la cámara 2» |
| **Brian** | «lo que avisaste del salame: se está sacando por mostrador» |
| Tomás, Nahuel, Kevin, los choferes | nada |

---

## 5. El mapa en mobile

Tenías razón: **si el mapa es la superficie del cruce y sólo lo ven dos personas,
el resto del equipo nunca ve que su aviso sirvió para algo.** Hoy es peor que
eso: `require_feature("mapa")` lo tiene **sólo Aldo** — Ramón tampoco.

Pero la respuesta no es darle el lienzo a los nueve. El mapa de escritorio
—nodos, aristas, tres capas— es una herramienta de *exploración*, y explorar no
es lo que hace alguien con guantes.

**Propongo dos superficies distintas, no una achicada:**

**a · «Tu aviso en el mapa» — para todos.** Una sola pantalla, sin lienzo,
enganchada a cada aviso propio: *qué dijiste · con qué se cruzó · qué salió de
ahí*. Para Nahuel:

```
Lo que dijiste       «El remito dice 40 bultos, no 80»          03/07
Se cruzó con         lo que dijeron Ramón, Brian y Marta        3 personas
                     la orden OC-2026-0847                      165 un. pendientes
Salió                Celeste frenó la confirmación de la orden nueva
                     Marta no pagó la factura hasta que la corrijan
```

Es el círculo cerrado de P3 **con la parte del cruce adentro**, y es lo que hace
que alguien entienda para qué carga cosas. Sale de `grafo.caminos`, que ya
guarda el camino de nodos de cada hallazgo.

**b · El mapa como lienzo — para Aldo y Ramón.** La versión apilada que ya
existe (`MapaSimpleMobile.jsx`). Ramón necesita `mapa` en sus features: hoy no lo
tiene, y es el que hizo cuatro de los avisos que lo alimentan.

---

## 6. Resumen: qué tiene motor y qué no

### Dos columnas de plata, y no son lo mismo

Corrección pedida por Lucas, y tiene razón: poner los $111,8M de C5 y los
$53.646 de C7 en la misma columna se malinterpreta solo. Son dos cosas
distintas y hay que leerlas distinto.

> **PLATA A LA VISTA** — deuda o exposición que **ya existe** y que el cruce
> pone delante de alguien que puede hacer algo. **El cruce no la recupera ni la
> crea: la hace visible.** Cuánto de eso se cobra depende de la gestión, no del
> software, y prometer lo contrario sería exactamente el tipo de número que este
> producto no inventa.
>
> **PLATA QUE SE AHORRA** — lo que se pierde si nadie hace nada, y que la acción
> evita. Mercadería que se vence y se tira; un ajuste de stock hecho sobre una
> diferencia que no existía. Acá el cruce **sí cambia el resultado**, y el monto
> es el techo de la pérdida evitada, no una ganancia.

Un caso no entra en ninguna de las dos y por eso va vacío: C3, C6, C9 y C11
tienen un valor operativo real —no confirmarle una orden a un proveedor que
entregó la mitad, no recibir un camión sin lugar en cámara— pero **ponerles un
número sería fabricarlo.** Se quedan sin monto a propósito.

| Cruce | A la vista | Se ahorra | Motor hoy | Qué falta |
|---|---|---|---|---|
| C6 · cámara × orden entrante | — | — | **sí, calculado** | sólo ruteo a Ramón |
| C11 · queja de cliente clave | — | — | **sí, calculado** | sólo ruteo a Diego |
| C1 · salame vence × mostrador | — | $945.431 | parcial | cruzar con `mostrador.grupos` |
| C3 · Campo Alegre multicanal | — | — | parcial | unir `notas` con `piso`; contar reincidencia |
| C4 · Doña Elsa | $19.200.000 | — | parcial | ampliar tipos de nota; + ruta |
| C8 · góndola vacía × central | — | — | parcial | cruzar local × central × regla |
| **C2 · vence × compra × ruta** | — | **$6.825.532** | **no** | el cruce entero |
| **C5 · deuda por camión** | **$111.800.000** | — | **sí, construido** | — |
| C7 · pasillo 4 explica la diferencia | — | **$53.646** | no | juntar dos consultas |
| C9 · mortadela: hecho + evidencia | — | — | no | cae con el reclamo dirigido |
| C10 · «no me lleves más» × pedido | $42.000.000 | — | no | filtro sobre C5 |
| C12 · el jamón de Tomás | — | $876.101 | no | notas de conteo × vencimientos |

Sumar las dos columnas entre sí no significa nada. La de la izquierda tiene
solapamiento propio —Doña Elsa está adentro de los $111,8M de C5, y 9 de Julio
está en la misma cartera—, así que tampoco se suma consigo misma. Cada monto
responde a su propio cruce y no hay un total.

**El orden que quedó acordado, y en qué anda cada uno:**

1. **C5** — la deuda sumada por camión. **Hecho**, en `feat/deuda-por-camion`.
   Fue el mejor ratio plata/esfuerzo del documento, como estaba previsto — y el
   número había que deduplicarlo.
2. **Cerrar el círculo, con el ruteo de C6 y C11 adentro.** Mismo riel:
   destinatario, estado, notificar al que originó, «lo que reportaste» y «tu
   aviso en el mapa». *Siguiente.*
3. **C7** — la explicación de la diferencia. Chico, y es el que mejor enseña qué
   es este producto.
4. **C2** — la parada enriquecida. Es el eje que pediste y el que no tiene motor.

Después de esos: la ficha de armado de Brian, y los dos gratuitos (el costo de
536 días en la ficha de mostrador y «preguntarle a Ramón» para el que recién
entró).

---

## 7. Supuestos

- **[S13]** Que un cruce puntual en la pantalla que la persona ya está mirando se
  lee, y una sección «Cruces» no. Sale de la lección de Escala ConTech (diseñar
  desde la obra), no de observación de este equipo.
- **[S14]** Que el chofer puede colocar un lote que vence en la parada. Depende
  de si lleva mercadería suelta en el camión, que el dataset no dice. Si no
  puede, C2 sirve igual pero un día antes, en el preventista.
- **[S15]** Que la reincidencia («otra vez») es señal y no ruido. `cruces.py` ya
  la asume: `REINCIDENCIA_MIN = 2`, con el comentario *«pasó dos veces es patrón;
  una vez es anécdota»*.
- **[S16]** Que Ramón debería tener el feature `mapa`. Es un cambio de permisos,
  y va con la misma advertencia que el resto: lo decide Agustín.
- **Sobre los montos:** los que doy son valor del lote a costo. El motor calcula
  `plata_en_riesgo` = sólo el sobrante que no se vende antes de la fecha, que es
  menor. Los míos son el techo, no la pérdida esperada.
