# Deploy del DEMO a Render — paso a paso (P22·C)

**Qué se publica:** SOLO el tenant demo (Distribuidora del Litoral). Los
directorios de datos de cualquier otro tenant, `backend/.env` y las
credenciales quedan afuera por `.dockerignore` **y** por la guardia del
Dockerfile (el build falla si algo se cuela).

## 1 · Crear el servicio

1. Cuenta en https://render.com (con GitHub).
2. **New +** → **Blueprint** → conectar este repo.
3. Render lee `render.yaml` (raíz del repo) y propone el servicio
   **polpilot-demo** (Docker, plan Starter).
   - Si el Blueprint no aparece: **New +** → **Web Service** → repo → Runtime
     **Docker** → Health Check Path
     `/api/health` → plan **Starter** (el Free se duerme: mala primera
     impresión para un partner).

## 2 · Los dos secrets (antes del primer deploy)

En el servicio → **Environment**:

| Variable | Valor |
|---|---|
| `ANTHROPIC_API_KEY` | la key real (está en tu `backend/.env` local — JAMÁS commiteada) |
| `POLPILOT_RESET_TOKEN` | un string largo random (ej. de https://1password.com/password-generator) — es el candado del reset manual |

**`ANGELA_MODEL=claude-sonnet-5`** ya viene declarada en `render.yaml` (no es un
secreto: es config). Va explícita a propósito — sin ella el código cae a su
default histórico (`claude-sonnet-4-6`, ver `backend/config.MODELO_VALIDACION`)
y producción correría con otro modelo que el validado. Si el servicio se creó a
mano (no por Blueprint), Render NO lee `render.yaml`: hay que agregarla también
en **Environment**. Se comprueba en `/api/health` → `modelo_angela`.

Todo lo demás ya viene en la imagen: `POLPILOT_TENANT=demo`,
`POLPILOT_DATA_DIR`, `POLPILOT_DEFAULT_LANG=en`,
`POLPILOT_DEMO_TODAY=2026-07-07`, `POLPILOT_DEMO_ROLE_SWITCH=1`,
`POLPILOT_DEMO_AUTOLOGIN=1`, `POLPILOT_DEMO_MSG_CAP=35`,
`POLPILOT_STATIC_DIR`, `POLPILOT_CANONICAL_DIR`. Para pisar alguno, se agrega
en Environment con el valor nuevo.

## 3 · Deploy

**Create/Deploy** y esperar el build (~5-8 min: compila el frontend, instala
WeasyPrint y sus libs de Linux). El contenedor **no queda healthy sin datos**:
el boot corre el seed y si falla, el healthcheck falla y Render no publica.

## 4 · Checklist post-deploy (ventana de incógnito)

1. Abrir `https://polpilot-demo.onrender.com` → entra DIRECTO como dueño
   (Aldo), en inglés, Home completo con datos ($444.7M inmovilizado, cards,
   feed). Nada de pantalla de login.
2. Preguntarle algo a Ángela ("who owes me money?") → responde con números.
3. **Cargar datos** → *Load from photo* → *Try a sample document* → la lista
   de precios → diff con las 2 anomalías → OK → el margen cambia →
   "revert the price update" en el chat → vuelve.
4. **Documents** → Executive summary → **Download PDF** → baja un PDF real con
   el logo (esto prueba WeasyPrint EN LINUX).
5. **My profile** → *View as* → Vanesa (Collections) y Ramón (Warehouse).
6. Abrir desde el **celular real** → el pulso del dueño + chat con camarita.
7. **Dos pestañas a la vez** chateando (roles distintos vía View as) → cero
   cruce de datos.
8. Mandar mensajes hasta pasar 35 → el cap corta con el mensaje honesto.
9. Verificar el aislamiento de tenants: la empresa es "Distribuidora
   del Litoral" en todos lados; `https://…/api/health` dice fuente "(DEMO)";
   ningún dato del otro tenant en la imagen (guardia del build).

## 5 · Reset del demo público

- **Automático**: cada restart o redeploy vuelve al estado canónico (el
  filesystem de Render es efímero; el boot re-siembra).
- **Manual** (antes de compartir el link, o si alguien lo ensució):
  `curl -X POST "https://polpilot-demo.onrender.com/api/admin/reset-demo?token=EL_RESET_TOKEN"`
  → `{"ok": true}`. Sin el token exacto responde 404 (ni revela que existe).
  Alternativa sin curl: **Manual Deploy → Restart** en el dashboard.

## 6 · Si algo falla

- **Logs**: servicio → pestaña **Logs**. El boot habla claro:
  `[boot] seed verificado` → `[boot] dataset ok: 430 artículos` → uvicorn.
  Un `[boot][X]` dice exactamente qué faltó.
- **Build falla en "guardia de privacidad"**: algo del piloto entró al
  contexto — revisar `.dockerignore`; es la guardia haciendo su trabajo.
- **PDF no genera**: mirar Logs por `OSError: cannot load library` → falta
  una lib de sistema (la lista vive en el Dockerfile; en local-Windows es el
  GTK3-Runtime, en la imagen ya están).
- **Primera carga lenta**: el análisis se precalienta en el arranque
  (lifespan); si Render recién levantó, darle ~20s.
- **El chat no responde**: `ANTHROPIC_API_KEY` ausente/incorrecta → Ángela
  cae al router simulado (funciona igual, con respuestas enlatadas). Cargar
  la key y redeploy.

## Estado de la verificación local (honesto)

El build local NO pudo correr: Docker Desktop está instalado pero su motor WSL
no arranca sin terminar el setup de primera vez (diálogos de GUI que Claude no
puede aceptar). **La protección no depende de eso**: la guardia de privacidad
vive DENTRO del Dockerfile y corre también en el build de Render — si algo del
piloto llegara a la imagen, el build de Render FALLA y no se publica nada.

Para verificar local antes del deploy (opcional, recomendado):

1. Abrir **Docker Desktop** una vez y aceptar los diálogos hasta que diga
   "Engine running".
2. En `polpilot-demo/`:
   ```
   docker build -t polpilot-demo .
   docker run --rm polpilot-demo sh -c "ls /app && test ! -e /app/data && echo PILOTO-AUSENTE-OK"
   docker run --rm -p 8080:8000 -e ANTHROPIC_API_KEY=TU_KEY polpilot-demo
   ```
3. `http://localhost:8080` → el checklist del punto 4 (incluido el PDF, que
   prueba WeasyPrint en Linux).

Si el build local falla en la "guardia de privacidad", es la guardia haciendo
su trabajo — nada sensible se publica.
