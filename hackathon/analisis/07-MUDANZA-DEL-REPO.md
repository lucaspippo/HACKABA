# El repo nuevo: análisis, y el riesgo que hay que mirar de frente

Nada de esto se ejecutó. Es análisis.

---

## 1. El riesgo, primero, porque cambia la pregunta

Pediste explícitamente que evaluara el riesgo del freeze de GitHub y de la regla
sobre código previo. Lo evalué y **el resultado no es "hay que tener cuidado": es
que la premisa del Bloque D choca de frente con la regla publicada.**

Texto del sitio oficial, `hackcba.com`, hoy:

> **«Podés venir con la idea pensada, pero no con el repo empezado.»**

Y en la descripción de reglas: todos los proyectos arrancan de cero el viernes a
la noche; los repositorios tienen que empezar vacíos.

**Eso no es un freeze ambiguo. Es una regla explícita sobre código preexistente,
y mover `main` de `polpilot-app` a un repo nuevo la viola literalmente.**

### Por qué el truco de "borrar la historia" no sirve

Es la primera idea que se le ocurre a cualquiera y hay que descartarla de forma
explícita, por dos razones distintas:

**La razón práctica.** No funciona. `main` tiene **372 commits** y **65.421
líneas de Python** sólo en el backend, más el frontend, más 159 archivos de test,
más `data-demo/` con 3,5 MB de dataset generado. Un repositorio "recién creado"
el viernes a las 21:00 con eso adentro se detecta sin abrir la historia: por el
volumen, por la madurez del `CLAUDE.md`, por el `render.yaml` con doce variables
de entorno, por el `backend/MCP.md` de 200 líneas. La historia de git sólo lo
haría **más** evidente; borrarla no lo hace menos.

**La razón que importa más.** Todo el pitch de PolPilot se sostiene sobre una
sola cosa: **que lo que decimos se puede verificar.** El documento de trabajo ya
tuvo que corregir dos afirmaciones que no eran ciertas (el conector de Odoo y el
funcionamiento sin conexión), y la conclusión que sacó fue la correcta: si nos
agarran inflando, se cae todo lo demás, que sí es verdad. **Presentar como
construido-en-24-horas algo que tardó meses es exactamente esa clase de error, con
el agravante de ser contra una regla.**

### Lo que sí haría, y creo que gana igual o más

**Separar las dos cosas, y decirlo en voz alta.**

1. **El repo nuevo arranca vacío el viernes a la noche** y adentro va **sólo lo
   que se construye durante la hackathon**. Que sea una pieza chica y buena: el
   grafo con el camino animado, el contrafáctico, el punto ciego por persona.
2. **PolPilot existe, está deployado, y se muestra como lo que es.** No se
   esconde: se declara. *"Esto es un producto que venimos construyendo. Lo que
   construimos en estas 24 horas es esto otro, y está en este repo, que arrancó
   vacío anoche."*

**Por qué esto no nos debilita.** Los jurados de hackathon premian el producto:
la propia cita que el documento de trabajo usa es la de una jurada de Anthropic
diciendo de un ganador *"esto se siente como un producto, no como un proyecto de
hackathon"*. La diferencia entre esto y hacer trampa es de una sola línea:
**declararlo**. Un equipo que dice "tenemos un producto y acá está lo que
agregamos anoche" se lee como serio. Un equipo al que le descubren el producto
escondido se lee como tramposo, y en la final se pierde todo.

### Lo que hace falta confirmar antes de decidir nada

En la zona de participantes, por escrito, y esta noche:

1. El texto exacto de la regla de código.
2. Si vale usar **bibliotecas y servicios propios** preexistentes (un backend
   desplegado que el proyecto nuevo consume por API/MCP es distinto de copiar el
   repo).
3. Si hay que entregar el repositorio como parte de la entrega, y si miran la
   historia.
4. Si hay una excepción declarada para equipos con producto previo.

**La respuesta a la pregunta 2 es la que decide todo.** Si el proyecto nuevo
puede consumir a PolPilot como un servicio externo —igual que otro equipo
consumiría la API de OpenAI o de Solana—, entonces se puede construir una pieza
nueva y chica que se apoye en un motor que ya existe, y eso es honesto y
defendible. **Es el mejor escenario y creo que es el probable.**

