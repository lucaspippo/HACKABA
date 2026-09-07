"""The Odoo connector's SAMPLE transport (core/odoo_demo.py).

What is protected, in order of how expensive it would be to get wrong:

  1. IT IS NEVER A FALLBACK. Without the owner explicitly connecting the
     sample there is no sample: the real connector keeps failing loudly with
     no configured connection — that failure is intentional product behavior
     (see CLAUDE.md's no-deterministic-fallback rule) and this suite pins it.
  2. A REAL CONNECTION ALWAYS WINS, even with the sample connected.
  3. ACTIVATION IS A LINK, NOT A DATA CHANGE: catalog values stay identical;
     only provenance (source/source_id/sku) is stamped — and deactivation
     undoes exactly that.
  4. THE PIPELINE DOWNSTREAM IS THE REAL ONE: linked rows update through
     store, new rows land in real staging batches for review. Same code path
     a real Odoo would exercise.
"""
from __future__ import annotations

import os
import xmlrpc.client

import pytest

from core import conectores, odoo_demo, odoo_ingest, staging, store
from core.db import odoo_connections_repo, tenant as _tenant
from tests.conftest import limpiar_tabla_tenant


@pytest.fixture
def tenant_id():
    return _tenant.current_tenant_id()


def _limpiar_proveedores() -> None:
    from core import esquema
    esquema.reemplazar_filas("proveedores", [])


@pytest.fixture(autouse=True)
def _aislar(tenant_id):
    """Fresh catalog, no marker, no staging leftovers — before and after."""
    def limpiar():
        try:
            os.remove(odoo_demo.MARKER_JSON)
        except OSError:
            pass
        odoo_connections_repo.delete(tenant_id)
        store.resetear_actual()
        _limpiar_proveedores()
        limpiar_tabla_tenant("staging_batches")
    limpiar()
    yield
    limpiar()


def test_sin_activar_el_conector_real_sigue_fallando_ruidoso(tenant_id):
    """No marker, no connection: the factory hands back the REAL connector
    and its pulls raise — the demo transport never sneaks in as a fallback."""
    assert odoo_demo.disponible()          # the demo dataset ships the sample
    assert not odoo_demo.activo()
    conector = conectores.conector_odoo(tenant_id)
    assert type(conector) is conectores.ConectorOdoo
    with pytest.raises(ValueError):
        conector.pull_productos()


def test_activar_vincula_sin_tocar_valores_y_desactivar_lo_deshace(tenant_id):
    antes = {d["codigo"]: dict(d) for d in store.raw_actual()}
    out = odoo_demo.activar("aldo")
    assert out["productos_vinculados"] == 24
    assert odoo_demo.activo()

    vinculados = [d for d in store.raw_actual() if d.get("source") == "odoo"]
    assert len(vinculados) == 24
    for d in vinculados:
        # provenance stamped, values untouched
        assert d["source_id"] == str(7000 + d["codigo"])
        previo = antes[d["codigo"]]
        for campo in ("descripcion", "stock", "costo_iva", "pvp", "estado"):
            assert d.get(campo) == previo.get(campo), (d["codigo"], campo)

    conector = conectores.conector_odoo(tenant_id)
    assert isinstance(conector, conectores.ConectorOdooDemo)
    pull = conector.pull_productos()
    assert pull["origen"] == "odoo" and pull["total"] == 26

    odoo_demo.desactivar("aldo")
    assert not odoo_demo.activo()
    assert not [d for d in store.raw_actual() if d.get("source") == "odoo"]
    assert type(conectores.conector_odoo(tenant_id)) is conectores.ConectorOdoo


def test_la_conexion_real_le_gana_a_la_muestra(tenant_id, monkeypatch):
    class _Proxy:
        def __init__(self, url):
            self._url = url
        def authenticate(self, db, user, pwd, ctx):
            return 7
        def execute_kw(self, *a, **k):  # pragma: no cover - not exercised
            return []
    monkeypatch.setattr(xmlrpc.client, "ServerProxy", lambda url: _Proxy(url))
    odoo_demo.activar("aldo")
    odoo_connections_repo.save(tenant_id, "https://x.odoo.com", "x", "admin",
                               "good-key")
    conector = conectores.conector_odoo(tenant_id)
    assert type(conector) is conectores.ConectorOdoo
    assert conector._conexion["url"] == "https://x.odoo.com"


def test_el_ingest_corre_el_pipeline_real_sobre_la_muestra(tenant_id):
    odoo_demo.activar("aldo")

    prod = odoo_ingest.ingest_productos("aldo")
    # 24 linked rows re-sync as direct updates; the 2 genuinely new products
    # go to a real staging batch for review — nothing lands unreviewed.
    assert prod["actualizados"] == 24
    assert prod["nuevos_para_revisar"] == 2
    assert prod["batch_id"]

    prov = odoo_ingest.ingest_proveedores("aldo")
    assert prov["nuevos_para_revisar"] == 6
    assert prov["batch_id"]

    oc = odoo_ingest.ingest_ordenes_compra("aldo")
    assert oc["nuevos_para_revisar"] == 2

    ventas = odoo_ingest.ingest_ventas("aldo")
    assert ventas["nuevos_para_revisar"] > 0

    recs = odoo_ingest.ingest_recepciones("aldo")
    assert recs["nuevos_para_revisar"] == len(odoo_demo.payloads()["recepciones"])

    tipos = {b["tipo"] for b in staging.listar()}
    assert {"producto", "proveedor", "orden_compra", "venta",
            "recepciones"} <= tipos


def test_disponibles_reporta_activo_y_demo(tenant_id):
    odoo_demo.activar("aldo")
    odoo = next(c for c in conectores.disponibles(tenant_id)
                if c["nombre"] == "odoo")
    assert odoo["estado"] == "activo"
    assert odoo.get("demo") is True
    assert odoo["schema"]["conectado"] is True
