# La superficie mobile, rol por rol

Diseño. Relevado contra `main` en `0778dda3`. Los mockups navegables:
[`prototipo/index.html`](prototipo/index.html) — 12 roles, 79 pantallas.
El flujo de devoluciones y reclamos tiene su propio documento:
[`01-DEVOLUCIONES-Y-RECLAMOS.md`](01-DEVOLUCIONES-Y-RECLAMOS.md).

---

## 1. La barra inferior

**Tres destinos + el botón de carga al centro. Nunca cinco.**

Guías: WCAG 2.2 SC 2.5.8 pide 24×24 px como piso legal, Apple recomienda 44×44 pt
y Material 48×48 dp. **Acá el piso es 48 y con separación amplia** — guantes,
frío y pantalla al sol. Con cinco ítems más un flotante, en 390 px cada destino
queda en ~65 px de ancho: entra, pero deja de perdonar el error, y el error acá
es tocar «Perfil» cuando querías «Trabajo».

Tres decisiones más, con su porqué:

**«Buscar» sale de la barra y va al encabezado.** Buscar no es un lugar, es una
acción, y no la usan todos: el de conteos llega a un producto desde su tarea y el
de armado desde el pedido. Un ítem fijo que dos oficios no tocan nunca es un
ítem que le robó el lugar a algo que sí usan. En el prototipo, la lupa aparece
sólo en los roles que la necesitan (§6).

**«Perfil» también sale.** Se abre desde el avatar del encabezado, que es donde
está en todas las apps que esta gente ya usa. Perfil es una visita por mes.

**El botón central cambia de significado.** Hoy en el código el centro es Ángela
(`MobileApp.jsx:144-154`). Propongo que sea **cargar**, y que Ángela sea uno de
los tres destinos. Razón: en la zona del pulgar va la acción primaria, y la
acción primaria de nueve de los doce roles es *meter algo al sistema*, no
preguntar. Ángela sigue a un toque, en el mismo alcance.

> **Lo que ya funciona y no toco:** la barra del código **ya es dinámica por
> features** — para Brian son hoy 4 slots y para Diego 3. El problema nunca fue
> que fuera rígida; era que los ítems no se eligen por oficio.

---

## 2. La superficie de cada rol

`Inicio` = dónde aterriza · `Barra` = los tres destinos · `Cargar` = lo que abre
el botón central.

### Depósito

| | Nahuel · recepción | Tomás · conteos | Brian · armado | Kevin · ayudante | Ramón · encargado |
|---|---|---|---|---|---|
| **Inicio** | Mi día | Mi día | Mi día | Mi día | Mi día (cola de decisiones) |
| **Barra** | Mi día · Recepción · Ángela | Mi día · Conteo · Ángela | Mi día · Armado · Ángela | **Mi día · Ángela** (dos) | Mi día · Depósito · Ángela |
| **Cargar** | Escanear · Hay un problema · Foto · Terminé de recibir | Escanear y contar · Contar una ubicación · No encuentro el producto | Escanear · No hay stock · Pedido armado | Escanear · Hay un problema | Escanear · Hay un problema · Pedir un conteo · Foto |
| **Cierra sin salir** | Un renglón del remito (1 toque) · balanzas (2) | Un conteo (3) | Un renglón del pedido (1) | Marcar hecha una tarea (1) | Una diferencia (1) |
| **Lupa** | no | no | no | no | sí |

### La calle

| | Walter · reparto | Diego · preventa |
|---|---|---|
| **Inicio** | Mi ruta (**una parada por pantalla**) | Mi ruta |
| **Barra** | Mi ruta · Lo mío · Ángela | Mi ruta · Clientes · Ángela |
| **Cargar** | Entregué · Me devolvió · Me pagó · No pude entregar | Tomar el pedido · Me pagó · Me pidió algo que no tenemos · Foto de la góndola |
| **Cierra sin salir** | Una entrega (2 toques) | Un renglón del pedido (1) |
| **Lupa** | no | **sí** |

