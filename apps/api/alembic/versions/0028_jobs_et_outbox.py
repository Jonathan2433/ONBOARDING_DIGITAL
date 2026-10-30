"""Le socle asynchrone du LOT 11 — modele §20.1 et §20.2 — `T1`.

La migration pose `async_job` et `outbox_message`. Elle ne pose PAS
`scheduled_task_run` (modele §20.3) : aucune des trois stories de `T1`
(`US001`, `US002`, `US003`) ne la nomme, et le §20.3 ne donne d'ailleurs aucune
liste de champs — seulement une liste de taches et la phrase « un verrou
PostgreSQL ou distribue garantit une seule execution logique ». Inventer ses
colonnes maintenant serait le defaut §6.5 de la passation. Elle sera posee a
`T4`, quand le verrou et son historique seront reellement construits.

`async_job.idempotency_key` est UNIQUE dans son PERIMETRE — lu comme
`(job_type, idempotency_key)`, le modele ne precisant pas lequel : un meme
jeton peut legitimement designer un envoi d'e-mail ET un export distincts.

`outbox_message` ne porte aucun `entity_id` : le §20.2 n'en liste aucun parmi
ses champs, meme lecture que `operational_alert`/`export_request` au LOT 10.
Son index unique de deduplication est PARTIEL — `WHERE processed_at IS NULL`
— pour que la meme cle puisse etre reutilisee une fois le message traite, et
ne bloque que les messages encore EN ATTENTE.

Revision ID: 0028
Revises: 0027
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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


def upgrade() -> None:
    # -----------------------------------------------------------------------
    #  §20.1 — `async_job`. `entity_id` NULLABLE : « job global ».
    # -----------------------------------------------------------------------
    op.create_table(
        "async_job",
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column(
            "state", sa.String(length=16), server_default=sa.text("'queued'"), nullable=False
        ),
        sa.Column("progress_current", sa.Integer(), nullable=True),
        sa.Column("progress_total", sa.Integer(), nullable=True),
        sa.Column("requested_by_person_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("5"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        #  Polymorphe, comme `audit_event.resource_reference` (LOT 10) : aucune
        #  cle etrangere unique ne pourrait couvrir un export, un media ou un
        #  import a la fois.
        sa.Column("result_reference", sa.Uuid(), nullable=True),
        *_champs_communs(),
        sa.CheckConstraint(
            "job_type IN ('import', 'media', 'export', 'purge', 'email', 'maintenance')",
            name=op.f("ck_async_job_job_type_valide"),
        ),
        sa.CheckConstraint(
            "state IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name=op.f("ck_async_job_state_valide"),
        ),
        sa.CheckConstraint(
            "length(btrim(idempotency_key)) > 0", name=op.f("ck_async_job_idempotency_key_non_vide")
        ),
        sa.CheckConstraint("attempt_count >= 0", name=op.f("ck_async_job_attempt_count_positif")),
        sa.CheckConstraint("max_attempts > 0", name=op.f("ck_async_job_max_attempts_positif")),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entity.id"], name=op.f("fk_async_job_entity_id_entity")
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_person_id"],
            ["person.id"],
            name=op.f("fk_async_job_requested_by_person_id_person"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_async_job")),
        sa.UniqueConstraint(
            "job_type", "idempotency_key", name=op.f("uq_async_job_job_type_idempotency_key")
        ),
    )
    op.create_index(op.f("ix_async_job_entity_id"), "async_job", ["entity_id"], unique=False)
    op.create_index(
        op.f("ix_async_job_requested_by_person_id"),
        "async_job",
        ["requested_by_person_id"],
        unique=False,
    )
    op.create_index(op.f("ix_async_job_state"), "async_job", ["state"], unique=False)
    #  Sert `T4` : « detection des jobs bloques » lit les jobs `running` dont le
    #  dernier battement est trop ancien. L'index est pose ici, avec la table,
    #  plutot que d'attendre la sous-etape qui le consomme.
    op.create_index(
        op.f("ix_async_job_last_heartbeat_at"), "async_job", ["last_heartbeat_at"], unique=False
    )

    # -----------------------------------------------------------------------
    #  §20.2 — `outbox_message`. GLOBALE : le §20.2 ne liste aucun `entity_id`.
    # -----------------------------------------------------------------------
    op.create_table(
        "outbox_message",
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_error_code", sa.Text(), nullable=True),
        sa.Column("deduplication_key", sa.Text(), nullable=True),
        *_champs_communs(),
        sa.CheckConstraint(
            "length(btrim(topic)) > 0", name=op.f("ck_outbox_message_topic_non_vide")
        ),
        sa.CheckConstraint(
            "attempt_count >= 0", name=op.f("ck_outbox_message_attempt_count_positif")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_message")),
    )
    #  Le relais interroge « processed_at IS NULL AND available_at <= :instant » :
    #  l'index composite sert directement cette requete.
    op.create_index(
        "ix_outbox_message_a_relayer",
        "outbox_message",
        ["processed_at", "available_at"],
        unique=False,
    )
    #  PARTIELLE : une cle de deduplication ne bloque que tant que le message
    #  qui la porte n'est pas encore traite — voir l'en-tete du module.
    op.create_index(
        "uq_outbox_message_deduplication_key_en_attente",
        "outbox_message",
        ["deduplication_key"],
        unique=True,
        postgresql_where=sa.text("processed_at IS NULL AND deduplication_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_table("outbox_message")
    op.drop_table("async_job")
