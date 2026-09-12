"""Environment guards for the deploy entrypoints (deploy/migrate.py and
deploy/boot.py).

Why these live here and not in core/paths.py: paths.py deliberately defaults
POLPILOT_TENANT to "demo" so local dev, the test suite and start_demo.py work
with no configuration at all. Removing that default would break all three.
But a *deployment* inheriting it silently is the failure this module exists
to prevent — a productive service that forgot the variable would come up
serving the demo tenant, with demo users and demo data, and nothing would
say so.

So the rule is enforced where it belongs: at deploy time, in the two scripts
Render runs. Local dev and tests never call them, and keep the default.
"""
from __future__ import annotations

import os
import sys
from typing import Mapping


def _env(env: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if env is None else env


def require_tenant(env: Mapping[str, str] | None = None) -> str:
    """The tenant this deployment serves, or exit non-zero saying so.

    Exits rather than raising a custom exception because both callers are
    scripts whose contract is to fail the deploy loudly."""
    tenant = _env(env).get("POLPILOT_TENANT", "").strip()
    if not tenant:
        print(
            "[deploy][X] POLPILOT_TENANT is not set.\n"
            "            Every deployment must name its tenant explicitly: "
            "core/paths.py falls back to 'demo', so an unset variable would "
            "silently serve the demo tenant's users and data.\n"
            "            Set it in the service's envVars (see render.yaml).",
            flush=True,
        )
        raise SystemExit(1)
    return tenant


def seed_on_boot(env: Mapping[str, str] | None = None) -> bool:
    """Whether this deployment should regenerate and seed its dataset.

    Opt-in, and it must stay opt-in: data-demo/generar.py rewrites the whole
    dataset deterministically, which is exactly right for the demo (Render's
    filesystem is ephemeral, and the admin reset endpoint depends on it) and
    is data loss on a productive tenant."""
    return _env(env).get("POLPILOT_SEED_ON_BOOT", "").strip() == "1"
