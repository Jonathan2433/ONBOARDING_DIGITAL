"""`scheduled_task_run` — modele §20.3 — LOT 11, `T4`, story `MVP-L11-US006`.

La migration pose la table que `T1` avait explicitement laissee de cote
(`0028_jobs_et_outbox.py`) : le §20.3 ne donne aucune liste de champs, et il a
fallu la sous-etape qui construit reellement le verrou pour les choisir.

CE QUE LE §20.3 DIT, MOT POUR MOT

  « Historique des executions periodiques : expiration des liens ; sessions ;
  evenements passes ; anonymisation a trois mois ; purge d'audit a un an ;
  nettoyage ; controle des jobs bloques. Un verrou PostgreSQL ou distribue
  garantit une seule execution logique. »

LE VERROU EST UN INDEX UNIQUE PARTIEL, PAS UN `pg_advisory_lock`

  Le modele laisse le mecanisme ouvert (« PostgreSQL OU distribue »). Ce depot
  en a deja un, eprouve par `async_job`/`outbox_message` (LOT 11 `T1`) :
  qu'une seule ligne porte `state = 'running'` pour un `task_name` donne, a la
  fois. Un `INSERT` qui violerait cela echoue sur la contrainte -- c'est la
  MEME garantie qu'un `pg_advisory_lock` nommerait, sans dependre d'une
  connexion tenue ouverte pendant toute l'execution (§7.27 : reutiliser un
  mecanisme deja prouve plutot que d'en inventer un second).

`task_name` EST UN VOCABULAIRE FERME, PAS OUVERT COMME `outbox_message.topic`

  Le §20.3 enumere une liste PRECISE et FINIE de taches systeme -- ce ne sont
  pas des categories metier extensibles comme `operational_alert.source`, ce
  sont les sept items que cette migration meme construit. Une contrainte de
  verification les ferme, meme discipline que `async_job.job_type`.

AUCUNE COLONNE SUR `person` : L'ANONYMISATION REUTILISE CE QUI EXISTE DEJA

  `person.account_state = 'anonymized'` et `person.anonymized_at` sont poses
  depuis le LOT 2 (`0004_personnes.py`), avec un declencheur
  (`fn_person_anonymisation_terminale`) qui rend l'etat irreversible. Rien
  n'est ajoute ici : `T4` est le premier CONSOMMATEUR de ces colonnes, pas
  leur createur.

Revision ID: 0029
Revises: 0028
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#  Les sept taches du §20.3, dans l'ordre ou le texte les enumere. « expiration
#  des liens » et « sessions » sont UNE seule tache ici (meme mecanisme
#  d'hygiene sur deux tables soeurs du LOT 3), ce qui fait six noms pour sept
#  items du texte -- voir `app/scheduling/modeles.py` pour la justification.
NOMS_DE_TACHE = (
    "expiration_liens_sessions",
    "evenements_passes",
    "anonymisation_apres_depart",
    "purge_audit",
    "detection_jobs_bloques",
    "nettoyage_medias",
)

ETATS_DE_TACHE = ("running", "succeeded", "failed")


def upgrade() -> None:
    op.create_table(
        "scheduled_task_run",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("task_name", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("items_processed", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_person_id", sa.Uuid(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by_person_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by_person_id", sa.Uuid(), nullable=True),
        sa.Column("archive_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "task_name IN (" + ", ".join(f"'{n}'" for n in NOMS_DE_TACHE) + ")",
            name=op.f("ck_scheduled_task_run_task_name_valide"),
        ),
        sa.CheckConstraint(
            "state IN (" + ", ".join(f"'{e}'" for e in ETATS_DE_TACHE) + ")",
            name=op.f("ck_scheduled_task_run_state_valide"),
        ),
        sa.CheckConstraint(
            "items_processed IS NULL OR items_processed >= 0",
            name=op.f("ck_scheduled_task_run_items_processed_positif"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scheduled_task_run")),
    )
    #  LE VERROU : au plus une ligne `running` par tache, a la fois.
    op.create_index(
        "uq_scheduled_task_run_task_name_en_cours",
        "scheduled_task_run",
        ["task_name"],
        unique=True,
        postgresql_where=sa.text("state = 'running'"),
    )
    #  Sert la lecture du dernier passage d'une tache (ex. le point de depart de
    #  l'archivage orphelin, et la pile de controle de T4).
    op.create_index(
        "ix_scheduled_task_run_task_name_started_at",
        "scheduled_task_run",
        ["task_name", "started_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("scheduled_task_run")
