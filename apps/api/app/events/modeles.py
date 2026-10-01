"""Les quatre tables evenementielles du modele §17 — LOT 8, `T1`.

CE QUE CE MODULE POSE, ET CE QU'IL NE POSE PAS

  Il pose `event`, `event_circle_scope`, `event_office_scope` et `event_media`,
  toutes locales en substance et protegees par les cles composites du §25.3.
  Il ne pose aucun service ni route : les lectures arrivent en `T2`, les
  ecritures en `T3` a `T6`.

  Une absence de ligne dans les deux tables de portee signifie « toute
  l'entite ». Ajouter `event_dsm_scope` pour combler `ECART-067` inventerait un
  modele que la source ne contient pas ; l'ecart reste donc volontairement
  ouvert jusqu'a `T3`.

CE QUI EST DERIVE, ET CE QUI NE L'EST PAS

  - l'etat « passe » n'existe pas : le §17.1 exige de le calculer depuis
    `ends_at` ;
  - la recurrence, les participants, inscriptions, presences et notifications
    n'ont ni table ni colonne — ils sont hors MVP ;
  - le §17.3 exige un ordre et un role d'affichage, sans donner de vocabulaire
    pour ce role. `display_role` est donc une chaine non vide, jamais une
    enumeration inventee ;
  - l'unicite du rang par evenement rend l'ordre total et deterministe, meme
    parti que `content_block` au LOT 6.
"""

from __future__ import annotations

import datetime as dt
import enum
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.modele import (
    Base,
    ChampsCommuns,
    RessourceLocale,
    contrainte_enumeration,
    nom_cle_composite,
)


class EtatEvenement(enum.StrEnum):
    """§17.1 : les quatre etats metier, sans pseudo-etat « passe »."""

    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


ETATS_EVENEMENT: tuple[str, ...] = tuple(membre.value for membre in EtatEvenement)


class Event(ChampsCommuns, RessourceLocale, Base):
    """Un evenement appartenant a une entite — modele §17.1."""

    __tablename__ = "event"

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'draft'"))
    cancelled_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        contrainte_enumeration("state", EtatEvenement, "state_valide"),
        CheckConstraint("starts_at < ends_at", name="chronologie_valide"),
        #  §26.2 nomme explicitement les deux parcours temporels et l'etat.
        Index("ix_event_entity_starts_at", "entity_id", "starts_at"),
        Index("ix_event_entity_ends_at", "entity_id", "ends_at"),
        Index("ix_event_entity_state", "entity_id", "state"),
        #  §25.3 : cible des trois tables de relation ci-dessous.
        UniqueConstraint("id", "entity_id"),
    )


class EventCircleScope(ChampsCommuns, RessourceLocale, Base):
    """Un cercle destinataire d'un evenement — modele §17.2."""

    __tablename__ = "event_circle_scope"

    event_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    circle_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(
            ["event_id", "entity_id"],
            ["event.id", "event.entity_id"],
            name=nom_cle_composite("event_circle_scope", "event"),
        ),
        ForeignKeyConstraint(
            ["circle_id", "entity_id"],
            ["circle.id", "circle.entity_id"],
            name=nom_cle_composite("event_circle_scope", "circle"),
        ),
        Index(
            "uq_event_circle_scope_event_circle_non_archive",
            "event_id",
            "circle_id",
            unique=True,
            postgresql_where=text("archived_at IS NULL"),
        ),
        UniqueConstraint("id", "entity_id"),
    )


class EventOfficeScope(ChampsCommuns, RessourceLocale, Base):
    """Un bureau destinataire d'un evenement — modele §17.2."""

    __tablename__ = "event_office_scope"

    event_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    office_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(
            ["event_id", "entity_id"],
            ["event.id", "event.entity_id"],
            name=nom_cle_composite("event_office_scope", "event"),
        ),
        ForeignKeyConstraint(
            ["office_id", "entity_id"],
            ["office.id", "office.entity_id"],
            name=nom_cle_composite("event_office_scope", "office"),
        ),
        Index(
            "uq_event_office_scope_event_office_non_archive",
            "event_id",
            "office_id",
            unique=True,
            postgresql_where=text("archived_at IS NULL"),
        ),
        UniqueConstraint("id", "entity_id"),
    )


class EventMedia(ChampsCommuns, RessourceLocale, Base):
    """Un media ordonne et type pour l'affichage d'un evenement — §17.3."""

    __tablename__ = "event_media"

    event_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    media_asset_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    display_role: Mapped[str] = mapped_column(String(32), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        ForeignKeyConstraint(
            ["event_id", "entity_id"],
            ["event.id", "event.entity_id"],
            name=nom_cle_composite("event_media", "event"),
        ),
        ForeignKeyConstraint(
            ["media_asset_id", "entity_id"],
            ["media_asset.id", "media_asset.entity_id"],
            name=nom_cle_composite("event_media", "media_asset"),
        ),
        CheckConstraint("display_order >= 0", name="ordre_positif"),
        CheckConstraint("length(btrim(display_role)) > 0", name="role_affichage_non_vide"),
        Index(
            "uq_event_media_event_ordre_non_archive",
            "event_id",
            "display_order",
            unique=True,
            postgresql_where=text("archived_at IS NULL"),
        ),
        UniqueConstraint("id", "entity_id"),
    )
