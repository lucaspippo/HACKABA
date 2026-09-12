"""
P11·B4 — El cache de análisis: hit instantáneo, invalidación por cada vía de
mutación real, un cache por idioma, precálculo en el arranque del server.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import auth
import main
from core import analisis_cache, cuentas, esquema, store, ventas


client = TestClient(main.app)


@pytest.fixture()
def h():
    creds = auth.cargar_o_generar_credenciales()
    tok = client.post("/api/login", json={"username": "emilio",
                                          "password": creds["emilio"]}).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


def _contador():
    llamadas = {"n": 0}
    def fn():
        llamadas["n"] += 1
        return {"valor": llamadas["n"]}
    return llamadas, fn


def test_hit_no_recomputa():
    llamadas, fn = _contador()
    a = analisis_cache.get_o_computar("t1", "es", fn)
    b = analisis_cache.get_o_computar("t1", "es", fn)
    assert llamadas["n"] == 1 and a == b


def test_datos_cambiaron_invalida():
    llamadas, fn = _contador()
    analisis_cache.get_o_computar("t2", "es", fn)
    analisis_cache.datos_cambiaron()
    analisis_cache.get_o_computar("t2", "es", fn)
    assert llamadas["n"] == 2


def test_cache_por_idioma_no_colisiona():
    llamadas, fn = _contador()
    es = analisis_cache.get_o_computar("t3", "es", fn)
    en = analisis_cache.get_o_computar("t3", "en", fn)
    assert llamadas["n"] == 2 and es != en


@pytest.mark.parametrize("mutar", [
    lambda: store.guardar(store.raw_actual()),
    lambda: esquema._save(esquema._load()),
    lambda: cuentas._save(cuentas._load()),
    lambda: ventas._val_save(ventas._val_load()),
], ids=["store.guardar", "esquema._save", "cuentas._save", "ventas._val_save"])
def test_cada_via_de_mutacion_invalida(mutar):
    """Confirmar comprobante, aplicar corrección, integrar staging, registrar
    un cobro o validar ventas: TODAS pasan por uno de estos choke points."""
    llamadas, fn = _contador()
    analisis_cache.get_o_computar("t4", "es", fn)
    mutar()
    analisis_cache.get_o_computar("t4", "es", fn)
    assert llamadas["n"] == 2
    store.resetear_actual()


def test_endpoint_analisis_cacheado_y_coherente(h):
    """Dos GET → byte-idéntico y igual al cómputo directo; una mutación real
    (guardar stock) → el próximo GET recomputa sin servir stale."""
    from core import analisis
    r1 = client.get("/api/analisis", headers=h).json()
    r2 = client.get("/api/analisis", headers=h).json()
    assert r1 == r2
    assert r1 == analisis.completo("es")
    store.guardar(store.raw_actual())      # mutación → invalida
    r3 = client.get("/api/analisis", headers=h).json()
    assert r3 == analisis.completo("es")   # coherente, no stale
    store.resetear_actual()


def test_evolucion_pasa_por_el_cache(h):
    r1 = client.get("/api/evolucion", headers=h).json()
    r2 = client.get("/api/evolucion", headers=h).json()
    assert r1 == r2


def test_lifespan_precalienta():
    """Con el ciclo de vida real del server, el arranque dispara el precálculo.

    OJO CON EL CONTRATO: antes esto corría DENTRO del lifespan y el cache
    estaba poblado antes del primer request. Con el tenant del demo eso tardaba
    ~70 s en los que el server no aceptaba una sola request — reiniciar durante
    una demo dejaba todo muerto más de un minuto. Ahora corre en un hilo: el
    server abre al instante y lo que llegue mientras tanto se computa
    on-demand, que es exactamente lo que pasaba sin precálculo.

    Así que lo que se verifica es que el precálculo EFECTIVAMENTE corre, no que
    ya terminó al salir del `with`: para eso hay que esperar al hilo.
    """
    analisis_cache.limpiar()
    with TestClient(main.app):
        assert main.PRECALC_THREAD is not None, "el arranque no lanzó el precálculo"
        main.PRECALC_THREAD.join(timeout=180)
        assert not main.PRECALC_THREAD.is_alive(), "el precálculo no terminó"
        assert len(analisis_cache._cache) >= 4   # analisis+evolucion × es+en
    analisis_cache.limpiar()