### El local

| | Vanesa · mostrador | Norma · sucursal |
|---|---|---|
| **Inicio** | Mostrador (**la pantalla ES la búsqueda**) | Mi local |
| **Barra** | Mostrador · Caja · Ángela | Mi local · Caja · Ángela |
| **Cargar** | Escanear · Me pidieron algo que no hay · Rendir la caja | Me falta stock · Novedad del día · Cerrar la caja |
| **Cierra sin salir** | Anotar un faltante (2 toques) · rendir la caja (2) | Pedir reposición (2) · cerrar caja (1) |
| **Lupa** | **sí** | sí |

### La oficina

| | Marta · administración | Celeste · compras | Aldo · dueño |
|---|---|---|---|
| **Inicio** | Pendientes | Compras (lo que le dirigieron) | **Decidir** |
| **Barra** | Pendientes · Documentos · Ángela | Compras · Proveedores · Ángela | Decidir · Negocio · Ángela |
| **Cargar** | Foto de un comprobante · Registrar un pago · Subir un archivo | Foto de una lista · Anotar algo de un proveedor · Subir un archivo | **Anotar una regla** · Foto · Pedirle algo a alguien |
| **Cierra sin salir** | Aprobar un comprobante (1) | Armar un reclamo (1) | Aprobar (1) |
| **Lupa** | sí | sí | sí |

**El dueño hoy aterriza en un chat vacío** (`MobileApp.jsx:81`:
`defaultView = piso ? "mi_dia" : "angela"`). Su vista-herramienta es su cola de
decisiones, con exactamente la misma forma que la de cualquier otro. Y su poder
extra vive en una capa que para los demás no existe —`Negocio`, el mapa, las
reglas— no en más botones en las pantallas compartidas.

---

## 3. Qué agregué, qué saqué, y por qué

Las imágenes traen **nueve acciones iguales para todos** (Escanear, Foto, Voz,
Registrar, Reportar problema, Crear pedido, Devolución, Cobro, Nota) — y ya se
contradicen solas: el Inicio del iPhone muestra seis, sin criterio visible de
cuáles se cayeron. Eso ya es la señal de que la lista quiere ser por oficio.

### Lo que saqué, y de quién

| Acción | Se la saqué a | Por qué |
|---|---|---|
| **Cobro** | Nahuel, Tomás, Brian, Kevin, Ramón | Nadie del depósito cobra. Era ruido en la pantalla de cinco personas. |
| **Crear pedido** | los cinco del depósito, Walter | No levantan pedidos. Walter entrega los que ya existen. |
| **Devolución** | Tomás, Brian, Kevin | Una diferencia de conteo o un faltante de picking no es una devolución. |
| **Recepción / Registrar remito** | Walter, Diego, Vanesa, Tomás, Brian | No reciben mercadería de proveedor. |
| **Nota (genérica)** | **todos** | Ver abajo — es el cambio más grande. |
| **Voz (como tile suelto)** | todos | Ver abajo. |
| **Foto (como tile suelto)** | Tomás, Brian, Walter, Vanesa | La foto es un paso *adentro* de un flujo, no un destino. Sacar una foto que no está enganchada a nada produce una foto que nadie mira. |

### «Nota» y «Voz» dejan de ser botones

**Esto es lo que más cambia respecto de las imágenes, y es deliberado.**

- **«Nota — agregar información» desaparece como tile.** Una nota genérica es
  exactamente el objeto que el modelo de flujo identificó como roto: nace sin
  destinatario y se muere. En su lugar, cada rol tiene **sus** avisos como
  botones directos (§5), y el destinatario lo propone Ángela y lo confirma la
  persona. La escritura libre sigue existiendo: es la última opción, detrás del
  micrófono, no la primera.
- **«Voz» deja de ser un tile y pasa a ser una franja fija al pie de cada hoja
  de carga.** Motivo: como tile compite con los otros ocho, cuando en realidad
  es *otra forma de hacer cualquiera de ellos*. En el prototipo es la banda azul
  «Decirlo hablando», siempre en el mismo lugar, siempre alcanzable con el pulgar.

