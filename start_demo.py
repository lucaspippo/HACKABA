#!/usr/bin/env python3
"""
start_demo.py · Un comando, demo lista.
=======================================
Levanta el demo de PolPilot (Distribuidora del Litoral) sin pasos manuales:

    python start_demo.py

Qué hace, en orden:
  1. Mata listeners huérfanos en :8001/:5174 (la trampa conocida de uvicorns
     viejos con código/fecha desactualizados).
  2. Avisa si el dataset versionado difiere del snapshot commiteado (residuos
     de pruebas manuales).
  3. Corre data-demo/generar.py: siembra lo que falte (determinista; lo ya
     existente no se toca).
  4. Levanta el backend con TODAS las env vars del demo y espera el healthcheck
     REAL: dataset cargado, actividad sembrada, análisis precalentado.
  5. Levanta el frontend y deja el link listo.

Ctrl+C apaga backend y frontend juntos. Pensado para reutilizarse en el deploy
(el seed + healthcheck son los mismos pasos que un container de Render corre).
"""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

# Consolas Windows (cp1252) vs acentos/glifos: UTF-8 con reemplazo, sin crash.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(HERE, "backend")
FRONTEND = os.path.join(HERE, "frontend")
DATA_DEMO = os.path.join(HERE, "data-demo")
API_PORT = 8001
FRONT_PORT = 5174
ES_WINDOWS = os.name == "nt"

DEMO_ENV = {
    "POLPILOT_TENANT": "demo",
    "POLPILOT_DATA_DIR": "../data-demo",
    "POLPILOT_DEFAULT_LANG": "en",
    "POLPILOT_DEMO_TODAY": "2026-07-07",
    "POLPILOT_DEMO_ROLE_SWITCH": "1",
    "POLPILOT_DEMO_MSG_CAP": "35",
    "POLPILOT_DEMO_AUTOLOGIN": "1",
}

VERDE, ROJO, AMARILLO, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[0m"


def log(msg: str) -> None:
    print(f"  {msg}", flush=True)


def ok(msg: str) -> None:
    print(f"{VERDE}[OK]{RESET} {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"{AMARILLO}[!] {msg}{RESET}", flush=True)


def fail(msg: str) -> None:
    print(f"{ROJO}[X] {msg}{RESET}", flush=True)


# ----------------------------------------------------------------------------
# 1 · Puertos limpios: matar listeners huérfanos (runbook del 23/7, automatizado)
# ----------------------------------------------------------------------------

def _pids_escuchando(puerto: int) -> set[int]:
    pids: set[int] = set()
    try:
        if ES_WINDOWS:
            # SIN "-p TCP": eso filtra solo IPv4 y Vite escucha solo en [::1]
            # (la trampa IPv6 conocida — el huérfano del front quedaba invisible).
            out = subprocess.run(["netstat", "-ano"],
                                 capture_output=True, text=True, timeout=15).stdout
            for linea in out.splitlines():
                partes = linea.split()
                if len(partes) >= 5 and partes[0] == "TCP" and "LISTENING" in linea:
                    if partes[1].endswith(f":{puerto}"):
                        pids.add(int(partes[-1]))
        else:
            out = subprocess.run(["lsof", "-ti", f"tcp:{puerto}", "-sTCP:LISTEN"],
                                 capture_output=True, text=True, timeout=15).stdout
            pids = {int(p) for p in out.split() if p.strip()}
    except (subprocess.SubprocessError, ValueError, FileNotFoundError):
        pass
    return pids


def limpiar_puerto(puerto: int) -> None:
    pids = _pids_escuchando(puerto)
    if not pids:
        return
    for pid in pids:
        warn(f"puerto {puerto} ocupado por PID {pid} — matando el proceso huérfano")
        try:
            if ES_WINDOWS:
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                               capture_output=True, timeout=15)
            else:
                os.kill(pid, signal.SIGTERM)
        except (subprocess.SubprocessError, OSError) as e:
            fail(f"no pude matar el PID {pid}: {e} — cerralo a mano y reintentá")
            sys.exit(1)
    time.sleep(1.5)
    if _pids_escuchando(puerto):
        fail(f"el puerto {puerto} sigue ocupado — cerralo a mano y reintentá")
        sys.exit(1)


# ----------------------------------------------------------------------------
# 2 · Guard del snapshot + 3 · seed idempotente
# ----------------------------------------------------------------------------

def guard_snapshot() -> None:
    try:
        out = subprocess.run(["git", "status", "--porcelain", "data-demo/"],
                             capture_output=True, text=True, cwd=HERE, timeout=15).stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        return  # sin git (p.ej. deploy): el seed determinista es la fuente de verdad
    sucios = [l for l in out.splitlines() if l.strip() and not l.lstrip().startswith("??")]
    if sucios:
        warn("EL DATASET VERSIONADO DIFIERE DEL SNAPSHOT COMMITEADO:")
        for l in sucios:
            warn(f"   {l.strip()}")
        warn("   (residuos de pruebas manuales — `git checkout -- data-demo/` para el estado canónico)")
    else:
        ok("dataset versionado = snapshot commiteado")


def sembrar() -> None:
    r = subprocess.run([sys.executable, os.path.join(DATA_DEMO, "generar.py")],
                       capture_output=True, text=True, cwd=DATA_DEMO, timeout=120)
    if r.returncode != 0:
        fail("generar.py falló:")
        print(r.stdout[-1200:] + r.stderr[-1200:])
        sys.exit(1)
    ok("seed verificado (generar.py: siembra solo lo que falta, byte-igual)")


# ----------------------------------------------------------------------------
# 4 · Backend + healthcheck real
# ----------------------------------------------------------------------------

def _http(metodo: str, ruta: str, token: str | None = None, timeout: float = 10.0):
    req = urllib.request.Request(f"http://127.0.0.1:{API_PORT}{ruta}", method=metodo)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if metodo == "POST":
        req.add_header("Content-Length", "0")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def levantar_backend() -> subprocess.Popen:
    env = {**os.environ, **DEMO_ENV}
    p = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--port", str(API_PORT)],
        cwd=BACKEND, env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if ES_WINDOWS else 0,
    )
    return p


