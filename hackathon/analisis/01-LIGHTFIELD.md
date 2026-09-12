# Lightfield, a fondo

Investigación propia, 11 de septiembre de 2026. Cada afirmación va etiquetada:

- **[P]** fuente primaria — la empresa o el inversor lo dice con su nombre
  (lightfield.app, docs.lightfield.app, el comunicado de PR Newswire, el post de
  a16z).
- **[S]** fuente secundaria — prensa que reporta lo anterior.
- **[N]** no lo pude verificar.

---

## 1. Lo verificado en fuente primaria

### La ronda

**[P]** 47 millones de dólares, Serie A, liderada por Andreessen Horowitz.
Participan Maverick Capital, Coatue, Audacious, Alumni Ventures, Greylock y
Lightspeed. Anuncio del 9 de septiembre de 2026.

**[P]** Más de 5.000 empresas registradas desde el lanzamiento en noviembre de
2025. Net dollar retention de 400%. Clientes desde startups tempranas hasta
empresas con cientos de usuarios de CRM.

**[P]** Alex Rampell (a16z): «Cada cambio de plataforma produce un nuevo sistema
de registro. Salesforce definió el de la era de la nube, y Lightfield está
definiendo el de la era de los agentes.»

**[P]** Joe Schmidt IV (a16z): construir un sistema de registro es de lo más
difícil del software porque hay que ganarse la confianza del cliente antes de
que entregue los datos con los que corre su negocio; este equipo se la ganó con
miles de empresas en menos de un año.

**[P]** Keith Peiris (CEO): los agentes fallan porque los datos con los que
trabajan están incompletos, son inexactos y les falta la estructura necesaria
para comprenderlos.

**[S]** Valuación ~121 millones, por análisis de mercado secundario. Reportado
por Upstarts Media; **no** aparece en el comunicado. Es prensa, no dato de la
empresa.

**[S]** El pivote desde Tome: 20–25 millones de usuarios, Serie B de ~81
millones en 2023 a valuación de 300 millones, recorte de 70 a 7 personas en
2024. Consistente entre Upstarts y el resto de la cobertura. Lightfield no lo
publica en su comunicado.

### Los cuatro diferenciadores, con el texto de ellos

**[P]** El comunicado y el sitio declaran los mismos cuatro:

1. **Un registro que se actualiza solo.** Ingesta autónoma y continua de cada
   interacción con el cliente a través de mail, calendario, llamadas, Slack y
   LinkedIn, estructurada dentro del registro sin carga manual.
2. **Un modelo del mundo del negocio.** Conecta cada interacción con las
   personas, negocios y cuentas que toca, y preserva cómo cambiaron en el
   tiempo, para que los agentes puedan razonar.
3. **Un arnés de agente.** SDK estandarizado, sandbox de código, y evals
   continuos. La frase del sitio: acceso consistente a los registros y salidas
   confiables en cada corrida.
4. **Plataforma abierta.** Todo legible y escribible por API, CLI y MCP.

### Cómo describen el modelo del negocio, técnicamente

**[P]** El término propio del producto es **temporal context graph** — grafo de
contexto temporal. El post de a16z lo nombra como la proeza de fondo: un grafo
de contexto temporal que captura el porqué detrás de cada negocio.

**[P]** La documentación lo describe como un grafo de contexto de objetos de CRM
relacionados —cuentas, oportunidades, contactos— que captura **tanto el estado
actual de los objetos como la historia de cómo, cuándo y por qué cambiaron**.
Esa frase —cómo, cuándo y por qué— es la definición operativa del eje temporal y
es lo más concreto que publican.

**[P]** El modelo de datos **se construye solo**: a16z lo describe como un modelo
flexible que no necesita configuración y se arma desde tus mails y llamadas en
minutos. El contraste explícito es contra los campos muertos, las semanas de
configuración y los reportes que nadie confía.

**[P]** Hay **objetos personalizados** (custom objects) que espejan los flujos
del negocio, documentados en "Objects in Lightfield" (tipos, campos,
relaciones).

### Cómo estructuran lo no estructurado

**[P]** La documentación dice: captura interacciones en tiempo real como datos
no estructurados —mails, transcripciones de reuniones— y esos datos quedan
**incluidos en el grafo de contexto** junto a los estructurados. Los agentes
razonan sobre los dos juntos y escriben de vuelta: actualizan campos y crean
registros.

**[P]** Hay endpoints específicos para esto en la API: manejo de mail y
adjuntos, recuperación y subida de transcripciones de reunión, subida de
archivos de conocimiento. O sea: la ingesta de lo no estructurado es una
superficie pública del producto, no un proceso interno escondido.

**[N]** **No pude encontrar documentación pública de qué campos exactos extraen
de un mail o una llamada, ni del algoritmo de resolución de entidades, ni de qué
hacen cuando hay ambigüedad.** Busqué en el sitio, la documentación, el
comunicado y la cobertura. No está publicado. Cualquier afirmación nuestra sobre
eso sería invento.

### Confianza, procedencia, "no sé"

**[N]** **No encontré nada.** Ni declaración de fuentes por dato, ni nivel de
confianza visible, ni un comportamiento documentado de negarse a responder.
Busqué específicamente. Lo más cerca es la promesa de trazabilidad del caso de
uso de medición —que un equipo de producto pueda rastrear una decisión hasta las
llamadas concretas que la motivaron— y la de los evals continuos, que es una
afirmación de calidad, no de procedencia por dato.

Esto es importante y conviene decirlo tal cual si sale el tema: **declaran
determinismo, no declaran procedencia ni abstención.** Es el único lugar del
cuadro donde estamos por delante de un producto de 47 millones, y está
verificado por ausencia de evidencia publicada, no por opinión. Dicho con
honestidad: ausencia de evidencia no es evidencia de ausencia. Puede que lo
tengan y no lo cuenten.

