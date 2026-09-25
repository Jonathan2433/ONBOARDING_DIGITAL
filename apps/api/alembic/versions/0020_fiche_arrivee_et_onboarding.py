"""La fiche d'arrivee et l'onboarding — modele §12.1 et §13 — LOT 7, `T1`.

Stories `MVP-L07-US001` a `US008` : toutes en dependent. Mesure du 25/09/2026
sur le schema reel : **39 tables**, `alembic_version` comprise, avant cette
migration 31 (32 moins `alembic_version`).

CE QUE CETTE MIGRATION POSE

  `arrival_profile` (§12.1) et six tables d'onboarding (§13.1 a §13.7).
  `photo_authorization` (LOT 5, migration `0014`) N'EST PAS TOUCHEE.

CE QU'ALEMBIC AVAIT PROPOSE EN PLUS, ET QUI A ETE RETIRE

  `alembic revision --autogenerate` a de nouveau propose :

      op.drop_index(op.f('ix_person_recherche_nom'), table_name='person')

  **C'est le MEME faux positif que `T1` du LOT 6** : un index sur EXPRESSION,
  pose en SQL brut par la migration `0015`, qu'autogenerate ne sait pas
  reconcilier. Voir `0017_tables_editoriales.py` pour le detail complet — le
  test qui le nomme desormais l'aurait fait tomber si cette ligne etait restee.

Revision ID: 0020
Revises: 0019
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


#  Les champs communs du §3.1, SANS `entity_id` — pour les tables GLOBALES ou
#  dont l'entite est portee ailleurs. Voir le module `app/onboarding/modeles.py`
#  pour le detail de qui recoit laquelle des trois formes.
def _champs_communs() -> tuple[sa.Column[Any], ...]:
    return (
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
    )


#  Les memes, AVEC `entity_id` NOT NULL — pour les tables locales EN SUBSTANCE.
def _champs_communs_locaux() -> tuple[sa.Column[Any], ...]:
    return (*_champs_communs(), sa.Column("entity_id", sa.Uuid(), nullable=False))


def upgrade() -> None:
    # -----------------------------------------------------------------------
    #  §12.1 — `arrival_profile`
    # -----------------------------------------------------------------------
    op.create_table(
        "arrival_profile",
        sa.Column("entity_membership_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=16), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("short_intro", sa.Text(), nullable=True),
        sa.Column("fun_fact", sa.Text(), nullable=True),
        sa.Column("photo_media_id", sa.Uuid(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recent_until", sa.Date(), nullable=True),
        *_champs_communs_locaux(),
        sa.CheckConstraint(
            "state IN ('draft', 'validated', 'published', 'archived')",
            name=op.f("ck_arrival_profile_state_valide"),
        ),
        #  `IS NOT NULL` explicite : `length(btrim(NULL))` rend NULL, et une
        #  CHECK dont l'expression rend NULL est SATISFAITE. Voir le module.
        sa.CheckConstraint(
            "state = 'draft' OR (short_intro IS NOT NULL AND length(btrim(short_intro)) > 0)",
            name=op.f("ck_arrival_profile_short_intro_requis_hors_brouillon"),
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_arrival_profile_entity_id_entity")
        ),
        sa.ForeignKeyConstraint(
            ["entity_membership_id", "entity_id"],
            ["entity_membership.id", "entity_membership.entity_id"],
            name="fk_arrival_profile_entity_membership",
        ),
        #  `media_asset.entity_id` est TOUJOURS NOT NULL : la cle composite est
        #  pleinement fiable, MATCH SIMPLE ne se derobe que si `photo_media_id`
        #  lui-meme est NULL — le comportement voulu pour une photo facultative.
        sa.ForeignKeyConstraint(
            ["photo_media_id", "entity_id"],
            ["media_asset.id", "media_asset.entity_id"],
            name="fk_arrival_profile_media_asset",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_arrival_profile")),
        #  §6.2 : une fiche par appartenance — jamais partielle, une fiche
        #  archivee garde son unicite.
        sa.UniqueConstraint("entity_membership_id", name="uq_arrival_profile_entity_membership_id"),
        sa.UniqueConstraint("id", "entity_id", name=op.f("uq_arrival_profile_id_entity_id")),
    )
    op.create_index(
        op.f("ix_arrival_profile_entity_id"), "arrival_profile", ["entity_id"], unique=False
    )
    op.create_index(
        op.f("ix_arrival_profile_entity_membership_id"),
        "arrival_profile",
        ["entity_membership_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_arrival_profile_photo_media_id"),
        "arrival_profile",
        ["photo_media_id"],
        unique=False,
    )

    # -----------------------------------------------------------------------
    #  §13.1 — `onboarding_task_reference`. PAS de `RessourceLocale` :
    #  `entity_id` est NULLABLE, pour la tache GLOBALE.
    # -----------------------------------------------------------------------
    op.create_table(
        "onboarding_task_reference",
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_champs_communs(),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_onboarding_task_reference_entity_id_entity")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_onboarding_task_reference")),
    )
    op.create_index(
        op.f("ix_onboarding_task_reference_entity_id"),
        "onboarding_task_reference",
        ["entity_id"],
        unique=False,
    )
    #  §13.1 : « stable et unique DANS SON PERIMETRE ». `entity_id` nullable
    #  interdit une unicite simple — NULL n'est jamais egal a NULL. Deux index
    #  PARTIELS, un par perimetre.
    op.create_index(
        "uq_onboarding_task_reference_entity_code_non_archive",
        "onboarding_task_reference",
        ["entity_id", "code"],
        unique=True,
        postgresql_where=sa.text("entity_id IS NOT NULL AND archived_at IS NULL"),
    )
    op.create_index(
        "uq_onboarding_task_reference_code_globale_non_archive",
        "onboarding_task_reference",
        ["code"],
        unique=True,
        postgresql_where=sa.text("entity_id IS NULL AND archived_at IS NULL"),
    )

    # -----------------------------------------------------------------------
    #  §13.2 — `onboarding_template`. PAS de `RessourceLocale`, meme motif.
    # -----------------------------------------------------------------------
    op.create_table(
        "onboarding_template",
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("target_status", sa.String(length=16), nullable=False),
        sa.Column("scope_type", sa.String(length=16), nullable=False),
        sa.Column("scope_person_id", sa.Uuid(), nullable=True),
        sa.Column("scope_circle_id", sa.Uuid(), nullable=True),
        sa.Column("state", sa.String(length=16), server_default=sa.text("'draft'"), nullable=False),
        *_champs_communs(),
        sa.CheckConstraint(
            "target_status IN ('mission', 'intercontract')",
            name=op.f("ck_onboarding_template_target_status_valide"),
        ),
        sa.CheckConstraint(
            "scope_type IN ('GLOBAL', 'ENTITY', 'DSM', 'CIRCLE')",
            name=op.f("ck_onboarding_template_scope_type_valide"),
        ),
        sa.CheckConstraint(
            "state IN ('draft', 'active', 'archived')",
            name=op.f("ck_onboarding_template_state_valide"),
        ),
        #  §13.2, les quatre contraintes du modele, DERIVEES en une seule
        #  implication par portee — voir le module pour le detail.
        sa.CheckConstraint(
            "(scope_type = 'GLOBAL' AND entity_id IS NULL"
            " AND scope_person_id IS NULL AND scope_circle_id IS NULL)"
            " OR (scope_type = 'ENTITY' AND entity_id IS NOT NULL"
            " AND scope_person_id IS NULL AND scope_circle_id IS NULL)"
            " OR (scope_type = 'DSM' AND entity_id IS NOT NULL"
            " AND scope_person_id IS NOT NULL AND scope_circle_id IS NULL)"
            " OR (scope_type = 'CIRCLE' AND entity_id IS NOT NULL"
            " AND scope_circle_id IS NOT NULL AND scope_person_id IS NULL)",
            name=op.f("ck_onboarding_template_colonnes_de_portee_selon_scope_type"),
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_onboarding_template_entity_id_entity")
        ),
        sa.ForeignKeyConstraint(
            ["scope_person_id"],
            ["person.id"],
            name=op.f("fk_onboarding_template_scope_person_id_person"),
        ),
        #  SIMPLE : `make isolation-check` exige `entity_id` NOT NULL a la
        #  SOURCE pour toute cle composite, sans condition — cette table est
        #  nullable. Voir le module `app/onboarding/modeles.py`.
        sa.ForeignKeyConstraint(
            ["scope_circle_id"],
            ["circle.id"],
            name=op.f("fk_onboarding_template_scope_circle_id_circle"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_onboarding_template")),
    )
    op.create_index(
        op.f("ix_onboarding_template_entity_id"), "onboarding_template", ["entity_id"], unique=False
    )
    op.create_index(
        op.f("ix_onboarding_template_scope_person_id"),
        "onboarding_template",
        ["scope_person_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_onboarding_template_scope_circle_id"),
        "onboarding_template",
        ["scope_circle_id"],
        unique=False,
    )

    # -----------------------------------------------------------------------
    #  §13.3 — `onboarding_template_version`. Pas d'`entity_id` propre : elle
    #  herite sa portee de `onboarding_template`, dont l'`entity_id` est
    #  nullable — une cle composite ici serait INERTE sous MATCH SIMPLE des
    #  qu'un modele est global. Voir le module.
    # -----------------------------------------------------------------------
    op.create_table(
        "onboarding_template_version",
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=16), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by_person_id", sa.Uuid(), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        *_champs_communs(),
        sa.CheckConstraint(
            "state IN ('draft', 'active', 'archived')",
            name=op.f("ck_onboarding_template_version_state_valide"),
        ),
        sa.CheckConstraint(
            "version_number > 0", name=op.f("ck_onboarding_template_version_version_number_positif")
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["onboarding_template.id"],
            name=op.f("fk_onboarding_template_version_template_id_onboarding_template"),
        ),
        sa.ForeignKeyConstraint(
            ["published_by_person_id"],
            ["person.id"],
            name=op.f("fk_onboarding_template_version_published_by_person_id_person"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_onboarding_template_version")),
        sa.UniqueConstraint(
            "template_id", "version_number", name="uq_onboarding_template_version_number"
        ),
    )
    op.create_index(
        op.f("ix_onboarding_template_version_template_id"),
        "onboarding_template_version",
        ["template_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_onboarding_template_version_published_by_person_id"),
        "onboarding_template_version",
        ["published_by_person_id"],
        unique=False,
    )

    # -----------------------------------------------------------------------
    #  §13.4 — `onboarding_template_task`. Meme motif que la version : pas
    #  d'`entity_id` propre.
    # -----------------------------------------------------------------------
    op.create_table(
        "onboarding_template_task",
        sa.Column("template_version_id", sa.Uuid(), nullable=False),
        sa.Column("task_reference_id", sa.Uuid(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("required", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("due_offset_days", sa.Integer(), nullable=False),
        sa.Column("title_override", sa.Text(), nullable=True),
        sa.Column("description_override", sa.Text(), nullable=True),
        *_champs_communs(),
        sa.CheckConstraint(
            "display_order >= 0", name=op.f("ck_onboarding_template_task_ordre_positif")
        ),
        #  NOMS EXPLICITES COURTS : la convention par defaut concatene table,
        #  colonne et table visee et depasse 63 octets sur ces deux cles.
        sa.ForeignKeyConstraint(
            ["template_version_id"],
            ["onboarding_template_version.id"],
            name="fk_onboarding_template_task_onboarding_template_version",
        ),
        sa.ForeignKeyConstraint(
            ["task_reference_id"],
            ["onboarding_task_reference.id"],
            name="fk_onboarding_template_task_onboarding_task_reference",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_onboarding_template_task")),
    )
    op.create_index(
        op.f("ix_onboarding_template_task_template_version_id"),
        "onboarding_template_task",
        ["template_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_onboarding_template_task_task_reference_id"),
        "onboarding_template_task",
        ["task_reference_id"],
        unique=False,
    )
    #  §25.1 « notamment » : deux taches de meme rang rendraient l'affichage
    #  non deterministe — meme motif que `content_block` au LOT 6.
    op.create_index(
        "uq_onboarding_template_task_version_ordre_non_archive",
        "onboarding_template_task",
        ["template_version_id", "display_order"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL"),
    )

    # -----------------------------------------------------------------------
    #  §13.5 — `onboarding_instance`
    # -----------------------------------------------------------------------
    op.create_table(
        "onboarding_instance",
        sa.Column("entity_membership_id", sa.Uuid(), nullable=False),
        sa.Column("template_version_id", sa.Uuid(), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column(
            "state", sa.String(length=16), server_default=sa.text("'active'"), nullable=False
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_instance_id", sa.Uuid(), nullable=True),
        sa.Column("replacement_reason", sa.Text(), nullable=True),
        *_champs_communs_locaux(),
        sa.CheckConstraint(
            "state IN ('active', 'completed', 'archived', 'replaced')",
            name=op.f("ck_onboarding_instance_state_valide"),
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_onboarding_instance_entity_id_entity")
        ),
        sa.ForeignKeyConstraint(
            ["entity_membership_id", "entity_id"],
            ["entity_membership.id", "entity_membership.entity_id"],
            name="fk_onboarding_instance_entity_membership",
        ),
        #  SIMPLE, et non composite : `onboarding_template_version` n'a pas
        #  d'`entity_id`. Voir l'en-tete de la migration.
        sa.ForeignKeyConstraint(
            ["template_version_id"],
            ["onboarding_template_version.id"],
            name="fk_onboarding_instance_onboarding_template_version",
        ),
        #  COMPOSITE : les deux cotes sont `onboarding_instance`, dont
        #  `entity_id` est TOUJOURS NOT NULL — aucun piege MATCH SIMPLE, et
        #  §2.5 exige que le remplacement reste dans la MEME entite.
        sa.ForeignKeyConstraint(
            ["replaced_by_instance_id", "entity_id"],
            ["onboarding_instance.id", "onboarding_instance.entity_id"],
            name="fk_onboarding_instance_onboarding_instance_replacement",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_onboarding_instance")),
        sa.UniqueConstraint("id", "entity_id", name=op.f("uq_onboarding_instance_id_entity_id")),
    )
    op.create_index(
        op.f("ix_onboarding_instance_entity_id"), "onboarding_instance", ["entity_id"], unique=False
    )
    op.create_index(
        op.f("ix_onboarding_instance_entity_membership_id"),
        "onboarding_instance",
        ["entity_membership_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_onboarding_instance_template_version_id"),
        "onboarding_instance",
        ["template_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_onboarding_instance_replaced_by_instance_id"),
        "onboarding_instance",
        ["replaced_by_instance_id"],
        unique=False,
    )
    #  §13.5 : « une SEULE instance active par appartenance » — meme motif
    #  exact que `uq_entity_membership_person_id_occupante` au LOT 2.
    op.create_index(
        "uq_onboarding_instance_membership_active",
        "onboarding_instance",
        ["entity_membership_id"],
        unique=True,
        postgresql_where=sa.text("state = 'active'"),
    )

    # -----------------------------------------------------------------------
    #  §13.6 — `onboarding_instance_task`
    # -----------------------------------------------------------------------
    op.create_table(
        "onboarding_instance_task",
        sa.Column("onboarding_instance_id", sa.Uuid(), nullable=False),
        sa.Column("task_reference_id", sa.Uuid(), nullable=False),
        sa.Column("title_snapshot", sa.Text(), nullable=False),
        sa.Column("description_snapshot", sa.Text(), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(length=16), server_default=sa.text("'todo'"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by_person_id", sa.Uuid(), nullable=True),
        sa.Column("reopened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reopened_by_person_id", sa.Uuid(), nullable=True),
        sa.Column("reopen_reason", sa.Text(), nullable=True),
        *_champs_communs_locaux(),
        sa.CheckConstraint(
            "state IN ('todo', 'completed', 'reopened', 'cancelled')",
            name=op.f("ck_onboarding_instance_task_state_valide"),
        ),
        #  Matrice §8.3, a la lettre : « La reouverture EXIGE un motif ».
        sa.CheckConstraint(
            "reopened_at IS NULL OR reopen_reason IS NOT NULL",
            name=op.f("ck_onboarding_instance_task_motif_requis_a_la_reouverture"),
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_onboarding_instance_task_entity_id_entity")
        ),
        sa.ForeignKeyConstraint(
            ["onboarding_instance_id", "entity_id"],
            ["onboarding_instance.id", "onboarding_instance.entity_id"],
            name="fk_onboarding_instance_task_onboarding_instance",
        ),
        #  SIMPLE : `onboarding_task_reference.entity_id` est nullable.
        sa.ForeignKeyConstraint(
            ["task_reference_id"],
            ["onboarding_task_reference.id"],
            name="fk_onboarding_instance_task_onboarding_task_reference",
        ),
        sa.ForeignKeyConstraint(
            ["completed_by_person_id"],
            ["person.id"],
            name=op.f("fk_onboarding_instance_task_completed_by_person_id_person"),
        ),
        sa.ForeignKeyConstraint(
            ["reopened_by_person_id"],
            ["person.id"],
            name=op.f("fk_onboarding_instance_task_reopened_by_person_id_person"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_onboarding_instance_task")),
        sa.UniqueConstraint(
            "id", "entity_id", name=op.f("uq_onboarding_instance_task_id_entity_id")
        ),
        sa.UniqueConstraint(
            "onboarding_instance_id",
            "task_reference_id",
            name="uq_onboarding_instance_task_reference",
        ),
    )
    op.create_index(
        op.f("ix_onboarding_instance_task_entity_id"),
        "onboarding_instance_task",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_onboarding_instance_task_onboarding_instance_id"),
        "onboarding_instance_task",
        ["onboarding_instance_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_onboarding_instance_task_task_reference_id"),
        "onboarding_instance_task",
        ["task_reference_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_onboarding_instance_task_completed_by_person_id"),
        "onboarding_instance_task",
        ["completed_by_person_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_onboarding_instance_task_reopened_by_person_id"),
        "onboarding_instance_task",
        ["reopened_by_person_id"],
        unique=False,
    )

    # -----------------------------------------------------------------------
    #  §13.7 — `onboarding_task_event`. Colonnes DERIVEES du role decrit en
    #  prose ; meme nature que `auth_event` (LOT 3). Voir le module.
    # -----------------------------------------------------------------------
    op.create_table(
        "onboarding_task_event",
        sa.Column("onboarding_instance_task_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor_person_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        *_champs_communs_locaux(),
        sa.CheckConstraint(
            "event_type IN ('ASSIGNED', 'COMPLETED', 'CANCELLED', 'REOPENED', "
            "'RETAINED_ON_REPLACEMENT', 'CANCELLED_ON_REPLACEMENT')",
            name=op.f("ck_onboarding_task_event_event_type_valide"),
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_onboarding_task_event_entity_id_entity")
        ),
        sa.ForeignKeyConstraint(
            ["onboarding_instance_task_id", "entity_id"],
            ["onboarding_instance_task.id", "onboarding_instance_task.entity_id"],
            name="fk_onboarding_task_event_onboarding_instance_task",
        ),
        sa.ForeignKeyConstraint(
            ["actor_person_id"],
            ["person.id"],
            name=op.f("fk_onboarding_task_event_actor_person_id_person"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_onboarding_task_event")),
    )
    op.create_index(
        op.f("ix_onboarding_task_event_entity_id"),
        "onboarding_task_event",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_onboarding_task_event_onboarding_instance_task_id"),
        "onboarding_task_event",
        ["onboarding_instance_task_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_onboarding_task_event_occurred_at"),
        "onboarding_task_event",
        ["occurred_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_onboarding_task_event_actor_person_id"),
        "onboarding_task_event",
        ["actor_person_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("onboarding_task_event")
    op.drop_table("onboarding_instance_task")
    op.drop_index("uq_onboarding_instance_membership_active", table_name="onboarding_instance")
    op.drop_table("onboarding_instance")
    op.drop_index(
        "uq_onboarding_template_task_version_ordre_non_archive",
        table_name="onboarding_template_task",
    )
    op.drop_table("onboarding_template_task")
    op.drop_table("onboarding_template_version")
    op.drop_table("onboarding_template")
    op.drop_index(
        "uq_onboarding_task_reference_code_globale_non_archive",
        table_name="onboarding_task_reference",
    )
    op.drop_index(
        "uq_onboarding_task_reference_entity_code_non_archive",
        table_name="onboarding_task_reference",
    )
    op.drop_table("onboarding_task_reference")
    op.drop_table("arrival_profile")
