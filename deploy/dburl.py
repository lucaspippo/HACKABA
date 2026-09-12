"""
De DATABASE_URL a APP_DATABASE_URL — una sola derivacion, dos consumidores.

POR QUE HACE FALTA.

La app usa DOS conexiones a la MISMA base, a proposito:

  DATABASE_URL      el rol duenio. Alembic (crea tablas, politicas) y las
                    consultas de administracion (la fila del tenant).
  APP_DATABASE_URL  un rol SIN bypass de RLS. TODA consulta con datos del
                    tenant va por aca.

Si las dos apuntan al mismo rol duenio, Row-Level Security deja de hacer
efecto EN SILENCIO —un superusuario lo saltea siempre, incluso con FORCE ROW
LEVEL SECURITY— y no hay ningun error que lo delate. Por eso son dos.

En local eso lo resuelve `docker/init-app-role.sql`, que la imagen de postgres
corre sola la primera vez. Una Postgres administrada de Render no tiene
`docker-entrypoint-initdb.d`: ahi no hay quien cree ese rol. Hasta ahora se
asumia creado a mano (era el caso de Supabase) y `APP_DATABASE_URL` se cargaba
a dedo en el dashboard — o sea que un deploy desde cero NO levantaba solo.

Este modulo cierra eso: `deploy/migrate.py` crea el rol con la contrasenia que
Render genera, y `deploy/boot.py` arma la URL. Los dos llaman aca, asi que no
pueden discrepar en el nombre del rol ni en la forma de la URL.

RESPETA LO EXPLICITO: si `APP_DATABASE_URL` ya viene seteada (Supabase, o una
base propia), no se toca nada. La derivacion es el default, no una imposicion.
"""
from __future__ import annotations

import os
from urllib.parse import quote, urlsplit, urlunsplit

# El rol que la app usa para todo lo que toca datos del tenant. Mismo nombre
# que en docker/init-app-role.sql: local y Render tienen que verse igual.
ROL_APP = "polpilot_app"

# De donde sale la contrasenia. En Render la genera el blueprint
# (generateValue) y queda sincronizada al servicio; en local, el .env.
ENV_PASSWORD = "POLPILOT_APP_DB_PASSWORD"


def password_app(env=None) -> str:
    env = os.environ if env is None else env
    return (env.get(ENV_PASSWORD) or "").strip()


def derivar(database_url: str, password: str) -> str:
    """La misma URL, con el rol de la app en vez del duenio.

    Cambia SOLO usuario y contrasenia: host, puerto, base y query (sslmode,
    entre otros) se preservan tal cual vinieron, que es justo lo que hay que
    respetar de una URL administrada.
    """
    partes = urlsplit(database_url)
    host = partes.hostname or ""
    puerto = f":{partes.port}" if partes.port else ""
    netloc = f"{ROL_APP}:{quote(password, safe='')}@{host}{puerto}"
    return urlunsplit((partes.scheme, netloc, partes.path, partes.query, partes.fragment))


def asegurar_app_database_url(env=None) -> tuple[str, str]:
    """Deja `APP_DATABASE_URL` puesta en el entorno. Devuelve (valor, origen).

    `origen` es para el log: importa distinguir «la puso el operador» de «la
    derivamos nosotros» cuando algo no conecta.
    """
    env = os.environ if env is None else env
    ya = (env.get("APP_DATABASE_URL") or "").strip()
    if ya:
        return ya, "explicita"
    base = (env.get("DATABASE_URL") or "").strip()
    pwd = password_app(env)
    if not base or not pwd:
        return "", "falta"
    url = derivar(base, pwd)
    env["APP_DATABASE_URL"] = url
    return url, "derivada"


# --- El rol, y lo que tiene que poder hacer ---------------------------------
# Puerto de docker/init-app-role.sql. Se corre con la conexion del duenio,
# antes de Alembic: ALTER DEFAULT PRIVILEGES solo alcanza a las tablas que se
# crean DESPUES, asi que el orden no es negociable.
#
# NO se usa un bloque `DO $$ ... $$`: un bloque anonimo de plpgsql no acepta
# parametros ligados (da «could not determine data type of parameter $1»), y
# meter el nombre del rol y la contrasenia por interpolacion de strings es
# exactamente como se escriben las inyecciones. La salida es preguntarle a
# Postgres como se citan: quote_ident/quote_literal devuelven el texto ya
# escapado por el mismo motor que despues lo va a leer.


def crear_rol(cx, rol: str, password: str) -> bool:
    """Crea (o resincroniza la clave de) el rol de la app. Devuelve si lo creo.

    `cx` es una conexion de SQLAlchemy ya abierta con el rol duenio.
    """
    from sqlalchemy import text

    ident, literal = cx.execute(
        text("SELECT quote_ident(:rol), quote_literal(:pwd)"),
        {"rol": rol, "pwd": password},
    ).one()
    existe = cx.execute(
        text("SELECT 1 FROM pg_roles WHERE rolname = :rol"), {"rol": rol}
    ).first() is not None

    if existe:
        # Un redeploy trae la MISMA contrasenia generada (Render la sincroniza),
        # pero resincronizarla igual hace que un cambio manual no deje el
        # servicio sin poder conectarse y sin decir por que.
        cx.execute(text(f"ALTER ROLE {ident} LOGIN PASSWORD {literal}"))
    else:
        cx.execute(text(
            f"CREATE ROLE {ident} LOGIN PASSWORD {literal} "
            f"NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE"))
    return not existe


def aplicar_grants(cx, rol: str, plantillas) -> None:
    from sqlalchemy import text

    ident = cx.execute(text("SELECT quote_ident(:rol)"), {"rol": rol}).scalar_one()
    for plantilla in plantillas:
        cx.execute(text(plantilla.format(rol=ident)))


# Lo que se corre DESPUES de Alembic: las tablas que ya existen no las alcanza
# ALTER DEFAULT PRIVILEGES (solo mira hacia adelante), asi que a esas hay que
# darles permiso de una. Es idempotente: correrlo dos veces no cambia nada.
SQL_GRANTS_EXISTENTES = (
    "GRANT USAGE ON SCHEMA public TO {rol}",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {rol}",
    "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {rol}",
)

SQL_GRANTS_FUTUROS = (
    "GRANT USAGE ON SCHEMA public TO {rol}",
    "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
    "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {rol}",
    "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
    "GRANT USAGE, SELECT ON SEQUENCES TO {rol}",
)