### Lo que agregué

| Nueva acción | Para quién | Qué resuelve |
|---|---|---|
| **Armado renglón por renglón** | Brian | Arma pedidos todo el día y **hoy no tiene ni una acción de su oficio** |
| **No hay stock (en un renglón)** | Brian | El faltante de picking hoy se grita al galpón y no queda |
| **Terminé de recibir** | Nahuel | Cerrar la descarga es un hecho, y hoy la recepción no se cierra |
| **Contar una ubicación** | Tomás | Cuenta por lugar, no por producto suelto |
| **No encuentro el producto** | Tomás, Kevin | El caso más común del depósito, y no está en ningún lado |
| **Pedir un conteo (a alguien)** | Ramón | Un encargado asigna; hoy sólo el dueño puede poner `para` |
| **Preguntarle a Ramón** | Kevin | `usuarios_demo.py` le declara `mentor: "ramon"` y **ninguna pantalla lo usa** |
| **No pude entregar (con motivo)** | Walter, Osmar | Es lo que hoy se muere en WhatsApp: dos de sus notas del dataset son esto |
| **Lo último de este cliente** | Diego, Lucía | Cruza las notas del equipo con la cuenta: ver §8 |
| **Rendir la caja del día** | Vanesa, Norma | Tu ejemplo. Es lo último que hacen todos los días y no estaba |
| **Me pidieron algo que no había** | Vanesa | La demanda no vendida no queda en ningún lado del ERP |
| **Anotar una regla (hablando)** | Aldo | Es cómo crece el diferencial del producto, y hoy vive sólo en desktop |

### Lo que se queda tal cual de las imágenes

La grilla de acciones rápidas como **patrón** (no como contenido); la pantalla de
escaneo con producto detectado; la conversación de Ángela que registra, **cita lo
que registró con sus identificadores** y recién después ofrece informar a
Compras; el Inbox con solapas; la ficha de cliente con franja de datos duros y
tabs. El lenguaje visual entero: tarjetas blancas sobre fondo claro, acentos por
color de estado, íconos redondeados.

---

## 4. Presupuesto de toques

**Cambié la vara del brief y lo digo en vez de maquillarlo.** «3 toques o menos»
es correcto para una cosa y falso para otra:

- **Cerrar** algo ya propuesto en pantalla: **≤ 3 toques.**
- **Originar** un hecho con evidencia para un tercero: **≤ 6 toques**, y cada
  toque tiene que reemplazar una pregunta que hoy se hace por WhatsApp.

Forzar el reclamo a tres toques sólo se logra sacándole la foto o el lote — es
decir, mandando un reclamo que el proveedor va a rechazar.

| Flujo | Rol | Toques | Tipo |
|---|---|---|---|
| Confirmar un renglón del remito | Nahuel | **1** | cerrar |
| Confirmar un renglón de picking (escaneo) | Brian | **1** | cerrar |
| Decidir una diferencia de conteo | Ramón | **1** | cerrar |
| Aprobar el reclamo | Aldo | **1** | cerrar |
| Sumar un renglón habitual al pedido | Diego | **1** | cerrar |
| Corregir las balanzas | Nahuel | **2** | cerrar |
| Confirmar una entrega con foto | Walter | **2** | cerrar |
| Anotar «me pidieron y no había» | Vanesa | **2** | originar |
| Rendir la caja | Vanesa | **2** | cerrar |
| Pedir reposición | Norma | **2** | originar |
| Registrar un conteo | Tomás | **3** | cerrar |
| Avisar «no hay stock» en un renglón | Brian | **3** | originar |
| **Reclamo completo, hablando** | Nahuel | **3** | originar |
| Devolución del cliente en la puerta | Walter | **4** | originar |
| «No pude entregar» con destinatario | Walter | **4** | originar |
| **Reclamo completo, tocando** | Nahuel | **6** | originar |

