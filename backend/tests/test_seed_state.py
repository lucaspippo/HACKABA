"""Re-seeding a domain whose on-disk dataset changed (core/db/seed_state.py).

The bug this closes was live in production: `notas_equipo.json` grew from 17
to 31 notes, the deploy shipped the new file, and the operation map kept
saying "0 de 17" because `team_notes` already had a blob and every module
only seeds when its blob is MISSING.

What is pinned here, in order of how expensive it would be to get wrong:

  1. A PRODUCTIVE TENANT NEVER RE-SEEDS ON ITS OWN. Same changed file, gate
     closed: the stored data is untouched and the change is announced, never
     silent. This is the case that must not regress — it is somebody's real
     business data.
  2. A demo tenant (POLPILOT_SEED_ON_BOOT=1) DOES pick up the new dataset.
  3. The comparison is against the FILE, never the blob: a demo where
     visitors write would otherwise re-seed on every boot.
  4. `decidir` is pure, so the whole policy is one readable table.
"""
from __future__ import annotations

import json
import os

import pytest

from core import notas, paths
from core.db import seed_state
from core.db import tenant as _tenant
from tests.conftest import limpiar_tabla_tenant

RUTA = os.path.join(paths.DATA_DIR, "notas_equipo.json")
DOMINIO = "team_notes"
TABLAS = ["team_notes"]


def _escribir(n: int) -> None:
    """A seed file with n notes — the shape core/notas.py reads."""
    with open(RUTA, "w", encoding="utf-8") as f:
        json.dump({"canales": ["voz"], "notas": [
            {"id": f"n{i}", "autor": "alguien", "fecha": "2026-01-01",
             "canal": "voz", "tipo": "observacion_campo",
             "texto": f"nota {i}", "texto_en": f"note {i}",
             "cliente": None, "producto": None, "proveedor": None,
             "ubicacion": None}
            for i in range(n)]}, f, ensure_ascii=False)


def _sembrar() -> str:
    return seed_state.sembrar(DOMINIO, [RUTA], TABLAS, notas.listar)


@pytest.fixture(autouse=True)
def _aislado():
    def limpiar():
        limpiar_tabla_tenant("team_notes")
        limpiar_tabla_tenant("seed_state")
        if os.path.exists(RUTA):
            os.remove(RUTA)
    limpiar()
    yield
    limpiar()


# --- 1 · the case that must not regress -------------------------------------

def test_un_tenant_productivo_no_resiembra_y_lo_dice(monkeypatch, capsys):
    """Gate closed + changed file: the data stays, and the change is loud."""
    monkeypatch.setenv("POLPILOT_SEED_ON_BOOT", "1")
    _escribir(1)
    assert _sembrar() == seed_state.SEMBRAR
    assert len(notas.listar()) == 1
    baseline = seed_state.estado(_tenant.current_tenant_id())[DOMINIO]

    # The same tenant stops re-seeding, and the dataset changes underneath.
    monkeypatch.setenv("POLPILOT_SEED_ON_BOOT", "0")
    _escribir(2)
    capsys.readouterr()                      # drop the seeding output
    assert _sembrar() == seed_state.AVISAR

    salida = capsys.readouterr().out
    assert "WARNING" in salida and DOMINIO in salida, salida
    # The blob is untouched: still the note it was seeded with.
    assert len(notas.listar()) == 1
    # And the baseline is NOT advanced, so the warning repeats until someone
    # acts on it instead of being swallowed by the first boot that saw it.
    assert seed_state.estado(_tenant.current_tenant_id())[DOMINIO] == baseline
    capsys.readouterr()
    assert _sembrar() == seed_state.AVISAR
    assert "WARNING" in capsys.readouterr().out


def test_revisar_avisa_sin_tocar_nada(monkeypatch, capsys):
    """What a productive tenant runs at boot: compare and report, no writes."""
    monkeypatch.setenv("POLPILOT_SEED_ON_BOOT", "1")
    _escribir(1)
    _sembrar()
    _escribir(3)
    capsys.readouterr()

    assert seed_state.revisar(DOMINIO, [RUTA]) == seed_state.AVISAR
    assert "WARNING" in capsys.readouterr().out
    assert len(notas.listar()) == 1


# --- 2 · the demo picks the new dataset up ----------------------------------

def test_el_demo_resiembra_cuando_cambia_el_dataset(monkeypatch, capsys):
    monkeypatch.setenv("POLPILOT_SEED_ON_BOOT", "1")
    _escribir(1)
    assert _sembrar() == seed_state.SEMBRAR
    assert len(notas.listar()) == 1

    _escribir(31)                            # the real production change
    capsys.readouterr()
    assert _sembrar() == seed_state.RESEMBRAR
    assert len(notas.listar()) == 31
    assert "resembrado" in capsys.readouterr().out
    # Baseline advanced: the next boot is a no-op, not a re-seed loop.
    assert _sembrar() == seed_state.NADA
    assert len(notas.listar()) == 31


# --- 3 · the comparison is against the file, never the blob -----------------

def test_lo_que_escribe_un_visitante_no_dispara_resiembra(monkeypatch):
    """The demo's blob always differs from the JSON (people use the demo).
    Only a change in the FILE counts, or every boot would wipe their work."""
    monkeypatch.setenv("POLPILOT_SEED_ON_BOOT", "1")
    _escribir(2)
    _sembrar()

    from core.db import team_notes_repo
    tid = _tenant.current_tenant_id()
    vivo = team_notes_repo.get_data(tid)
    vivo["notas"].append({"id": "visita", "autor": "alguien", "fecha": "2026-02-02",
                          "canal": "voz", "tipo": "observacion_campo",
                          "texto": "lo que anotó alguien usando la demo",
                          "texto_en": "what a visitor wrote"})
    team_notes_repo.save_data(tid, vivo)

    assert _sembrar() == seed_state.NADA
    assert len(notas.listar()) == 3, "el trabajo del visitante sobrevivió"


def test_un_dominio_sin_archivo_en_disco_no_se_sigue(monkeypatch):
    """organizacion/extraccion have no on-disk seed: in-code fallback, no
    state, exactly the behaviour they had before this existed."""
    monkeypatch.setenv("POLPILOT_SEED_ON_BOOT", "1")
    assert not os.path.exists(RUTA)
    assert seed_state.hash_de([RUTA]) is None
    assert _sembrar() == seed_state.NADA
    assert DOMINIO not in seed_state.estado(_tenant.current_tenant_id())


# --- 4 · the policy, as a table ---------------------------------------------

@pytest.mark.parametrize("previo,actual,gate,espera", [
    (None,  None,  True,  seed_state.NADA),       # no seed file at all
    (None,  None,  False, seed_state.NADA),
    (None,  "aa",  True,  seed_state.SEMBRAR),    # first time
    (None,  "aa",  False, seed_state.SEMBRAR),
    ("aa",  "aa",  True,  seed_state.NADA),       # unchanged
    ("aa",  "aa",  False, seed_state.NADA),
    ("aa",  "bb",  True,  seed_state.RESEMBRAR),  # changed, demo
    ("aa",  "bb",  False, seed_state.AVISAR),     # changed, productive
])
def test_la_politica_entera(previo, actual, gate, espera):
    assert seed_state.decidir(previo, actual, gate) == espera


def test_el_hash_cambia_solo_si_cambia_el_contenido():
    _escribir(1)
    h1 = seed_state.hash_de([RUTA])
    _escribir(1)
    assert seed_state.hash_de([RUTA]) == h1, "mismo contenido, mismo hash"
    _escribir(2)
    assert seed_state.hash_de([RUTA]) != h1