def esperar_backend(proc: subprocess.Popen, timeout_s: int = 45) -> None:
    inicio = time.time()
    while time.time() - inicio < timeout_s:
        if proc.poll() is not None:
            fail("el backend murió al arrancar — revisá el error de uvicorn arriba")
            sys.exit(1)
        try:
            h = _http("GET", "/api/health", timeout=3)
            if h.get("meta", {}).get("empresa"):
                ok(f"backend arriba: {h['meta']['empresa']} (autologin={'sí' if h.get('autologin') else 'NO'})")
                return
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            pass
        time.sleep(1)
    fail(f"el backend no respondió /api/health en {timeout_s}s")
    proc.terminate()
    sys.exit(1)


def healthcheck(proc: subprocess.Popen) -> None:
    """Los tres chequeos que evitan el 'Home vacío que parece real'."""
    try:
        sesion = _http("POST", "/api/demo/autologin")
        token = sesion["token"]
    except Exception as e:  # noqa: BLE001 — cualquier fallo acá es fatal e informativo
        fail(f"autologin falló ({e}) — ¿POLPILOT_DEMO_AUTOLOGIN=1 llegó al backend?")
        proc.terminate()
        sys.exit(1)

    problemas = []
    try:
        inv = _http("GET", "/api/inventario", token)
        n_arts = inv.get("resumen", {}).get("total_articulos", 0)
        if n_arts > 0:
            ok(f"dataset cargado: {n_arts} artículos, inmovilizado ${inv['resumen']['inmovilizado_total']:,.0f}")
        else:
            problemas.append("inventario vacío (¿generar.py corrió? ¿DATA_DIR correcto?)")
    except Exception as e:  # noqa: BLE001
        problemas.append(f"/api/inventario falló: {e}")

    try:
        ini = _http("GET", "/api/inicio", token)
        feed = (ini.get("actividad") or {}).get("feed") or []
        if feed:
            ok(f"actividad sembrada: {len(feed)} eventos en el feed")
        else:
            problemas.append("feed de actividad vacío (el Home diría 'no pasó nada' — mentira)")
    except Exception as e:  # noqa: BLE001
        problemas.append(f"/api/inicio falló: {e}")

    try:
        # además de verificar, este hit deja el cache caliente si el precálculo
        # del arranque todavía está corriendo
        for _ in range(10):
            an = _http("GET", "/api/analisis", token, timeout=30)
            if an.get("disponible"):
                ok("análisis precalentado (Oportunidades entra instantáneo)")
                break
            time.sleep(1)
        else:
            problemas.append("el análisis no reporta disponible (¿ventas sin validar?)")
    except Exception as e:  # noqa: BLE001
        problemas.append(f"/api/analisis falló: {e}")

    # El mapa dispara ~16 fetches al abrirse (señales + cruces + conocimiento) y
    # el backend es un worker sync: si esos endpoints entran FRÍOS, la primera
    # apertura tarda ~45s (tormenta de requests serializada). Precalentarlos acá
    # deja la primera apertura del mapa en pocos segundos (revisitas: instantáneas
    # por el cache del front). Best-effort: si alguno falla, el mapa igual carga.
    endpoints_mapa = ("/api/oportunidades", "/api/cuentas", "/api/ventas",
                      "/api/pagos", "/api/deposito", "/api/evolucion",
                      "/api/inicio", "/api/calidad", "/api/macro",
                      "/api/anomalias", "/api/equipo/actividad", "/api/conocimiento")
    calientes = 0
    for ruta in endpoints_mapa:
        try:
            _http("GET", ruta, token, timeout=30)
            calientes += 1
        except Exception:  # noqa: BLE001 — best-effort, el mapa no depende de esto
            pass
    ok(f"mapa precalentado ({calientes}/{len(endpoints_mapa)} endpoints — primera apertura rápida)")

    if problemas:
        for p in problemas:
            fail(p)
        fail("healthcheck FALLÓ: el demo NO está listo para mostrarse. Backend queda arriba para diagnosticar.")
        sys.exit(1)


