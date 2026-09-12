# El rediseño de la pantalla del cerebro

Propuesta. Nada construido todavía.

---

# 1 · Arriba del lienzo: tres tarjetas

Hoy hay siete bloques. El criterio para elegir es uno solo: **que alguien que
entra por primera vez sepa qué hacer**. Hoy no lo sabe, porque hay once
píldoras de hallazgos y ninguna dice que son botones.

## Lo que queda

### Tarjeta 1 · **Preguntá** — siempre visible

```
┌──────────────────────────────────────────────────────────────────┐
│  El cerebro de tu negocio                                        │
│  Todo lo que pasó, cruzado. Preguntá y te muestro de dónde salió.│
│                                                                  │
│  ┌────────────────────────────────────────────────────┐          │
│  │ 🔍  Llegaron ocho cajas rotas de Campo Alegre…     │  [↵]     │
│  └────────────────────────────────────────────────────┘          │
│                                                                  │
│  Probá:  ¿qué le reclamo a Campo Alegre?  ·  ¿qué se me vence?   │
└──────────────────────────────────────────────────────────────────┘
```

**Por qué ésta primero:** es la única instrucción que hace falta. Hoy la puerta
de entrada son once píldoras que no parecen botones; acá hay una caja de texto,
que todo el mundo sabe usar, y **tres preguntas sugeridas en vez de once
títulos**. El que entra no elige entre once cosas que no entiende: escribe o
toca una sugerencia.

### Tarjeta 2 · **La respuesta** — aparece cuando hay un camino

```
┌──────────────────────────────────────────────────────────────────┐
│  Reclamo a Lácteos Campo Alegre                                  │
│                                                                  │
│  Ya tengo el número de remito. Falta la foto del lote.           │
│                                                                  │
│  · nahuel lo avisó por WhatsApp: «Llegaron ocho cajas rotas…»    │
│  · Campo Alegre pide foto del lote y remito, por mail, 5 días.   │
│  · Ya lo tiene: OC-2026-0847. Le falta: la foto.                 │
│  · Esa regla la enseñó Celeste el 18/06, porque nos rechazaron   │
│    un reclamo por mandarlo sin la foto.                          │
└──────────────────────────────────────────────────────────────────┘
```

**Por qué:** es el texto que el jurado lee mientras mira el grafo. Una frase
grande arriba y cuatro renglones cortos. Nada más.

### Tarjeta 3 · **De dónde salió** — aparece cuando hay un camino

```
┌──────────────────────────────────────────────────────────────────┐
│  DE DÓNDE SALIÓ                                                  │
│  Consultó   ▸ notas del equipo   ▸ órdenes de compra             │
│             ▸ depósito                                           │
│  Se acordó  ▸ «A Campo Alegre el reclamo va por mail, con foto   │
│               del lote y el remito. Cinco días.»                 │
│               — se lo enseñó Celeste · 18 jun 2026 · usada 3 veces│
└──────────────────────────────────────────────────────────────────┘
```

**Por qué:** es tu punto 6, y es la respuesta preparada a «¿cómo sé que no lo
inventó?». Separa lo que **consultó** (herramientas) de lo que **se acordó**
(memoria de la casa), que son dos cosas distintas y la segunda es la que no
tiene ningún ERP.

### Y una barra fina de controles, que no es tarjeta

`Proyectar · Pantalla completa · Ver todo el grafo · ⋯`

## Lo que se va, y adónde

| Qué | Adónde |
|---|---|
| **Las once píldoras de hallazgos** | Se reemplazan por tres preguntas sugeridas. El resto vive detrás de «⋯ → Otros hallazgos» |
| **El punto ciego** | Detrás de «⋯». Es material de reserva para preguntas, no del guion de 2:30 |
| **El contrafáctico** | Baja al panel del nodo: se toca una evidencia del camino y ahí aparece «quitar este dato». Es donde uno lo busca |
| **Los chips de «Cruzó»** | Se funden en la tarjeta 3, que dice lo mismo mejor |
| **«Lo que disparó esto»** | Se va. Los nodos están en el lienzo, grandes y con nombre: la lista era una muleta de cuando no se leían |
| **El contador «605 entidades / 2.062 relaciones»** | Pasa a la barra de controles, en chico. Impresiona, pero no es lo primero que hay que leer |
| **Los evals** | Detrás de «⋯» |

**Total arriba del lienzo: tres tarjetas y una barra.** Sin camino encendido,
una sola tarjeta.

---

# 2 · Los ocho nodos

Los siete que pediste, más uno.

