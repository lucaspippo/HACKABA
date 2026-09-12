"""Deploy-time environment guards (backend/deploy_guard.py).

core/paths.py defaults POLPILOT_TENANT to "demo" so that local dev, the test
suite and start_demo.py need no configuration. That default is convenient
locally and dangerous in a deployment: once the variable is no longer baked
into the image, a productive service that forgets to set it would silently
come up serving the demo tenant. These guards make the deploy entrypoints —
and only them — demand it explicitly.
"""
from __future__ import annotations

import pytest

import deploy_guard


def test_require_tenant_returns_the_configured_slug():
    assert deploy_guard.require_tenant({"POLPILOT_TENANT": "horizonte"}) == "horizonte"


@pytest.mark.parametrize("env", [
    {},
    {"POLPILOT_TENANT": ""},
    {"POLPILOT_TENANT": "   "},
])
def test_require_tenant_exits_when_absent_or_blank(env):
    with pytest.raises(SystemExit) as excinfo:
        deploy_guard.require_tenant(env)
    assert excinfo.value.code != 0


def test_require_tenant_names_the_variable_in_its_message(capsys):
    with pytest.raises(SystemExit):
        deploy_guard.require_tenant({})
    printed = capsys.readouterr().out + capsys.readouterr().err
    assert "POLPILOT_TENANT" in printed


def test_require_tenant_does_not_accept_the_implicit_default(monkeypatch):
    # The point of the guard: core/paths.py's "demo" fallback must not be
    # what a deployment silently inherits. An explicit demo is fine; an
    # absent variable is not, even though paths.py would resolve it.
    monkeypatch.delenv("POLPILOT_TENANT", raising=False)
    with pytest.raises(SystemExit):
        deploy_guard.require_tenant({})
    assert deploy_guard.require_tenant({"POLPILOT_TENANT": "demo"}) == "demo"


@pytest.mark.parametrize("value,expected", [
    ("1", True),
    ("0", False),
    ("", False),
])
def test_seed_on_boot_is_opt_in(value, expected):
    assert deploy_guard.seed_on_boot({"POLPILOT_SEED_ON_BOOT": value}) is expected


def test_seed_on_boot_defaults_to_off():
    # Fails safe: regenerating the dataset on a productive tenant is data
    # loss, so a service that says nothing must not seed.
    assert deploy_guard.seed_on_boot({}) is False
