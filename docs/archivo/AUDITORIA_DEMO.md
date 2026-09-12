<!-- Archivo traído de PolPilot-TOP el 2026-09-07. Los nombres del cliente
     real (ERP, dueño, empleada, familiar) están REDACTADOS: PRODUCT.md dice
     que ningún dato de cliente real vive en este repo, y este informe era
     justamente el mapa real→ficticio. Lo que vale de él —qué se filtró, cómo
     se midió, cómo se cerró— queda entero. -->

# ⚠️ RESUELTO el 11/08/2026 — ver el cierre al final de esta nota

La limpieza que este informe pedía SE HIZO y la demo SE PUBLICÓ:
repo `lucaspippo/POLPILOT-DEMO-SINTETICA-YC`, commit inicial `7b5c491`
(historial nuevo, sin arrastre). Cliente real → identidad ficticia
("Supermercados Horizonte" / tenant `piloto`), [ERP real]→Faro, [dueño real]→Emilio,
[empleada real]→Paula, [familiar real]→Osvaldo. Auditoría final: 0 coincidencias.
Suite: 822 passed / 24 skipped. El informe de abajo queda como registro
histórico de QUÉ había antes de limpiar.

---

# Auditoría de `polpilot-demo/` — resultado: **NO PUBLICABLE**

> Ejecutada el 11/08/2026 sobre `polpilot-demo/`, antes de cualquier `git init` o `push`.
> **No se inicializó git ni se pusheó nada.** El repo `POLPILOT-DEMO-SINTETICA-YC` sigue vacío.

## Veredicto en una línea

El **dataset** de la demo está limpio (es 100% sintético), pero el **código** que lo sirve
no lo está: es el mismo código del piloto, y menciona al cliente real por nombre en 30
archivos. **429 coincidencias** de rastros del piloto en total.

## La razón de fondo (esto no es un descuido suelto)

La demo **no es un proyecto aparte**. Es *el mismo codebase* del piloto corriendo con
`POLPILOT_TENANT=demo` y `POLPILOT_DATA_DIR=data-demo`. La separación se diseñó a nivel
**runtime** (`backend/core/paths.py`), y el aislamiento de privacidad se puso en el
**Dockerfile** — que excluye `data/` y hace fallar el build si algo del piloto se cuela
en la imagen.

Ese diseño protege **la imagen que corre en Render**. No protege **el código fuente**,
porque el repo de GitHub siempre fue privado. El propio test lo dice:

```
backend/tests/test_p37.py:7
# No se testea el bare "santa-elena": el repo se llama "polpilot-santa-elena"
```

Publicar el fuente cambia esa premisa. Por eso la auditoría falla.

## Qué se buscó y qué se encontró

| # | Patrón buscado | Resultado | Coincid. | Archivos |
|---|---|---|---|---|
| 1 | `santa elena` / `santa_elena` / `santa-elena` / `santaelena` | **FUGA** | 80 | 30 |
| 2 | `Supermercados Santa …` (razón social) | **FUGA** | 6 | 6 |
| 3 | `[ERP real]` (el ERP real del cliente) | **FUGA** | 37 | 17 |
| 4 | `Pilar, Buenos Aires` (ciudad del piloto) | **FUGA** | 1 | 1 |
| 5 | `[dueño real]` (dueño real) | **FUGA** | 215 | 42 |
| 6 | `[familiar real]` (padre del dueño) | **FUGA** | 2 | 2 |
| 7 | `[empleada real]` (empleada real) | **FUGA** | 71 | 13 |
| 8 | Claves del piloto (`cheddar-2311`, `pilar-8930`, `remito-5138`) | **FUGA** | 4 | 1 |
| 9 | Cifra real `$541.447.852` / `$541M` | **FUGA** | 9 | 5 |
| 10 | Nombres de los exports del ERP real (`CONSOLIDADO_Santa_Elena.xlsx`, …) | **FUGA** | 1 | 1 |
| 11 | `MUZZARELLA` (marcador de inventario real, el del −17.534) | **FUGA** | 3 | 3 |
| 12 | Otras cifras reales (`262.187.013`, `69.556.425`, `89.254`) | LIMPIO | 0 | 0 |
| 13 | API keys (`sk-ant-…`) | LIMPIO | 0 | 0 |
| 14 | Archivos `.env` / `credenciales.json` | LIMPIO | 0 | 0 |

310 archivos de texto inspeccionados (excluyendo `node_modules`, `dist`, `__pycache__`).
Se buscó además en **nombres de archivo**, no sólo en contenido.

> Nota de método: `grep` recursivo falló de forma intermitente en esta máquina — un run
> abortó con exit 134 y otro dio falsos negativos verificables. Por eso el barrido
> definitivo se hizo con un script Python determinista
> (`_por_revisar/herramientas-auditoria/auditoria.py`), y los hallazgos se confirmaron
> archivo por archivo.

## Los hallazgos que más importan (con la línea exacta)

### 1. `backend/angela.py:185-190` — el peor. Es el prompt del sistema.

```python
_INTRO_PILOTO = """Sos Ángela, la inteligencia de PolPilot para Supermercados Santa Elena.

Santa Elena es una distribuidora de alimentos de Pilar, Buenos Aires, que también
vende al público y se está expandiendo a varios locales y franquicias. El dueño
([dueño real]) y su padre ([familiar real]) vienen del mostrador: no son técnicos y no quieren
aprender ningún sistema."""
```

Razón social + ciudad + nombre del dueño + nombre de su padre + descripción del negocio,
en cuatro líneas.

