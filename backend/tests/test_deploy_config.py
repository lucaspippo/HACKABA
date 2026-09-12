"""The deployment contract in Dockerfile and render.yaml.

These are text assertions on purpose: there is no YAML parser in
requirements.txt, and building the image in the suite would cost minutes.
What matters is checkable as text — which variables the image bakes in, and
which the blueprint sets.

The finding this file exists to prevent from recurring: the image used to
hard-code POLPILOT_TENANT=demo *and* POLPILOT_DEMO_AUTOLOGIN=1, so any
productive service built from it came up autologged-in as the tenant owner
unless each of them was overridden by hand in the dashboard. Silent, and an
unauthenticated production app.
"""
from __future__ import annotations

import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _read(name: str) -> str:
    with open(os.path.join(REPO_ROOT, name), encoding="utf-8") as fh:
        return fh.read()


# The image is built once and must be usable by ANY tenant, so the only
# POLPILOT_* names allowed in it are properties of the image layout. Stated as
# an allowlist rather than a list of forbidden names on purpose: a denylist of
# POLPILOT_TENANT and POLPILOT_DEMO_* left POLPILOT_DEFAULT_LANG (the demo
# pins "en") and POLPILOT_DATA_DIR — both just as tenant-specific — free to be
# reintroduced into the image with nothing failing.
_IMAGE_WIDE_VARS = {"POLPILOT_CANONICAL_DIR", "POLPILOT_STATIC_DIR"}


def test_the_image_bakes_in_nothing_tenant_specific():
    dockerfile = _read("Dockerfile")
    found = set(re.findall(r"POLPILOT_\w+", dockerfile))
    assert found <= _IMAGE_WIDE_VARS, (
        f"tenant-specific configuration in the image: {sorted(found - _IMAGE_WIDE_VARS)}. "
        "It must live in render.yaml's envVars — a productive service built "
        "from this image would otherwise inherit the demo's. Comments count: "
        "do not name these variables in the Dockerfile even to explain them."
    )


def test_the_image_keeps_its_image_wide_paths():
    # These are properties of the image layout, not of a tenant, so they stay.
    dockerfile = _read("Dockerfile")
    assert "POLPILOT_STATIC_DIR" in dockerfile
    assert "POLPILOT_CANONICAL_DIR" in dockerfile


def test_the_privacy_guard_is_still_in_the_image():
    dockerfile = _read("Dockerfile")
    assert "Supermercados Horizonte" in dockerfile, "the privacy guard was weakened"
    assert "credenciales.json" in dockerfile


def test_the_blueprint_sets_the_demo_configuration_explicitly():
    blueprint = _read("render.yaml")
    for key in ("POLPILOT_TENANT", "POLPILOT_DEMO_AUTOLOGIN",
                "POLPILOT_SEED_ON_BOOT"):
        assert key in blueprint, f"{key} must be declared in render.yaml"
    # The model slug must be pinned, but WHICH variable holds it depends on the
    # active provider: ANGELA_MODEL direct, GATEWAY_MODEL through the gateway.
    # Demanding ANGELA_MODEL by name failed the day the provider changed, on a
    # blueprint that was in fact correct.
    assert ("ANGELA_MODEL" in blueprint) or ("GATEWAY_MODEL" in blueprint), (
        "no model slug pinned: production would run whatever the code defaults to"
    )


def test_the_blueprint_runs_migrations_before_the_deploy():
    blueprint = _read("render.yaml")
    assert "preDeployCommand" in blueprint
    assert "deploy/migrate.py" in blueprint


def test_the_blueprint_no_longer_names_the_service_after_the_demo():
    """The service name must not encode a TENANT, and must not collide with
    the product's own service.

    This used to pin the literal `polpilot-app`. Two things made that wrong:
    the invariant was never that exact string —it was "the name does not say
    which tenant this is", because POLPILOT_TENANT decides that— and
    `polpilot-app` is the service of the product repo
    (agustindelmonti/polpilot-app), where the public demo lives. Two services
    with that name in one account collide outright; in separate accounts they
    are a trap for whoever has to read a log under pressure.
    """
    blueprint = _read("render.yaml")
    nombre = re.search(r"^\s*-\s*type:\s*web\s*$.*?^\s*name:\s*(\S+)\s*$",
                       blueprint, re.M | re.S)
    assert nombre, "render.yaml declares no web service name"
    servicio = nombre.group(1)
    assert servicio != "polpilot-app", (
        "that is the product repo's service; this blueprint would collide with it"
    )
    for tenant in ("demo", "papasud", "santa-elena"):
        assert not servicio.endswith(tenant), (
            f"the service name says '{tenant}'; POLPILOT_TENANT decides which "
            f"tenant it serves, so the name must not claim one"
        )


# Anything whose value would be a credential. Not "which variables exist" —
# that list changes with the provider — but "none of these ever carries a
# literal value in the repo".
_NUNCA_LITERAL = ("ANTHROPIC_API_KEY", "AI_GATEWAY_API_KEY", "POLPILOT_RESET_TOKEN",
                  "DATABASE_URL", "APP_DATABASE_URL", "POLPILOT_APP_DB_PASSWORD")


def test_the_blueprint_keeps_every_secret_out_of_the_repo():
    """No credential may carry a literal value here.

    This used to demand four specific names and count four `sync: false`
    markers, which tied the test to one provider and one topology. Both moved:
    the AI credential is the Vercel gateway's now (ANTHROPIC_API_KEY is gone),
    DATABASE_URL comes from the blueprint's own database (`fromDatabase`), and
    APP_DATABASE_URL is derived at boot from a generated password — so it is
    not in the file at all. Counting markers would have failed on a change
    that made things SAFER.

    What actually matters is checked instead: whatever credential-bearing
    variable is declared, its value never sits in the repo. `sync: false`
    (typed in the dashboard), `generateValue` (Render invents it) and
    `fromDatabase` (Render wires it) are the three legitimate shapes.
    """
    blueprint = _read("render.yaml")
    for nombre in _NUNCA_LITERAL:
        # `- key: X` followed by whatever that entry declares, up to the next key
        bloque = re.search(
            rf"^\s*-\s*key:\s*{re.escape(nombre)}\s*$(.*?)(?=^\s*-\s*key:|\Z)",
            blueprint, re.M | re.S)
        if not bloque:
            continue        # not declared with this provider/topology: fine
        cuerpo = bloque.group(1)
        assert not re.search(r"^\s*value:", cuerpo, re.M), (
            f"{nombre} has a literal value in render.yaml — that commits a credential"
        )
        assert re.search(r"sync:\s*false|generateValue|fromDatabase", cuerpo), (
            f"{nombre} is declared but neither sync:false, generateValue nor "
            f"fromDatabase — say explicitly where its value comes from"
        )
