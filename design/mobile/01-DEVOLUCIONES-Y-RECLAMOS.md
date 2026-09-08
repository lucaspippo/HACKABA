# Devoluciones y reclamos, conducidos por lo que pide cada proveedor

Diseño. Relevado contra `main` en `0778dda3`. Los mockups navegables están en
[`prototipo/`](prototipo/index.html) — el flujo completo de recepción son las
pantallas `nahuel.r1` … `nahuel.r5`; el del chofer, `walter.dev1` … `walter.dev3`.

---

## 1. Qué resuelve

Aparece mercadería rota, vencida, de menos, o un cliente devuelve algo. Ahí
arranca un ida y vuelta que el que está en el depósito no tiene por qué saber
resolver: *¿este proveedor pide foto? ¿pide el lote? ¿acepta por mail o hay que
llamar? ¿tiene plazo?* Por eso el reclamo se hace mal, tarde, o no se hace.

La apuesta: **que la app sepa qué exige cada proveedor y le pida a la persona
exactamente eso — ni más ni menos.** La persona no elige qué mandar: contesta lo
que le van pidiendo, y puede contestar hablando en cualquier paso.

---

## 2. Dónde vive ese conocimiento

**Veredicto: entra en `core/conocimiento.py` sin forzar nada. Hace falta agregar
un valor a un catálogo, y nada más.**

### Por qué entra

Una pieza de conocimiento ya tiene exactamente la forma que hace falta
(`conocimiento.py:279`):

```
texto · texto_en · tipo · ambito · entidad · nodo · efecto ·
efecto_profundo · params · origen{quien,cuando} · estado · veces_aplicada
```

Y los cuatro campos que importan ya están en uso con este mismo patrón:

| Campo | Valor que necesitamos | ¿Existe hoy? |
|---|---|---|
| `tipo` | `protocolo` | Sí — 4 de las 22 piezas sembradas lo usan |
| `ambito` | `proveedor` | Sí — `AMBITOS` (`conocimiento.py:46`) |
| `entidad` | `"Lácteos Campo Alegre"` | Sí, con match fuzzy (`_match_entidad`) |
| `nodo` | `proveedores` | Sí — `NODOS` (`conocimiento.py:49`) |
| `params` | los requisitos | **Sí, y es el precedente que cierra el caso** |

`params` es un dict libre que **cada motor lee con su propia clave**, y eso ya
está en producción en cinco lugares: `cuentas.py:111` lee `tolerancia_dias`,
`deposito.py:152` lee `umbral_pct`, `conciliacion.py:73` lee `umbral_pct`,
`carpeta.py:183` lee `tolerancia_dias`, `oportunidades_neg.py:391` lee
`evitar_dia`. La pieza sembrada `k09` es literalmente un `protocolo` de ámbito
`proveedor` con `params: {"umbral_suba_pct": 15}`.

> «A Campo Alegre mandale siempre foto del lote» tiene **la misma forma** que
> «A Doña Elsa tolerale hasta 45 días». Un módulo aparte sería una segunda
> memoria de la casa que no declara su fuente ni se aprende.

### La pieza, concreta

```json
{
  "tipo": "protocolo",
  "ambito": "proveedor",
  "entidad": "Lácteos Campo Alegre",
  "nodo": "proveedores",
  "efecto": "exige_evidencia",
  "params": {
    "reclamo": {
      "requisitos": ["foto_producto", "numero_lote", "numero_remito"],
      "canal": "email",
      "plazo_dias": 5
    }
  },
  "origen": {"quien": "aldo", "cuando": "2026-06-20"},
  "texto": "Campo Alegre acepta reclamos por mail, con foto del producto, el lote y el número de remito. Tiene 5 días de plazo.",
  "texto_en": "Campo Alegre takes claims by email, with a photo of the goods, the lot and the delivery-note number. Five-day window."
}
```

El contacto y el mail **no van en la pieza**: ya están en
`apartados.proveedores` (`contacto`, `telefono`, `email`, `cuit`). La pieza dice
*qué hace falta*, no *a quién se le manda*.

### Lo único que hay que agregar

**Un valor al catálogo `EFECTOS`** (`conocimiento.py:47`). Hoy son cinco:
`ajusta_umbral`, `suprime_alerta`, `genera_alerta`, `contexto_para_angela`,
`requiere_aprobacion`.

