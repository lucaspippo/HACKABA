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


def test_the_image_bakes_in_no_tenant_and_no_demo_switches():
    dockerfile = _read("Dockerfile")
    assert "POLPILOT_TENANT" not in dockerfile
    assert not re.search(r"POLPILOT_DEMO_\w+", dockerfile), (
        "demo-only configuration must live in render.yaml's envVars, never in "
        "the image — a productive service built from this image would inherit it"
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
