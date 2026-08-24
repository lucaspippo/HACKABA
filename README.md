# PolPilot — demo sintética

> **Todo lo que hay acá es ficticio.** La empresa ("Distribuidora del Litoral"),
> las personas, los clientes, los proveedores, las marcas y cada número del
> dataset fueron generados por `data-demo/generar.py` con seed fija. No hay
> datos de ningún cliente real en este repositorio.

PolPilot es un AI ops manager para PyMEs: se monta sobre el ERP que el negocio
ya usa, encuentra la plata escondida (stock inmovilizado, datos rotos, morosos,
quiebres) y ejecuta el trabajo con aprobación del dueño. Ángela — la
inteligencia del sistema — habla con cada rol como un socio que conoce el
negocio de memoria.

Esta es la demo que se presentó a YC: una distribuidora de alimentos ficticia
con 10 años de historia, 3 bocas, ~430 artículos, cuentas corrientes con
morosos, depósito y reparto.

## Correr la demo

Requisitos: Python 3.12+, Node 20+.

```bash
# 1. Backend (el tenant demo y data-demo/ son los defaults: no hay que configurar nada)
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --port 8000

# 2. Frontend (en otra terminal)
cd frontend
npm ci
npm run dev          # http://localhost:5173
```

O todo junto, con siembra y healthcheck incluidos: `python start_demo.py`.

- **Usuarios:** el equipo ficticio vive en `backend/usuarios_demo.py`
  (`aldo` es el dueño). Las contraseñas se generan en el primer arranque, se
  imprimen en consola y quedan en `data-demo/credenciales.json` (gitignored).
- **Ángela (chat con IA):** opcional. Exportá `ANTHROPIC_API_KEY` antes de
  levantar el backend; sin la key, todo lo demás funciona igual (los análisis
  son deterministas, no dependen de la IA).
- **El "hoy" del dataset** es 2026-07-07. Para que los análisis coincidan con
  la historia sembrada, corré con `POLPILOT_DEMO_TODAY=2026-07-07` (así corre
  el deploy; `start_demo.py` ya lo setea).

## Qué mirar

- **El mapa de tu negocio** — 8 dominios con semáforos, sub-nodos reales y
  conclusiones numéricas.
- **Oportunidades / Alertas** — el set curado de hallazgos accionables con
  su plata: capital recuperable, cliente frío, quiebre de stock, pre-pico.
- **Saneamiento** — los datos rotos del catálogo (fantasmas, negativos, sin
  precio, balanza) con corrección asistida y delta-export de vuelta al ERP.
- **Equipo** — cada persona ve SU PolPilot: probá `aldo` (dueño) contra
  `vanesa` (mostrador) o `tomas` (depósito).
- **Bilingüe** — EN|ES por usuario, con el selector del perfil.

## Arquitectura (resumen)

```
backend/    FastAPI · núcleo determinista (core/) + Ángela (angela.py)
frontend/   React + Vite · desktop y mobile
data-demo/  el dataset sintético (seed) + su generador determinista
deploy/     boot de producción (un solo servicio: API + frontend compilado)
```

- El **borde determinista** vive en `backend/core/`: los números salen de
  cálculo, no del modelo. Ángela narra y ejecuta herramientas; no inventa
  cifras.
- **Multi-tenant por diseño:** `POLPILOT_TENANT` + `POLPILOT_DATA_DIR` aíslan
  instancias por completo (directorios, usuarios, credenciales). Este repo
  trae dos tenants de ejemplo, ambos ficticios: `demo` (Distribuidora del
  Litoral, el default) y `piloto` (Supermercados Horizonte, el seed
  chico de `backend/auth.py`).

## Tests

```bash
cd backend && python -m pytest
```

La suite corre contra el tenant `piloto` sobre `data-demo/` (ver
`tests/conftest.py`). **Ojo:** los tests escriben en el data dir; después de
correrlos, restaurá los seeds con `git checkout -- data-demo/`.

## Deploy

`render.yaml` + `Dockerfile` levantan todo como un único servicio Docker
(frontend compilado servido por el backend). Ver `deploy/DEPLOY.md`. El único
secreto es `ANTHROPIC_API_KEY` (se carga en el dashboard del hosting, jamás en
el repo).
