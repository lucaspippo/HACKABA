# Render — todas las variables, y qué se rompe si falta cada una

Para verificar en dos minutos desde el dashboard, sin abrir código.

El blueprint (`render.yaml`) crea **tres cosas** de una sincronización: la base
Postgres, el servicio web, y el esquema + los datos (Alembic como
`preDeployCommand`, el seed en el arranque del contenedor). Un deploy desde
cero no necesita que nadie corra nada a mano.

---

## 1 · Las que TENÉS que cargar vos (Dashboard → Environment)

Son dos. Todo lo demás ya viene en el blueprint.

| Variable | Valor | Si falta |
|---|---|---|
| `AI_GATEWAY_API_KEY` | el token del gateway de Vercel | **`modo_angela: "offline"`.** El deploy queda en verde igual y la pregunta del demo sigue andando (no llama al modelo), pero **cualquier otra pregunta no contesta**. Es la única variable que arruina el pitch sin que nada se vea roto. |
| `POLPILOT_RESET_TOKEN` | una cadena larga al azar | `POST /api/admin/reset-demo` queda sin protección o sin funcionar. No afecta al demo; sí es la forma de volver a un estado limpio sin redeployar. |

---

## 2 · Las que pone Render sola (del `render.yaml`)

### La base

| Variable | De dónde sale | Si falta |
|---|---|---|
| `DATABASE_URL` | `fromDatabase` → la base del propio blueprint | **el deploy falla en el `preDeployCommand`**: `alembic upgrade head` no tiene a dónde conectarse. Si está vacía, el servicio no quedó enlazado a la base. |
| `POLPILOT_APP_DB_PASSWORD` | `generateValue: true` | el deploy falla en el mismo paso: sin ella no se puede crear el rol sin bypass de RLS. |

**`APP_DATABASE_URL` no está en la lista, y no es un olvido.** La app usa dos
conexiones a la misma base: `DATABASE_URL` con el rol dueño (Alembic, fila del
tenant) y `APP_DATABASE_URL` con un rol **sin bypass de RLS** para todo lo que
toca datos del tenant. Si las dos usan el dueño, Row-Level Security deja de
tener efecto **en silencio** — un superusuario lo saltea siempre — y no hay
error que lo delate.

Render no puede armarla (`fromDatabase` sólo da la del dueño), así que el rol
lo crea `deploy/migrate.py` y la URL la deriva `deploy/boot.py`
(`deploy/dburl.py`, una sola derivación para los dos). Si algún día apuntás a
Supabase, seteá `APP_DATABASE_URL` a mano: lo explícito le gana a lo derivado.

### La IA — por el gateway de Vercel, no por Anthropic directo

| Variable | Valor | Si falta |
|---|---|---|
| `LLM_PROVIDER` | `gateway` | se autodetecta (habría gateway igual), pero el día que alguien cargue una `ANTHROPIC_API_KEY` "para probar", el proveedor cambia solo y los slugs de abajo dejan de servir. |
| `GATEWAY_MODEL` | `anthropic/claude-sonnet-5` | cae al default `anthropic/claude-sonnet-4.6`, de una familia anterior. Riesgo de HTTP 400 en la primera pregunta. |
| `ANGELA_MODEL_SIMPLE` | `anthropic/claude-haiku-4.5` | el routing por tema no baja al modelo chico: anda igual, sale más caro. |

**El formato del slug no es cosmético.** Por el gateway va con prefijo de
proveedor y versión **con punto** (`anthropic/claude-sonnet-5`); por Anthropic
directo va con **guiones** y sin prefijo (`claude-sonnet-5`). Mezclarlos
devuelve **HTTP 400** y Ángela queda muda en la primera pregunta. Por eso son
dos variables distintas: `GATEWAY_MODEL` le gana a `ANGELA_MODEL` cuando el
proveedor activo es el gateway, así que las dos formas pueden convivir.

### El tenant y los datos

| Variable | Valor | Si falta |
|---|---|---|
| `POLPILOT_TENANT` | `demo` | `migrate.py` y `boot.py` **se niegan a arrancar**. Es a propósito: `core/paths.py` cae a `demo`, así que sin esto un deploy mal configurado serviría datos de otro tenant por descuido. |
| `POLPILOT_SEED_ON_BOOT` | `1` | el servicio levanta **sin datos**. El disco de Render es efímero: sin esto, cada reinicio deja la demo vacía. **Nunca en un tenant productivo**: `generar.py` reescribe todo el dataset. |
| `POLPILOT_CANONICAL_DIR` | `/app/data-canonica` | `reset-demo` no tiene desde dónde restaurar. No afecta al arranque. |

