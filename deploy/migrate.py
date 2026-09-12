"""Render's preDeployCommand: bring the schema to head before any instance
of the new version starts.

Why this is not in boot.py any more: when Alembic ran inside the container, a
failed migration exited the process, failed the healthcheck and took the
service DOWN. As a pre-deploy step the deploy fails instead and the running
instance keeps serving. It also keeps migrations single-writer if the service
is ever split (D2).

YA NO ESTA AUSENTE: crear el rol NOBYPASSRLS al que se conecta
APP_DATABASE_URL. Existia en Supabase (docker/init-app-role.sql es el
equivalente local), pero una Postgres administrada de Render no tiene
docker-entrypoint-initdb.d — ahi no hay quien lo cree. Ese bootstrap es
justamente "cuando la base se mude" (D12), y la base se mudo: ahora la crea el
blueprint. Sin esto, un deploy desde cero exige que alguien entre a la consola
de Postgres a mano, que es exactamente lo que no puede pasar.

El ORDEN adentro de main() no es negociable:
    rol -> permisos futuros -> alembic -> permisos de lo ya creado
ALTER DEFAULT PRIVILEGES solo alcanza a las tablas que se crean DESPUES, asi
que si se corre despues de Alembic el rol de la app se queda sin permisos
sobre todo el esquema y el server levanta sin poder leer nada.
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BACKEND = os.path.join(ROOT, "backend")

sys.path.insert(0, BACKEND)
import deploy_guard  # noqa: E402  (needs BACKEND on the path first)
sys.path.insert(0, HERE)
import dburl  # noqa: E402


# Cuanto se espera a que la base acepte conexiones, y cada cuanto se prueba.
ESPERA_MAX_S = 300
ESPERA_PASO_S = 3


def _esperar_a_la_base(motor) -> None:
    """Bloquea hasta que Postgres atienda, o corta con un mensaje que sirva.

    POR QUE EXISTE ESTO. En la PRIMERA sincronizacion del blueprint, Render crea
    la base y deploya el servicio casi al mismo tiempo, pero una Postgres
    administrada tarda un par de minutos en levantar. El preDeployCommand
    llegaba antes y moria con:

        connection to server at "10.205.139.65", port 5432 failed:
        Connection refused

    ...que se lee como un problema de configuracion y no lo es: DATABASE_URL
    estaba perfectamente enlazada. El deploy fallaba por llegar temprano.

    No es solo el primer deploy: una base administrada tambien se reinicia sola
    por mantenimiento, y ahi un redeploy simultaneo se comeria lo mismo.

    SE DISTINGUE "todavia no esta" de "esta mal". Solo se reintenta cuando nadie
    atiende (conexion rechazada / no se pudo resolver el host). Una credencial
    equivocada o una base que no existe fallan de una: reintentar cinco minutos
    contra un error que nunca se va a arreglar solo es cambiar un mensaje claro
    por cinco minutos de silencio y el mismo final.
    """
    import time

    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    # Lo que significa "todavia no levanto". Cualquier otra cosa es un problema
    # de verdad y no mejora esperando.
    TRANSITORIOS = (
        "connection refused",
        "could not translate host name",
        "is starting up",
        "could not connect to server",
        "timeout expired",
        "server closed the connection unexpectedly",
    )

    t0 = time.monotonic()
    intento = 0
    while True:
        intento += 1
        try:
            with motor.connect() as cx:
                cx.execute(text("SELECT 1"))
            if intento > 1:
                print(f"[migrate] la base atendio despues de "
                      f"{time.monotonic() - t0:.0f}s ({intento} intentos)", flush=True)
            return
        except OperationalError as e:
            detalle = str(e).lower()
            if not any(t in detalle for t in TRANSITORIOS):
                print(f"[migrate][X] la base rechaza la conexion por algo que no "
                      f"se arregla esperando: {e}", flush=True)
                raise SystemExit(1)
            esperado = time.monotonic() - t0
            if esperado >= ESPERA_MAX_S:
                print(f"[migrate][X] la base no acepto conexiones en "
                      f"{ESPERA_MAX_S}s. Si es la primera sincronizacion del "
                      f"blueprint puede seguir aprovisionando: mira el estado de "
                      f"la base en el dashboard y volve a disparar el deploy. "
                      f"Ultimo error: {e}", flush=True)
                raise SystemExit(1)
            if intento == 1:
                print(f"[migrate] la base todavia no atiende; esperando hasta "
                      f"{ESPERA_MAX_S}s", flush=True)
            time.sleep(ESPERA_PASO_S)


def _preparar_rol_de_la_app() -> None:
    """Crea el rol sin bypass de RLS y le deja los permisos puestos.

    Se conecta con DATABASE_URL (el duenio) porque es el unico que puede crear
    roles. Nunca imprime la contrasenia.
    """
    base = (os.environ.get("DATABASE_URL") or "").strip()
    pwd = dburl.password_app()
    if not base:
        print("[migrate][X] DATABASE_URL no esta seteada. Con el blueprint de "
              "render.yaml la completa Render sola desde la base del propio "
              "blueprint (fromDatabase); si esta vacia, el servicio no quedo "
              "enlazado a ninguna base.", flush=True)
        raise SystemExit(1)
    if not pwd:
        print(f"[migrate][X] {dburl.ENV_PASSWORD} no esta seteada. La genera el "
              "blueprint (generateValue: true) y es lo unico con lo que se "
              "puede crear el rol de la app. Sin ella no hay forma de separar "
              "el rol duenio del rol sin bypass de RLS — y usar el duenio para "
              "todo apaga Row-Level Security en silencio.", flush=True)
        raise SystemExit(1)

    from sqlalchemy import create_engine
    from core.db.url import normalize_driver

    # `connect_timeout` NO es decoracion: sin el, un intento contra un host que
    # no contesta se cuelga ~130s por su cuenta, y el tope de espera de abajo
    # se vuelve mentira (medido: tope de 6s, tardo 260s). Con 5s por intento,
    # el tope de verdad manda.
    motor = create_engine(normalize_driver(base), pool_pre_ping=True,
                          connect_args={"connect_timeout": 5})
    _esperar_a_la_base(motor)
    with motor.begin() as cx:
        creado = dburl.crear_rol(cx, dburl.ROL_APP, pwd)
        dburl.aplicar_grants(cx, dburl.ROL_APP, dburl.SQL_GRANTS_FUTUROS)
    motor.dispose()
    print(f"[migrate] rol '{dburl.ROL_APP}' {'creado' if creado else 'ya existia'} "
          f"(NOBYPASSRLS), con permisos sobre lo que Alembic cree a continuacion",
          flush=True)


def _permisos_sobre_lo_existente() -> None:
    """Lo que ALTER DEFAULT PRIVILEGES no alcanza: las tablas que YA estaban.

    Hace falta en todo redeploy sobre una base que ya tiene esquema, y en el
    primero tambien, porque Alembic corre como duenio y las tablas nacen suyas.
    """
    from sqlalchemy import create_engine
    from core.db.url import normalize_driver

    motor = create_engine(normalize_driver(os.environ["DATABASE_URL"]), pool_pre_ping=True)
    with motor.begin() as cx:
        dburl.aplicar_grants(cx, dburl.ROL_APP, dburl.SQL_GRANTS_EXISTENTES)
    motor.dispose()
    print(f"[migrate] permisos de '{dburl.ROL_APP}' al dia sobre el esquema", flush=True)


def main() -> None:
    tenant = deploy_guard.require_tenant()
    print(f"[migrate] tenant={tenant}", flush=True)

    # 1 · el rol de la app y los permisos de lo que viene. ANTES de Alembic.
    _preparar_rol_de_la_app()

    # 2 · el esquema
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True, text=True, cwd=BACKEND, timeout=300,
    )
    if r.returncode != 0:
        print(r.stdout[-1500:] + r.stderr[-1500:], flush=True)
        print("[migrate][X] alembic upgrade head failed — the deploy stops "
              "here and the running instance keeps serving", flush=True)
        raise SystemExit(1)
    print("[migrate] schema at head", flush=True)

    # 3 · y los permisos sobre lo que quedo creado
    _permisos_sobre_lo_existente()


if __name__ == "__main__":
    main()
