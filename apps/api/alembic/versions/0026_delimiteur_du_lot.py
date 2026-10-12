"""`import_batch.delimiter` — LOT 9, `T10`, `MVP-L09-US006` (2/2).

LE RESIDU NOMME PAR `T6`, CORRIGE ICI

  Le separateur du CSV est detecte par `_detecter_le_delimiteur` (`DEC-432`)
  depuis `T6`, mais n'a jamais ete PERSISTE : l'en-tete de `app.imports.depot`
  le disait deja explicitement — "`criteres-qualite-import.md` §4 l'exige
  aux cotes de l'empreinte SHA-256 dans LE RAPPORT D'IMPORT, qui est construit
  par `T10` : le consigner relevait donc de cette sous-etape-la, nomme
  explicitement ici pour ne pas perdre le residu." Mesure avant d'ecrire
  cette migration : zero colonne nommee `delimiter` ou equivalent sur
  `import_batch`, dans le modele comme dans le schema reel.

  NULLABLE : les lots deposes avant cette migration (aucun n'existe en dehors
  des tests, qui ne persistent rien au-dela de leur propre transaction
  annulee) n'ont jamais eu ce separateur consigne — inventer une valeur pour
  eux serait une hypothese, pas une mesure (§6.5).

  La contrainte `IN (';', ',')` n'est pas une regle de plus : c'est `DEC_432`
  lui-meme (`app.imports.depot._DELIMITEUR_PAR_DEFAUT`/`_DELIMITEUR_TOLERE`),
  les deux SEULES valeurs que `_detecter_le_delimiteur` peut jamais rendre.

Revision ID: 0026
Revises: 0025
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOM_CONTRAINTE = "ck_import_batch_delimiter_connu"
EXPRESSION = "delimiter IS NULL OR delimiter IN (';', ',')"


def upgrade() -> None:
    op.add_column("import_batch", sa.Column("delimiter", sa.Text(), nullable=True))
    op.create_check_constraint(op.f(NOM_CONTRAINTE), "import_batch", EXPRESSION)


def downgrade() -> None:
    op.drop_constraint(op.f(NOM_CONTRAINTE), "import_batch", type_="check")
    op.drop_column("import_batch", "delimiter")
