"""Warm every screen the demo touches, BEFORE going on stage.

Why this exists, and it is not a nicety. The analyses are cached per
(name, language, date) and the cache is empty on a cold process. The first
request that needs one pays for it: measured on this dataset, the brain takes
about 6 s cold and 0.3 s warm, and the counterfactual (which recomputes with
one note removed) the same. In a 2m30 pitch, six seconds of a still screen is
where a demo dies — and the mentors said it plainly: test the whole demo so it
does not break live.

So: run this once, after the backend is up and before the pitch. It logs in
like the browser does and touches exactly what the demo touches, in order.
Nothing here is demo-only behaviour inside the product: it is an outside
client making the same calls a person would, just earlier.

    py backend/scripts/precalentar_demo.py --api http://127.0.0.1:8099

It does NOT run the evals (those are locked off — see core/evals.py). It only
reads the recorded run the panel shows.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import urllib.error
import urllib.request

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

# The evidence the counterfactual removes on stage. These are the notes that
# hang off the offer finding — the ones a judge would be handed. Warming them
# means the click is instant instead of a six-second pause.
#
# If the demo path changes, change these: a stale list warms the wrong screen
# and the cold one is the one that gets clicked.
EVIDENCIAS_DEMO = ["nt08", "wa01", "nt09", "ft02"]


def _pedir(api: str, ruta: str, token: str | None = None) -> tuple[int, float, bytes]:
    req = urllib.request.Request(api.rstrip("/") + ruta)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    arranque = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, time.time() - arranque, r.read()
    except urllib.error.HTTPError as e:
        return e.code, time.time() - arranque, b""
    except Exception:
        return 0, time.time() - arranque, b""


def _login(api: str, usuario: str, password: str) -> str | None:
    datos = json.dumps({"username": usuario, "password": password}).encode()
    req = urllib.request.Request(api.rstrip("/") + "/api/login", data=datos,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()).get("token")
    except Exception as e:  # noqa: BLE001
        print(f"  no pude entrar: {e}")
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Precalienta las pantallas de la demo.")
    ap.add_argument("--api", default="http://127.0.0.1:8099")
    ap.add_argument("--usuario", default="aldo")
    ap.add_argument("--password", default="demo-password")
    args = ap.parse_args()

    print(f"\n  Precalentando {args.api} …\n")
    token = _login(args.api, args.usuario, args.password)
    if not token:
        return 1

    # En el orden del guion. Lo primero es lo que más tarda en frío.
    rutas = [
        ("el mapa de la operación", "/api/mapa-operacion"),
        ("el cerebro (grafo)", "/api/grafo"),
        ("prioridades", "/api/prioridades"),
        ("inicio", "/api/inicio"),
        ("el panel de evals (lee el JSON, no calcula)", "/api/evals"),
    ]
    for nombre, ruta in rutas:
        codigo, segundos, _ = _pedir(args.api, ruta, token)
        estado = "ok " if codigo == 200 else f"HTTP {codigo}"
        print(f"  {estado}  {segundos:6.2f}s  {nombre}")

    # El contrafáctico: una llamada por evidencia que el jurado puede sacar.
    print()
    for nid in EVIDENCIAS_DEMO:
        codigo, segundos, _ = _pedir(args.api, f"/api/grafo?sin_notas={nid}", token)
        estado = "ok " if codigo == 200 else f"HTTP {codigo}"
        print(f"  {estado}  {segundos:6.2f}s  contrafáctico sin «{nid}»")

    # La segunda pasada es la que importa: es lo que va a sentir el jurado.
    print("\n  Segunda pasada (esto es lo que se va a ver en vivo):")
    for nombre, ruta in rutas[:2]:
        _, segundos, _ = _pedir(args.api, ruta, token)
        print(f"       {segundos:6.2f}s  {nombre}")
    _, segundos, _ = _pedir(args.api, f"/api/grafo?sin_notas={EVIDENCIAS_DEMO[0]}", token)
    print(f"       {segundos:6.2f}s  contrafáctico")
    print("\n  Listo.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
