# Levantar esto desde cero

PolPilot para Córdoba Hack. De un clon limpio a la demo andando.

Los documentos de la hackathon (lo que nos dijeron los mentores, el análisis de
Lightfield, los guiones) están en [`hackathon/`](hackathon/).

---

## Lo que hace falta

- **Python 3.12+**
- **Node 20+**
- **Docker** (sólo para levantar el Postgres; si ya tenés uno, no hace falta)

## 1 · La base de datos

```bash
docker compose up -d db
```

Levanta Postgres 16 en el **puerto 5434** del host (no 5432 — ver el comentario
en `docker-compose.yml`, es a propósito) y crea el rol `polpilot_app`, que es
con el que la app hace toda consulta con alcance de tenant. Ese rol **no** tiene
`BYPASSRLS`: si se usara el superusuario, el aislamiento entre tenants dejaría
de aplicarse en silencio.

## 2 · La configuración

```bash
cp backend/.env.example backend/.env
```

Y editá `backend/.env`. Lo mínimo para que arranque:

| Variable | Para qué | Valor local |
|---|---|---|
| `DATABASE_URL` | Conexión admin: Alembic y filas de tenant | el default del example ya apunta al docker |
| `APP_DATABASE_URL` | Toda consulta con alcance de tenant. **Rol sin BYPASSRLS** | idem |
| `POLPILOT_TENANT` | Qué tenant sirve el proceso | `demo` |
| `POLPILOT_DATA_DIR` | Dónde vive el dataset | `../data-demo` |
| **`POLPILOT_DEMO_TODAY`** | **El "hoy" congelado** | **`2026-07-07`** |

**`POLPILOT_DEMO_TODAY` no es opcional para la demo.** El dataset sembrado
termina el 2026-07-06. Sin la fecha congelada, los análisis corren contra la
fecha real, las notas del equipo caen fuera de la ventana de 30 días y **los
cruces dejan de emitir**: el cerebro queda sin hallazgos y la demo no existe.

Opcionales:

- `ANTHROPIC_API_KEY` — sólo para el chat de Ángela. **Sin la clave todo lo
  demás funciona igual**: los análisis son determinísticos y no dependen del
  modelo. Toda la demo del grafo anda sin API key.
- `ODOO_ENCRYPTION_KEY` / `WHATSAPP_ENCRYPTION_KEY` — sólo si se conectan esos
  canales. Se generan con
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.

## 3 · Migraciones y datos

```bash
cd backend
pip install -r requirements.txt
python -m alembic upgrade head
python ../data-demo/seed_db.py
```

La siembra es idempotente: se puede volver a correr.

## 4 · Levantar

```bash
# Backend
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8099

# Frontend (otra terminal)
cd frontend
npm ci
POLPILOT_API_PORT=8099 npm run dev -- --port 5184
```

Queda en **http://127.0.0.1:5184**, entrando directo como `aldo` (el dueño) si
`POLPILOT_DEMO_AUTOLOGIN=1`. Si no: usuario `aldo`, contraseña `demo-password`.

> El atajo `python start_demo.py` hace todo lo anterior de una (docker,
> migraciones, siembra, backend y frontend) en los puertos 8001 y 5174.

## 5 · Antes del pitch — **esto no es opcional**

```bash
python backend/scripts/precalentar_demo.py --api http://127.0.0.1:8099
```

Los análisis se cachean por (nombre, idioma, fecha) y el cache arranca vacío.
El primer request que necesita uno lo paga. **Medido sobre este dataset:**

| Pantalla | En frío | Precalentada |
|---|---|---|
| Prioridades | 14,7 s | 0,2 s |
| El cerebro (grafo) | 5,2 s | 0,18 s |
| Mapa de la operación | 5,2 s | 0,05 s |
| Contrafáctico | 5,9 s | 0,20 s |

Seis segundos de pantalla quieta es donde se cae una demo. Corré esto después
de levantar el backend y antes de subir.

---

## Dónde está cada cosa

Todo lo nuevo vive en **el Cerebro**:
`/mapa` → **"Lo que sé de tu negocio"** → **"Ver el grafo completo de entidades"**

| Qué | Dónde |
|---|---|
| Cruce de la oferta | En los hallazgos: *"El 18% de descuento de Frigorífico La Ribera conviene rechazarlo"* |
| Animación del camino | Tocá ese hallazgo → **"Reproducir el camino"** |
| Contrafáctico | Debajo: las evidencias (`tomas · foto`, `ramon · whatsapp`…). Tocá una |
| Modo presentación | Botón **"Proyectar"**, arriba a la derecha |
| Punto ciego | Bloque **"El punto ciego"** → tocá **walter** |
| Panel de evals | Botón **"Qué tan seguido acierta"** |
| MCP | `/mcp` — ver [`backend/MCP.md`](backend/MCP.md) |

## Los evals están apagados

Correr las suites recomputa todo y tarda. **El default es que no corran**, por
ningún camino: ni al arrancar la app, ni en CI, ni al abrir el panel.

El panel **sólo lee** `data-demo/evals_run.json`, la última corrida grabada, que
está versionada justamente para que un clon nuevo muestre el número sin
calcular nada. Si el archivo no está, el panel lo dice y listo.

Para correrlas a propósito:

```bash
POLPILOT_EVALS=1 py backend/scripts/run_evals.py
```

Sin esa variable, `evals.correr()` levanta `EvalsApagados` — el cerrojo está en
`core/evals.py`, no en el script, así que alcanza a cualquier llamador futuro.
