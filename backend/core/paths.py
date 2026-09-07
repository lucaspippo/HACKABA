"""
paths.py · UN solo lugar decide dónde viven los datos — la base del multi-tenant.

Cada instancia de PolPilot apunta a SU directorio de datos:
  - Demo (Distribuidora del Litoral): sin env → `data-demo/` (el default de este
    repo: la demo corre sola, sin configurar nada).
  - Piloto ("Supermercados Horizonte", empresa FICTICIA de ejemplo del segundo
    tenant): POLPILOT_TENANT=piloto + POLPILOT_DATA_DIR=<su dir> → aislamiento
    físico total; imposible que se mezclen ni por accidente.

POLPILOT_TENANT ("demo" | "piloto") elige además el seed de usuarios
(auth.py). Cada tenant se levanta como instancia aparte en otro puerto.
"""
from __future__ import annotations

import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT = os.path.abspath(os.path.join(_HERE, "..", "..", "data-demo"))

DATA_DIR = os.path.abspath(os.environ.get("POLPILOT_DATA_DIR") or _DEFAULT)
TENANT = os.environ.get("POLPILOT_TENANT", "demo")

# Identidad visible de la instancia (el header/meta de la API la usa).
# `nombre_corto` es cómo el negocio se nombra a sí mismo ante SUS clientes
# (el mensaje de cobro por WhatsApp firma con esto — byte-igual al histórico
# en el piloto).
# P37 — INCIDENTE DE PRIVACIDAD: el logo del cliente se sirve POR TENANT y jamás
# se empaqueta el de otro tenant en el bundle público. El demo (empresa
# ficticia) usa su logo bundleado; el piloto (cliente REAL) lo sirve el backend
# desde su data dir (data/logo.*), que SOLO existe en la imagen del piloto. Así
# el nombre/asset del piloto no puede aparecer nunca en la demo pública.
_IDENTIDAD = {
    "piloto": {"empresa": "Supermercados Horizonte",
                    "nombre_corto": "Horizonte",
                    "fuente": "Faro ERP · núcleo de verdad PolPilot",
                    "sistema_gestion": "Faro",
                    "logo": "/api/marca/logo"},   # servido del data dir del piloto
    "demo": {"empresa": "Distribuidora del Litoral",
             "nombre_corto": "Distribuidora del Litoral",
             "fuente": "ERP de la distribuidora · núcleo de verdad PolPilot (DEMO)",
             "sistema_gestion": "Odoo",
             "logo": "/logos/litoral.png"},        # empresa ficticia: bundle seguro
}
EMPRESA = _IDENTIDAD.get(TENANT, _IDENTIDAD["demo"])["empresa"]
NOMBRE_CORTO = _IDENTIDAD.get(TENANT, _IDENTIDAD["demo"])["nombre_corto"]
FUENTE = _IDENTIDAD.get(TENANT, _IDENTIDAD["demo"])["fuente"]
LOGO = _IDENTIDAD.get(TENANT, _IDENTIDAD["demo"])["logo"]
# Which management system this tenant's data flows back INTO. Tenant identity,
# not a UI constant: the product mounts on whatever ERP the business already
# uses, and the operation map's "returns to <system>" band names it. Read from
# the same table as the rest of the identity so a new tenant sets it in ONE
# place (see deploy/DEPLOY.md §4 on what a new slug does not get for free).
SISTEMA_GESTION = _IDENTIDAD.get(TENANT, _IDENTIDAD["demo"]).get(
    "sistema_gestion", "ERP")

# Idioma default del tenant (config por env, NO hardcodeado por nombre de tenant).
# El demo arranca con POLPILOT_DEFAULT_LANG=en para los reviewers de YC; el piloto
# sin la var queda en español, exactamente como siempre. La preferencia POR USUARIO
# (perfiles.idioma_de) pisa este default.
IDIOMAS = ("es", "en")
DEFAULT_LANG = os.environ.get("POLPILOT_DEFAULT_LANG", "es")
if DEFAULT_LANG not in IDIOMAS:
    DEFAULT_LANG = "es"
