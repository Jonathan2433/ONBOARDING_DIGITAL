"""Les six tables du LOT 10 — modele §21 et §22.3 — `T1`.

La migration pose `audit_event`, `operational_alert`, `alert_comment`,
`bug_report`, `export_request` et `data_subject_request`. Elle ne pose
volontairement ni `retention_action` ni `privacy_notice_version`/
`privacy_notice_acknowledgement` (modele §22.1, §22.2, §22.4) : aucune des
huit stories du LOT 10 ne les nomme.

`audit_event` porte un `entity_id` NULLABLE (evenement global) ; `bug_report`
seule recoit `entity_id` NOT NULL (`RessourceLocale`) ; les quatre autres
tables n'en portent aucun. Voir `app/audit/modeles.py` pour le detail complet
des choix et des deux vocabulaires ouverts (`operational_alert.source`,
`data_subject_request.state`).

Revision ID: 0027
Revises: 0026
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


#  Les champs communs du §3.1, SANS `entity_id` — pour les tables GLOBALES.
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


#  Les memes, AVEC `entity_id` NOT NULL — pour `bug_report` seule.
def _champs_communs_locaux() -> tuple[sa.Column[Any], ...]:
    return (*_champs_communs(), sa.Column("entity_id", sa.Uuid(), nullable=False))


def upgrade() -> None:
    # -----------------------------------------------------------------------
    #  §21.1 — `audit_event`. PAS de `RessourceLocale` : `entity_id` nullable.
    # -----------------------------------------------------------------------
    op.create_table(
        "audit_event",
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("actor_person_id", sa.Uuid(), nullable=True),
        sa.Column("actor_service_account_id", sa.Uuid(), nullable=True),
        sa.Column("action_code", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_reference", sa.Uuid(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("old_values", postgresql.JSONB(), nullable=True),
        sa.Column("new_values", postgresql.JSONB(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("correlation_token", sa.Text(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "retention_until",
            sa.DateTime(timezone=True),
            server_default=sa.text("(now() + interval '1 year')"),
            nullable=False,
        ),
        *_champs_communs(),
        sa.CheckConstraint(
            "length(btrim(action_code)) > 0", name=op.f("ck_audit_event_action_code_non_vide")
        ),
        sa.CheckConstraint(
            "length(btrim(resource_type)) > 0", name=op.f("ck_audit_event_resource_type_non_vide")
        ),
        sa.CheckConstraint(
            "length(btrim(summary)) > 0", name=op.f("ck_audit_event_summary_non_vide")
        ),
        sa.CheckConstraint(
            "length(btrim(correlation_token)) > 0",
            name=op.f("ck_audit_event_correlation_token_non_vide"),
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_audit_event_entity_id_entity")
        ),
        sa.ForeignKeyConstraint(
            ["actor_person_id"], ["person.id"], name=op.f("fk_audit_event_actor_person_id_person")
        ),
        sa.ForeignKeyConstraint(
            ["actor_service_account_id"],
            ["service_account.id"],
            name=op.f("fk_audit_event_actor_service_account_id_service_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_event")),
    )
    op.create_index(op.f("ix_audit_event_entity_id"), "audit_event", ["entity_id"], unique=False)
    op.create_index(
        op.f("ix_audit_event_actor_person_id"), "audit_event", ["actor_person_id"], unique=False
    )
    op.create_index(
        op.f("ix_audit_event_actor_service_account_id"),
        "audit_event",
        ["actor_service_account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_event_resource_reference"),
        "audit_event",
        ["resource_reference"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_event_occurred_at"), "audit_event", ["occurred_at"], unique=False
    )
    op.create_index(
        "ix_audit_event_entity_occurred", "audit_event", ["entity_id", "occurred_at"], unique=False
    )
    op.create_index(
        "ix_audit_event_resource",
        "audit_event",
        ["resource_type", "resource_reference"],
        unique=False,
    )

    # -----------------------------------------------------------------------
    #  §21.2 — `operational_alert`. GLOBALE, aucun `entity_id`.
    # -----------------------------------------------------------------------
    op.create_table(
        "operational_alert",
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=16), server_default=sa.text("'open'"), nullable=False),
        sa.Column("assigned_to_person_id", sa.Uuid(), nullable=True),
        sa.Column(
            "opened_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        *_champs_communs(),
        sa.CheckConstraint(
            "severity IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL')",
            name=op.f("ck_operational_alert_severity_valide"),
        ),
        sa.CheckConstraint(
            "state IN ('open', 'acknowledged', 'resolved')",
            name=op.f("ck_operational_alert_state_valide"),
        ),
        sa.CheckConstraint(
            "length(btrim(source)) > 0", name=op.f("ck_operational_alert_source_non_vide")
        ),
        sa.CheckConstraint(
            "length(btrim(fingerprint)) > 0", name=op.f("ck_operational_alert_fingerprint_non_vide")
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to_person_id"],
            ["person.id"],
            name=op.f("fk_operational_alert_assigned_to_person_id_person"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_operational_alert")),
        sa.UniqueConstraint("fingerprint", name=op.f("uq_operational_alert_fingerprint")),
    )
    op.create_index(
        op.f("ix_operational_alert_assigned_to_person_id"),
        "operational_alert",
        ["assigned_to_person_id"],
        unique=False,
    )

    # -----------------------------------------------------------------------
    #  §21.3 — `alert_comment`. GLOBALE, enfant de `operational_alert`.
    # -----------------------------------------------------------------------
    op.create_table(
        "alert_comment",
        sa.Column("operational_alert_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        *_champs_communs(),
        sa.CheckConstraint(
            "length(btrim(content)) > 0", name=op.f("ck_alert_comment_content_non_vide")
        ),
        sa.ForeignKeyConstraint(
            ["operational_alert_id"],
            ["operational_alert.id"],
            name=op.f("fk_alert_comment_operational_alert_id_operational_alert"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alert_comment")),
    )
    op.create_index(
        op.f("ix_alert_comment_operational_alert_id"),
        "alert_comment",
        ["operational_alert_id"],
        unique=False,
    )

    # -----------------------------------------------------------------------
    #  §21.4 — `bug_report`. SEULE table locale de ce module.
    # -----------------------------------------------------------------------
    op.create_table(
        "bug_report",
        sa.Column("reported_by_person_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=16), server_default=sa.text("'new'"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reproduction_steps", sa.Text(), nullable=True),
        sa.Column("page_path", sa.Text(), nullable=False),
        sa.Column("application_version", sa.Text(), nullable=False),
        sa.Column("environment", sa.String(length=32), nullable=False),
        sa.Column("browser_summary", sa.Text(), nullable=True),
        sa.Column("correlation_token", sa.Text(), nullable=True),
        *_champs_communs_locaux(),
        sa.CheckConstraint(
            "state IN ('new', 'investigating', 'fixed', 'rejected')",
            name=op.f("ck_bug_report_state_valide"),
        ),
        sa.CheckConstraint(
            "length(btrim(description)) > 0", name=op.f("ck_bug_report_description_non_vide")
        ),
        sa.CheckConstraint(
            "length(btrim(page_path)) > 0", name=op.f("ck_bug_report_page_path_non_vide")
        ),
        sa.CheckConstraint(
            "length(btrim(application_version)) > 0",
            name=op.f("ck_bug_report_application_version_non_vide"),
        ),
        sa.CheckConstraint(
            "length(btrim(environment)) > 0", name=op.f("ck_bug_report_environment_non_vide")
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_bug_report_entity_id_entity")
        ),
        sa.ForeignKeyConstraint(
            ["reported_by_person_id"],
            ["person.id"],
            name=op.f("fk_bug_report_reported_by_person_id_person"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bug_report")),
        sa.UniqueConstraint("id", "entity_id", name=op.f("uq_bug_report_id_entity_id")),
    )
    op.create_index(op.f("ix_bug_report_entity_id"), "bug_report", ["entity_id"], unique=False)
    op.create_index(
        op.f("ix_bug_report_reported_by_person_id"),
        "bug_report",
        ["reported_by_person_id"],
        unique=False,
    )

    # -----------------------------------------------------------------------
    #  §21.5 — `export_request`. GLOBALE. Pas de `job_id` : `async_job`
    #  n'existe pas encore (LOT 11), voir le module.
    # -----------------------------------------------------------------------
    op.create_table(
        "export_request",
        sa.Column("export_type", sa.Text(), nullable=False),
        sa.Column("requested_by_person_id", sa.Uuid(), nullable=False),
        sa.Column("normalized_scope", postgresql.JSONB(), nullable=True),
        sa.Column("generated_media_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        *_champs_communs(),
        sa.CheckConstraint(
            "length(btrim(export_type)) > 0", name=op.f("ck_export_request_export_type_non_vide")
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_person_id"],
            ["person.id"],
            name=op.f("fk_export_request_requested_by_person_id_person"),
        ),
        sa.ForeignKeyConstraint(
            ["generated_media_id"],
            ["media_asset.id"],
            name=op.f("fk_export_request_generated_media_id_media_asset"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_export_request")),
    )
    op.create_index(
        op.f("ix_export_request_requested_by_person_id"),
        "export_request",
        ["requested_by_person_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_export_request_generated_media_id"),
        "export_request",
        ["generated_media_id"],
        unique=False,
    )

    # -----------------------------------------------------------------------
    #  §22.3 — `data_subject_request`. GLOBALE.
    # -----------------------------------------------------------------------
    op.create_table(
        "data_subject_request",
        sa.Column("data_subject_person_id", sa.Uuid(), nullable=False),
        sa.Column("request_type", sa.String(length=32), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "identity_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("responsible_person_id", sa.Uuid(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        *_champs_communs(),
        sa.CheckConstraint(
            "request_type IN ('access', 'rectification', 'erasure', 'objection')",
            name=op.f("ck_data_subject_request_request_type_valide"),
        ),
        sa.CheckConstraint(
            "length(btrim(channel)) > 0", name=op.f("ck_data_subject_request_channel_non_vide")
        ),
        sa.CheckConstraint(
            "length(btrim(state)) > 0", name=op.f("ck_data_subject_request_state_non_vide")
        ),
        sa.ForeignKeyConstraint(
            ["data_subject_person_id"],
            ["person.id"],
            name=op.f("fk_data_subject_request_data_subject_person_id_person"),
        ),
        sa.ForeignKeyConstraint(
            ["responsible_person_id"],
            ["person.id"],
            name=op.f("fk_data_subject_request_responsible_person_id_person"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_subject_request")),
    )
    op.create_index(
        op.f("ix_data_subject_request_data_subject_person_id"),
        "data_subject_request",
        ["data_subject_person_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_data_subject_request_responsible_person_id"),
        "data_subject_request",
        ["responsible_person_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("data_subject_request")
    op.drop_table("export_request")
    op.drop_table("bug_report")
    op.drop_table("alert_comment")
    op.drop_table("operational_alert")
    op.drop_table("audit_event")
