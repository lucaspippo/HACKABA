# Objetivos medidos — qué es real y qué es sintético (P36·E4)

Los 7 objetivos que Ángela "mide sola" (`core/objetivos_medidos.py` + endpoint
`/api/objetivos-medidos`) combinan **datos reales en vivo** con **historial
sintético**. Este archivo documenta exactamente qué se generó sintéticamente y
con qué criterio. **Solo tenant demo** (`POLPILOT_TENANT=demo`); jamás toca el
piloto ni el canónico. Todas las fechas ≤ `POLPILOT_DEMO_TODAY` (2026-07-07).

## Qué es REAL (en vivo, del mismo cálculo que ya usa la app)
El `valor actual` de cada objetivo se computa en el endpoint desde la MISMA
fuente que el resto de la app — no se hardcodea nada:

| Objetivo | `actual` real | Fuente |
|---|---|---|
| Días de cobro | `kpis.cobro_dias` = 25 | análisis (cuentas corrientes) |
| Datos a corregir | `libro_triado.total_issues` = 20 | saneamiento |
| Liberar dormido | `baseline − kpis.dormido.monto` → $19.1M liberados | inventario |
| PVP + margen | `kpis.margen_teorico.sin_pvp` = 8 | margen teórico |
| Concentración | card `concentracion.datos.pct_top3` = 41.5% | oportunidades/clientes |
| Cobrar morosos | `cuentas.alertas().impacto_pesos` = $85,7M | cuentas corrientes |
| Reponer antes de quebrar | productos con cobertura ≤ 14 días = 35 | rotación × stock |

Como el `actual` es el dato vivo, el objetivo **se mueve solo** cuando el dueño
opera (cobra, corrige, carga precios): abre la app y ya avanzó. El progreso se
CALCULA: `(baseline − actual) / (baseline − meta)`.

## Qué es SINTÉTICO (solo demo)
Para que la barra tenga pasado y se vea la tendencia, cada objetivo lleva un
**baseline** (punto de partida ~4 semanas atrás) y un **historial de 3 puntos
semanales** (16, 23 y 30 de junio 2026). El 4º punto es el `actual` real de hoy.
Criterio: coherente con la escala real del dataset (mismos empleados, mismos
clientes/SKUs, montos en ARS), y elegido para que la distribución sea creíble —
**la mayoría a mitad de camino, uno casi cumplido, uno estancado** (que todo
vaya perfecto no es creíble ni interesante).

| Objetivo | baseline (sint.) | historial (sint.) | meta | progreso | estado |
|---|---|---|---|---|---|
| Liberar dormido | $88M dormido | 8M → 14M → 17M liberados | $20M | ~95% | **casi cumplido** |
| PVP + margen | 20 sin precio | 20 → 15 → 11 | 0 | ~60% | avanza |
| Datos a corregir | 44 registros | 44 → 34 → 26 | 0 | ~55% | avanza |
| Días de cobro | 29 días | 29 → 27 → 26 | 20 | ~44% | avanza |
| Concentración | 44% | 44 → 42 → 41 | 15% | ~9% | **estancado** |
| Cobrar morosos | $132M de mora | 132M → 118,4M → 99,1M | $20M | ~41% | avanza |
| Reponer antes de quebrar | 58 productos | 58 → 49 → 41 | 10 | ~48% | avanza |

- **Responsables**: empleados REALES del demo (Marta, Celeste, Aldo) según su rol.
- **"Estancado"** se detecta del historial: el último tramo casi no se movió
  (concentración: 41→41.5, sin avance) → se marca distinto (ámbar) del que avanza.
- **Permisos server-side**: el dueño ve los 7; cada empleado, solo los suyos
  (filtro por `responsable` en el endpoint, sin bypass en el cliente).

## Dónde vive
- Definiciones + cálculo: `backend/core/objetivos_medidos.py` (no lee datos;
  recibe los `actuales` reales que arma el endpoint → una sola fuente de verdad).
- Endpoint: `backend/main.py` → `/api/objetivos-medidos`.
- UI: `frontend/src/sections/ObjetivosPanel.jsx` (desktop Equipo + mobile).

## Los dos que se sumaron (P41·3.3)
`cobrar_morosos` y `reponer_quiebres` siguen EXACTAMENTE el mismo contrato: el
`actual` se LEE de donde ya lo lee el resto de la app (la mora es el mismo
$85,7M que muestran Alertas y la card de morosos — no se recalcula ni se mueve),
y solo el baseline+historial son sintéticos. El umbral de "por quebrar" es el
MISMO que usa el hallazgo de quiebre inminente
(`objetivos_medidos.COBERTURA_QUIEBRE_DIAS` = 14), para que el objetivo y el
hallazgo nunca cuenten cosas distintas.

Las metas no son cero donde cero sería mentira: la mora de una distribuidora
nunca llega a $0 y siempre hay algo por reponer — por eso $20M y 10 productos.

Si mañana cambian los datos reales (se cobra, se corrige, se cargan precios),
los `actual` cambian y el progreso se recalcula solo. El baseline/historial
sintético queda fijo (es el "pasado" del demo).
