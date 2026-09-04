"""Environment guards for the deploy entrypoints (deploy/migrate.py, deploy/boot.py).

Not in core/paths.py, deliberately: paths.py defaults POLPILOT_TENANT to
"demo" so local dev, the suite and start_demo.py need no configuration, and
removing that default would break all three. A *deployment* inheriting it
silently is what these guards prevent — so the rule lives in the two scripts
Render runs, which local dev and tests never call.
"""
from __future__ import annotations

import os
import sys
from typing import Mapping


def _env(env: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if env is None else env


def require_tenant(env: Mapping[str, str] | None = None) -> str:
    """The tenant this deployment serves, or exit non-zero saying so.

    Exits rather than raising: both callers are scripts contracted to fail
    the deploy loudly."""
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

    Must stay opt-in: generar.py rewrites the whole dataset — right for the
    demo on Render's ephemeral filesystem, data loss on a real tenant."""
    return _env(env).get("POLPILOT_SEED_ON_BOOT", "").strip() == "1"
