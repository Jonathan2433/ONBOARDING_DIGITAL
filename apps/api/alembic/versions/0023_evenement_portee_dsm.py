"""La cinquieme table evenementielle, `event_dsm_scope` — `ECART-067`, `DEC-622`.

La matrice §11 donne au DSM deux portees de creation, « Entite ou consultants »,
et le modele §17.2 n'en representait que trois : entite entiere, cercle, bureau.
Cette migration ajoute la portee manquante sans toucher les quatre tables
posees par `0022` : une seule ligne non archivee par evenement, portant
directement le DSM (`dsm_person_id`, cle simple vers `person.id`, meme choix
que `dsm_assignment.dsm_person_id` au modele §8.5).

Revision ID: 0023
Revises: 0022
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _champs_communs_locaux() -> tuple[sa.Column[Any], ...]:
    """Champs communs du §3.1 et rattachement local obligatoire."""

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
        sa.Column("entity_id", sa.Uuid(), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "event_dsm_scope",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("dsm_person_id", sa.Uuid(), nullable=False),
        *_champs_communs_locaux(),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entity.id"],
            name=op.f("fk_event_dsm_scope_entity_id_entity"),
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "entity_id"],
            ["event.id", "event.entity_id"],
            name="fk_event_dsm_scope_event",
        ),
        sa.ForeignKeyConstraint(
            ["dsm_person_id"],
            ["person.id"],
            name=op.f("fk_event_dsm_scope_dsm_person_id_person"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_event_dsm_scope")),
        sa.UniqueConstraint("id", "entity_id", name=op.f("uq_event_dsm_scope_id_entity_id")),
    )
    op.create_index(
        op.f("ix_event_dsm_scope_entity_id"), "event_dsm_scope", ["entity_id"], unique=False
    )
    op.create_index(
        op.f("ix_event_dsm_scope_event_id"), "event_dsm_scope", ["event_id"], unique=False
    )
    op.create_index(
        op.f("ix_event_dsm_scope_dsm_person_id"),
        "event_dsm_scope",
        ["dsm_person_id"],
        unique=False,
    )
    op.create_index(
        "uq_event_dsm_scope_event_non_archive",
        "event_dsm_scope",
        ["event_id"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_event_dsm_scope_event_non_archive", table_name="event_dsm_scope")
    op.drop_table("event_dsm_scope")
