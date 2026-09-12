# Qué gana una hackathon de IA, y qué es Córdoba Hack en concreto

Investigación del 11 de septiembre de 2026. Lo no verificable va marcado.

---

# Parte A · Qué gana hoy

## A.1 · El caso más cercano al nuestro, verificado

**GitLab AI Hackathon 2026.** Del 9 de febrero al 25 de marzo de 2026, en
Devpost. Google Cloud y Anthropic como co-sponsors. Cerca de 7.000
desarrolladores, más de 600 agentes y flujos construidos. Diecinueve jurados,
dieciocho días de evaluación.

**Los criterios publicados: cuatro ejes.** Trabajo técnico, diseño, impacto
potencial, y calidad de la idea. Nótese que son cuatro pesos parejos, no el
20/25/25/30 del documento interno — ese reparto viene de otro rubric y conviene
no citarlo como si fuera de acá.

**Los ganadores verificados:**

| Proyecto | Premio | Qué es |
|---|---|---|
| **lore** (Living Organizational Record Engine) | **Grand Prize** | Sistema de ocho agentes para capturar el conocimiento institucional **antes de que el ingeniero que se va se lo lleve** |
| **graphdev** | **Anthropic Grand Prize** | Mapea las relaciones del código entre proyectos y **muestra cómo el sistema cambia en el tiempo** |
| **gitdefender** | **Google Cloud Grand Prize** | Trabaja dentro del flujo de revisión de código: encuentra el problema de seguridad, escribe el arreglo y abre el review |
| **greenpipe** | (track sostenibilidad) | Analiza la huella de carbono del CI/CD. Un proyecto del track bajó un costo de US$556 a US$18 mensuales |

**Un jurado de GitLab dijo de graphdev que estaba "en sintonía con nuestro
trabajo en el knowledge graph de GitLab".** Ese comentario es la lección
completa: el proyecto ganó porque el jurado reconoció el problema desde adentro.

### Qué de lo que dice el documento interno queda confirmado y qué no

- ✅ **"Ganó un proyecto sobre conocimiento que se pierde cuando alguien se va."**
  Confirmado: es *lore*, y se llevó el Grand Prize general.
- ✅ **"El Grand Prize de Anthropic fue para uno que mapea relaciones y muestra
  cómo el sistema cambia en el tiempo."** Confirmado literalmente: *graphdev*.
- ⚠️ **"Otro fue premiado por explicar cada decisión que toma."** **No lo pude
  verificar.** No aparece en las fuentes que conseguí. No lo diría en una sala.
- ⚠️ **El rubric 20/25/25/30.** Los criterios publicados de este evento son otros
  (cuatro ejes: técnico, diseño, impacto, idea). El reparto porcentual del
  documento puede venir de otra hackathon; no lo pude atribuir.

**Los dos ganadores grandes de la hackathon de IA con jurados de Anthropic de
este año fueron: conocimiento que se va con la persona, y grafo de relaciones
con evolución temporal.** Eso no es una coincidencia que podamos explotar como
truco — es una señal de qué problema le parece real a esa clase de jurado. Y es
exactamente lo que hace PolPilot.

## A.2 · Qué hace que un jurado técnico crea que hay profundidad

Esto es interpretación mía sobre los casos que pude verificar, y lo digo así:
**no es una regla publicada, es una lectura.**

Los cuatro ganadores tienen la misma forma, y no es la forma de una demo linda:

1. **Todos se meten dentro de un flujo de trabajo que ya existe.** gitdefender no
   hace un panel de seguridad: abre el code review. lore no hace un wiki: corre
   antes de que la persona se vaya. **Ninguno fabrica una pantalla nueva; todos
   se paran en un momento que ya ocurre.** Es exactamente el Action Principle
   nuestro, dicho desde afuera.
2. **Todos tienen un número que se puede verificar.** $556 → $18. Ocho agentes.
   Cambios en el tiempo. Nada es "mejora la productividad".
3. **Todos atacan una pérdida, no una ganancia.** Conocimiento que se pierde,
   bugs que pasan, carbono que se quema. Un jurado siente una pérdida.
4. **Ninguno es un chat.** Ninguno de los cuatro se presenta como "pregúntale
   cosas a tu X".

### Lo que hace perder a un proyecto que se ve impresionante

**No pude verificar casos concretos de proyectos que perdieron.** Los sitios de
hackathon publican ganadores, no autopsias. Lo que sí puedo señalar, y lo marco
como razonamiento y no como dato: en un evento donde el jurado ve treinta demos
en dos horas, **la interfaz deslumbrante es el default, no la diferencia.** En
2026 una pantalla hermosa cuesta veinte minutos. Lo que no se puede improvisar
es un dataset con catorce personas que se contradicen. El documento interno ya
lo dice y lo dice bien.

---

# Parte B · Córdoba Hack

## B.1 · Lo verificado en el sitio oficial (hackcba.com)

Todo esto sale de la página pública, hoy.