---

## 2. Las tres formas de mudar, si igual se decide mudar

Para el escenario en que se confirma que se puede llevar código, o para después
de la hackathon.

### a) Clon completo con historia

```
git clone --mirror  →  cambiar remote  →  push
```

**A favor:** nada se pierde. Los 372 commits, las 32 ramas remotas, los mensajes
de PR, todo. `git blame` sigue funcionando, que es lo que más se extraña.

**En contra:** es exactamente lo que la regla busca detectar, y queda escrito con
fecha y autor en cada commit. Si alguien mira, lo ve en cinco segundos.

**Cuándo:** después de Córdoba, si el repo nuevo pasa a ser el principal.

### b) Copia limpia sin historia

```
copiar el árbol  →  git init  →  un commit inicial
```

**A favor:** rápido, limpio.

**En contra:** se pierde `git blame`, que en un repo con comentarios tan densos
como éste es una pérdida real — la mitad del valor de los comentarios es saber
en qué PR se decidió cada cosa. Y **no resuelve el problema de la regla**: el
volumen sigue delatándolo.

**Cuándo:** casi nunca. Es el peor de los tres: paga el costo de perder la
historia sin comprar el beneficio de cumplir la regla.

### c) Fork

**A favor:** GitHub muestra la relación, que es honesto.

**En contra:** justamente eso. Y los forks arrastran configuración de la relación
con el upstream (PRs que se abren por default contra el original) que molesta.

**Cuándo:** si la intención es contribuir de vuelta. No es el caso.

**Mi recomendación, si hay que mudar:** **(a), clon completo con historia.** La
transparencia es la política correcta acá, y perder `git blame` en este repo
duele de verdad.

---

## 3. Qué viaja y qué no

| Qué | ¿Viaja? | Por qué |
|---|---|---|
| `backend/`, `frontend/` | **Sí** | Es el producto |
| `data-demo/` (3,5 MB) | **Sí** | Sin el dataset no hay demo. Está declarado 100% ficticio con semilla fija |
| `PRODUCT.md`, `DESIGN.md`, `CLAUDE.md` | **Sí** | Es lo que hace que el repo se pueda seguir trabajando |
| `backend/MCP.md` | **Sí** | Es de lo mejor escrito y es una prueba de seriedad |
| `.github/workflows/ci.yml` | **Sí**, pero hay que revisar secretos | Un CI roto en el repo nuevo es ruido |
| `render.yaml` | **Sí**, pero **hay que tocarlo** | Ver §4 |
| `design/` + los 79 mockups de la rama `design/mobile-roles` | **Como rama, no como `main`** | Son diseño, no código de producto. Mezclarlos en `main` ensucia lo que se entrega |
| `docs/superpowers/plans` y `specs` | **Sí** | Son el registro de por qué se decidió cada cosa |
| Las 32 ramas remotas | **No todas** | Traería `main` y `design/mobile-roles`. El resto son ramas de feature ya mergeadas: ruido |
| `.impeccable/`, `.claude/skills/` | **Opcional** | Son herramientas de trabajo, no producto. Yo las llevaría |
| `assets-origen/` | **Revisar** | No lo inspeccioné en detalle. Vale mirar el peso antes |

---

## 4. Qué se rompe al mudar

Recorrido concreto, no genérico.

### Render — **se rompe seguro, y hay que planearlo**

`render.yaml` define el servicio `polpilot-app` y **doce variables de entorno**.
De ésas, **cuatro son secretos con `sync: false`**, o sea que **no están en el
repo y no viajan**:

- `ANTHROPIC_API_KEY`
- `POLPILOT_RESET_TOKEN`
- `DATABASE_URL` (rol owner: Alembic y lookups de tenant)
- `APP_DATABASE_URL` (rol NOBYPASSRLS: toda consulta con alcance de tenant)

**Consecuencia práctica:** un Blueprint nuevo apuntado al repo nuevo levanta el
servicio pero **no arranca** hasta que alguien cargue esas cuatro a mano en el
dashboard. Las dos de base de datos son las peligrosas: son dos roles distintos
sobre la misma base, y confundirlos rompe el aislamiento entre tenants, que es
una falla de seguridad, no un bug de demo.