---

## 5. Los avisos habituales por oficio — **para cerrar entre los dos**

No sembrar todavía. Cada lista tiene 4 botones (5 como máximo) más «es otra cosa,
decilo hablando». Marcadas **[SUPUESTO]**: no hay un dato de esto en el repo —
las 31 notas sembradas tienen otra forma, y PolPilot no tiene usuarios activos.

**Depósito · recepción (Nahuel)** — los cuatro son los motivos que **ya existen**
en `core/piso.py:62` (`roto · faltante · vencido · no_pedido`), así que éste es
el único caso que no es supuesto:
> Vino roto · Vino de menos · Vino vencido o por vencer · No era lo que pedimos
>
> *Quité «el camión no llegó» del brief: es un aviso de la orden, no de la
> mercadería, y su lugar natural es la pantalla de la recepción («el camión de
> hoy no vino»), no la lista de problemas de un producto.*

**Depósito · conteos (Tomás)** [SUPUESTO]:
> Hay menos de lo que dice el sistema · Hay más · No encuentro el producto ·
> Está en otra ubicación

**Depósito · armado (Brian)** [SUPUESTO] — no estaba en el brief:
> No hay stock de este renglón · Hay menos de lo que pide el pedido ·
> El producto está roto · No entra en el bulto

**Depósito · ayudante (Kevin)** [SUPUESTO] — deliberadamente dos:
> No encuentro algo · Algo no me cierra (va a Ramón)

**Encargado (Ramón)** [SUPUESTO]:
> No entra más en la cámara · Falta gente para hoy · Se rompió algo ·
> Este proveedor entregó mal otra vez

**Chofer (Walter, Osmar)** [SUPUESTO] — los cuatro del brief menos uno:
> El cliente no estaba · Rechazó parte del pedido · No pudo pagar ·
> La dirección está mal · Me devolvió mercadería
>
> *Son cinco y me parece el máximo tolerable. «Me devolvió mercadería» tiene
> flujo propio (es la devolución), así que en el prototipo vive en el botón de
> carga, no en esta lista.*

**Preventista (Diego, Lucía)** [SUPUESTO]:
> Me pidió algo que no tenemos · Me pidió otro precio · Está comprando en otro
> lado · Está por cerrar / complicado
>
> *Cambié «me preguntó por una promoción» por «está comprando en otro lado»:
> la segunda aparece literal en el dataset (nota `nt05`, Diego sobre La Rural)
> y la primera no aparece nunca.*

**Mostrador (Vanesa)** [SUPUESTO]:
> Me pidieron algo que no había · Un cliente reclamó · Este precio parece mal ·
> Se está por acabar

**Encargada de sucursal (Norma)** [SUPUESTO]:
> Me falta stock de algo · Novedad del día · Diferencia de caja ·
> Un cliente reclamó

**Administración (Marta) y Compras (Celeste)**: no tienen lista de botones. Son
oficinas: escriben, no avisan desde el piso. Su carga es foto de comprobante y
subida de archivo.

---

## 6. La búsqueda en mobile

Pantalla `buscar` del prototipo. Tres decisiones:

**1 · La caja va abajo, no arriba.** Con el teclado abierto queda pegada al
pulgar, y los resultados crecen hacia arriba con el más relevante más cerca de la
mano. Es el patrón de las apps de mensajería que esta gente ya usa diez veces por
día.

**2 · El escaneo comparte la caja.** Para el depósito, un código de barras **es**
una búsqueda: el mismo cuadro, dos formas de entrar.

**3 · Ángela es una fila del resultado, y su posición la decide el backend.**
`buscador.parece_pregunta()` (`core/buscador.py:130`) ya distingue un nombre de
una pregunta —más de cuatro palabras, o un signo de interrogación— y sólo decide
orden. «Doña Elsa» → Ángela va última. «¿Qué pasa con Doña Elsa?» → Ángela va
primera. Ésas son las dos velocidades: abrir una ficha son 300 ms y no amerita un
turno de chat, ni gastar el cap de mensajes del demo público.

