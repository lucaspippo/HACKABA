# Léeme primero — las tres cosas que cambian el plan

11 de septiembre de 2026 · análisis, nada construido, nada pusheado, nada deployado.

---

## 1. El cronograma del documento no coincide con el sitio oficial

Esto es lo primero porque cambia todo lo demás. Traído de `hackcba.com` hoy
(fuente primaria, el sitio público):

| | Lo que dice el documento de trabajo | Lo que dice hackcba.com |
|---|---|---|
| Arranque | jueves 11, 10:30 | **viernes 11, 18:30 puertas / 20:00 apertura** |
| Duración | no dice | **24 horas.** Entrega sábado 12 a las 16:00 |
| Demos | no dice | sábado 16:30–18:30, resultados 18:30–19:00 |
| Sede | no dice | **Casa Naranja X, Córdoba** |
| Cupo | 15 equipos × 3 tracks (45) | **100 hackers**, equipos de **hasta 4** |
| Elección de track | se gana con una pregunta técnica a las 10:30 | **se elige en la apertura del viernes 20:00**, junto con la formación de equipos |
| Tracks | IA / Web3 / Agro | **tres retos sin revelar**, se anuncian el día del evento |

El 11 de septiembre de 2026 es **viernes**, no jueves. Eso encaja con el sitio,
no con el documento.

Dos lecturas posibles, y no puedo decidir entre ellas desde acá:

- El documento se armó con información de la zona con contraseña para
  participantes (a la que no tengo acceso) o de Instagram, y esa información es
  más nueva que la página pública.
- O el documento mezcla este evento con otro.

**Lo que hay que hacer antes de cualquier otra cosa: entrar a la zona de
participantes y confirmar horario, mecánica de track y regla de código.** Si el
sitio público tiene razón, no hay "tiempo para construir": hay una noche.

## 2. La regla de código prohíbe exactamente lo que plantea el Bloque D

Texto del sitio, literal:

> «Podés venir con la idea pensada, pero no con el repo empezado.»

Y en la descripción de reglas: todos los proyectos arrancan de cero el viernes a
la noche; los repositorios tienen que empezar vacíos.

Eso no es un "freeze de GitHub" ambiguo. Es una regla explícita sobre código
preexistente, y **mudar `main` de `polpilot-app` a un repo nuevo la viola de
forma literal**, con o sin historia de git. El detalle de la historia es
secundario: aunque se borre, sesenta y cinco mil líneas de backend maduro
aparecidas a las 21:00 del viernes no se defienden.

El plan completo de cómo encarar esto —incluida la única salida que considero
honesta— está en `07-MUDANZA-DEL-REPO.md`. Resumen: **no mudar**. Construir en el
repo nuevo, de cero, una pieza chica y nueva, y usar PolPilot como lo que es —un
producto que ya existe, mostrado aparte y declarado como tal.

## 3. Dos cosas del guion no se sostienen contra los datos de hoy

Las encontré yendo al código y al dataset, que es el método que el documento
mismo pide. Detalle completo en `03-NUESTROS-CUATRO-DIFERENCIADORES.md` y
`05-EJEMPLOS.md`.

- **«Si Ramón se va, la empresa pierde siete reglas que sólo él sabe.»**
  Falso hoy. Las 22 piezas de `conocimiento_negocio.json` tienen
  `origen.quien = "aldo"`. **Las 22.** Nadie más enseñó nada. El conocimiento en
  riesgo, tal como está escrito el guion, no se puede mostrar sin cambiar el
  dataset primero.
- **El pasillo 4 no tiene camino en el grafo.** Vive en
  `deposito.explicaciones()`, no en `cruces.py`. `grafo.caminos()` sólo resuelve
  los seis cruces de `cruces.py` más dos cards de Oportunidades. El mejor
  ejemplo que tenemos es justo el que el cerebro no puede encender.

Ninguna de las dos es grave de arreglar. Las dos son fatales si se dicen en voz
alta sin arreglarlas.

---

## Los siete documentos

1. `01-LIGHTFIELD.md` — investigación, separando fuente primaria de prensa, y la
   lista de lo que ellos tienen y nosotros no, ordenada por costo.
2. `02-QUE-GANA-Y-CORDOBA-HACK.md` — hackathons ganadores verificados, y todo lo
   verificable de Córdoba Hack con lo no confirmado marcado.
3. `03-NUESTROS-CUATRO-DIFERENCIADORES.md` — el análisis honesto contra los
   cuatro de ellos. Incluye evals versus tests.
4. `04-GRAFO-DIAGNOSTICO-Y-PROPUESTA.md` — cómo está construido el grafo hoy, qué
   no se entiende, y la propuesta de diseño con costos.
5. `05-EJEMPLOS.md` — los tres pedidos más cinco nuevos encontrados en el dataset
   real, con la fila exacta que los respalda.
6. `06-DISRUPTIVO.md` — las propuestas ordenadas por impacto, con costo.
7. `07-MUDANZA-DEL-REPO.md` — el plan de repo y el riesgo de la regla de código.

Y al final de todo: `08-QUE-CONSTRUIRIA.md`, el orden y el tiempo.
