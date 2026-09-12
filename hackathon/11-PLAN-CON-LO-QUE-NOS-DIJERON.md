# El plan, rehecho con lo que nos dijeron en la sede

11 de septiembre de 2026, de noche. Reemplaza a `09-COMO-SEGUIR.md` y a
`10-GUION-DEL-DEMO.md` en todo lo que se contradiga.

---

# 1 · El guion de 2:30

150 segundos. La estructura es la que nos repitieron todos por separado: de lo
macro a lo micro, arrancando por el problema.

## Lo que entra

| Tiempo | Qué | Qué se dice |
|---|---|---|
| **0:00–0:30**<br>30 s | **El problema, en grande** | "El cerebro de cualquier empresa hoy es su sistema de gestión. SAP, Tango, el que sea. Pero ese cerebro no está conectado con el cuerpo. El depósito no funciona como el mostrador, el reparto no funciona como compras — cada parte trabaja distinto, y el cerebro recibe apenas una parte de lo que pasa. Y para el que está en el piso, ese sistema es imposible de usar." |
| **0:30–0:45**<br>15 s | **A quién le duele, y el caso** | "Un cliente te devuelve mercadería. Cada proveedor funciona distinto: a uno le escribís por mail, a otro le mandás foto del lote, otro te da cinco días. Y cambia según el producto. Eso no está escrito en ningún lado: está en la cabeza de dos personas." |
| **0:45–1:35**<br>50 s | **Capa 1 — lo que ve el usuario** | La pantalla del depósito. "Nahuel recibe ocho cajas rotas. No elige nada, no busca nada: el sistema le pide **exactamente** lo que este proveedor necesita. El lote ya lo sabe. El remito ya lo sabe. Lo único que le pide es la foto." |
| **1:35–2:15**<br>40 s | **Capa 2 — cómo funciona atrás** | El grafo. **"Esto es lo que ve el que está en el depósito. Esto es lo que pasa por atrás para que él no tenga que saber nada."** Se enciende el camino: lo que dijo una persona por WhatsApp, lo que sabía el sistema, y dónde se cruzaron. |
| **2:15–2:30**<br>15 s | **Cierre** | "En cuatro años todos los sistemas de gestión van a tener IA adentro. Ese motor va a ser un commodity. Lo que le va a faltar es el alimento: el contexto de cómo funciona realmente esa empresa. Eso es lo que construimos." |

## Lo que pasa a reserva

Coincido con tu intuición, con una salvedad al final.

| Qué | Por qué sale | Cuándo se usa |
|---|---|---|
| **El contrafáctico** | Es espectacular pero necesita 20 s bien hechos | Si preguntan "¿cómo sé que no lo inventó?" |
| **El punto ciego** | 25 s. Es el golpe emocional y duele sacarlo | Si preguntan por el equipo, o si sobra tiempo |
| **Los evals** | Necesita explicar qué es un eval. Muy caro en 2:30 | Si preguntan "¿qué tan preciso es?" |
| **El MCP** | Sólo le habla a quien ya sabe qué es MCP | Si preguntan por integración o por agentes |
| **La animación del camino** | Cuatro segundos que se pueden reemplazar por encender el camino de una | Si el ritmo lo permite en la capa 2 |

**La salvedad:** esto vale **si la capa 1 existe**. Si la pantalla de
devoluciones no llega a estar, el guion se cae — no hay "solución que ve el
usuario" que mostrar, y quedamos contando el grafo, que es exactamente el
error que nos advirtieron (empezar por la arquitectura). Ver §5.

---

# 2 · Las dos capas: qué falta construir

## Lo que ya existe y sirve

| Pieza | Dónde | Qué aporta |
|---|---|---|
| Memoria de reglas con `params` libre | `core/conocimiento.py` | "Qué pide cada proveedor" entra sin tabla nueva |
| Reporte del piso, tipo `faltante` | `core/piso.py` | El riel por donde entra el hecho |
| Procedencia por campo | `core/carpeta.py` | `valor` / `fuente` / `estado` — **es exactamente la forma de "lo que este proveedor pide, ya completado hasta donde se pudo"** |
| Círculo cerrado | `core/mis_avisos.py` | El reclamo llega a alguien y vuelve |
| Voz del piso | `core/voz.py` | La frase que colapsa pasos |
| Superficie mobile por oficio | `frontend/src/mobile/` | Dónde vive la pantalla |

## Lo que falta

Del documento de diseño (`design/mobile/01-DEVOLUCIONES-Y-RECLAMOS.md`, rama
`design/mobile-roles`), lo único estructural que falta en el backend es **una
línea**: agregar `exige_evidencia` al catálogo `EFECTOS` de
`conocimiento.py:47`. Todo lo demás es superficie.

### Versión mínima que se ve bien en demo

**Costo: 5 a 6 horas.** Tres piezas:

1. **Tres piezas de conocimiento sembradas** (~45 min). Una por proveedor, con
   requisitos distintos a propósito — porque la diferencia entre proveedores
   *es* el punto:
   - Campo Alegre: foto del lote + número de remito, por mail, 5 días.
   - La Ribera: número de remito nada más, por WhatsApp, 48 h.
   - Guaraní: foto + lote + remito + conformidad del transportista, 10 días.
2. **La pantalla** (~3 h). Cuatro pasos, seis toques: qué pasó → cuánto → lo
   que pide este proveedor (ya tildado lo que el sistema sabe) → a quién le
   llega. Lo que hace el momento es el paso 3: **dos tildes verdes y un solo
   pedido**.
3. **El reclamo armado** (~1,5 h). Que el resultado sea un aviso dirigido real
   por el riel que ya existe, con la evidencia adentro.

**Qué NO entra en esas horas, y hay que decirlo si preguntan:** mandar el mail
o el WhatsApp de verdad al proveedor. El reclamo queda armado y aprobado
adentro del sistema; el envío es el paso siguiente.

---

# 3 · El consejo del CTO de Clicky

## "Preguntar es la respuesta" — sí, y es casi gratis

Es el mejor encaje de toda la jornada, porque **el mecanismo ya está
construido**. `carpeta.py` guarda por campo un `estado`: `completo`, `falta`,
`opcional`. Un documento incompleto se muestra igual, con los huecos marcados.

Eso *es* preguntar. Lo único que falta es darlo vuelta en la superficie: en vez
de mostrar un formulario con campos vacíos, mostrar **una sola pregunta por
vez, y sólo las que faltan**.

**Costo: +1 hora encima de la pantalla de devoluciones.** Va junto, no aparte.

La frase para la sala: *"no le pedimos que llene un formulario. Le pedimos lo
único que falta, porque el resto ya lo sabemos."*

## La arquitectura de dos modelos — factible, y hay algo mejor que decir

**Es factible y parte ya está.** Tres cosas:

1. **Modelo chico para herramientas.** `config.py` ya resuelve proveedor y
   modelo por variable (`ANGELA_MODEL`); poner haiku para el camino de
   tool-use es configuración, no refactor.
2. **Cargar herramientas según de qué parte del negocio se hable.** **Esto ya
   lo hacemos, por otro eje.** `angela.TOOL_FEATURE` filtra las herramientas
   por el rol del usuario, y el servidor MCP hace exactamente el mismo filtrado
   antes de listar. Filtrar por *tema* en vez de por *rol* es el mismo
   mecanismo con otra llave.
3. **El modelo que razona por atrás, en los 30-40 s.** Esto sí es nuevo: una
   tarea que prepara contexto para la pregunta siguiente. **~1 jornada.**

**La respuesta si preguntan por velocidad** —y con Rauch dando vueltas, van a
preguntar— es mejor que la arquitectura:

> "Lo más rápido es no llamar al modelo. Todos los números de este producto los
> calcula código, no el modelo; el modelo pone las palabras. Por eso una
> pantalla como ésta responde en milisegundos. Y para el chat, el filtrado de
> herramientas por contexto ya está: no le colgamos cincuenta herramientas al
> modelo, le damos las de la parte del negocio de la que se está hablando."

Eso es verdad hoy y es más fuerte que prometer una arquitectura.

---

# 4 · Fricción y offline

## Offline: qué costaría y qué contestamos

**La versión completa** (service worker + cola local + sincronización) es **1
jornada larga y es riesgosa**: si falla en vivo, falla en el momento más
visible.

**La versión mínima honesta que sí se puede mostrar: 3 horas.** No es offline
de verdad — es **el modelo de datos que el mentor nos describió**, funcionando:

- Dos marcas de tiempo en el reporte del piso: `ocurrido_en` y `registrado_en`.
- Una nota sembrada donde las dos difieren (ocurrió 10:00, llegó 11:00).
- La pantalla ordena por **hora de registro**, muestra las dos, y marca cuál
  llegó primero aunque haya sincronizado después.
- La decisión final la toma la persona.

Eso demuestra que entendimos el problema sin afirmar que funciona sin conexión.

**Mi recomendación: no construirlo.** No entra junto con devoluciones, y
devoluciones vale más. **La respuesta preparada:**

> "Está diseñado, no construido, y te digo exactamente cómo: dos marcas de
> tiempo, la del momento en que ocurrió y la del momento en que llegó a la
> base. Si alguien registró a las 10 sin señal y sincronizó a las 11, y a las
> 10:30 pasó otra cosa sobre lo mismo, **tiene prioridad el de las 10**. El
> sistema lo ordena por hora de registro, se lo muestra a una persona, y la
> decisión es de ella. Es el modelo de las valijas de aerolínea."

Decirlo con ese nivel de detalle prueba que lo pensamos. **Y es el mentor que
ya sabe que es nuestro punto débil el que lo va a preguntar** — contestarle con
su propio consejo bien entendido es lo mejor que podemos hacer.