# ----------------------------------------------------------------------------
# 6 · Frontend
# ----------------------------------------------------------------------------

def levantar_frontend() -> subprocess.Popen:
    # Re-limpiar justo antes de lanzar: si el arranque mató a un start_demo
    # anterior, su Vite puede tardar unos segundos en soltar el puerto (carrera
    # vista el 20/7: el front terminaba en 5176 y el link canónico quedaba muerto).
    # --strictPort: si el puerto sigue tomado, Vite FALLA en vez de derivar
    # en silencio a otro puerto.
    limpiar_puerto(FRONT_PORT)
    env = {**os.environ, "POLPILOT_API_PORT": str(API_PORT)}
    npm = "npm.cmd" if ES_WINDOWS else "npm"
    p = subprocess.Popen(
        [npm, "run", "dev", "--", "--port", str(FRONT_PORT), "--strictPort"],
        cwd=FRONTEND, env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if ES_WINDOWS else 0,
    )
    return p


def esperar_puerto(puerto: int, proc: subprocess.Popen, timeout_s: int = 60) -> None:
    inicio = time.time()
    while time.time() - inicio < timeout_s:
        if proc.poll() is not None:
            fail("el frontend murió al arrancar (¿npm install pendiente?)")
            sys.exit(1)
        try:
            # "localhost" prueba TODAS las direcciones resueltas (127.0.0.1 y ::1):
            # Vite en Windows suele escuchar solo en IPv6 — la trampa conocida.
            with socket.create_connection(("localhost", puerto), timeout=1):
                return
        except OSError:
            time.sleep(1)
    fail(f"el frontend no abrió el puerto {puerto} en {timeout_s}s")
    sys.exit(1)


def main() -> None:
    print("\nPolPilot - demo Distribuidora del Litoral\n" + "-" * 45)
    limpiar_puerto(API_PORT)
    limpiar_puerto(FRONT_PORT)
    guard_snapshot()
    sembrar()
    backend = levantar_backend()
    frontend = None
    try:
        esperar_backend(backend)
        healthcheck(backend)
        frontend = levantar_frontend()
        esperar_puerto(FRONT_PORT, frontend)
        print("-" * 45)
        ok(f"Demo lista -> http://localhost:{FRONT_PORT}")
        log("(entra directo como dueño; EN|ES arriba a la derecha; Ctrl+C apaga todo)")
        while True:
            time.sleep(2)
            for nombre, p in (("backend", backend), ("frontend", frontend)):
                if p.poll() is not None:
                    fail(f"el {nombre} se cayó (exit {p.returncode})")
                    raise KeyboardInterrupt
    except KeyboardInterrupt:
        print()
        log("apagando…")
    finally:
        for p in (frontend, backend):
            if p and p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    p.kill()
        ok("puertos limpios")


if __name__ == "__main__":
    main()