Los cinco describen qué le hace la regla a un **análisis**. Ninguno describe
"cambia lo que la app le pide a una persona". Reutilizar `requiere_aprobacion`
sería mentir: significa «no lo ejecutes sin un OK», y eso ya es cierto de todo
reclamo. Propongo `exige_evidencia`: una línea en un `frozenset`, no una tabla
nueva.

**Lo que NO hace falta:** ni tabla nueva, ni `tenant_tables.py`, ni endpoint
nuevo de escritura — `POST /api/conocimiento` y el flujo
`crear` → `pendiente` → `aprobar` ya existen y ya están auditados.

---

## 3. El flujo, paso por paso

### 3.1 Recepción (Nahuel) — el camino principal

| # | Pantalla | Qué se le pide | Toques |
|---|---|---|---|
| 0 | `nahuel.esc` | Escanear el producto o el remito | 1 + apuntar |
| 1 | `nahuel.r1` | **Qué pasó**: roto · de menos · vencido · no era lo que pedimos | 1 |
| 2 | `nahuel.r2` | **Cuánto**: teclado grande, con el total de la entrega a la vista | 2 |
| 3 | `nahuel.r3` | **Lo que pide este proveedor** — ya completado hasta donde se pudo | 1 |
| 4 | `nahuel.r4` | **A quién le llega** — Ángela propone, la persona confirma | 1 |

**Total: 6 toques.** Y sobre eso, lo que importa: **de los tres requisitos de
Campo Alegre, la app resuelve dos sola.**

- El **lote** sale de `apartados.deposito` (el producto que se está recibiendo
  ya tiene su fila con `lote` y `vencimiento`).
- El **remito** sale de la orden abierta de ese proveedor
  (`esquema.filas("ordenes_compra")`, estado `abierta` — el helper
  `piso._orden_abierta` ya hace exactamente esta búsqueda, `piso.py:206`).
- La **foto** es lo único que sólo puede aportar la persona.

El paso 3 no es un formulario de tres campos: es una lista de tres tildes verdes
y **un** botón.

### 3.2 El mismo reclamo, hablando

`nahuel.voz`. Una frase —«ocho cajas de manteca Santa Clara vinieron rotas, del
lote L-2026-368»— llena motivo, producto, cantidad y lote de una vez.

**Total: 3 toques** (micrófono, parar, mandar).

Ése es el argumento real de la voz: no que sea más cómoda, sino que **colapsa
pasos**. Y no reemplaza a nada: la alternativa táctil está siempre, porque la voz
falla con ruido de depósito. Lo que se muestra después de hablar es lo que
`voz.proponer` (`core/voz.py:210`) ya devuelve hoy — transcripción, candidatos de
producto, `avisos[]` y `bloqueado[]` — y el número pasa por
`core/validacion`, el mismo peaje que una cantidad leída de un remito.

### 3.3 Chofer (Walter) — devolución del cliente en la puerta

**Tres pasos, no cuatro, y ninguno pide requisitos de proveedor.** Walter está
parado, con el motor andando y un cliente enfrente. El reclamo, si corresponde,
lo arma Compras después.

| # | Pantalla | Qué se le pide | Toques |
|---|---|---|---|
| 1 | `walter.dev1` | Qué pasó: roto · no era lo que pidió · vencido · no lo quiso | 1 |
| 2 | `walter.dev2` | Qué renglón vuelve — **los renglones del pedido ya están en pantalla** | 2 |
| 3 | `walter.dev3` | A dónde va: Ramón recibe la mercadería, Celeste se entera | 1 |

**Total: 4 toques.** Nada se escribe: el producto se toca de la lista del pedido
que él mismo lleva.

### 3.4 Por qué no entran en 3 toques, y qué hago con eso

**Cambio la vara del brief, y lo digo en vez de maquillarlo.** «3 toques o
menos» es correcto para una cosa y falso para otra:

- **Cerrar** algo que ya está propuesto en pantalla: **≤ 3 toques.** Confirmar un
  conteo, marcar una entrega, aceptar un aviso, corregir las balanzas. Todos los
  flujos de cierre del prototipo cumplen.