**Y lo más importante: la demo publicada hoy sigue apuntando al repo viejo.**
Mientras no se cambie eso, un push al repo nuevo no despliega nada. Eso es bueno
—protege la demo— pero hay que saberlo, porque es exactamente la clase de cosa
que se descubre a las 3 de la mañana.

**Mi recomendación:** **no tocar el servicio de Render existente.** Si hace falta
un deploy del repo nuevo, que sea un servicio **nuevo**, con base de datos
**nueva**, en paralelo. La demo publicada se queda como está, como pediste.

### Base de datos y migraciones

Alembic corre `upgrade head`. Las migraciones viajan con el código, así que una
base nueva se construye sola. **Pero el estado sembrado no viaja**: `conocimiento`
vive en Postgres (tabla `business_knowledge_pieces`, migración 0039) sembrada
desde `data-demo/conocimiento_negocio.json` **la primera vez que el tenant lee sin
filas propias**; `notas` igual, vía `team_notes_repo`. En una base nueva se
resiembra solo. **Lo que no se resiembra es lo que alguien tocó a mano en la demo
actual.** Si hay ajustes hechos sobre la demo viva que no están en `data-demo/`,
se pierden.

**Hay que verificar eso antes de mudar** y no lo pude verificar desde acá.

### Rutas y nombre del repo

Busqué y **no encontré rutas absolutas ni el nombre del repo hardcodeado en el
código de producción**. `core/paths.py` resuelve por variable de entorno
(`POLPILOT_DATA_DIR`) con `data/` de default.

Lo que sí menciona el repo por nombre:

- `render.yaml` línea 12, en un comentario de instrucciones.
- `README.md` y `CLAUDE.md`, en las instrucciones de clonado.
- Los enlaces de PR en los mensajes de commit (`#69`, `#68`…), que **quedan
  apuntando al repo viejo** si se lleva la historia. Cosmético, pero confunde.

### CI

`.github/workflows/ci.yml`. Si usa secretos del repositorio, hay que recrearlos.
Un CI rojo en el repo nuevo es peor que no tener CI, porque parece un producto
roto.

---

## 5. Cómo queda la relación con `polpilot-app` después

Hay dos preguntas distintas acá y conviene no mezclarlas.

**Si el repo nuevo es sólo para la hackathon** (mi recomendación): la relación es
ninguna. Son dos cosas. Lo que se construya durante la noche y valga la pena
—el camino animado, el contrafáctico, el punto ciego por persona— vuelve después
como PRs normales contra `polpilot-app`, escritos con calma. **Eso es mejor que
un merge de vuelta**: el código de una hackathon no debería entrar a `main` sin
pasar por el estándar de la casa, y ese estándar es alto (se nota leyendo
cualquier archivo del repo).

**Si el repo nuevo pasa a ser el principal**: hay que decidirlo a propósito,
archivar el viejo, y mover el servicio de Render. No es una decisión para tomar
un viernes a la noche.

**Lo que hay que evitar a toda costa: que los dos repos estén vivos a la vez.**
Dos `main` divergiendo con el mismo producto adentro es el peor de los mundos, y
con un deploy apuntando a uno de los dos es como se pierde una demo.

---

## 6. Resumen ejecutable

1. **Esta noche, antes que nada:** confirmar en la zona de participantes el texto
   exacto de la regla de código y si se pueden consumir servicios propios
   preexistentes.
2. **Si la regla es la publicada** (y todo indica que sí): **no mudar.** Repo
   nuevo vacío, adentro sólo lo de la hackathon, PolPilot declarado como producto
   aparte que ya existe.
3. **No tocar Render.** La demo publicada se queda como está.
4. **No mergear nada a `polpilot-app`** durante la hackathon. Lo bueno vuelve
   después, como PRs.
5. **Si en algún momento se muda de verdad:** clon completo con historia, sólo
   `main` y `design/mobile-roles`, servicio de Render nuevo con base nueva, y las
   cuatro variables secretas cargadas a mano antes del primer arranque.
