# Reorganización de `PolPilot-TOP/` — 11/08/2026

Todo movimiento fue **mover o copiar**. No se reescribió código, no se borró nada, no se
commiteó ni se pusheó nada. Rama: `feat/bloques-a-f`.

## Cómo quedó la raíz

```
PolPilot-TOP/
├── polpilot-santa-elena/    ← el cliente real (la app + sus datos + _cliente/)
├── polpilot-demo/           ← la demo sintética (NO publicable todavía, ver abajo)
├── polpilot-landing/        ← la landing (era web-polpilot/)
├── _por_revisar/            ← lo que no encajó claro (con NOTAS.md)
├── render.yaml              ← NO se movió: rompería el deploy vivo de Render
├── AUDITORIA_DEMO.md        ← el informe de la auditoría
└── REORGANIZACION.md        ← este archivo
```

## El hallazgo estructural

**La demo no era una carpeta.** Es *el mismo codebase* del piloto corriendo con
`POLPILOT_TENANT=demo` + `POLPILOT_DATA_DIR=data-demo` (ver `backend/core/paths.py`).
Render deploya con `rootDir: polpilot-santa-elena` y el aislamiento lo hace el
`.dockerignore` + una guardia en el `Dockerfile`.

Por eso `polpilot-demo/` **no se movió: se copió**, sacándole los datos del piloto. El
original quedó intacto y todo lo que funciona sigue funcionando.

## Movimientos

### → `polpilot-santa-elena/_cliente/` (carpeta nueva)

Los archivos del cliente real que estaban sueltos en la raíz:

`CONSOLIDADO_Santa_Elena.xlsx` · `CHESS WEBSITE.xlsx` · `COSTOS CHESS.xlsx` ·
`PRODUCTOS CHESS 11.xlsx` · `STOCK_ordenado.xlsx` · `STOCK_ordenado(1).xlsx` ·
`PolPilot Founding Document_ Santa Elena Assessment…pdf` ·
`Santa elena transcripcion (2).pdf` · `santa elena_logo.jpg` · `RESUMEN_EJECUTIVO.pdf` ·
`NUMEROS_REALES_SANTA_ELENA.md`

El resto de `polpilot-santa-elena/` **no se tocó**.

### → `polpilot-demo/` (copia nueva)

Copiado desde `polpilot-santa-elena/` con `robocopy /E`, excluyendo:
`data/` · `docs/` · `.env` · `credenciales.json` · `node_modules/` · `dist/` ·
`__pycache__/` · `.pytest_cache/` · `versions/` · `piso_adjuntos/` · `.git/` · `*.pyc`

343 archivos, 7,03 MB. Se le sumó:
- `assets-origen/Fotos/` ← la carpeta `Fotos/` de la raíz (retratos de las personas
  ficticias de la demo + el logo de Distribuidora del Litoral; verificado visualmente).
- `render.yaml` (copia; el original sigue en la raíz).
- `NO_PUBLICAR_TODAVIA.md` (nuevo).

### → `polpilot-landing/`

`web-polpilot/` renombrada con `git mv`. Carpeta autocontenida (React + Vite + servidor
Express propio), no depende de rutas de afuera. `package.json` sigue diciendo
`"name": "web-polpilot"` — **no lo cambié**, cambiarlo es tocar código.

### → `_por_revisar/`

`landing/` (la landing vieja) · `docs/` · `pitch-deck/` · los 6 prompts de build `00_`–`06_` ·
`ESTADO_POLPILOT.md` · `POLPILOT_PRODUCTO_COMPLETO.md` · `AUDITORIA_FABLE5.md` ·
`PENDIENTES.md` · `REPORTE_PROMPT9.md` · `REPORTE_PROMPT10.md` ·
`RESUMEN_CAMBIOS_POLPILOT.md` · `README.md` (el de la raíz) ·
`Captura de pantalla 2026-06-22 182826.png` · `caso2_id.txt` ·
`resumen_ejecutivo-2026-07-20.pdf` · `polpilot_logo.png` ·
`FRANCISCO.jpeg` / `LUCAS (YO).jpeg` / `WENCESLAO.jpeg`

Detalle y dudas abiertas en [`_por_revisar/NOTAS.md`](_por_revisar/NOTAS.md).

## Lo que NO se movió, a propósito

| Qué | Por qué |
|---|---|
| `render.yaml` (raíz) | Es el blueprint **vivo** de Render y apunta a `rootDir: polpilot-santa-elena`. Moverlo o editarlo rompe el deploy del demo público. |
| `polpilot-santa-elena/` (la carpeta en sí) | Es el `rootDir` de Render **y** el target de las 4 configs de `.claude/launch.json` (`demo-api`, `demo-front`, `piloto-api`, `piloto-front`). Renombrarla rompe deploy y arranque local. |
| `polpilot-santa-elena/docs/` | Capturas de la instancia **real** del piloto. Su lugar es ahí; no van a la demo. |
| `.claude/`, `.git/`, `.gitignore`, `desktop.ini` | Infraestructura (`desktop.ini` lo maneja OneDrive). |
| `.claude/worktrees/unruffled-lehmann-16b1db/` | Worktree de git con una copia completa del repo — **contiene datos del cliente**. Tocarlo rompe git. Ojo si alguna vez se comparte la carpeta entera. |

## Verificación post-mudanza

- ✅ `render.yaml` → `rootDir: polpilot-santa-elena` (intacto).
- ✅ Las 4 configs de `.claude/launch.json` apuntan a `polpilot-santa-elena\...` (intacto).
- ✅ `polpilot-landing/` no referencia rutas de afuera (sólo su propio nombre viejo en
  `package.json` y `README.md`, que no afecta el build).
- ✅ Los scripts de captura del frontend escriben a `../docs/`, que sigue existiendo
  dentro de `polpilot-santa-elena/`.
- ✅ Ningún archivo borrado.

## Cómo revertir

Los archivos versionados se movieron con `git mv`, así que basta con:

```bash
git -C "C:/Users/Usuario/OneDrive/Desktop/PolPilot-TOP" reset --hard HEAD
```

⚠️ Eso también descartaría el cambio previo en `.claude/launch.json`. Para revertir sólo
la mudanza, sin tocar nada más:

```bash
git -C "C:/Users/Usuario/OneDrive/Desktop/PolPilot-TOP" checkout -- .
```

Lo que **no** estaba versionado (`pitch-deck/`, `Fotos/`, los 3 retratos,
`NUMEROS_REALES_SANTA_ELENA.md`, `caso2_id.txt`, `resumen_ejecutivo-2026-07-20.pdf`) hay
que moverlo a mano de vuelta; está listado arriba, uno por uno.

`polpilot-demo/` es una copia: borrarla no pierde nada.

## Estado de la publicación a GitHub

**Publicada el 11/08/2026** (segunda sesión): los 429 rastros se limpiaron
(cliente real → identidad ficticia), la suite quedó 822 passed / 24 skipped, y
`polpilot-demo/` se pusheó con historial nuevo a
`lucaspippo/POLPILOT-DEMO-SINTETICA-YC` (commit `7b5c491`).
Ver [`AUDITORIA_DEMO.md`](AUDITORIA_DEMO.md) para el antes/después.