Cada resultado trae `seccion` + `foco`, así que el toque **abre enfocado en la
fila que motivó la visita** (Focus Rule), nunca en la fila 1 de 430.

**Quién la necesita** (la lupa aparece sólo ahí):

| Mucho | Bastante | Nada — se la saco |
|---|---|---|
| Vanesa (mostrador) · Diego y Lucía (preventa) · Marta | Celeste · Ramón · Norma · Aldo | Nahuel · Tomás · Brian · Kevin · Walter y Osmar |

Los seis de la última columna llegan al dato **por escaneo o desde su tarea**, que
es más rápido y no se equivoca de producto. Nahuel es el caso interesante: parece
que debería buscar, y no — tiene la caja en la mano.

---

## 7. Las pantallas de datos

El desktop tiene 34 secciones en `CATALOGO` (`DesktopApp.jsx:107`). El criterio
para mobile no es cuáles caben: es que **la entrada correcta a un dato en el
teléfono casi nunca es una lista — es un escaneo, una búsqueda, o una tarea que
ya lo trae enfocado.** Una lista de 430 productos no la scrollea nadie con guantes.

### Se quedan como están

`perfil` · `prioridades/insights` · `equipo` · `aprendizaje` · `documentos`
(la carpeta con el patrón campo/valor/fuente/estado ya **es** una cola de
revisión, no una tabla) · `caja` · **la lista de clientes del preventista** (son
24 y son suyos; se ordenan por lo que hay que hacer, no alfabéticamente).

### Cambian de forma

| Sección | En mobile es | Se llega desde |
|---|---|---|
| `productos` | **La ficha, nunca la lista** — y distinta por rol: Nahuel ve ubicación, lote y vencimiento; Vanesa ve precio, stock y qué tan viejo es el costo | escaneo · búsqueda · tarea |
| `deposito` | Dos colas de decisión: **vence pronto** y **diferencias sin resolver** | Mi día |
| `logistica` | **Una parada por pantalla** | Mi ruta |
| `recepciones` / `ordenes_compra` | «Lo que llega hoy», controlado renglón por renglón | Mi día |
| `cuentas` / `cobranzas` | La ficha del cliente que estás visitando | la ruta · búsqueda |
| `conciliacion` | Sólo la diferencia que te toca decidir | Mi día |
| `saneamiento` | Sólo las tareas cerrables (esto ya funciona así en `MiDia.jsx`) | Mi día |
| `proveedores` | La ficha, con **qué pide para un reclamo** | desde el reclamo |
| `mapa` | La versión apilada que ya existe, y sólo para Aldo y Ramón | Negocio |

### No van en mobile

`ventas` · `movimientos` · `evolucion` · `finanzas` · `auditoria` · `conectores` ·
`admin_contexto` · `imported` · `ubicaciones` (la grilla de 21) · `staging` (la
lista; sí el batch que te toca) · `inventario` (la grilla de 430).

Todas son tablas anchas para barrer muchas filas buscando la que está mal. **Ésa
es la fuerza de una tabla y la debilidad de un teléfono.** Van a desktop, donde
están, y en mobile se alcanzan por el hallazgo que las motiva.

---

## 8. Propuestas nuevas, por impacto

Cada una: qué resuelve · para quién · qué cuesta · qué le devuelve a la persona
por el hábito que le pedimos cambiar.

**1 · «Lo que reportaste», con su estado.**
El endpoint existe y ninguna pantalla lo llama (`api.piso.reportes`,
`lib/api.js:277`); el backend hasta filtra por actor para eso (`main.py:1315`).
Sumado a que `piso.resolver` emita la notificación al que originó.
*Para:* los ocho de piso. *Cuesta:* dos días. *Devuelve:* la única razón para no
volver al grupo de WhatsApp. **Es lo más barato y lo más decisivo que hay acá.**

