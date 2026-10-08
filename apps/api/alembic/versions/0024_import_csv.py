"""Les quatre tables de l'import CSV — modele §19 — LOT 9, `T1`.

La migration pose `import_batch`, `import_row`, `import_row_issue` et
`import_decision`. Les trois tables dependantes repetent `entity_id` afin que
leurs cles etrangeres composites ferment les quatre chemins de fuite
inter-entites du §25.3.

Elle ne pose volontairement ni `async_job` ni `outbox_message` : l'import reste
SYNCHRONE (`DEC-462`), confirme par Jonathan le 08/10/2026 ; ces deux tables
restent reservees au LOT 11.

Revision ID: 0024
Revises: 0023
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024"
down_revision: str | None = "0023"
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
        "import_batch",
        sa.Column("source_filename", sa.Text(), nullable=False),
        sa.Column("source_object_key", sa.Text(), nullable=True),
        sa.Column("source_checksum_sha256", sa.Text(), nullable=False),
        sa.Column(
            "state", sa.String(length=16), server_default=sa.text("'uploaded'"), nullable=False
        ),
        sa.Column("total_rows", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("valid_rows", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("warning_rows", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("rejected_rows", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("approved_by_person_id", sa.Uuid(), nullable=True),
        *_champs_communs_locaux(),
        sa.CheckConstraint(
            "state IN ('uploaded', 'analyzing', 'preview_ready', 'approved', 'importing', "
            "'completed', 'failed', 'cancelled')",
            name=op.f("ck_import_batch_state_valide"),
        ),
        sa.CheckConstraint(
            "total_rows >= 0 AND valid_rows >= 0 AND warning_rows >= 0 AND rejected_rows >= 0",
            name=op.f("ck_import_batch_comptes_non_negatifs"),
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_import_batch_entity_id_entity")
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_person_id"],
            ["person.id"],
            name=op.f("fk_import_batch_approved_by_person_id_person"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_batch")),
        sa.UniqueConstraint("id", "entity_id", name=op.f("uq_import_batch_id_entity_id")),
    )
    op.create_index(op.f("ix_import_batch_entity_id"), "import_batch", ["entity_id"], unique=False)
    op.create_index(
        op.f("ix_import_batch_approved_by_person_id"),
        "import_batch",
        ["approved_by_person_id"],
        unique=False,
    )
    op.create_index(
        "ix_import_batch_entity_state", "import_batch", ["entity_id", "state"], unique=False
    )

    op.create_table(
        "import_row",
        sa.Column("import_batch_id", sa.Uuid(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("raw_data", postgresql.JSONB(), nullable=False),
        sa.Column("normalized_data", postgresql.JSONB(), nullable=True),
        sa.Column("state", sa.String(length=16), server_default=sa.text("'valid'"), nullable=False),
        sa.Column("target_person_id", sa.Uuid(), nullable=True),
        sa.Column("target_membership_id", sa.Uuid(), nullable=True),
        sa.Column(
            "error_codes", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False
        ),
        *_champs_communs_locaux(),
        sa.CheckConstraint(
            "state IN ('valid', 'warning', 'needs_decision', 'rejected', 'imported', 'updated')",
            name=op.f("ck_import_row_state_valide"),
        ),
        sa.CheckConstraint("row_number > 0", name=op.f("ck_import_row_numero_de_ligne_positif")),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_import_row_entity_id_entity")
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id", "entity_id"],
            ["import_batch.id", "import_batch.entity_id"],
            name="fk_import_row_import_batch",
        ),
        sa.ForeignKeyConstraint(
            ["target_person_id"], ["person.id"], name=op.f("fk_import_row_target_person_id_person")
        ),
        sa.ForeignKeyConstraint(
            ["target_membership_id", "entity_id"],
            ["entity_membership.id", "entity_membership.entity_id"],
            name="fk_import_row_entity_membership",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_row")),
        sa.UniqueConstraint("id", "entity_id", name=op.f("uq_import_row_id_entity_id")),
    )
    op.create_index(op.f("ix_import_row_entity_id"), "import_row", ["entity_id"], unique=False)
    op.create_index(
        op.f("ix_import_row_import_batch_id"), "import_row", ["import_batch_id"], unique=False
    )
    op.create_index(
        op.f("ix_import_row_target_person_id"), "import_row", ["target_person_id"], unique=False
    )
    op.create_index(
        op.f("ix_import_row_target_membership_id"),
        "import_row",
        ["target_membership_id"],
        unique=False,
    )
    op.create_index(
        "ix_import_row_entity_state", "import_row", ["entity_id", "state"], unique=False
    )
    op.create_index(
        "uq_import_row_batch_numero",
        "import_row",
        ["import_batch_id", "row_number"],
        unique=True,
    )

    op.create_table(
        "import_row_issue",
        sa.Column("import_row_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("field", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=False),
        sa.Column("normalized_value_safe", sa.Text(), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        *_champs_communs_locaux(),
        sa.CheckConstraint(
            "length(btrim(code)) > 0", name=op.f("ck_import_row_issue_code_non_vide")
        ),
        sa.CheckConstraint(
            "length(btrim(level)) > 0", name=op.f("ck_import_row_issue_niveau_non_vide")
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_import_row_issue_entity_id_entity")
        ),
        sa.ForeignKeyConstraint(
            ["import_row_id", "entity_id"],
            ["import_row.id", "import_row.entity_id"],
            name="fk_import_row_issue_import_row",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_row_issue")),
        sa.UniqueConstraint("id", "entity_id", name=op.f("uq_import_row_issue_id_entity_id")),
    )
    op.create_index(
        op.f("ix_import_row_issue_entity_id"), "import_row_issue", ["entity_id"], unique=False
    )
    op.create_index(
        op.f("ix_import_row_issue_import_row_id"),
        "import_row_issue",
        ["import_row_id"],
        unique=False,
    )

    op.create_table(
        "import_decision",
        sa.Column("import_row_id", sa.Uuid(), nullable=False),
        sa.Column("decision_type", sa.String(length=32), nullable=False),
        sa.Column("target_person_id", sa.Uuid(), nullable=True),
        sa.Column("target_client_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        *_champs_communs_locaux(),
        sa.CheckConstraint(
            "decision_type IN ('person_merge', 'profile_reactivation', "
            "'client_alias_creation', 'canonical_client_selection', 'voluntary_rejection')",
            name=op.f("ck_import_decision_decision_type_valide"),
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_import_decision_entity_id_entity")
        ),
        sa.ForeignKeyConstraint(
            ["import_row_id", "entity_id"],
            ["import_row.id", "import_row.entity_id"],
            name="fk_import_decision_import_row",
        ),
        sa.ForeignKeyConstraint(
            ["target_person_id"],
            ["person.id"],
            name=op.f("fk_import_decision_target_person_id_person"),
        ),
        sa.ForeignKeyConstraint(
            ["target_client_id"],
            ["client.id"],
            name=op.f("fk_import_decision_target_client_id_client"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_decision")),
        sa.UniqueConstraint("id", "entity_id", name=op.f("uq_import_decision_id_entity_id")),
    )
    op.create_index(
        op.f("ix_import_decision_entity_id"), "import_decision", ["entity_id"], unique=False
    )
    op.create_index(
        op.f("ix_import_decision_import_row_id"),
        "import_decision",
        ["import_row_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_decision_target_person_id"),
        "import_decision",
        ["target_person_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_decision_target_client_id"),
        "import_decision",
        ["target_client_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("import_decision")
    op.drop_table("import_row_issue")
    op.drop_table("import_row")
    op.drop_table("import_batch")
