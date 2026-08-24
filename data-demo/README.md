# Instancia DEMO — "Distribuidora del Litoral" (100% ficticia)

El dataset sintético de PolPilot para mostrar (YC). Es el tenant por defecto de
este repo: sin ninguna env, el backend arranca contra este directorio. El otro
tenant de ejemplo ("piloto", Supermercados Horizonte, también ficticio) usa su
propio data dir y credenciales — no se mezclan ni por accidente.

## Levantar el demo

**La forma corta (un comando, desde la raíz del repo):** `python start_demo.py`
— limpia puertos, siembra lo que falte, verifica el healthcheck real y levanta backend + frontend.

### A mano (lo que el script automatiza)

```bash
# Backend demo (puerto 8001) — desde backend/
# POLPILOT_DEFAULT_LANG=en → el demo arranca en INGLÉS (reviewers de YC);
# cada usuario puede cambiarlo con el selector EN|ES y queda en su perfil.
# POLPILOT_DEMO_TODAY → congela el "hoy" de TODOS los análisis en la fecha de
# referencia del dataset (la misma con la que generar.py lo produjo): los
# números son idénticos hoy, en el deploy y el día de la grabación.
# POLPILOT_DEMO_ROLE_SWITCH=1 → habilita el "View as / Ver como" del perfil
# (los reviewers de YC cambian de rol sin logins). En un tenant real NO se
# setea: el endpoint no existe ahí.
# POLPILOT_DEMO_MSG_CAP=35 → freno de gasto: mensajes de Ángela por sesión
# (la URL pública para YC va sin login; nadie quema tokens al infinito).
POLPILOT_TENANT=demo POLPILOT_DATA_DIR=../data-demo POLPILOT_DEFAULT_LANG=en POLPILOT_DEMO_TODAY=2026-07-07 POLPILOT_DEMO_ROLE_SWITCH=1 POLPILOT_DEMO_MSG_CAP=35 python -m uvicorn main:app --port 8001

# Frontend demo (puerto 5174) — desde frontend/
POLPILOT_API_PORT=8001 npm run dev -- --port 5174
```

Sin env, el backend levanta este mismo tenant demo con sus defaults (API 8000,
front 5173). Las variables de arriba son las del deploy público (inglés, "hoy"
congelado, view-as).

## Usuarios

El equipo ficticio vive en `backend/usuarios_demo.py` (aldo=dueño, marta,
celeste, ramón, brian, walter, nahuel, vanesa, diego + polpilot). Las
contraseñas se generan al primer arranque y quedan en
`data-demo/credenciales.json` (gitignored) — se imprimen en la consola.

## Los datos

`generar.py` (determinista: seed fija Y fecha de referencia fija, 2026-07-07)
produce el dataset completo y coherente: catálogo con hallazgos estrella,
10 años de ventas con estacionalidad e inflación real y 3 bocas, cuentas con
morosos, depósito estilo WMS y logística estilo TMS.
PolPilot NO es un WMS/TMS: estos son los datos que esos sistemas exportarían.

## Resetear el demo a fábrica

El uso del demo muta su estado (como el producto real). Para volver al seed:

```bash
git checkout -- data-demo/
# borrar el runtime no versionado si quedó (CONSERVANDO macro_cache.json y
# credenciales.json): inventory_actual.json, versions/, audit.json,
# staging.json, caja.json, perfiles.json
python data-demo/generar.py   # OBLIGATORIO: re-siembra caja, staging, la
                              # auditoría (historia de uso), la solicitud de
                              # vanesa y finanzas.json — sin esto el demo
                              # arranca "virgen" y miente menos historia
```
