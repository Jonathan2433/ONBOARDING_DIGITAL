"""Les quatre tables evenementielles — modele §17 — LOT 8, `T1`.

La migration pose `event`, `event_circle_scope`, `event_office_scope` et
`event_media`. Les trois relations repetent `entity_id` afin que leurs cles
etrangeres composites ferment les six chemins de fuite inter-entites du §25.3.

Elle ne pose volontairement ni recurrence, ni participant, ni inscription, ni
presence, ni notification metier. L'etat « passe » n'est pas stocke : le §17.1
le derive de `ends_at`.

Revision ID: 0022
Revises: 0021
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
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
        "event",
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location_text", sa.Text(), nullable=True),
        sa.Column("state", sa.String(length=16), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        *_champs_communs_locaux(),
        sa.CheckConstraint(
            "state IN ('draft', 'published', 'cancelled', 'archived')",
            name=op.f("ck_event_state_valide"),
        ),
        sa.CheckConstraint("starts_at < ends_at", name=op.f("ck_event_chronologie_valide")),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_event_entity_id_entity")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_event")),
        sa.UniqueConstraint("id", "entity_id", name=op.f("uq_event_id_entity_id")),
    )
    op.create_index(op.f("ix_event_entity_id"), "event", ["entity_id"], unique=False)
    op.create_index("ix_event_entity_starts_at", "event", ["entity_id", "starts_at"], unique=False)
    op.create_index("ix_event_entity_ends_at", "event", ["entity_id", "ends_at"], unique=False)
    op.create_index("ix_event_entity_state", "event", ["entity_id", "state"], unique=False)

    op.create_table(
        "event_circle_scope",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("circle_id", sa.Uuid(), nullable=False),
        *_champs_communs_locaux(),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entity.id"],
            name=op.f("fk_event_circle_scope_entity_id_entity"),
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "entity_id"],
            ["event.id", "event.entity_id"],
            name="fk_event_circle_scope_event",
        ),
        sa.ForeignKeyConstraint(
            ["circle_id", "entity_id"],
            ["circle.id", "circle.entity_id"],
            name="fk_event_circle_scope_circle",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_event_circle_scope")),
        sa.UniqueConstraint("id", "entity_id", name=op.f("uq_event_circle_scope_id_entity_id")),
    )
    op.create_index(
        op.f("ix_event_circle_scope_entity_id"),
        "event_circle_scope",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_event_circle_scope_event_id"),
        "event_circle_scope",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_event_circle_scope_circle_id"),
        "event_circle_scope",
        ["circle_id"],
        unique=False,
    )
    op.create_index(
        "uq_event_circle_scope_event_circle_non_archive",
        "event_circle_scope",
        ["event_id", "circle_id"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL"),
    )

    op.create_table(
        "event_office_scope",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("office_id", sa.Uuid(), nullable=False),
        *_champs_communs_locaux(),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entity.id"],
            name=op.f("fk_event_office_scope_entity_id_entity"),
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "entity_id"],
            ["event.id", "event.entity_id"],
            name="fk_event_office_scope_event",
        ),
        sa.ForeignKeyConstraint(
            ["office_id", "entity_id"],
            ["office.id", "office.entity_id"],
            name="fk_event_office_scope_office",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_event_office_scope")),
        sa.UniqueConstraint("id", "entity_id", name=op.f("uq_event_office_scope_id_entity_id")),
    )
    op.create_index(
        op.f("ix_event_office_scope_entity_id"),
        "event_office_scope",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_event_office_scope_event_id"),
        "event_office_scope",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_event_office_scope_office_id"),
        "event_office_scope",
        ["office_id"],
        unique=False,
    )
    op.create_index(
        "uq_event_office_scope_event_office_non_archive",
        "event_office_scope",
        ["event_id", "office_id"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL"),
    )

    op.create_table(
        "event_media",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("media_asset_id", sa.Uuid(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("display_role", sa.String(length=32), nullable=False),
        *_champs_communs_locaux(),
        sa.CheckConstraint("display_order >= 0", name=op.f("ck_event_media_ordre_positif")),
        sa.CheckConstraint(
            "length(btrim(display_role)) > 0",
            name=op.f("ck_event_media_role_affichage_non_vide"),
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_event_media_entity_id_entity")
        ),
        sa.ForeignKeyConstraint(
            ["event_id", "entity_id"],
            ["event.id", "event.entity_id"],
            name="fk_event_media_event",
        ),
        sa.ForeignKeyConstraint(
            ["media_asset_id", "entity_id"],
            ["media_asset.id", "media_asset.entity_id"],
            name="fk_event_media_media_asset",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_event_media")),
        sa.UniqueConstraint("id", "entity_id", name=op.f("uq_event_media_id_entity_id")),
    )
    op.create_index(op.f("ix_event_media_entity_id"), "event_media", ["entity_id"], unique=False)
    op.create_index(op.f("ix_event_media_event_id"), "event_media", ["event_id"], unique=False)
    op.create_index(
        op.f("ix_event_media_media_asset_id"),
        "event_media",
        ["media_asset_id"],
        unique=False,
    )
    op.create_index(
        "uq_event_media_event_ordre_non_archive",
        "event_media",
        ["event_id", "display_order"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_event_media_event_ordre_non_archive", table_name="event_media")
    op.drop_table("event_media")
    op.drop_index("uq_event_office_scope_event_office_non_archive", table_name="event_office_scope")
    op.drop_table("event_office_scope")
    op.drop_index("uq_event_circle_scope_event_circle_non_archive", table_name="event_circle_scope")
    op.drop_table("event_circle_scope")
    op.drop_table("event")