| # | Nodo | Por qué |
|---|---|---|
| 1 | **Nahuel** · persona | El octavo, y es mi elección. Toda la tesis es que el dato no existe hasta que alguien lo dice: si la cadena no empieza en una persona, es un diagrama de sistema |
| 2 | **La nota** · WhatsApp | «Llegaron ocho cajas rotas» |
| 3 | **Leche Campo Alegre** · producto | Lo que se rompió |
| 4 | **Lácteos Campo Alegre** · proveedor | |
| 5 | **Su regla** · memoria | Foto del lote + remito · mail · 5 días |
| 6 | **OC-2026-0847** · orden | El remito que el sistema ya tenía |
| 7 | **Frigorífico La Ribera** · proveedor | **El contraste.** Está para que se vea que el otro pide otra cosa |
| 8 | **Su regla** · memoria | Sólo el remito · WhatsApp · 48 horas |

**Nada más. Ni tenue ni de fondo.** El grafo completo queda detrás de «Ver todo
el grafo».

## Sobre el plazo — sí, pero como etiqueta, no como nodo

Lo evalué y **no haría un nodo**. Un plazo no es una cosa: es una propiedad de
la relación. Meterlo como nodo sería inventar una entidad para cargar un número.

Va como **etiqueta de la arista** entre la regla y el proveedor:

> `exige — foto del lote + remito · por mail · 5 días`

y el dato de si estamos a tiempo va en la tarjeta 2, en una línea:

> *La entrega fue el 02/07. Quedan 3 días para reclamar.*

Eso entra sin ensuciar y contesta la pregunta del plazo mejor que un círculo
más en el lienzo.

---

# 3 · Cómo se ve cada nodo, y cómo se acomodan

## La decisión que resuelve el «todo superpuesto»: **posiciones fijas**

Hoy el lienzo corre una simulación de fuerzas. Con seiscientos nodos eso está
bien —el núcleo denso emerge y eso es parte de lo que impresiona—. **Con ocho
nodos es lo peor posible**: la simulación los empuja, los junta, tiembla, y las
etiquetas se pisan.

Para este caso: **layout fijo, leído de izquierda a derecha**, como el mapa de
la operación, que funciona justamente porque la posición significa algo.

```
   QUIÉN LO DIJO          QUÉ PASÓ              A QUIÉN            QUÉ EXIGE

   ┌────────┐   dijo    ┌─────────┐  menciona  ┌──────────┐      ┌──────────┐
   │ Nahuel │ ────────▸ │  nota   │ ─────────▸ │  Leche   │      │  REGLA   │
   │   👤   │  WhatsApp │ 8 cajas │            │ Campo A. │      │ foto del │
   └────────┘           │ rotas   │            └────┬─────┘      │ lote +   │
                        │  [WA]   │                 │ provee    │ remito   │
                        └─────────┘            ┌────┴─────┐  ◂── │ mail·5d  │
                                               │  CAMPO   │ exige└──────────┘
                                               │  ALEGRE  │
                                               └────┬─────┘
                                                    │ ordena
                                               ┌────┴─────┐
                                               │OC-2026-  │
                                               │  0847    │
                                               └──────────┘
   ─────────────────────────  el otro proveedor, para el contraste  ────────
                                               ┌──────────┐      ┌──────────┐
                                               │   LA     │ exige│  REGLA   │
                                               │  RIBERA  │ ◂────│ sólo el  │
                                               └──────────┘      │ remito   │
                                                                 │ WA · 48h │
                                                                 └──────────┘
```

La banda de abajo, separada por una línea fina y en un gris más apagado: **es
el contraste, no parte del reclamo**. Que se lea «este pide otra cosa» sin que
compita.

## Cada tipo

| Tipo | Forma | Tamaño | Detalle |
|---|---|---|---|
| **Persona** | Círculo con silueta de cabeza y hombros | ⌀ 76 px | El nombre debajo, grande. Es el único nodo con cara |
| **Nota** | Rectángulo tipo post-it, esquina doblada, **borde discontinuo** | 150×90 px | El texto de la nota ADENTRO (dos renglones) + **insignia del canal arriba a la derecha** |
| **Producto** | Círculo lleno, hielo | ⌀ 64 px | |
| **Proveedor** | Rombo, ocre | ⌀ 72 px | |
| **Regla / memoria** | Tarjeta con esquina superior izquierda plegada, amarillo | 170×80 px | El texto de la regla adentro + `Celeste · 18 jun` al pie |
| **Orden** | Hoja vertical con el borde superior ondulado | 60×80 px | El número adentro |