### El demo

| Variable | Valor | Si falta |
|---|---|---|
| `POLPILOT_DEMO_TODAY` | `2026-07-07` | **los cruces dejan de emitir.** El dataset tiene una historia sembrada que termina ahí y los cruces se calculan contra "hoy": con la fecha real todo queda fuera de ventana. La pantalla no se rompe — **se queda vacía**, que es peor, porque parece que el producto no encontró nada. |
| `POLPILOT_DEFAULT_LANG` | `es` | el chrome arranca en inglés, y además el precalentado llena **primero** el idioma default: con `en`, la pantalla que vas a mostrar es la última en quedar caliente. |
| `POLPILOT_PRECALENTAR_IDIOMAS` | *(sin setear)* | Sin setear, el arranque precalienta **sólo el idioma del tenant**. Medido contra este servicio: `es` 105 s + `en` 75 s = 180 s, y durante esos 180 s la primera pregunta del demo tardó **2 m 15 s** en vez de ~3 s, porque el hilo de precalc compite por el medio núcleo del plan. El idioma que no se precalienta no queda roto: se computa a demanda. Poné `todos` para volver al comportamiento anterior. |
| `POLPILOT_DEMO_AUTOLOGIN` | `1` | aparece la pantalla de login y el link público deja de entrar directo. |
| `POLPILOT_DEMO_ROLE_SWITCH` | `1` | se pierde el selector "Ver como". |
| `POLPILOT_DEMO_MSG_CAP` | `35` | sin tope por sesión: no rompe, gasta. Ojo al revés: si probás mucho con la misma sesión antes del pitch, recargá para que se mintee un token nuevo, o Ángela contesta el mensaje de límite. |
| `POLPILOT_DEMO_IP_CAP` | `60` | ídem por IP/día. |

---

## 3 · El chequeo de dos minutos

```bash
curl -s https://<tu-servicio>.onrender.com/api/health
```

| Campo | Tiene que decir | Si dice otra cosa |
|---|---|---|
| `modo_angela` | `"claude"` | `"offline"` → falta `AI_GATEWAY_API_KEY`. **El único valor que tumba el pitch.** |
| `modelo_angela` | `anthropic/claude-sonnet-5` | un slug con guiones por el gateway → HTTP 400 en la primera pregunta. |
| `hoy` | `2026-07-07` | falta `POLPILOT_DEMO_TODAY` → los cruces no emiten. |
| `tenant` | `demo` | otro tenant, otros datos. |
| `idioma_default` | `es` | arranca en inglés. |

`modo_angela` dice que hay credencial configurada, **no** que sea válida. La
única prueba que vale es preguntarle algo que **no** sea la del demo — por
ejemplo *¿cuánta plata hay en caja hoy?* — y ver que conteste con números y que
aparezcan las tarjetas de herramienta.

Si sale el error genérico, el motivo real está en los logs de Render (nunca
viaja al navegador):

```
[angela/stream] ...        una llamada que salió bien
[angela/stream] failed...  el motivo real
```

---

## 4 · Lo que NO depende de la credencial

La pregunta del demo (`core/guion.py`) **no llama al modelo**: corre
herramientas reales y arma la respuesta con datos del negocio. Sigue andando
aunque la credencial esté mal.

Es una red de seguridad, no una excusa para no verificar: si el jurado
pregunta cualquier otra cosa —y va a preguntar— ahí sí hace falta el modelo.

---

## 5 · El nombre del servicio

Se llama **`polpilot-hackathon`**, no `polpilot-app`. `polpilot-app` es el
servicio del repo del producto (`agustindelmonti/polpilot-app`), donde vive la
demo pública. Dos servicios con el mismo nombre en la misma cuenta chocan, y
aunque estén en cuentas distintas, tener dos "polpilot-app" apuntando a repos
distintos es una confusión esperando a pasar: el día que haya que mirar un log,
nadie va a saber cuál es cuál.