| Ítem | Dato |
|---|---|
| Fechas | **11 y 12 de septiembre de 2026** |
| Duración | **24 horas** |
| Sede | **Casa Naranja X, Córdoba** |
| Cupo | **100 hackers**, con revisión de perfil |
| Costo | Gratuito |
| Equipos | **Hasta 4 personas** |
| Tracks | **Tres retos, sin revelar hasta el día del evento** |
| Elección de track | **En la ceremonia de apertura del viernes a las 20:00**, junto con la formación de equipos |
| Lema | "Entrás con una idea. Salís con un producto" |

**Agenda publicada:**

- Viernes 18:30 — puertas, snacks
- Viernes 20:00 — apertura y presentación de los tracks
- Viernes 20:30 → sábado 15:30 — hackeo continuo, workshops opcionales, se
  hackea de noche
- Sábado 16:00 — **cierre de entrega**
- Sábado 16:30–18:30 — demos ante el jurado
- Sábado 18:30–19:00 — resultados y cierre

**Regla de código, textual del sitio:**

> «Podés venir con la idea pensada, pero no con el repo empezado.»

Y en la descripción de reglas: todos los proyectos arrancan de cero el viernes a
la noche; los repositorios tienen que empezar vacíos. **No hace falta ser
programador senior: se valoran por igual código, diseño y producto.** Se puede
participar solo; los equipos se arman en la apertura.

**Sponsors publicados:** Naranja X (anfitrión), Cognition, de/Recruiters, Lazo,
Fidelando, Superteam Argentina, RedotsClub Argentina, Twin.

**Organizadores publicados:** Foncea, Giorgis, Mazzitello.

## B.2 · Las contradicciones con el documento de trabajo

Esto es lo más importante de todo el bloque y quiero que quede sin ambigüedad.

| | Documento de trabajo | Sitio oficial |
|---|---|---|
| Día | jueves 11 | **11 de septiembre de 2026 es viernes** |
| Hora de arranque | 10:30 | 18:30 puertas / 20:00 apertura |
| Duración | implícitamente varios días | 24 horas |
| Cómo se asigna el track | se gana respondiendo primero una pregunta técnica que contesta el capitán una sola vez | **se elige en la apertura** |
| Tracks | IA, Web3, Agro (nombrados) | tres retos **sin revelar** |
| Equipos por track | quince | 100 hackers ÷ 4 ≈ 25 equipos en total |
| Mentorías 1:1 | desde las 18:00 del 11 | la agenda publicada no las menciona |

**No puedo resolver esto desde acá.** Hay una zona con contraseña para
participantes a la que no tengo acceso, y es perfectamente posible que la
información de ahí sea más nueva o más detallada que la página pública. También
es posible que parte del documento venga de otro evento.

**Lo que hay que hacer, y antes que cualquier otra cosa:** entrar a la zona de
participantes y confirmar por escrito (a) el horario real, (b) la mecánica de
asignación de track, (c) el texto exacto de la regla sobre código preexistente, y
(d) si existe un rubric publicado. Los cuatro cambian decisiones grandes.

## B.3 · Los sponsors, y qué sesgo introducen

**Naranja X** — fintech cordobesa (grupo Naranja / Tarjeta Naranja), anfitriona
del evento en su sede. Es la casa. Un proyecto que toque plata, crédito, cobro o
pagos de PyMEs le habla directo. **PolPilot toca cuentas corrientes, mora,
crédito y caja.** Eso no es un detalle: es la superficie del producto que más
cerca está de la casa.

**Cognition** — la empresa de Devin, el ingeniero de software con IA
(estadounidense). Sponsor inequívocamente de IA y de agentes que hacen trabajo,
no que conversan. **[Hipótesis]** Si hay un premio de track de IA, es el
candidato más obvio a ponerlo.

**Superteam Argentina** — comunidad del ecosistema Solana. Sponsor claramente
asociado al track Web3.

**Lazo** — **[probable]** startup que conecta founders early-stage con sus
inversores. Hay un producto argentino con ese nombre y esa descripción
reportado por prensa del sector; no pude confirmar que sea el mismo.

**Fidelando, Twin, RedotsClub Argentina, de/Recruiters** — **no los pude
identificar con confianza.** de/Recruiters suena a reclutamiento técnico por el
nombre, pero eso es inferencia, no dato.

### La conclusión que importa

**Hay dos sponsors que apuntan a dos tracks distintos y ninguno apunta a Agro:**
Cognition a IA, Superteam a Web3. Si alguno de los tres retos es agro, es de la
casa o de un sponsor que no identifiqué.

**No pude confirmar que algún sponsor ponga el premio de un track específico.**
Es la pregunta correcta y no tiene respuesta pública. Está en la lista de cosas
a confirmar en la zona de participantes.

## B.4 · Jurados, mentores, ediciones anteriores

**No hay jurados publicados** en la parte pública del sitio. El documento de
trabajo nombra mentores (Ata Herrera de trama., Joaquín Giorgis de TicketSpace,
Augusto Pinto, Martina Insaurralde, Nicolás Fernández) que no aparecen en la
página pública que pude leer. Nótese que **"Giorgis" figura como organizador en
el sitio** — es coherente con que Joaquín Giorgis esté del lado de la
organización, no sólo de las mentorías.

