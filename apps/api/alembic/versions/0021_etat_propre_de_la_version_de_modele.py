"""La version d'un modele recoit sa PROPRE enumeration — LOT 7, `T5`.

CE QUE CETTE MIGRATION CORRIGE, ET POURQUOI CE N'EST PAS UNE MODIFICATION DE `0020`

  Le modele §13.2 donne au CONTENEUR (`onboarding_template`) les valeurs
  `draft`/`active`/`archived`. Le §13.3 donne a SA VERSION
  (`onboarding_template_version`) les valeurs `draft`/`published`/`retired` --
  une enumeration DIFFERENTE, sur une table voisine. `0020` (`T1`) avait
  reutilise `EtatDuModele` -- celle du conteneur -- pour les DEUX tables, un
  defaut trouve en relisant le §13 en preparant `T4` (compte-rendu `T4`, §2.6)
  et nomme pour `T5`, non bloquant a l'epoque : `onboarding_task_reference` ne
  touche ni l'une ni l'autre.

  **Bloquant pour `T5`, en revanche** : le temoin d'immuabilite de cette
  sous-etape exige qu'une version `published` refuse toute ecriture -- et la
  contrainte HERITEE DE `0020` REFUSAIT `published` elle-meme, avant meme
  qu'un ecrivain n'existe. `0020` est deja APPLIQUEE : une migration deja
  appliquee ne se modifie jamais, elle se corrige par une NOUVELLE (`CLAUDE.md`
  §7, regle n°10 de fait). D'ou `0021`.

  Aucune ligne n'existe encore dans `onboarding_template_version` -- mesure le
  26/09/2026, `T2` a `T4` n'ecrivent ni l'une ni l'autre table -- la nouvelle
  contrainte ne rejette donc aucune donnee existante.

Revision ID: 0021
Revises: 0020
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#  Meme idiome que `0019` : le nom EST le nom final, `op.f()` ne le prefixe pas
#  une seconde fois.
NOM: str = "ck_onboarding_template_version_state_valide"


def upgrade() -> None:
    op.drop_constraint(op.f(NOM), "onboarding_template_version", type_="check")
    op.create_check_constraint(
        op.f(NOM), "onboarding_template_version", "state IN ('draft', 'published', 'retired')"
    )


def downgrade() -> None:
    op.drop_constraint(op.f(NOM), "onboarding_template_version", type_="check")
    op.create_check_constraint(
        op.f(NOM), "onboarding_template_version", "state IN ('draft', 'active', 'archived')"
    )