- **Originar** un hecho con evidencia para un tercero: **≤ 6 toques**, y cada
  toque tiene que reemplazar una pregunta que hoy se hace por WhatsApp.

Forzar el reclamo a tres toques sólo se logra sacándole la foto o el lote — es
decir, mandando un reclamo que el proveedor va a rechazar. El ahorro sería falso.

---

## 4. Cómo arranca, por rol

| Rol | Entrada principal | Entrada secundaria | Por qué |
|---|---|---|---|
| **Recepción** (Nahuel) | **Escaneo del producto** | Desde el renglón de la recepción abierta | Tiene la caja en la mano; el código de barras es más rápido y no se equivoca de producto |
| **Encargado** (Ramón) | **Desde la diferencia ya detectada** | Escaneo | Él no descarga: revisa lo que ya está marcado |
| **Chofer** (Walter/Osmar) | **Desde la parada** | Foto | El cliente y el pedido ya están en pantalla: elegirlos de nuevo sería absurdo |
| **Mostrador** (Vanesa) | **Escaneo** | Búsqueda por nombre | Un cliente devuelve algo comprado ahí |
| **Armado** (Brian) | No es su flujo | — | Un faltante de picking es un aviso, no un reclamo |
| **Conteos** (Tomás) | No es su flujo | — | Una diferencia de conteo no es un reclamo a nadie |
| **Compras** (Celeste) | **Desde el aviso que le llegó** | — | Ella no origina: recibe y arma |

**El escaneo es la entrada principal de todo el depósito**, y no por moderno: un
producto agarrado mal es un reclamo mandado contra el proveedor equivocado.
`buscador` y el escaneo comparten caja en la pantalla de búsqueda por eso mismo.

---

## 5. Cómo se aprende

Cuatro caminos, todos con `origen` declarado, ninguno con un formulario de
sesenta campos. Los cuatro nacen `estado: "pendiente"` y **no aplican hasta que
alguien los aprueba** — eso ya funciona así (`conocimiento.aprobar`, auditado).

1. **La primera vez, preguntando.** Cuando el dueño aprueba el primer reclamo a
   un proveedor, Ángela pregunta tres cosas: qué pide, por dónde, y en cuánto
   tiempo. Tres preguntas, una vez en la vida de ese proveedor.
2. **Porque volvió rechazado.** El reclamo vuelve con «falta el lote» → se
   propone la pieza con `origen.quien: "Ángela"` y la evidencia adentro (el id
   del reclamo rechazado). Es la pantalla `aldo.regla` del prototipo.
3. **Mirando lo que hace el dueño.** Si agrega la misma foto tres veces antes de
   mandar, eso es una regla que todavía no dijo en voz alta.
4. **Porque lo anota él.** Hablando, desde el botón de carga. El riel ya existe:
   `angela.py` tiene la herramienta `proponer_conocimiento`.

El mecanismo genérico para (2) y (3) también existe: `pattern_feedback.learn()`,
que el docstring de `conocimiento.py` describe como el «Enseñale a Ángela» que
cualquier motor de detección puede usar sin código nuevo acá.

---

## 6. Los límites

**Automático hasta armar el reclamo, nunca hasta mandarlo.** La app junta la
evidencia, arma el reclamo con lo que ese proveedor pide y lo deja listo; una
persona lo aprueba y lo manda.

Es el mismo límite que `core/ordenes.py` ya pone, con las mismas palabras:
*«aprobarla no la manda al proveedor: la deja lista para salir, con su registro
en la auditoría»*. Y es coherente con `core/autonomia.py:37`, donde `plata` y
`stock` están clavados en `pide_ok` sin setting que los afloje. Acá importa más
que en otros lados: del otro lado hay un tercero y hay plata.

**Si no sabemos qué pide ese proveedor, se dice.** Pantalla `nahuel.r3b`:

> «De Golosinas Costa Dulce todavía no sé qué pide. Junto lo básico y lo
> aprendemos con la respuesta.»

Nada de mostrar un set genérico fingiendo que es el correcto. Una lista de
requisitos inventada que hace rechazar el reclamo es peor que no tener ninguna,
porque enseña a desconfiar de la pantalla.