## Entrenamiento: la voz

Respuesta corta, ya la tenemos construida a medias (`core/voz.py`):

> "Con la voz. La interfaz de la capa agéntica puede ser un chat de voz: le
> hablás y contesta. Sin internet, una capa mínima que transcribe y deja la
> ejecución para cuando haya señal."

---

# 5 · Diseño: qué está flojo

Ordenado por lo que se va a proyectar.

## El grafo — el problema más grande

**Hoy abre con 559 nodos y eso es una nube.** El núcleo emerge, pero emerge
después de 220 ticks de simulación, y el que mira no sabe que tiene que
esperar. El primer segundo decide si el jurado se engancha, y hoy lo gasta una
mancha que se mueve.

| Qué | Costo | Por qué |
|---|---|---|
| **Estado inicial que enseña** | 1,5 h | Que abra **ya con el camino del hallazgo encendido** y el resto al 6%, en vez de con todo. El jurado entra a una historia, no a una nube |
| **Entrar en modo Proyectar** | 15 min | Que "Proyectar" esté activo por defecto cuando se llega desde un hallazgo |
| **La transición de claro a oscuro** | 30 min | El lienzo negro dentro de un producto blanco entra de golpe. Un degradado corto en el borde lo cose |
| **Etiquetas del camino siempre visibles** | 45 min | Hoy dependen del zoom. En el camino encendido tienen que estar sí o sí |

## La pantalla de devoluciones — nace ahora, que nazca bien

Es la que más se va a mirar y no existe todavía. Que salga con: tipografía
grande de verdad (es una pantalla de depósito, se mira con el celular en una
mano), **una sola decisión por pantalla**, las tildes verdes de lo que el
sistema ya sabe bien visibles, y el pedido único destacado. Nada de formulario
denso. El azul sigue siendo de Ángela: los tildes van en salvia, el pedido
pendiente en oro.

## Lo que NO tocaría

La tarjeta de atención del inicio y el mapa de la operación están bien. El
tiempo es escaso y no es ahí donde se gana.

---

# 6 · Qué construiría, en orden

Sabiendo que el pitch es de 2:30, que el jurado **sólo ve lo que mostramos en
vivo**, y que quedan unas 20 horas.

| # | Qué | Horas | Por qué en ese lugar |
|---|---|---|---|
| 1 | **La pantalla de devoluciones (capa 1)**, con el "pide sólo lo que falta" adentro | **6–7** | Sin esto no hay guion. Es la mitad del pitch y es lo que más se va a mirar |
| 2 | **El grafo: estado inicial que enseña** + Proyectar por defecto | **2** | Es la capa 2, es lo que se proyecta, y hoy abre mal |
| 3 | **Ensayar cronometrado, 5 veces** | **2** | Nos lo dijeron explícitamente y es donde más equipos se caen |
| 4 | **Precalentar y probar la demo entera en la máquina y la pantalla reales** | **1** | Ya está el script. Sin esto, 15 s de pantalla quieta |
| 5 | *(si sobra)* Las dos marcas de tiempo | 3 | Sólo si 1 a 4 están cerrados y probados |

**Suman 11–12 horas de las ~20.** El resto es colchón, y el colchón es a
propósito: el riesgo más grande no es que falte una feature, es que algo se
rompa en vivo.

## Lo que NO construiría

- **Offline de verdad.** Riesgoso y hay respuesta preparada.
- **La arquitectura de dos modelos.** Es una respuesta, no una feature.
- **Nada nuevo en el grafo** más allá del estado inicial. Ya tiene de sobra.
- **Combinar tracks.** El dataset es una distribuidora de alimentos, no agro.
  Forzar AgroTech nos hace perder foco en IA, que es el track donde tenemos
  algo real. Se juzgan por separado, así que no hay upside en presentarse mal
  en dos.

---

# 7 · Dos cosas que encontré y hay que decidir

**La regla dice "algo realmente funcionando en producción".** Hoy corremos en
local. Hay `render.yaml` listo y `deploy/DEPLOY.md` escrito, pero desplegar
lleva tiempo y mete riesgo. Hay que decidir si "producción" significa
desplegado o alcanza con que funcione en vivo. Si hay que desplegar, es 1–2 h y
conviene hacerlo mañana temprano, no a última hora.

**El CI lleva dos claves Fernet en texto plano** (`ODOO_ENCRYPTION_KEY`,
`WHATSAPP_ENCRYPTION_KEY` en `.github/workflows/ci.yml`). Están documentadas
como descartables de CI y lo son — sólo cifran datos de la base efímera de cada
corrida. No son un secreto real, pero en un repo público quedan feas. Moverlas
a GitHub Secrets son 10 minutos. El jurado no mira el código, así que lo dejo
anotado y no lo toco sin que me digas.
