"""`scheduled_task_run` — modele §20.3 — `T4`, story `MVP-L11-US006`.

POURQUOI « EXPIRATION DES LIENS » ET « SESSIONS » NE FONT QU'UNE TACHE

  Le §20.3 les cite separement dans sa liste, mais les deux relevent du MEME
  geste d'hygiene -- marquer `invalidated_at`/`revoked_at` sur ce qui est deja
  expire par sa propre colonne (`magic_link_request.expires_at`,
  `user_session.absolute_expires_at`, l'inactivite calculee sur
  `last_activity_at`, `service_token.expires_at`) -- sur deux familles de
  tables soeurs du meme domaine (LOT 3). Les separer en deux taches aurait
  double le verrou pour un seul mecanisme.

LE VERROU EST L'INDEX UNIQUE PARTIEL, PAS UNE COLONNE DE PLUS

  « Une seule execution logique » (§20.3) est tenue par
  `uq_scheduled_task_run_task_name_en_cours` : au plus une ligne `running` par
  `task_name`. Meme garantie qu'un `pg_advisory_lock` nommerait, sans
  connexion tenue ouverte pendant tout le cycle -- voir `migration 0029`.

CE MODULE NE CONTIENT AUCUNE LOGIQUE DE TACHE

  Le cycle de vie (demarrer/reussir/echouer) vit dans
  `app.scheduling.execution`, exactement le decoupage deja pose par
  `app.jobs.modeles`/`app.jobs.execution` pour `async_job` -- reutilise, pas
  invente une seconde fois (§7.27).
"""

from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.modele import Base, ChampsCommuns, contrainte_enumeration


class NomDeTachePlanifiee(enum.StrEnum):
    """Les six taches du §20.3, vocabulaire FERME — voir l'en-tete du module."""

    EXPIRATION_LIENS_SESSIONS = "expiration_liens_sessions"
    EVENEMENTS_PASSES = "evenements_passes"
    ANONYMISATION_APRES_DEPART = "anonymisation_apres_depart"
    PURGE_AUDIT = "purge_audit"
    DETECTION_JOBS_BLOQUES = "detection_jobs_bloques"
    NETTOYAGE_MEDIAS = "nettoyage_medias"


NOMS_DE_TACHE_PLANIFIEE: tuple[str, ...] = tuple(membre.value for membre in NomDeTachePlanifiee)


class EtatDeLaTachePlanifiee(enum.StrEnum):
    """Trois etats, aucune reprise automatique au-dela du prochain cycle."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


ETATS_DE_LA_TACHE_PLANIFIEE: tuple[str, ...] = tuple(
    membre.value for membre in EtatDeLaTachePlanifiee
)


class ScheduledTaskRun(ChampsCommuns, Base):
    """Historique des executions periodiques — modele §20.3."""

    __tablename__ = "scheduled_task_run"

    task_name: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    items_processed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        #  **LE NOM NE PORTE PAS SON PREFIXE** : la convention de nommage du
        #  socle l'ajoute (`ck_%(table_name)s_%(constraint_name)s`). Un nom
        #  deja prefixe produirait un DOUBLE prefixe — defaut deja documente
        #  dans `app.media.modeles` (`photo_authorization`), rejoue ici et
        #  corrige avant commit grace a `test_aucun_nom_de_contrainte_du_
        #  modele_ne_depasse_la_limite`.
        contrainte_enumeration("task_name", NomDeTachePlanifiee, "task_name_valide"),
        contrainte_enumeration("state", EtatDeLaTachePlanifiee, "state_valide"),
        CheckConstraint(
            "items_processed IS NULL OR items_processed >= 0",
            name="items_processed_positif",
        ),
        #  LE VERROU, voir l'en-tete du module.
        Index(
            "uq_scheduled_task_run_task_name_en_cours",
            "task_name",
            unique=True,
            postgresql_where=text("state = 'running'"),
        ),
        Index(
            "ix_scheduled_task_run_task_name_started_at",
            "task_name",
            "started_at",
        ),
    )
