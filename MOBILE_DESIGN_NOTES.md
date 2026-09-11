# PolPilot · Notas de diseño mobile (P35)

Principios aplicados al rediseño mobile (< 1024px, `useViewport.DESKTOP_MIN`).
No se cita la teoría: se documenta **dónde** se aplicó cada principio.

## Principios guía
- **Ley de Hick** — menos opciones visibles = decisión más rápida. La home
  ("Today") responde UNA pregunta: "¿qué hago hoy?". No expone todo lo que la
  app sabe.
- **Zona del pulgar** — lo accionable abajo (bottom-nav fija), lo informativo
  arriba (saludo, pulso, resúmenes).
- **Targets ≥ 44×44pt** — todo control tocable respeta el mínimo.
- **Jerarquía por peso y aire**, no por cajas y bordes — menos contenedores,
  más espacio en blanco.
- **Progressive disclosure** — la fila muestra titular + $; el detalle se abre
  al tocar. Nada de tarjetas de 400px en un viewport de 380.
- **Regla de corte** — si una sección no entra en el primer scroll, se resume,
  no se comprime.

---

## Etapa 1 — Header mobile
- **Ley de Hick / carga cognitiva**: se quitó el toggle EN/ES del header (una
  decisión menos en la barra superior). El idioma se **hereda** de la sesión
  (`POLPILOT_DEFAULT_LANG` / preferencia del usuario), no se fuerza. El toggle
  sigue en desktop.
- Se eliminó la palabra "FOR" (ruido sin información).
- **Jerarquía por aire**: el logo del cliente pasa a `h-11` con `object-contain`
  (respeta aspect-ratio, no se deforma ni se ve angosto). Fila única
  `[PolPilot] [cliente] … [campana] [avatar] [salir]`, sin wrap ni superposición
  (`min-w-0` + `shrink` para que el logo ceda espacio antes de romper la fila).
- Implementación: `Brand.jsx` gana un prop `variant` (`desktop` por defecto,
  intacto); `variant="mobile"` cambia solo el layout mobile. `MobileApp.jsx`
  deja de renderizar `<LangSwitch/>`.

---

## Etapa 2 — Bottom nav fija y simétrica
- **Zona del pulgar**: la barra pasa a `position: fixed; bottom:0` (antes había
  que scrollear hasta el fondo para verla). Respeta `env(safe-area-inset-bottom)`
  (iPhone con notch); el `<main>` lleva `pb-24` para que el último elemento no
  quede tapado.
- **Ley de Hick**: se eliminó "Más" (y sus dos ítems sueltos) y el mapa de la
  barra. Quedan 5 destinos fijos y claros: **Today · Insights · Ángela · Warehouse
  · Team**, con Ángela al centro (botón circular). También se quitó el botón
  flotante "preguntá a Ángela" (redundante con el centro de la barra).
- **Simetría**: `grid` con `repeat(n, minmax(0,1fr))` → columnas exactamente
  iguales (no flex con tamaños distintos). El slot se **oculta** si el rol no
  tiene la feature (Ángela siempre); el dueño del demo ve los 5.
- **Estado activo**: color + peso tipográfico, sin caja. Targets ≥44px.
- "Insights" es la fusión Alertas+Oportunidades (Etapa 3).

---

## Etapa 3 — Insights (fusión Alertas + Oportunidades)
- **Ley de Hick / progressive disclosure**: una sola lista de FILAS compactas
  (≤80px, medidas 65px) en vez de dos pantallas de cards grandes. Cada fila:
  punto de severidad + icono + título (máx 2 líneas) + $ a la derecha. Sin
  botón dentro. Al tocar se abre el detalle (DrillNegocio: el porqué + "Crucé:
  [fuentes]" + la acción "Que Ángela se encargue" / "Ver análisis").
- **Segmented control** Todo / Alertas / Oportunidades (default Todo), siempre
  ordenado por $ descendente.
- **Distinción visual** alerta vs oportunidad por icono + color del punto
  (rojo/oro/azul = alerta; verde + sparkle = oportunidad).
- **Riesgos separados**: la exposición (concentración $470.8M) va en su propio
  bloque "Riesgos a mirar", NUNCA mezclada con el capital capturable.
- **Fuente única, cero datos nuevos**: se extrajo la presentación de alertas a
  `lib/alertasNegocio.jsx` (usada por el desktop AlertasNegocio —sin cambio de
  comportamiento— y por InsightsMobile). Las oportunidades salen de
  `api.oportunidades` (mismas cards que desktop). Desktop conserva Alertas y
  Oportunidades como secciones separadas, intactas.

---

## Etapa 4 — Today (home mobile)
- **Ley de Hick / regla de corte**: Today responde UNA pregunta ("¿qué hago
  hoy?") en un scroll corto. Antes eran tarjetas grandes; ahora un resumen de 6
  bloques, cada tarjeta ≤120px (las listas usan filas compactas que se abren al
  tocar). Orden fijo: saludo → caja de hoy → el pulso → lo más importante →
  necesita tu decisión → el equipo hoy.
- **Zona del pulgar**: lo accionable (hablar con Ángela, resolver, ver todo)
  abajo de cada bloque; lo informativo arriba.
- **Datos reales**: caja de hoy = `api.cajaEstado().totales.total` (si no hay
  valor de hoy, se OMITE el bloque, no se inventa). El pulso = los cruces del
  día (los hallazgos que el mapa surface, incluida la exposición/concentración,
  como titulares SIN $: es el teaser del mapa, con link "Ver el mapa" → E6). Lo
  más importante = top 3 oportunidades accionables con $ → "Ver todo" a Insights.
  Necesita tu decisión = la approval queue real (armarDecisiones: staging +
  correcciones + solicitudes), máx 3 + contador. El equipo hoy = objetivos en
  proceso + recordatorios, máx 3 → "Ver equipo".

## Etapa 6 — Vista simple del mapa (mobile)
- **Read-only, sin React Flow, sin canvas/hover/doble clic**: una lista vertical
  de los 8 dominios, cada uno con su semáforo REAL + una línea de conclusión.
  Al tocar un dominio se expande su conclusión + "Preguntar a Ángela".
- **Progressive disclosure**: arriba "Fuentes conectadas · 8" + "N cruces" (14,
  coincide exacto con el desktop). Accesible SOLO desde "Ver el mapa" de Today;
  no está en la barra inferior.
- **Misma fuente que el panel derecho del mapa, cero datos nuevos**: se replica
  la lógica de `tonoDe`/`datoNodo`/fuentes del mapa desktop sobre los mismos
  endpoints (`cargarSenales` + `api.macro` + `api.oportunidades`), reusando las
  claves i18n del mapa (`mapa.d_*`, `mapa.n_*`). NO se tocó MapaNegocio.jsx
  (innegociable): el desktop queda 100% intacto.
