import os
import shutil
import tempfile
import uuid as _uuid

import pytest
from sqlalchemy import text as _text

# La suite corre contra el tenant "piloto" — la empresa FICTICIA "Supermercados
# Horizonte" (usuarios emilio/paula/vendedor/deposito). Sin este pin, el default
# del repo es el tenant demo (usuarios aldo/marta/…) y media suite, escrita
# contra los roles del piloto, no encontraría a sus usuarios.
#
# El data dir de la suite es un directorio TEMPORAL con SOLO el catálogo
# (inventory.json): el estado "carga inicial" de un tenant recién montado, que
# es el que la suite del piloto siempre asumió (sin ventas, sin apartados, sin
# historia — cada test siembra lo que necesita). Los tests escriben y hasta
# reemplazan datasets enteros (fixtures): jamás sobre el seed versionado.
# Los tests que verifican los números canónicos del DEMO (test_p27/p38/p45/…)
# apuntan su subproceso al data-demo/ real, que así queda prístino.
os.environ.setdefault("POLPILOT_TENANT", "piloto")
if "POLPILOT_DATA_DIR" not in os.environ:
    _raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    _scratch = os.path.join(tempfile.mkdtemp(prefix="polpilot-suite-"), "data")
    os.makedirs(_scratch)
    shutil.copy2(os.path.join(_raiz, "data-demo", "inventory.json"),
                 os.path.join(_scratch, "inventory.json"))
    os.environ["POLPILOT_DATA_DIR"] = _scratch


@pytest.fixture
def db_tenant():
    """A throwaway tenant row for one test. Deleting it cascades to every
    tenant-scoped table (auth_credentials, sessions, and — from Task 8 on —
    customer_accounts/account_movements), so tests never leak rows.
    Uses the admin engine: creating/deleting a tenants row is admin-level
    work, not a tenant-scoped query — see the Task 4 correction note in the
    plan for why that distinction matters."""
    from core.db.engine import get_admin_engine

    engine = get_admin_engine()
    slug = f"test-{_uuid.uuid4().hex[:8]}"
    with engine.begin() as conn:
        tid = conn.execute(_text(
            "INSERT INTO tenants (slug, name, short_name, source) "
            "VALUES (:slug, 'Test Tenant', 'Test', 'test') RETURNING id"
        ), {"slug": slug}).scalar_one()
    yield str(tid)
    with engine.begin() as conn:
        conn.execute(_text("DELETE FROM tenants WHERE id = :id"), {"id": tid})


@pytest.fixture(autouse=True)
def _analisis_cache_limpio():
    """P11·B4: el cache de análisis jamás se filtra entre tests — ni siquiera
    cuando un test reescribe los JSON a mano sin pasar por los hooks."""
    from core import analisis_cache
    analisis_cache.limpiar()
    yield
    analisis_cache.limpiar()


@pytest.fixture
def articulos_raw():
    """Cuatro artículos que cubren cada categoría de issue + uno sano."""
    return [
        # fantasma: anulado con stock vivo
        {"codigo": 1, "descripcion": "QUESO FANTASMA", "estado": "anulado",
         "stock": 10, "costo_iva": 100, "pvp": 200, "inmovilizado": 0},
        # negativo: stock < 0
        {"codigo": 2, "descripcion": "MASA CREMOSA", "estado": "activo",
         "stock": -5, "costo_iva": 50, "pvp": 80, "inmovilizado": 0},
        # sin precio: activo sin pvp, con plata parada
        {"codigo": 3, "descripcion": "MANTECA SIN PRECIO", "estado": "activo",
         "stock": 4, "costo_iva": 100, "pvp": None, "inmovilizado": 400},
        # balanza: peso fuera de rango
        {"codigo": 4, "descripcion": "JAMON FETEADO", "estado": "activo",
         "stock": 2, "costo_iva": 500, "pvp": 900, "inmovilizado": 1000,
         "venta_x_peso": True, "cota_inf": 4, "cota_sup": 6, "valor_peso": 3},
        # costo viejo: > 365 días
        {"codigo": 5, "descripcion": "ACEITE VIEJO", "estado": "activo",
         "stock": 3, "costo_iva": 200, "pvp": 300, "inmovilizado": 600,
         "antiguedad_costo_dias": 400},
        # sano: nada
        {"codigo": 6, "descripcion": "LECHE OK", "estado": "activo",
         "stock": 8, "costo_iva": 90, "pvp": 130, "inmovilizado": 720,
         "antiguedad_costo_dias": 30},
    ]
