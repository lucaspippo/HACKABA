"""business_knowledge_pieces: el efecto `exige_evidencia`

Revision ID: 0049
Revises: 0048
Create Date: 2026-09-12

OJO CON EL NUMERO: esto nacio como 0045 y choco de frente con
`0045_angela_conversations.py`, que llego con el trabajo de Agustin y ya tiene
tres migraciones encadenadas encima (0046, 0047, 0048). Dos archivos con el
mismo `revision` dejan a Alembic con dos cabezas y `upgrade head` falla: la
base no migra y el server arranca contra un esquema viejo. Cede esta, que es
la que no tiene nada colgando, y se encadena al final.

Los cinco efectos que había describen qué le hace una regla a un ANÁLISIS:
mueve un umbral, silencia una alerta, genera otra, da contexto, pide una
aprobación. Ninguno describe lo que hace falta para una devolución, que es
otra cosa: **cambiar qué le pide la app a una persona**.

«A Campo Alegre mandale foto del lote y el remito, por mail, dentro de cinco
días» no es un umbral ni una alerta. Es un procedimiento que cambia el
formulario que ve el que está en el depósito con las manos ocupadas.

Reutilizar `requiere_aprobacion` sería mentir: eso significa «no lo ejecutes
sin un OK», y eso ya es cierto de todo reclamo. Los requisitos concretos viajan
en `params`, que ya es un dict libre que cada motor lee con su propia clave
(cuentas lee `tolerancia_dias`, depósito lee `umbral_pct`) — así que el efecto
nuevo no necesita ni una columna ni una tabla, sólo un valor más en el
catálogo.

El catálogo vive en dos lados y los dos tienen que decir lo mismo: este CHECK
y `core/conocimiento.py::EFECTOS`.
"""
from alembic import op

revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None

_NOMBRE = "business_knowledge_pieces_efecto_check"
_VIEJOS = ("ajusta_umbral", "suprime_alerta", "genera_alerta",
           "contexto_para_angela", "requiere_aprobacion")
_NUEVOS = _VIEJOS + ("exige_evidencia",)


def _lista(valores) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def upgrade() -> None:
    op.drop_constraint(_NOMBRE, "business_knowledge_pieces", type_="check")
    op.create_check_constraint(_NOMBRE, "business_knowledge_pieces",
                               f"efecto IN ({_lista(_NUEVOS)})")


def downgrade() -> None:
    # Las filas con el efecto nuevo tienen que irse antes de angostar el
    # catálogo, o la restricción no puede volver a crearse.
    op.execute("DELETE FROM business_knowledge_pieces "
               "WHERE efecto = 'exige_evidencia'")
    op.drop_constraint(_NOMBRE, "business_knowledge_pieces", type_="check")
    op.create_check_constraint(_NOMBRE, "business_knowledge_pieces",
                               f"efecto IN ({_lista(_VIEJOS)})")