**2 · La ficha de armado de Brian.**
Un rol completo sin superficie: la regex de `lib/roles.js:21` lo mete en
«depósito» y le ofrece cargar remitos y marcar conteos, que no son su trabajo.
*Cuesta:* partir el rol en `roles.js` + una pantalla de picking. *Devuelve:* que
lo que arma quede registrado, y que un faltante llegue a Compras sin gritarlo.

**3 · La parada como pantalla.**
Una parada por pantalla con tres botones de 70px, en vez de una lista de nueve.
*Para:* Walter y Osmar. *Devuelve:* poder cerrar una entrega sin apoyar el
teléfono.

**4 · El reclamo guiado por proveedor.** Documento aparte.

**5 · «Lo último de este cliente» para el preventista.**
Cruza `core/notas.py` con `core/cuentas.py` y le pone delante a Diego lo que
dijeron Walter y él mismo **antes de entrar al local**. Hoy la nota de Walter
sobre San Martín cerrado vive sólo en el mapa del dueño, y el que puede hacer
algo no la ve. *Cuesta:* poco, las dos fuentes existen. *Devuelve:* no entrar a
un cliente sin saber lo que pasó la semana pasada.

**6 · Rendir la caja del día.**
Tu ejemplo, y tenías razón: los 153 cierres por local y fecha ya están sembrados
(`core/mostrador.py`); falta la pantalla donde se rinde **y la diferencia queda
explicada por quien la vio**. *Para:* Vanesa y Norma. *Devuelve:* que Marta no
las llame al día siguiente a preguntar de qué era la diferencia.

**7 · La antigüedad del costo, donde alguien puede hacer algo.**
Descubrimiento del relevamiento: el jamón cocido de mostrador tiene el costo
cargado hace **536 días** (`antiguedad_costo_dias`, dato real del dataset), y su
precio se calculó sobre eso. Hoy ese número vive en un análisis de desktop.
En la ficha de Vanesa, que es quien revisa los precios de fiambres por regla de
la casa, es accionable. *Cuesta:* casi nada. *Devuelve:* dejar de vender abajo
del costo sin saberlo.

**8 · «Preguntarle a Ramón» para el que recién entró.**
`usuarios_demo.py` le declara `mentor: "ramon"` a Kevin y ninguna pantalla lo
usa. El bloque de onboarding ya existe y se apaga solo. *Cuesta:* nada.
*Devuelve:* a un tipo de una semana, un lugar donde preguntar sin exponerse.

**9 · Progreso personal, nunca comparación.**
Tomás ve «contaste 14 de 21 ubicaciones». No hay ranking entre compañeros en
ninguna pantalla, y está dicho en la pantalla misma. Hay evidencia de que los
rankings empeoran el clima en trabajo de primera línea; el hábito se refuerza
con progreso propio.

**10 · El chip de «guardado, se manda solo» siempre visible.**
Si sólo aparece cuando falla la red, la primera vez que aparezca nadie va a
saber qué significa. *(Sin motor — ver §9.)*

---

## 9. Qué tiene motor y qué no

### Tiene motor hoy — se puede construir con lo que hay

- Las tareas cerrables desde el piso (`saneamiento`, ya funciona en `MiDia.jsx:105`)
- Reportar faltante / conteo / entrega / reposición / pedido (`piso.reportar`)
- La voz con validación de cantidad y candidatos de producto (`core/voz.py`)
- La foto como prueba, guardada como archivo (`piso.py` · `adjuntos`)
- Recepciones contra orden de compra abierta (`apartados.ordenes_compra`)
- Vencimientos y diferencias de depósito (`core/deposito.py`)
- Hoja de ruta y estado de envíos (`core/logistica.py`)
- Ficha de cliente con deuda, plazo y promedio de pago (`core/cuentas.py`)
- Reglas de la casa, con fuente y contador (`core/conocimiento.py`)
- Búsqueda global con gate por tipo (`/api/buscar-global`)
- Cierres de mostrador por local y fecha (`core/mostrador.py`)
- Tareas asignadas y su cierre (`core/recordatorios.py`)
- Notificación interna por campanita (`core/notificaciones.py`)

