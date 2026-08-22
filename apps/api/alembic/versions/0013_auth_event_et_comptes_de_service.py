"""Le lien `auth_event` -> `service_account` que le diagramme §11 declare.

Revision : 0013
Precedente : 0012
Creee le : 2026-08-22

CE QUE CETTE MIGRATION CORRIGE, ET POURQUOI CE N'EST PAS UNE INVENTION

  Le diagramme du modele §11 declare **`SERVICE_ACCOUNT ||--o{ AUTH_EVENT :
  produces`**. La table posee par `T2` ne porte que `person_id` et
  `user_account_id` : **le lien vers le compte de service manque**. C'est
  `ECART-037`, constate en `T10`.

  Ajouter la colonne, c'est donc **implementer le modele**, pas l'etendre. Et sans
  elle, le critere de `US007` -- « chaque appel est audite » -- serait
  insatisfaisable sans inventer un huitieme type d'evenement, ce que le §10.6
  interdit : il en declare **sept**, et `T12` auditera exactement ces sept.

  **LES DEUX TYPES EMPLOYES SONT DONC CEUX QUI EXISTENT** : `LOGIN_SUCCESS` quand
  un jeton de service est accepte, `LOGIN_FAILURE` quand il est refuse. Le §10.6
  les nomme « succes » et « echec » sans les restreindre aux humains, et le §11
  place bien `service_account` en producteur d'evenements.

UNE CONTRAINTE DE COHERENCE, ET UNE SEULE

  `ck_auth_event_un_seul_acteur` : un evenement ne peut pas porter **a la fois**
  une personne et un compte de service. Les deux nuls restent permis, et c'est
  **indispensable** -- un magic link demande pour une adresse inconnue, ou un jeton
  inconnu refuse, ne designe personne. `T3`, `T4` et `T9` en produisent, et une
  contrainte qui l'interdirait casserait la reponse generique.

  Aucune autre contrainte : le §10.6 n'en ecrit aucune, et en poser serait exiger
  plus que le modele -- §7.20.

PAS D'`autogenerate` ICI

  `DEC-500` : c'est un brouillon. Sur une colonne unique avec sa cle etrangere, son
  index et sa contrainte, l'ecrire a la main est plus court que de relire son
  brouillon -- et la contrainte de coherence, il ne l'aurait pas devinee.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("auth_event", sa.Column("service_account_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_auth_event_service_account_id"),
        "auth_event",
        ["service_account_id"],
    )
    op.create_foreign_key(
        "fk_auth_event_service_account_id_service_account",
        "auth_event",
        "service_account",
        ["service_account_id"],
        ["id"],
    )
    op.create_check_constraint(
        "ck_auth_event_un_seul_acteur",
        "auth_event",
        "person_id IS NULL OR service_account_id IS NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_auth_event_un_seul_acteur", "auth_event", type_="check")
    op.drop_constraint(
        "fk_auth_event_service_account_id_service_account", "auth_event", type_="foreignkey"
    )
    op.drop_index(op.f("ix_auth_event_service_account_id"), table_name="auth_event")
    op.drop_column("auth_event", "service_account_id")