### 2. `README.md` — el primer archivo que alguien abre en GitHub

```
línea 1  : # PolPilot × Santa Elena — Sprint 0
línea 7-8: …datos reales del [ERP real] ERP de Santa Elena: **$541.447.852 ARS** parados en
           mercadería — el número que el dueño dijo…
línea 32 : **Flujo de datos:** `CONSOLIDADO_Santa_Elena.xlsx` (hoja Datos Consolidados) →
línea 106: - Los datos de Santa Elena son **reales y confidenciales**.
```

Nombre del cliente, su ERP, su cifra real de inmovilizado y el nombre del archivo que
entregó. El README también documenta cómo recalcular el $541M desde los Excel reales.

### 3. `backend/core/paths.py:26-44` — el nombre del cliente es el **tenant por defecto**

```python
TENANT = os.environ.get("POLPILOT_TENANT", "santa_elena")
_IDENTIDAD = {
    "santa_elena": {"empresa": "Supermercados Santa Elena",
                    "nombre_corto": "Santa Elena", …},
```

No es un comentario: es config viva. Lo mismo en `backend/core/organizacion.py:26-27`
(`"id": "santa-elena"`) y en `backend/main.py:95` (`title="PolPilot · Santa Elena"`).

### 4. `backend/auth.py:86-166` — los usuarios reales del piloto, hardcodeados

`juan`, `romina` con sus nombres, roles y descripciones ("Soy el dueño. Conduzco toda la
operación de Santa Elena…"). Y `backend/tests/test_p37.py:21` los etiqueta él mismo:

```python
"[empleada real]", "[familiar real]",           # empleados reales del piloto
```

### 5. `frontend/shot3.mjs:24,41,46` — **las contraseñas del piloto en claro**

```js
await login(d, "juan", "cheddar-2311");
await login(d, "vendedor", "pilar-8930");
await login(d, "deposito", "remito-5138");
```

Son las credenciales de la instancia real, no las de la demo.

### 6. `Dockerfile:44-46` — la guardia de privacidad **enumera lo que protege**

```dockerfile
if find /app -iname "santa-elena.*" | grep -q .; then …
if grep -rilE "Supermercados Santa Elena|santa-elena\.(png|jpg|jpeg|svg)|MUZZARELLA" …
```

Ironía peligrosa: el mecanismo que impide la fuga en la imagen, publicado como fuente,
*es* la fuga — dice el nombre del cliente y un producto de su inventario real.

### 7. `backend/tests/` — 42 archivos con `juan`, 13 con `romina`

Toda la suite usa los usuarios reales del piloto como fixtures.

### 8. Contaminación de estado (menor, pero real)

`data-demo/perfiles.json` tiene una clave `"juan"` — usuario del piloto filtrado al
estado vivo de la demo en alguna corrida local. Está en `.gitignore`, así que no viajaría
en un commit, pero conviene regenerarlo.

## Lo que SÍ está limpio

- **El dataset sintético es genuinamente sintético.** `data-demo/` = Distribuidora del
  Litoral: 1.506 menciones a "Litoral", 430 artículos con marcas inventadas
  ("SANTA CLARA", "EL PARANÁ", "COSTA DULCE"), proveedores ficticios, personas ficticias
  (Aldo, Vanesa, Ramón, Marta, Norma, Nahuel, Celeste). Cero rastro de [ERP real], de
  MUZZARELLA o de las cifras del piloto.
- **Cero secretos.** No hay `.env` (sólo `.env.example`), ni `credenciales.json`, ni
  ninguna `sk-ant-…`. Ya los había excluido al armar la carpeta.
- **Cero assets del cliente.** `frontend/public/logos/` tiene sólo `litoral.png` y
  `polpilot.png`. El logo del cliente nunca estuvo bundleado (diseño P37).
- **Los datos reales no viajan.** `data/` no se copió a `polpilot-demo/`.

## Qué haría falta para poder publicar (decisión tuya — yo no toqué código)

La regla que me diste fue *ordenar sin reescribir código*, así que **no cambié ni una
línea**. Para que esto pase la auditoría hay que tocar fuente, y eso es un trabajo con
riesgo de romper la suite (581 tests) y el deploy vivo. En orden de esfuerzo:

1. **Renombrar el tenant** `santa_elena` → `piloto` (o `tenant_a`) en `paths.py`,
   `auth.py`, `organizacion.py`, `main.py` + toda la suite. Es el cambio estructural.
2. **Reescribir `_INTRO_PILOTO`** en `angela.py`: sacar razón social, ciudad, [dueño real] y [familiar real].
3. **README nuevo**, escrito para la demo: sin cliente, sin [ERP real], sin $541M, sin el
   nombre de los Excel.
4. **Renombrar los usuarios seed** `juan`/`romina` → genéricos, y borrar las contraseñas
   de `shot3.mjs`.
5. **Reescribir la guardia del Dockerfile** para que valide sin nombrar lo que protege
   (leer los patrones de una variable de entorno, por ejemplo).
6. **Sacar `[ERP real]`** de los 17 archivos donde aparece como nombre del ERP de origen.
7. Volver a correr `_por_revisar/herramientas-auditoria/auditoria.py` hasta que dé
   **todo LIMPIO**, y recién ahí `git init` + push.

**Alternativa más barata y más segura:** publicar sólo lo que ya está limpio —
`data-demo/` (el dataset sintético) + capturas + un README escrito de cero — y dejar el
código de la app fuera hasta hacer el punto 1. Depende de para qué necesitás el repo.