**No encontré ninguna edición anterior de este evento.** El índice de búsqueda no
tiene prácticamente nada sobre hackcba fuera del propio sitio: ni cobertura de
prensa, ni ganadores previos, ni menciones en medios cordobeses. Eso sugiere
—**hipótesis**— que es una primera edición, o al menos la primera con este
nombre y esta escala.

## B.5 · Contexto de Córdoba, verificado

- Córdoba tiene alrededor de **400 empresas de tecnología y más de 200
  startups** en la ciudad, con base fuerte en software y talento universitario.
- El **Foro de Inversiones Córdoba 2026** (Gobierno de Córdoba + ARCAP, séptima
  edición) reunió más de 2.200 asistentes, 95 oradores y 34 eventos paralelos.
- **HackIA** es un programa público-privado de las agencias Competitividad
  Córdoba y ProCórdoba con la Fundación Uvitec, para la adopción de IA **en
  PyMEs cordobesas**, con encuentros en Córdoba, Río Cuarto, San Francisco y
  Villa María.

Ese último punto es el que más nos sirve y no está en el documento de trabajo:
**hay un programa provincial vigente cuyo objetivo declarado es meter IA en las
PyMEs de Córdoba.** PolPilot es literalmente eso. Si en la sala hay alguien
ligado al ecosistema institucional cordobés —y con Naranja X de anfitriona y el
Foro de Inversiones en la misma ciudad, es probable—, ese marco vale más que
cualquier comparación con Salesforce.

---

# Parte C · Qué gana el track de IA acá

Dado quién patrocina, quién organiza y dónde se hace, esto es lo que creo. Va
como juicio, no como dato.

### Lo que juega a favor nuestro

1. **El sponsor de IA es Cognition.** Su tesis pública es agentes que hacen
   trabajo de ingeniería real, con verificación, no asistentes que charlan. Un
   proyecto que separa qué calcula el código de qué interpreta el modelo le habla
   en su idioma.
2. **La anfitriona es una fintech de PyMEs.** Mora, cuenta corriente, crédito y
   caja son su mundo.
3. **El ecosistema local tiene un programa vivo de IA para PyMEs.** El problema
   le suena real a cualquier cordobés del sector.
4. **Los dos ganadores grandes de la hackathon de IA con Anthropic este año
   fueron conocimiento que se pierde y grafo temporal.** Son nuestros dos
   momentos más fuertes.

### Lo que juega en contra

1. **24 horas y repo vacío.** Nuestra ventaja estructural —un producto maduro— es
   justo lo que la regla prohíbe traer. Ver `07-MUDANZA-DEL-REPO.md`.
2. **Los tracks no están revelados.** Todo el guion está escrito para un track de
   IA que puede no existir con ese nombre.
3. **El jurado no está publicado.** No sabemos si son técnicos, inversores o
   fundadores, y eso cambia el guion entero.

### Qué van a llevar los demás

Con sponsors de IA y Web3 y 24 horas de reloj, la distribución previsible es:

- **Mayoría: un agente sobre un dominio.** Un asistente que lee tus X y contesta
  preguntas. Chat con RAG sobre documentos. Automatización de una tarea.
- **Varios: la demo en vivo con voz o visión.** Es lo que más rinde por hora
  invertida.
- **Uno o dos: algo con el producto de un sponsor** (Devin, Solana), porque el
  premio es visible.
- **Casi ninguno va a medir nada.** En 24 horas nadie hace evals. Ése es el hueco
  más grande y el más barato de ocupar.
- **Casi ninguno va a tener datos reales de una empresa entera.** Ése es el otro.

**La distinción que hay que enseñarle al jurado temprano —alerta versus cruce—
sigue siendo la jugada correcta, y en 24 horas es todavía más fuerte: nadie más
va a tener tiempo de construir un cruce de verdad.**

---

## Fuentes

- [hackcba.com](https://hackcba.com)
- [GitLab AI Hackathon 2026: Meet the winners — GitLab](https://about.gitlab.com/blog/gitlab-ai-hackathon-2026-meet-the-winners/) (el blog devolvió 403 a la lectura directa; los datos vienen del resumen indexado y del espejo de daily.dev)
- [GitLab AI Hackathon 2026: Meet the winners — daily.dev](https://daily.dev/posts/gitlab-ai-hackathon-2026-meet-the-winners-2cehmn6x4)
- [2026-02 AI Hackathon — GitLab](https://gitlab.com/gitlab-community/community-projects/2026-02-ai-hackathon)
- [Vuelve HackIA — Agencia ProCórdoba](https://procordoba.org/vuelve-hackia-un-programa-publico-privado-para-llevar-la-inteligencia-artificial-a-las-pymes-cordobesas/)
- [Boom de inversión en startups: Córdoba gana peso — Punto a Punto](https://puntoapunto.com.ar/boom-de-inversion-en-startups-cordoba-gana-peso-en-un-ecosistema-que-ya-capto-mas-de-us400-millones-en-2026)
- [Lazo lanza producto para founders early stage — Startups Latam](https://startupslatam.com/lazo-lanza-producto-para-que-founders-early-stage-se-relacionen-con-sus-inversores/)
