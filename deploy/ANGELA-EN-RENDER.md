# Que Ángela responda en Render — verificación de dos minutos

Para chequear **antes del pitch**, sin desplegar nada ni abrir código.

## 1. El chequeo rápido: un solo request

```bash
curl -s https://<tu-servicio>.onrender.com/api/health
```

Mirá estos tres campos:

| Campo | Tiene que decir | Si dice otra cosa |
|---|---|---|
| `modo_angela` | `"claude"` | `"offline"` → **no hay credencial configurada**. Ángela no va a contestar NADA fuera del guion del demo. Es el único valor que tumba el pitch. |
| `angela_online` | `true` | `false` → lo mismo que arriba. |
| `modelo_angela` | el slug que esperás | si dice `claude-sonnet-4-6` estás corriendo el default viejo del código, que es de una familia anterior y puede no existir en la API. |

`modo_angela` sale de mirar si hay credencial, **no** de haber llamado al modelo: dice que está configurado, no que la clave sea válida. Para eso, el paso 3.

## 2. Las variables, según el proveedor

El proveedor se autodetecta: si hay `ANTHROPIC_API_KEY` → Anthropic directo; si no, si hay `AI_GATEWAY_API_KEY` → gateway. `LLM_PROVIDER=anthropic|gateway` fuerza uno.

### Por el Gateway (lo que estamos usando)

| Variable | Valor | Obligatoria | Si falta |
|---|---|---|---|
| `AI_GATEWAY_API_KEY` | el token del gateway | **sí** | `modo_angela: "offline"`. Ángela muda. |
| `GATEWAY_MODEL` | `anthropic/claude-sonnet-5` | **sí en la práctica** | cae al default `anthropic/claude-sonnet-4.6`, que es de una familia anterior. Riesgo de HTTP 400 en la primera pregunta. |
| `AI_GATEWAY_BASE_URL` | la URL del gateway | no | usa el default de `config.DEFAULT_GATEWAY_BASE_URL`. |
| `ANGELA_MODEL_SIMPLE` | `anthropic/claude-haiku-4-5` | no | el routing por tema no baja al modelo chico: todo va al grande. Anda igual, sólo más caro y un poco más lento en navegación. |

**El slug del gateway lleva otra forma que el directo** y no es un detalle cosmético: el gateway quiere prefijo de proveedor y versión **con punto** (`anthropic/claude-sonnet-5`); el directo quiere el slug **con guiones** y sin prefijo (`claude-sonnet-5`). Un slug con guiones por el gateway devuelve HTTP 400. Por eso son dos variables distintas: `GATEWAY_MODEL` le gana a `ANGELA_MODEL` cuando el proveedor activo es el gateway, así que un mismo `.env` puede tener las dos formas sin pisarse.

### Por Anthropic directo

| Variable | Valor | Obligatoria |
|---|---|---|
| `ANTHROPIC_API_KEY` | la clave | **sí** |
| `ANGELA_MODEL` | `claude-sonnet-5` | **sí en la práctica** (si no, el default viejo) |
| `ANGELA_MODEL_SIMPLE` | `claude-haiku-4-5-20251001` | no |

### Las que no son del modelo pero también lo tumban

| Variable | Si falta |
|---|---|
| `DATABASE_URL` | el deploy falla en la migración (`deploy/migrate.py`). No arranca. |
| `APP_DATABASE_URL` | arranca, pero **Row-Level Security queda sin efecto en silencio**. No da error. |
| `POLPILOT_TENANT` | `migrate.py` y `boot.py` se niegan a correr: sin esto serviría el tenant `demo` por descuido. |
| `POLPILOT_DEMO_MSG_CAP` | sin cap por sesión. No rompe; gasta. |
| `POLPILOT_DEMO_IP_CAP` | ídem por IP. |

Ojo con el cap: si el jurado hace más de `POLPILOT_DEMO_MSG_CAP` preguntas en la misma sesión, Ángela contesta el mensaje de límite alcanzado en vez de la respuesta. Está en 35, que alcanza de sobra, pero si probaste mucho con la misma sesión antes del pitch, recargá para que se mintee un token nuevo.

## 3. La prueba de verdad: preguntarle algo

`/api/health` dice que hay credencial, no que funcione. La única prueba que vale es una pregunta real:

Abrí la demo → "Lo que sé de tu negocio" → escribí cualquier cosa que **no** sea la del demo (por ejemplo *¿cuánta plata hay en caja hoy?*) y mirá que conteste con números y que aparezcan las tarjetas de herramienta.

Si sale el mensaje de error genérico, mirá los logs de Render: el detalle técnico se loguea y nunca viaja al navegador.

```
[angela/stream] ...        una llamada que salió bien
[angela/stream] failed...  el motivo real del error
```

## 4. Lo que NO depende de nada de esto

La pregunta del demo (`core/guion.py`) **no llama al modelo**: corre herramientas reales y arma la respuesta con los datos del negocio. O sea que aunque la credencial esté mal, la pregunta del demo sigue funcionando.

Eso es una red de seguridad, no una excusa para no verificar: si el jurado pregunta cualquier otra cosa después —y va a preguntar— ahí sí hace falta el modelo.