### Superficie de producto (fuente primaria, sitio)

Generación de pipeline con agentes que identifican prospectos parecidos a tus
mejores clientes; asistente de ventas (investigación de cuenta, calificación,
preparación de reunión, seguimientos); captura automática de datos de CRM;
grabador de reuniones; coaching de negocios; pronóstico y análisis. Casos:
SF Compute, Macroscope, Power, Intent HQ. Seis interfaces de acceso: HTTP,
SDK de Python, SDK de TypeScript, SDK de Go, CLI y MCP. Hay documentación
pública en `docs.lightfield.app`, blog y changelog.

---

## 2. Lo que no pude ver, y por qué importa

**[N]** **No conseguí capturas ni video de cómo dibujan el grafo temporal.** La
documentación describe la estructura de datos; el sitio muestra producto de
ventas (pipeline, asistente, grabador de reuniones). No hay una vista de grafo
publicada que yo haya podido encontrar.

Hipótesis, marcada como tal: **es posible que no tengan una visualización de
grafo**, y que el "modelo del mundo" sea una estructura interna que el agente
consume, no una pantalla que una persona mira. La evidencia a favor es que
buscamos capturas de grafo en sitio, docs y prensa y no aparece ninguna, y que
todo el material visual que sí publican es producto de ventas convencional.

Si la hipótesis es correcta, la consecuencia para nosotros es concreta: ellos
tienen el grafo como **infraestructura**, nosotros lo tenemos como
**superficie**. Eso no lo podemos afirmar en una sala; sí podemos afirmar lo
nuestro, que es lo que importa.

---

## 3. Lo que ellos tienen y nosotros no

Ordenado por lo que nos costaría tenerlo, de más barato a más caro. El detalle de
qué tenemos está en `03-NUESTROS-CUATRO-DIFERENCIADORES.md`.

| # | Lo de ellos | Nuestro estado | Costo de tenerlo |
|---|---|---|---|
| 1 | **Evals continuos y visibles** | 159 archivos de test, incluidas dos baterías que son casi evals. Ninguna reporta una métrica; todas son pasa/no pasa | **Media jornada.** Es re-presentar lo que ya corre, con precisión y falsos positivos sobre casos conocidos |
| 2 | **CLI** | No existe. Pero existe el MCP y la API REST completa | **Dos a cuatro horas.** Un cliente de línea de comandos contra la API que ya está |
| 3 | **MCP de escritura** | El nuestro es estrictamente de sólo lectura, y está documentado por qué | **Una a dos jornadas**, y hay un plan escrito en `backend/MCP.md` (propose→apply, `destructiveHint`, token propio). No es trivial y no lo haría para una hackathon |
| 4 | **Grafo con eje temporal** | El nuestro es una foto del estado actual. Hay fechas en las notas y en el conocimiento, pero el grafo no las usa | **Una jornada** para la versión honesta (ver `04`) |
| 5 | **SDK en varios lenguajes** | No existe | **Dos a tres jornadas** por lenguaje bien hecho. No vale la pena para esto |
| 6 | **Sandbox de código para el agente** | No existe, y nuestra arquitectura resuelve el mismo problema al revés: el modelo nunca calcula | **Semanas.** Y es discutible que lo queramos |
| 7 | **Modelo de datos que se arma solo desde el canal** | Tenemos el canal (voz, foto, WhatsApp) pero el esquema es fijo | **Semanas.** Es el corazón de su producto |
| 8 | **Migración asistida y sync en dos vías** | No | **Semanas**, y no aplica: nosotros no reemplazamos, nos montamos encima |

Accionable esta semana: los tres primeros y el cuarto. El resto es hoja de ruta
de producto, no de hackathon.

---

## 4. Tres correcciones al documento interno

El documento adjunto es bueno y sus conclusiones se sostienen. Tres ajustes de
precisión:

1. **"a16z maneja más de 90.000 millones"** es cierto pero irrelevante y suena a
   relleno. La frase que pega es la de Rampell sobre el sistema de registro.
2. **La valuación de 121 millones es prensa, no dato de la empresa.** Si se dice
   en una sala hay que decir "según análisis de mercado secundario". Es el único
   número del documento sin fuente primaria y es justo el que más tentación da
   de repetir.
3. **Falta el término propio: *temporal context graph*.** No para usarlo —el
   documento tiene razón en que "world model" en boca nuestra suena prestado—
   sino para saber que existe: si un jurado lo conoce, decir "nuestro mapa
   guarda cómo cambió lo que sabe, no sólo lo que sabe" lo ubica al instante.

---

## Fuentes

- [Lightfield Raises $47 Million Series A to Build the CRM for Companies that Run on Agents — PR Newswire](https://www.prnewswire.com/news-releases/lightfield-raises-47-million-series-a-to-build-the-crm-for-companies-that-run-on-agents-302874024.html)
- [lightfield.app](https://lightfield.app)
- [docs.lightfield.app](https://docs.lightfield.app)
- [Investing in Lightfield — Andreessen Horowitz](https://a16z.com/announcement/investing-in-lightfield/)
- [AI-native CRM startup Lightfield raises $47M — SiliconANGLE](https://siliconangle.com/2026/09/09/ai-native-crm-startup-lightfield-raises-47m-to-build-an-ai-agent-ready-replacement-for-salesforce/)
- [AI CRM Startup Lightfield Raises $47M Series A Led by a16z — Upstarts Media](https://www.upstartsmedia.com/p/ai-sales-startup-lightfield-raises-47m)
- [Lightfield Raises $47M Series A Led by a16z — Unite.AI](https://www.unite.ai/lightfield-raises-47m-series-a-led-by-a16z-to-accelerate-growth/)
