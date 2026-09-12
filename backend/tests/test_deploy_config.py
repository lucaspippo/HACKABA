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
                "POLPILOT_SEED_ON_BOOT", "ANGELA_MODEL"):
        assert key in blueprint, f"{key} must be declared in render.yaml"


def test_the_blueprint_runs_migrations_before_the_deploy():
    blueprint = _read("render.yaml")
    assert "preDeployCommand" in blueprint
    assert "deploy/migrate.py" in blueprint


def test_the_blueprint_no_longer_names_the_service_after_the_demo():
    blueprint = _read("render.yaml")
    assert re.search(r"^\s*name:\s*polpilot-app\s*$", blueprint, re.M), (
        "the service is polpilot-app; POLPILOT_TENANT decides which tenant it serves"
    )


def test_the_blueprint_keeps_every_secret_out_of_the_repo():
    blueprint = _read("render.yaml")
    for secret in ("ANTHROPIC_API_KEY", "POLPILOT_RESET_TOKEN",
                   "DATABASE_URL", "APP_DATABASE_URL"):
        assert secret in blueprint, f"{secret} must be declared"
    # Four secrets, four sync:false markers — a literal value here would
    # commit a credential.
    assert blueprint.count("sync: false") >= 4
