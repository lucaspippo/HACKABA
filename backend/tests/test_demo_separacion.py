"""
El demo (Distribuidora del Litoral) y el piloto (Horizonte) NO se mezclan:
directorios de datos distintos, usuarios distintos, y el dataset demo es
coherente. La separación vive en core/paths.py (env al arrancar la instancia).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAIZ = os.path.dirname(BACKEND)
DATA_DEMO = os.path.join(RAIZ, "data-demo")


def _en_demo(codigo: str) -> str:
    """Corre un snippet en un proceso con el entorno del DEMO y devuelve stdout."""
    env = {**os.environ, "POLPILOT_TENANT": "demo", "POLPILOT_DATA_DIR": DATA_DEMO,
           "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)  # el test no gasta API
    r = subprocess.run([sys.executable, "-c", codigo], cwd=BACKEND, env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    return r.stdout


def test_piloto_en_la_suite():
    # ESTE proceso corre con el pin del conftest → tenant piloto (Horizonte)
    # sobre una copia temporal de data-demo/ (jamás sobre el seed versionado).
    from core import paths
    import auth
    assert paths.TENANT == "piloto"
    assert not paths.DATA_DIR.endswith("data-demo")   # la copia scratch, no el seed
    assert os.path.isfile(os.path.join(paths.DATA_DIR, "inventory.json"))
    assert "emilio" in auth.USUARIOS and "aldo" not in auth.USUARIOS
    assert paths.EMPRESA == "Supermercados Horizonte"


def test_demo_por_default_sin_env():
    # Un proceso SIN env corre el tenant demo sobre data-demo/: el repo
    # publicado arranca la demo solo, sin configurar nada.
    env = {k: v for k, v in os.environ.items()
           if k not in ("POLPILOT_TENANT", "POLPILOT_DATA_DIR")}
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(
        [sys.executable, "-c",
         "from core import paths; import auth;"
         "print(paths.TENANT, paths.DATA_DIR.replace(chr(92), '/').split('/')[-1]);"
         "print('aldo' in auth.USUARIOS)"],
        cwd=BACKEND, env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    lineas = r.stdout.strip().splitlines()
    assert lineas[0] == "demo data-demo"
    assert lineas[1] == "True"


def test_demo_aislado_en_su_directorio():
    out = _en_demo(
        "from core import paths; import auth, data_store as ds;"
        "print(paths.TENANT, paths.DATA_DIR.replace(chr(92), '/').split('/')[-1]);"
        "print(','.join(sorted(auth.USUARIOS)));"
        "print(ds.meta()['empresa'])"
    )
    lineas = out.strip().splitlines()
    assert lineas[0] == "demo data-demo"
    assert "aldo" in lineas[1] and "emilio" not in lineas[1]  # equipos separados
    assert lineas[2] == "Distribuidora del Litoral"


def test_demo_no_escribe_fuera_de_su_directorio(tmp_path):
    # El data dir de OTRO tenant (acá, uno de mentira en tmp) no puede moverse
    # por una escritura del demo — y el demo tampoco puede crear un `data/` en
    # la raíz del repo (el layout viejo del piloto).
    inv_otro = tmp_path / "inventory.json"
    inv_otro.write_text("{}", encoding="utf-8")
    antes = inv_otro.stat().st_mtime
    # una operación de ESCRITURA en el demo (cobro a un cliente demo)
    _en_demo(
        "from core import cuentas, caja;"
        "caja.abrir(0); cuentas.registrar_cobro('kiosco_la_terminal', 1000); caja.cerrar();"
        "print('ok')"
    )
    assert inv_otro.stat().st_mtime == antes              # el otro tenant ni se enteró
    assert not os.path.isdir(os.path.join(RAIZ, "data"))  # no apareció un data/ fantasma
    # cuentas.py y caja.py son Postgres-backed (ver core/db/MIGRATING_A_MODULE.md):
    # registrar_cobro()/abrir()/cerrar() ya no tocan ningún archivo en DATA_DIR.
    # cuentas.json sigue existiendo porque es el seed versionado (git-tracked),
    # no porque el cobro lo haya escrito — lo importante ya está cubierto arriba
    # (nada se movió fuera del directorio del tenant). NO limpiar caja.json acá:
    # generar.py lo escribe como seed legítimo, core.caja no lo toca más, y
    # borrarlo rompía tests/test_p38.py cada vez que este test corría antes
    # (alfabéticamente) en la misma suite.
    assert os.path.exists(os.path.join(DATA_DEMO, "cuentas.json"))


def test_dataset_demo_es_coherente():
    """v2 (P7): empresa SANA — el dataset luce por coherencia, no por desastre."""
    arts = json.load(open(os.path.join(DATA_DEMO, "inventory.json"), encoding="utf-8"))["articulos"]
    assert len(arts) > 350
    balanzas = [a for a in arts if a["venta_x_peso"]]
    assert len(balanzas) >= 60
    inmovilizado = sum(a["inmovilizado"] for a in arts)
    # el inmovilizado cierra con stock × costo (coherencia, no números random)
    for a in arts[:80]:
        esperado = round(a["stock"] * a["costo_iva"], 2) if (a["stock"] or 0) > 0 and a["costo_iva"] else 0.0
        assert a["inmovilizado"] == esperado

    # NEGOCIO SANO: margen agregado positivo de distribuidora (15-30%)
    con_precio = [a for a in arts if a["estado"] == "activo" and a.get("pvp") and a["costo_iva"]]
    margen = sum(a["pvp"] - a["costo_iva"] for a in con_precio) / sum(a["costo_iva"] for a in con_precio)
    assert 0.14 < margen < 0.30, f"margen agregado insano: {margen:.1%}"
    # los "puntitos": POCOS problemas realistas, no un desastre
    assert sum(1 for a in arts if a["estado"] == "activo" and not a.get("pvp")) <= 12
    assert sum(1 for a in arts if a.get("pvp") and a["costo_iva"] > a["pvp"]) == 0  # nada a pérdida
    assert sum(1 for a in arts if (a["stock"] or 0) < 0) <= 4

    ap = json.load(open(os.path.join(DATA_DEMO, "apartados.json"), encoding="utf-8"))
    filas = ap["venta"]["filas"]
    por_mes = {}
    for f in filas:
        por_mes.setdefault(f["fecha"][:7], 0)
        por_mes[f["fecha"][:7]] += f["cantidad"] * f["precio"]
    # 10 años de historia para Evolución/estacionalidad decenal
    assert len({m[:4] for m in por_mes}) >= 10
    # facturación mensual en millones de distribuidora real + cobertura sana
    hoy_mes = max(m for m in por_mes if len([f for f in filas if f["fecha"][:7] == m and f.get("codigo")]) > 100)
    assert 450_000_000 < por_mes[hoy_mes] < 1_100_000_000
    dias_cobertura = inmovilizado / (por_mes[hoy_mes] / 1.20 / 30)
    assert 12 < dias_cobertura < 45, f"cobertura insana: {dias_cobertura:.0f} días"
    # estacionalidad: diciembre factura más que enero (fiestas)
    dic = [v for m, v in por_mes.items() if m.endswith("-12")]
    ene = [v for m, v in por_mes.items() if m.endswith("-01")]
    assert dic and ene and max(dic) > max(ene) * 1.15
    # multi-sucursal visible en los datos recientes
    assert len({f.get("boca") for f in filas if f.get("codigo")}) >= 3
    # las recepciones existen y cruzan con el catálogo (lo comprado entró)
    codigos = {a["codigo"] for a in arts}
    rec = ap["recepciones"]["filas"]
    assert len(rec) > 300 and all(r["codigo"] in codigos for r in rec[:50])


def _hashes_json(carpeta: str) -> dict[str, str]:
    """El SHA-256 de cada JSON que dejó el generador, por nombre."""
    import hashlib
    return {f: hashlib.sha256(open(os.path.join(carpeta, f), "rb").read()).hexdigest()
            for f in sorted(os.listdir(carpeta)) if f.endswith(".json")}


def test_generador_es_determinista():
    """Correr generar.py DOS VECES tiene que dar el mismo inventory.json —
    pero NUNCA contra data-demo/ real ni el tenant "demo" real: sus
    sembrar_staging()/sembrar_solicitud()/sembrar_fotos() llaman directo a
    módulos ya-Postgres (core.staging, core.perfiles), y hasta hace poco
    hardcodeaban POLPILOT_TENANT="demo" sin importar el env externo —
    corriendo este test mutaba de verdad el tenant demo compartido (más
    grave: dos veces por corrida). Ahora esas funciones usan
    os.environ.setdefault(...), así que un tenant descartable puesto ANTES
    de invocar generar.py se respeta. Nunca vuelvas a este patrón sin esa
    garantía — ver core/db/MIGRATING_A_MODULE.md para la historia completa."""
    import shutil
    import tempfile
    import uuid
    from sqlalchemy import text
    from core.db.engine import get_admin_engine

    tenant_slug = f"generar-determinismo-{uuid.uuid4().hex[:8]}"
    tmp = tempfile.mkdtemp(prefix="polpilot-generar-test-")
    data_dir = os.path.join(tmp, "data-demo")
    shutil.copytree(DATA_DEMO, data_dir)
    try:
        env = {**os.environ, "PYTHONIOENCODING": "utf-8",
               "POLPILOT_TENANT": tenant_slug, "POLPILOT_DATA_DIR": data_dir,
               # generar.py's own sembrar_*() do sys.path.insert(0,
               # "<their dir>/../backend") — correct when run from the real
               # data-demo/, wrong from this isolated temp copy. PYTHONPATH
               # makes `from core import ...` resolve regardless.
               "PYTHONPATH": BACKEND}
        env.pop("ANTHROPIC_API_KEY", None)

        r0 = subprocess.run(
            [sys.executable, "-c", f"import seed_db; seed_db.ensure_tenant({tenant_slug!r})"],
            cwd=data_dir, env=env, capture_output=True, text=True, timeout=60)
        assert r0.returncode == 0, r0.stderr[-500:]

        r1 = subprocess.run([sys.executable, "generar.py"], cwd=data_dir,
                            capture_output=True, text=True, timeout=180, env=env)
        assert r1.returncode == 0, r1.stderr[-500:]
        hashes1 = _hashes_json(data_dir)
        r2 = subprocess.run([sys.executable, "generar.py"], cwd=data_dir,
                            capture_output=True, text=True, timeout=180, env=env)
        assert r2.returncode == 0, r2.stderr[-500:]
        hashes2 = _hashes_json(data_dir)
        # TODOS los JSON, no sólo inventory.json: desde la resiembra por hash
        # (core/db/seed_state.py) el determinismo de CADA archivo es lo que
        # evita que la demo se resiembre en cada boot y pierda lo que hicieron
        # los visitantes. Un archivo que derive sería un fallo silencioso.
        distintos = [f for f in hashes1 if hashes1[f] != hashes2.get(f)]
        assert not distintos, f"generar.py no es determinista en {distintos}"
        assert set(hashes1) == set(hashes2), "cambió el SET de archivos generados"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        with get_admin_engine().begin() as conn:
            conn.execute(text("DELETE FROM tenants WHERE slug = :slug"), {"slug": tenant_slug})