**Nada se descuenta ni se reserva.** Ni el reclamo ni la devolución tocan el
stock: son hechos que prueban que el stock del ERP está mal. El ajuste lo hace el
ERP cuando alguien lo aprueba (**Record Rule**, ahora en `PRODUCT.md`).

---

## 7. Qué ve el que lo originó

**Este flujo es el que mejor cierra el círculo de P3, y por eso es el que más
lo expone si no se construye.** Pantalla `nahuel.rep1`:

```
● Lo reportaste                    Hoy 09:14 · desde Recepción
● Celeste lo vio                   Hoy 09:31
● Se armó el reclamo a Campo Alegre  Con tu foto, el lote y el remito · $53.323
● Aldo lo aprobó y salió           Hoy 11:03 · por mail, como pide el proveedor
○ Esperando la nota de crédito     Contesta en 5 días hábiles · te aviso
```

Cinco renglones. Los cuatro primeros ya son datos que el sistema tiene o tendría;
el quinto es el único que le importa a Nahuel.

Cada rol ve el tramo que le toca, no el tablero entero:

| Rol | Qué ve de este reclamo |
|---|---|
| Nahuel (lo originó) | Los cinco renglones, con nombres |
| Celeste (lo armó) | Todo, y además los otros avisos del mismo proveedor |
| Ramón (encargado) | Que pasó por su galpón y en qué quedó |
| Aldo | La decisión y el monto |
| Tomás, Brian, Walter | Nada — no es de ellos |

---

## 8. Sin señal

La devolución se arma en la cámara de frío o en la banquina. Estados, explícitos
en pantalla:

```
● Guardado en tu teléfono      no se pierde aunque cierres la app
○ Esperando señal              sale solo cuando haya
○ Celeste lo ve                te aviso cuando lo abra
```

**Esto hoy no se puede construir.** Verificado en el repo: no hay service worker,
no hay `manifest.webmanifest`, no hay IndexedDB, no hay ninguna cola local en
`frontend/src`. Todo lo offline de este documento es **pantalla sin motor**, y
está separado como tal en el entregable.

Y una decisión de diseño que sí depende de eso: **el chip «guardado, se manda
solo» aparece siempre, no sólo cuando falla la red.** Si sólo aparece cuando hay
problema, la primera vez que aparezca nadie va a saber qué significa.

---

## 9. Qué hace falta para construirlo

Ordenado por cuánto lo bloquea:

| # | Qué | Dónde | Tamaño |
|---|---|---|---|
| 1 | `destinatario` + `estado` en el reporte de piso | `core/piso.py` + migración | Medio |
| 2 | Notificar al que originó, al cerrar | `piso.resolver` → `notificaciones.emitir` | Chico |
| 3 | Consumir `api.piso.reportes` en una pantalla | Front | Chico |
| 4 | `exige_evidencia` en `EFECTOS` | `conocimiento.py:47` | Una línea |
| 5 | Leer `params.reclamo` al armar el reclamo | Motor nuevo, chico | Medio |
| 6 | Sembrar las piezas de los 6 proveedores | `data-demo/seed_conocimiento.py` | Chico — **rama aparte, a confirmar** |
| 7 | Cola offline | No existe nada | Grande |
| 8 | Permiso «decide en su dominio» para Ramón | `authz` | **Lo decide Agustín, no se toca acá** |

---

## 10. Supuestos

- **[S6]** Que los proveedores de una distribuidora de alimentos tienen
  requisitos distintos y estables entre sí. Es plausible y es lo que dice el
  brief, pero no hay un solo dato de esto en el repo: `proveedores_condiciones.json`
  guarda plazos de reposición y frecuencia de listas, nada de reclamos.
- **[S7]** Que la foto es el requisito más común y el único que la app no puede
  resolver sola. Si resulta que el número de factura del proveedor es más común,
  el paso 3 cambia de contenido pero no de forma.
- **[S8]** Que el chofer prefiere tres pasos sin requisitos a cuatro con ellos.
  Sale de la condición física (parado, motor andando), no de observación.
- **[S9]** Que un reclamo rechazado vuelve con un motivo legible. Si vuelve como
  «no corresponde», el camino de aprendizaje 2 no aprende nada y quedan los
  otros tres.