### No tiene motor — es pantalla, y lo digo

| Diseñado | Qué falta | Tamaño |
|---|---|---|
| **El aviso con destinatario y acuse** | `destinatario` + `estado` en el reporte de piso, y unificarlo con `notas` (que hoy **no tiene API de escritura**) | Medio |
| **«Lo que reportaste» con su estado** | Consumir un endpoint que ya existe | Chico |
| **Que cerrar avise al que originó** | `piso.resolver` → `notificaciones.emitir` | Chico |
| **Todo lo offline** | No hay service worker, ni manifest, ni IndexedDB, ni cola local. Nada. | Grande |
| **Ramón decidiendo** | Un permiso entre piso y dueño. **Diseñado como si existiera; no se construye acá** — tocar `authz` lo decide Agustín | Medio |
| **Requisitos de reclamo por proveedor** | Un valor en `EFECTOS` + leer `params.reclamo` | Chico |
| **Armado / picking** | Pantalla y ficha de rol nuevas | Medio |
| **El escalado del aviso no visto en N horas** | No hay scheduler; `recordatorios` evalúa de forma perezosa al listar | Medio |
| **Push al teléfono** | El código dice explícito que no se finge (`recordatorios.py:80`) | Fuera de alcance |

---

## 10. Tres cosas donde me aparté de las imágenes

**1 · El azul deja de ser el color de los botones primarios.**
En las imágenes todo lo importante es azul: botones, tabs activas, badges.
`DESIGN.md` dice lo contrario y con todas las letras: *«Ángela Blue sólo
significa el agente de IA»*, y `button-primary` es `tinta` (#21201d). En el
prototipo el primario es tinta y **el azul aparece únicamente donde habla o
propone Ángela**. Se nota apenas se mira una pantalla: el ojo va derecho a lo que
propuso el sistema y lo distingue de lo que decidís vos. Si preferís el azul de
las imágenes, es cambiar dos variables — pero perdemos esa lectura.

**2 · «Juan Pérez / Vendedor» no existe.** El equipo del dataset son 14 personas
con nombre; los preventistas son **Diego** (zona centro) y **Lucía** (zona sur).
Todo el prototipo usa gente, productos, clientes, proveedores, lotes, órdenes y
pedidos reales del demo. El logo es el del repo (`frontend/public/logos/polpilot.png`).

**3 · La ilustración de la caja y la bolsa: va la evidencia.** Como acordamos, en
la tarjeta de atención va **la foto real** —el remito, la mercadería— que
`piso.py` ya guarda como adjunto. Un tipo con guantes reconoce su propia foto en
un segundo; una caja dibujada no le dice nada. En el prototipo se ve como un
placeholder rayado con la leyenda de qué foto es.

---

## 11. Supuestos sobre el trabajador

PolPilot no tiene usuarios activos. Todo esto es hipótesis, no dato.

- **[S1]** Que el de piso deja de usar la app si no ve qué pasó con lo que cargó.
- **[S2]** Que nadie del piso quiere elegir un destinatario de una lista de 14.
- **[S3]** Que los avisos habituales de cada oficio son los de §5.
- **[S4]** Que el encargado de depósito quiere y puede decidir sobre su dominio.
- **[S5]** Que el picking es un oficio distinto y no una variante de recepción.
- **[S10]** Que tres destinos alcanzan para todos los oficios de piso. El que más
  tensiona es Ramón, que es encargado y tiene ocho módulos.
- **[S11]** Que el escaneo es más rápido que la búsqueda para el depósito. Es lo
  que dicen los benchmarks del rubro; con este equipo, no lo sabemos.
- **[S12]** Que la voz se usa. Depende del ruido real del galpón, y por eso toda
  pantalla con voz tiene alternativa táctil sin excepción.
