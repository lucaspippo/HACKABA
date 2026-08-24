# Conocimiento sintético del negocio — "lo que Aldo le enseñó a Ángela"

La capa NO estructurada que ningún ERP tiene: reglas, excepciones, protocolos y
contexto. 22 piezas sembradas SOLO en el tenant demo (Distribuidora del Litoral),
atribuidas a **Aldo** entre el **5 de junio y el 6 de julio de 2026**, coherentes
con el dataset (mismos 24 clientes, 6 proveedores, 8 rubros, empleados reales del
demo, escala ARS, fechas ≤ 2026-07-07). El piloto NO tiene este archivo:
`git diff data/` (piloto) = 0.

- **Modelo/persistencia:** `backend/core/conocimiento.py` → `data-demo/conocimiento_negocio.json`.
- **Siembra determinista e idempotente:** `data-demo/seed_conocimiento.py` (ids fijos `k01…k22`).
- **Endpoints:** `GET/POST /api/conocimiento…` (lectura scopeada por rol; escritura solo el dueño).
- **Enganche del efecto:** los motores llaman `conocimiento.para(...)` / `aplicables(...)`
  y adjuntan `conocimiento_aplicado` (con `texto`/`texto_en`) al hallazgo. `veces_aplicada`
  es acumulado sembrado (no se mueve en el recálculo → cero churn del snapshot).

## Bilingüe (i18n estricto)

Cada pieza lleva `texto` (como lo diría Aldo, ES) y `texto_en` (lo que Ángela le
muestra al reviewer). El frontend elige por idioma; las líneas que el backend
inyecta en el porqué usan claves i18n ES/EN. Verificado EN+ES.

## Estado de los efectos

- **✓ efecto profundo** — cableado a un motor y verificado en vivo en E2.
- **○ contexto/panel** — sembrada con tipo/efecto/params correctos y servida por el
  endpoint (scopeada); su efecto visible es el panel **"Lo que Aldo me enseñó"** del
  nodo + el camino de conocimiento, que se construyen en **E3**. Degradada a
  `contexto_para_angela` por decisión de diseño (el efecto profundo tocaba un
  cálculo correcto o faltaba dato — ver "Nota" por pieza).

Las **4 piezas del video** (1, 7+8, 11, 12) tienen efecto profundo, no degradado.

