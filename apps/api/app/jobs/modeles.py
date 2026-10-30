"""Les deux tables du socle asynchrone — modele §20.1 et §20.2 — `T1`.

FONDEMENT — modele §20.1 `async_job`, §20.2 `outbox_message`. Champs communs
du §3.1.

CE QUE CE MODULE POSE, ET CE QU'IL NE POSE PAS

  Il pose les deux tables, avec les champs communs du §3.1. Il ne pose pas
  `scheduled_task_run` (§20.3) : aucune des trois stories de `T1` ne la nomme,
  et le §20.3 ne donne d'ailleurs aucune liste de champs — voir la migration
  `0028` pour le detail. Elle sera posee a `T4`.

  Il ne pose aucun service ni aucun acteur Dramatiq : la logique d'execution
  idempotente vit dans `app/jobs/execution.py`, la publication dans l'outbox
  dans `app/jobs/outbox.py`, le fournisseur d'e-mail dans `app/jobs/email.py`.
  Les acteurs Dramatiq eux-memes vivent dans `apps/worker/worker/actors.py` —
  c'est le worker, pas l'API, qui possede le courtier et le cycle de vie des
  messages.

PAS `RessourceLocale`

  `async_job.entity_id` est NULLABLE par le modele lui-meme (« job global »).
  Meme motif qu'`audit_event` au LOT 10 : une cle COMPOSITE vers une table dont
  `entity_id` est nullable serait rendue inerte par `MATCH SIMPLE` des qu'un
  job global se produit.

  `outbox_message` ne porte AUCUN `entity_id` : le §20.2 n'en liste aucun
  parmi ses champs — meme lecture qu'`operational_alert`/`export_request` au
  LOT 10, un message technique n'etant pas un fait D'UNE entite.

`idempotency_key` UNIQUE DANS SON PERIMETRE, LU COMME `(job_type, idempotency_key)`

  Le modele ecrit « Unique dans son perimetre » sans nommer ce perimetre. Un
  meme jeton d'idempotence peut legitimement designer un envoi d'e-mail ET un
  export distincts ; le borner au seul `job_type` est la lecture la plus
  etroite qui n'interdit rien que le modele n'interdit pas lui-meme.

`result_reference`, PAS `result_id`

  Meme defaut que `audit_event.resource_id` au LOT 10 (§7.25 de la passation,
  rejoue en connaissance de cause) : une colonne polymorphe — un job peut
  produire un export, un media, ou rien — ne peut porter aucune cle etrangere
  unique. Le nom ne finit donc pas par `_id`, pour ne jamais laisser croire au
  controle d'isolation qu'il en manque une.
"""

from __future__ import annotations

import datetime as dt
import enum
import uuid
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.modele import Base, ChampsCommuns, contrainte_enumeration


class TypeDeJob(enum.StrEnum):
    """§20.1 : « Import, media, export, purge, e-mail, maintenance »."""

    IMPORT = "import"
    MEDIA = "media"
    EXPORT = "export"
    PURGE = "purge"
    EMAIL = "email"
    MAINTENANCE = "maintenance"


TYPES_DE_JOB: tuple[str, ...] = tuple(membre.value for membre in TypeDeJob)


class EtatDuJob(enum.StrEnum):
    """§20.1 : les cinq etats fermes du modele."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


ETATS_DU_JOB: tuple[str, ...] = tuple(membre.value for membre in EtatDuJob)

#  Defaut technique, jamais nomme par le modele ni par une story : un job qui
#  echoue sans borne retenterait indefiniment. Cinq essais, comme les defauts
#  de retenue habituels de ce depot (`DRAMATIQ_QUEUES`, etc.) — une valeur
#  raisonnable, pas une decision produit.
MAX_TENTATIVES_PAR_DEFAUT = 5


class AsyncJob(ChampsCommuns, Base):
    """La source durable de suivi des traitements — modele §20.1."""

    __tablename__ = "async_job"

    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text(f"'{EtatDuJob.QUEUED.value}'"), index=True
    )
    progress_current: Mapped[int | None] = mapped_column(Integer, nullable=True)
    progress_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requested_by_person_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text(str(MAX_TENTATIVES_PAR_DEFAUT))
    )
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    #  PAS `result_id` : voir l'en-tete du module.
    result_reference: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    __table_args__ = (
        contrainte_enumeration("job_type", TypeDeJob, "ck_async_job_job_type_valide"),
        contrainte_enumeration("state", EtatDuJob, "ck_async_job_state_valide"),
        CheckConstraint(
            "length(btrim(idempotency_key)) > 0", name="ck_async_job_idempotency_key_non_vide"
        ),
        CheckConstraint("attempt_count >= 0", name="ck_async_job_attempt_count_positif"),
        CheckConstraint("max_attempts > 0", name="ck_async_job_max_attempts_positif"),
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(["requested_by_person_id"], ["person.id"]),
        UniqueConstraint("job_type", "idempotency_key"),
    )


class OutboxMessage(ChampsCommuns, Base):
    """Message technique enregistre dans la meme transaction que l'action metier — §20.2.

    GLOBALE, voir l'en-tete du module. `topic` est un vocabulaire OUVERT : le
    §20.2 l'ecrit en PROSE (« envoi d'e-mail, generation de media, recalcul de
    progression, notification de supervision, preparation d'export »), jamais
    backticke — meme lecture qu'`operational_alert.source` au LOT 10. Une
    chaine non vide, jamais une enumeration inventee.
    """

    __tablename__ = "outbox_message"

    topic: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    available_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    processed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    deduplication_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("length(btrim(topic)) > 0", name="ck_outbox_message_topic_non_vide"),
        CheckConstraint("attempt_count >= 0", name="ck_outbox_message_attempt_count_positif"),
        Index("ix_outbox_message_a_relayer", "processed_at", "available_at"),
        #  PARTIELLE, voir l'en-tete du module et la migration `0028`.
        Index(
            "uq_outbox_message_deduplication_key_en_attente",
            "deduplication_key",
            unique=True,
            postgresql_where=text("processed_at IS NULL AND deduplication_key IS NOT NULL"),
        ),
    )
