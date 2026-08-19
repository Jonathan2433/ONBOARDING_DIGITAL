"""Historisation : rendre les contraintes d'exclusion autoportantes.

LOT 2, sous-etape `T9`, story `MVP-L02-US004`.
Revision : 0010
Revision precedente : 0009

FONDEMENT — modele §25.2, les SEPT relations a contrainte temporelle.

**CETTE SOUS-ETAPE NE CREE AUCUNE TABLE.** Les sept relations existent depuis `T4`
a `T8`. `T9` devait les COMPTER et prouver que le chevauchement est rejete par la
BASE -- et le controle qu'elle a pose a trouve un defaut le jour meme.

CE QUE LE CONTROLE A TROUVE, ET QU'AUCUN TEST N'AVAIT VU

  `technical_role_assignment` portait une exclusion dont la cle incluait
  `entity_id`. Or `entity_id` est NUL pour un `SUPER_ADMIN` -- le §8.6 l'exige --
  et **l'operateur `=` ne rapproche jamais deux NULL**. Deux `SUPER_ADMIN` de la
  meme personne aux periodes qui se chevauchent **n'auraient PAS ete detectes**.

  C'est exactement le defaut `T8-1`, dans une table ou je croyais l'avoir traite :
  j'avais corrige `framework_responsibility_assignment` et pas celle-ci. **Une
  correction appliquee a la main table par table en oublie une.** Le controle
  mecanique, lui, les a toutes examinees.

ET UN ANGLE MORT D'`alembic check`, MESURE

  Avec 10 exclusions declarees dans le modele et 9 en base, `alembic check` a
  repondu « **No new upgrade operations detected** », code 0.

  **`alembic check` est AVEUGLE aux contraintes d'exclusion.** Il ne les compare
  pas, et `autogenerate` n'a produit pour cette migration qu'un `pass`. C'est une
  precision importante sur `DEC-500` : `autogenerate` REND fidelement une exclusion
  quand il cree la table, mais il ne la COMPARE jamais ensuite.

  Consequence : `make historisation-check` est le SEUL controle du depot qui
  detecte une derive d'exclusion. C'est ce qui justifie son existence.

  Il exige une base **migree**, donc il n'entre ni dans `make check`, qui est
  statique, ni dans `make stack-check`, que l'integration continue lance AVANT
  `make migrate` -- les tables n'y existent pas encore. Il est appele par la tache
  « stack » de la CI **juste apres les migrations**, et reste une cible autonome en
  local.

  Le placement a demande deux rectifications de cet en-tete, et c'est instructif :
  un controle qui depend de l'etat de la base ne se range pas ou l'on croit.

CE QUE CETTE MIGRATION FAIT

  1. **Scinde** l'exclusion de `technical_role_assignment` en deux exclusions
     PARTIELLES, chacune sur une cle sans colonne nullable ;
  2. **Rend autoportantes** les clauses `WHERE` des deux exclusions de
     `framework_responsibility_assignment` qui portent une colonne nullable, par un
     `IS NOT NULL` explicite.

  Le second point est une REDONDANCE assumee : `portee_selon_le_type` garantit deja
  la non-nullite. Mais **une contrainte dont la justesse depend d'une AUTRE
  contrainte est fragile**, et le controle exige desormais la forme explicite --
  sans heuristique. Ma premiere version du controle toleraient toute clause
  mentionnant `responsibility_type`, ce qui etait une heuristique dans un controle.

RETOUR ARRIERE. La descente retablit exactement les exclusions de `0009`, y compris
celle qui portait le defaut : une descente doit rendre l'etat precedent, pas un
etat ameliore.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    #  1. `technical_role_assignment` : une exclusion aveugle aux
    #     `SUPER_ADMIN`, remplacee par DEUX exclusions partielles.
    # ------------------------------------------------------------------
    op.execute(
        "ALTER TABLE technical_role_assignment "
        "DROP CONSTRAINT ex_technical_role_assignment_sans_chevauchement"
    )
    op.execute(
        "ALTER TABLE technical_role_assignment ADD CONSTRAINT "
        "ex_technical_role_assignment_entity_admin "
        "EXCLUDE USING gist (person_id WITH =, role_type WITH =, entity_id WITH =, "
        "period WITH &&) "
        "WHERE (role_type = 'ENTITY_ADMIN' AND entity_id IS NOT NULL)"
    )
    op.execute(
        "ALTER TABLE technical_role_assignment ADD CONSTRAINT "
        "ex_technical_role_assignment_super_admin "
        "EXCLUDE USING gist (person_id WITH =, role_type WITH =, period WITH &&) "
        "WHERE (role_type = 'SUPER_ADMIN')"
    )

    # ------------------------------------------------------------------
    #  2. `framework_responsibility_assignment` : clauses `WHERE` rendues
    #     autoportantes par un `IS NOT NULL` explicite.
    # ------------------------------------------------------------------
    op.execute(
        "ALTER TABLE framework_responsibility_assignment "
        "DROP CONSTRAINT ex_framework_responsibility_assignment_booster"
    )
    op.execute(
        "ALTER TABLE framework_responsibility_assignment ADD CONSTRAINT "
        "ex_framework_responsibility_assignment_booster "
        "EXCLUDE USING gist (person_id WITH =, circle_id WITH =, period WITH &&) "
        "WHERE (responsibility_type = 'BOOSTER' AND circle_id IS NOT NULL)"
    )
    op.execute(
        "ALTER TABLE framework_responsibility_assignment "
        "DROP CONSTRAINT ex_framework_responsibility_assignment_office_manager"
    )
    op.execute(
        "ALTER TABLE framework_responsibility_assignment ADD CONSTRAINT "
        "ex_framework_responsibility_assignment_office_manager "
        "EXCLUDE USING gist (person_id WITH =, office_id WITH =, period WITH &&) "
        "WHERE (responsibility_type = 'OFFICE_MANAGER' AND office_id IS NOT NULL)"
    )


def downgrade() -> None:
    #  Retablir EXACTEMENT les exclusions de `0009`, defaut compris : une descente
    #  rend l'etat precedent, pas un etat ameliore.
    op.execute(
        "ALTER TABLE framework_responsibility_assignment "
        "DROP CONSTRAINT ex_framework_responsibility_assignment_office_manager"
    )
    op.execute(
        "ALTER TABLE framework_responsibility_assignment ADD CONSTRAINT "
        "ex_framework_responsibility_assignment_office_manager "
        "EXCLUDE USING gist (person_id WITH =, office_id WITH =, period WITH &&) "
        "WHERE (responsibility_type = 'OFFICE_MANAGER')"
    )
    op.execute(
        "ALTER TABLE framework_responsibility_assignment "
        "DROP CONSTRAINT ex_framework_responsibility_assignment_booster"
    )
    op.execute(
        "ALTER TABLE framework_responsibility_assignment ADD CONSTRAINT "
        "ex_framework_responsibility_assignment_booster "
        "EXCLUDE USING gist (person_id WITH =, circle_id WITH =, period WITH &&) "
        "WHERE (responsibility_type = 'BOOSTER')"
    )
    op.execute(
        "ALTER TABLE technical_role_assignment "
        "DROP CONSTRAINT ex_technical_role_assignment_super_admin"
    )
    op.execute(
        "ALTER TABLE technical_role_assignment "
        "DROP CONSTRAINT ex_technical_role_assignment_entity_admin"
    )
    op.execute(
        "ALTER TABLE technical_role_assignment ADD CONSTRAINT "
        "ex_technical_role_assignment_sans_chevauchement "
        "EXCLUDE USING gist (person_id WITH =, role_type WITH =, entity_id WITH =, "
        "period WITH &&)"
    )