| # | id | Tipo · Efecto | Qué hace (verificable) | Dónde verificarlo | Estado |
|---|----|---|---|---|---|
| 1 | k01 | regla · ajusta_umbral | El 113% de Doña Elsa NO desaparece; se reencuadra contra los 45 días tolerados: "los 66 son 21 más que tu límite". | `GET /api/cuentas/despensa_dona_elsa` → `tolerancia_dias:45, exceso_tolerancia:21`; estado de cuenta → veredicto con la línea de tolerancia (ES/EN). | ✓ |
| 2 | k02 | regla · ajusta_umbral | Tope de $5M de cuenta corriente para clientes < 6 meses. **Nota:** el dataset no tiene antigüedad de alta por cliente → degradada. | Panel del nodo **clientes** (E3). | ○ |
| 3 | k03 | protocolo · requiere_aprobacion | Intimación de moroso a 60 días: prepararla, no mandarla sin OK. **Nota:** no hay cola de cobranzas con acción de intimación hoy → degradada. | Panel del nodo **clientes** (E3). | ○ |
| 4 | k04 | contexto · contexto_para_angela | La card de concentración se reencuadra: "son los que pagan en fecha, el riesgo es de concentración, no de cobro" (el 41.5% no cambia). | `GET /api/oportunidades` → card `concentracion` → `conocimiento_aplicado:[k04]` + línea en `drill.porque`. | ✓ |
| 5 | k05 | excepcion · suprime_alerta | A Rotisería Avenida se le vende bajo margen a propósito (vencimiento corto). **Nota:** la card `margen_bajo` es por-producto, no por-cliente → sin match limpio, degradada. | Panel del nodo **clientes** (E3). | ○ |
| 6 | k06 | contexto · contexto_para_angela | El Comedor Escolar N°12 factura poco en enero (cierra). **Nota:** la caída de Evolución es interanual (enero vs enero) → no se dispara sola; queda como contexto. | Panel del nodo **clientes** (E3). | ○ |
| 7 | k07 | regla · ajusta_umbral | La ventana de compra nunca propone viernes (depósito a media dotación) y lo dice; si el día natural cae viernes lo corre al jueves. | `GET /api/oportunidades` → card `ventana_compra` → `datos.evito_viernes:true`, `dia_pedido`; línea de viernes en `drill.porque` (ES/EN). | ✓ |
| 8 | k08 | contexto · contexto_para_angela | La ventana cita que Lácteos Campo Alegre sube la lista todos los meses hace un año (refuerza comprar antes). | `GET /api/oportunidades` → card `ventana_compra` → `conocimiento_aplicado:[k08,k07]` + línea de suba en `drill.porque`. | ✓ |
| 9 | k09 | protocolo · requiere_aprobacion | Lista que sube > 15%: no aplicar, avisar. **Nota:** el gate real vive en `lista_precios.diff` (umbral hoy 20%); no se cableó en E2 para no tocar la ingesta → degradada. | Panel del nodo **proveedores** (E3). | ○ |
| 10 | k10 | regla · contexto_para_angela | A Frigorífico La Ribera se le paga a 30 días: declarado como supuesto de la proyección 30/60/90. | `GET /api/pagos` → `proyeccion.conocimiento_aplicado` incluye k10 + `notas_conocimiento`. | ✓ |
| 11 | k11 | regla · genera_alerta | GASEOSA COLA LA RIBERA sube al tope del quiebre inminente y lleva chip "Regla de Aldo: crítico". | `GET /api/oportunidades` → card `quiebre_inminente` → `chip_conocimiento`, `conocimiento_aplicado:[k11]`, regla citada en `drill.porque[0]`. | ✓ |
| 12 | k12 | excepcion · suprime_alerta | Discrepancia de balanza < 1% suprimida y mostrada como "1 alerta suprimida por tu regla — vela acá". | `GET /api/deposito` → `discrepancias_suprimidas:[{QUESO…, 0.65%, regla:k12}]`; la discrepancia sembrada (lote codigo 1302, ~0.65%) no aparece en `discrepancias`. | ✓ |
| 13 | k13 | protocolo · contexto_para_angela | Cámara de frío > 4°C por > 2h: avisar a Aldo primero. Protocolo activo con responsable. | Panel del nodo **deposito** (E3). | ○ |
| 14 | k14 | contexto · contexto_para_angela | El stock dormido de limpieza fue una compra por precio, no un error: la card lo distingue. | `GET /api/oportunidades` → card `despertar_dormido` → `conocimiento_aplicado:[k14]` + línea en `drill.porque`. | ✓ |
| 15 | k15 | regla · contexto_para_angela | Fiambres: nunca más de 15 días de stock. **Nota:** el umbral de rotación es global (35/60d) y compartido por varios hallazgos + tests → degradada (no se toca el cálculo). | Panel del nodo **inventario** (E3). | ○ |
| 16 | k16 | regla · contexto_para_angela | Los precios de fiambres los revisa Vanesa antes de aplicar. **Nota:** no hay hoy una superficie de "renglones de precio de fiambres" para colgar "requiere OK" → degradada. | Panel del nodo **equipo/inventario** (E3). | ○ |
| 17 | k17 | contexto · contexto_para_angela | Tomás maneja depósito martes y jueves. **Nota:** no hay motor de asignación de tareas por día → degradada. | Panel del nodo **equipo** (E3). | ○ |
| 18 | k18 | protocolo · requiere_aprobacion | Correcciones de stock en lote: solo el dueño. **Nota:** no hay cola de aprobación de correcciones en lote hoy → degradada. | Panel del nodo **equipo** (E3). | ○ |
| 19 | k19 | contexto · contexto_para_angela | Diego es el que más consulta cobranzas: es su tema. | Panel del nodo **equipo** (E3). | ○ |
| 20 | k20 | regla · contexto_para_angela | El IPC que se usa para deflactar es el oficial. **Nota:** Evolución ya deflacta por IPC oficial; queda como tooltip/contexto. | Panel del nodo **contexto** (E3). | ○ |
| 21 | k21 | regla · genera_alerta | Piso de caja $10M (colchón de sueldos): declarado en la proyección con `piso_caja`. **Nota:** el cruce absoluto necesita el saldo de caja base (la proyección es flujo neto) → se declara el piso, no se computa el cruce. | `GET /api/pagos` → `proyeccion.piso_caja:10000000` + k21 en `conocimiento_aplicado`. | ✓ |
| 22 | k22 | contexto · contexto_para_angela | Junio y diciembre tienen aguinaldo: esos meses no se comparan. Declarado como supuesto de la proyección. | `GET /api/pagos` → `proyeccion.conocimiento_aplicado` incluye k22 + nota. | ✓ |

**Resumen:** 22/22 sembradas, 0 vacías. **10 con efecto profundo verificado en E2**
(k01, k04, k07, k08, k10, k11, k12, k14, k21, k22) — incluye las 4 del video.
**12 degradadas a `contexto_para_angela`** cuyo efecto visible se completa en E3
(panel "Lo que Aldo me enseñó" + camino de conocimiento por nodo). Ninguna descartada.

## Pendiente E3 (auditoría de leaks de categoría en templates de hallazgo)

Aparte del bug de sub-nodos (E0, resuelto), estos templates inyectan la categoría
cruda en inglés (muestran español con la app en EN). A barrer en E3 con un
traductor de categorías backend (espejo del `tCat` del front):
`core.opn.pico_t/pico_r/pico_chat/pico_q1/pico_g` (card pre-pico),
`core.opn.margen_i` (card margen bajo), `core.analisis.obj_pico_titulo` (objetivos),
`core.analisis.est_aviso` (aviso de estacionalidad).

## Cómo grabar la escena de enseñar una regla (E4 — pendiente)

La pieza 12 (balanza) es el caso de grabación: Aldo escribe la regla por chat →
Ángela la reconoce como conocimiento (no consulta), confirma tipo y cómo la va a
aplicar → con el OK se persiste y aparece en el nodo Depósito al instante, y la
discrepancia < 1% pasa a "1 alerta suprimida — vela acá". (Mecanismo en E4.)
