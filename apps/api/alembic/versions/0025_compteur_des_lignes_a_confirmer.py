"""`import_batch.needs_decision_rows` — LOT 9, `T7`, `MVP-L09-US004` (2/2).

LE DEFAUT TROUVE EN CONSTRUISANT `T7`, AVANT TOUT CODE DE SERVICE

  `T1` posait quatre compteurs sur `import_batch` — `total_rows`, `valid_rows`,
  `warning_rows`, `rejected_rows` — calques sur les QUATRE termes de la
  reconciliation POST-import du modele §19 (`criteres-qualite-import.md` §4 :
  `total = creations + mises_a_jour + rejets + en_attente_de_decision`, lu la
  AVEC les etats APRES import). Mais `import_row.state` compte SIX valeurs
  (modele §19.2), et la PREVISUALISATION (cahier §9.5 point 3, AVANT tout
  import) doit deja distinguer une ligne `needs_decision` d'une ligne
  `rejected` — `T7` est la PREMIERE sous-etape a produire des lignes
  `needs_decision` (`D-PERSONNE-001`, `D-PERSONNE-002`, `D-PERSONNE-003`), et
  aucune colonne ne pouvait les compter : `total_rows` aurait depasse la somme
  des trois autres sans qu'aucune colonne n'explique l'ecart.

  Mesure avant d'ecrire cette migration : zero colonne nommee `needs_decision`
  ou equivalent sur `import_batch`, dans le modele comme dans le schema reel.

Revision ID: 0025
Revises: 0024
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#  **LA CONTRAINTE EST RECREEE SOUS LE MEME NOM** — `ck_import_batch_
#  comptes_non_negatifs` — plutot que d'en ajouter une seconde : une colonne
#  de plus dans une contrainte EXISTANTE, pas une regle nouvelle.
NOM_CONTRAINTE = "ck_import_batch_comptes_non_negatifs"
EXPRESSION_ANCIENNE = (
    "total_rows >= 0 AND valid_rows >= 0 AND warning_rows >= 0 AND rejected_rows >= 0"
)
EXPRESSION_NOUVELLE = (
    "total_rows >= 0 AND valid_rows >= 0 AND warning_rows >= 0 "
    "AND needs_decision_rows >= 0 AND rejected_rows >= 0"
)


def upgrade() -> None:
    op.drop_constraint(op.f(NOM_CONTRAINTE), "import_batch", type_="check")
    op.add_column(
        "import_batch",
        sa.Column("needs_decision_rows", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.create_check_constraint(op.f(NOM_CONTRAINTE), "import_batch", EXPRESSION_NOUVELLE)


def downgrade() -> None:
    op.drop_constraint(op.f(NOM_CONTRAINTE), "import_batch", type_="check")
    op.drop_column("import_batch", "needs_decision_rows")
    op.create_check_constraint(op.f(NOM_CONTRAINTE), "import_batch", EXPRESSION_ANCIENNE)