**El post-it y la regla llevan su texto adentro.** Con ocho nodos hay lugar de
sobra, y leer «8 cajas rotas» dentro del nodo es infinitamente mejor que una
etiqueta flotando al lado que se pisa con otra.

## Las etiquetas

Van **en el nodo o pegadas a él**, nunca sueltas. Con posiciones fijas se
reservan las zonas y no se pisa nada — que es lo que hoy no se puede garantizar
porque la simulación mueve todo.

## Las líneas

- **Curvas suaves**, no rectas. Una recta entre dos cajas parece un cable; una
  curva parece un recorrido.
- **Punta de flecha** en el destino: la dirección es la mitad del significado.
- **Etiqueta sobre la línea**, en una píldora con fondo del lienzo para que no
  se lea encima de nada: `dijo · WhatsApp`, `menciona`, `provee`, `ordena`,
  `exige · 5 días`.
- **Cuando se traza el camino**, la línea **se dibuja de origen a destino**
  (el trazo crece), no aparece entera. Y queda una partícula recorriéndola.

## Iconos — no necesito que armes nada

WhatsApp y el sobre los dibujo a trazo: escalan sin pixelarse y ya los tengo.
**Si querés la marca exacta**, pasame el SVG oficial de WhatsApp y lo uso tal
cual en la insignia. El resto de las formas son propias y no hacen falta
imágenes.

---

# 4 · Pantalla completa con Ángela al costado

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Reclamo a Lácteos Campo Alegre          Proyectar · Todo el grafo · ✕   │
├────────────────────────────────────────────────┬─────────────────────────┤
│                                                │  ● Ángela               │
│                                                │                         │
│              EL LIENZO                         │  ¿qué le reclamo a      │
│         (los ocho nodos, grandes)              │   Campo Alegre?         │
│                                                │                         │
│                                                │  ─────────────────────  │
│                                                │  El proveedor es        │
│                                                │  Lácteos Campo Alegre.  │
│                                                │  Va por mail, con foto  │
│                                                │  del lote y el remito.  │
│                                                │  Cinco días de plazo.   │
│                                                │                         │
│                                                │  El remito y el lote ya │
│                                                │  los tengo. Falta la    │
│                                                │  foto.                  │
│                                                │                         │
│                                                │  Lo armé. ¿Te lo mando? │
│                                                │                         │
│                                                │  ▸ consultó: notas,     │
│                                                │    órdenes, depósito    │
│                                                │  ▸ se acordó: la regla  │
│                                                │    de Celeste (18 jun)  │
│                                                ├─────────────────────────┤
│                                                │ [ preguntá algo…    ↵ ] │
└────────────────────────────────────────────────┴─────────────────────────┘
```

- El chat **entra desde la derecha** cuando se abre pantalla completa, 380 px.
- **Fondo oscuro**, para que sea la misma pieza que el lienzo y no una ventana
  pegada encima.
- La caja de pregunta abajo, siempre visible.
- **Todo el show ocurre acá adentro**: se pregunta, el camino se traza a la
  izquierda mientras la respuesta aparece a la derecha. No se sale nunca.
- Esc cierra.

---

# 5 · Que cualquier pregunta encienda el camino

El mecanismo general, en tres pasos:

1. **Ángela ya registra qué herramientas corrió** en su vuelta de tool-use
   (`angela._run_tool`). Eso es la lista de «consultó».
2. **Un resolutor** toma esa lista y los nombres propios que aparecen en la
   respuesta, y los convierte en nodos del grafo — es el mismo
   `grafo._resolver` que ya existe para las semillas de un hallazgo.
3. **Si la herramienta fue `consultar_cruces`**, el hallazgo trae su camino
   exacto y se enciende ése, que es el caso del demo y sale perfecto.

Así la pregunta del caso da los ocho nodos clavados, y *"¿quién me debe?"* da
los clientes morosos con sus cuentas. **General, con el caso del demo afinado.**

---

# 6 · Qué necesito que decidas

1. **¿Las tres tarjetas son las correctas?** Mi duda es si la 3 («de dónde
   salió») merece ser tarjeta propia o va dentro del chat, que es donde el
   jurado va a estar mirando cuando Ángela conteste.
2. **¿La banda de La Ribera abajo, o al costado?** Abajo separa mejor el
   contraste; al costado deja el lienzo más ancho para el camino principal.
3. **¿Querés el SVG oficial de WhatsApp** o te alcanza con el trazo que ya
   está?

Con eso arranco.
