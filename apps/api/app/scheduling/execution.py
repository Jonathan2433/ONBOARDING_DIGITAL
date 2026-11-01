"""Le cycle de vie d'une execution de tache planifiee — modele §20.3 — `T4`.

MEME DECOUPAGE EN TROIS FONCTIONS QU'`app.jobs.execution`, POUR LA MEME RAISON

  `commencer_l_execution` rend `None` quand une execution de la MEME tache est
  deja `running` ailleurs — jamais une exception : ce n'est pas une erreur
  pour l'orchestrateur, c'est le signal qu'il doit sauter cette tache CE
  cycle-ci et la retrouver au prochain (`T4` auto-replanifie toutes les
  `SCHEDULED_TASKS_INTERVAL_MINUTES`).

  Contrairement a `async_job`, il n'y a ni `idempotency_key` ni
  `max_attempts` : une tache planifiee n'est pas demandee par un appelant
  precis avec un jeton d'idempotence — elle est la MEME tache, cycle apres
  cycle, et un echec se rattrape simplement au cycle suivant plutot que par un
  compteur de tentatives.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import TYPE_CHECKING, Final

from psycopg import errors as erreurs_psycopg
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

_COLONNES: Final = (
    "id, task_name, state, started_at, finished_at, items_processed, error_message, version"
)

#  `INSERT` direct, jamais `ON CONFLICT` : le verrou EST l'echec de cet
#  `INSERT` quand une ligne `running` existe deja pour cette tache
#  (`uq_scheduled_task_run_task_name_en_cours`). Un `ON CONFLICT DO NOTHING`
#  masquerait cette violation au lieu de la laisser refuser l'insertion.
_COMMENCER: Final = text(
    "INSERT INTO scheduled_task_run "  # noqa: S608
    "(task_name, state, started_at, created_at, updated_at) "
    "VALUES (:tache, 'running', :instant, :instant, :instant) "
    f"RETURNING {_COLONNES}"
)

_TERMINER_AVEC_SUCCES: Final = text(
    "UPDATE scheduled_task_run SET "  # noqa: S608
    "state = 'succeeded', finished_at = :instant, items_processed = :nombre, "
    "updated_at = :instant "
    "WHERE id = :id "
    f"RETURNING {_COLONNES}"
)

_TERMINER_EN_ECHEC: Final = text(
    "UPDATE scheduled_task_run SET "  # noqa: S608
    "state = 'failed', finished_at = :instant, error_message = :erreur, "
    "updated_at = :instant "
    "WHERE id = :id "
    f"RETURNING {_COLONNES}"
)


@dataclasses.dataclass(frozen=True, slots=True)
class LigneDExecution:
    """Une ligne de `scheduled_task_run` — modele §20.3."""

    id: uuid.UUID
    task_name: str
    state: str
    started_at: dt.datetime
    finished_at: dt.datetime | None
    items_processed: int | None
    error_message: str | None
    version: int


def _en_ligne(ligne: object) -> LigneDExecution:
    return LigneDExecution(**dict(ligne._mapping))  # type: ignore[attr-defined]


class TacheDejaEnCours(RuntimeError):
    """Une autre execution de la meme tache est deja `running`.

    Translatee depuis la violation de l'index unique partiel : jamais une
    `IntegrityError` brute remontee a l'orchestrateur.
    """


def commencer_l_execution(
    connexion: Connection, *, task_name: str, instant: dt.datetime
) -> LigneDExecution:
    """Ouvrir une ligne `running`, ou lever `TacheDejaEnCours`.

    L'appelant (l'orchestrateur) attrape cette exception et saute la tache
    pour ce cycle — voir `app.scheduling.orchestrateur`.
    """
    savepoint = connexion.begin_nested()
    try:
        ligne = connexion.execute(_COMMENCER, {"tache": task_name, "instant": instant}).one()
    except IntegrityError as erreur:
        savepoint.rollback()
        if isinstance(erreur.orig, erreurs_psycopg.UniqueViolation):
            raise TacheDejaEnCours(task_name) from erreur
        raise
    else:
        savepoint.commit()
        return _en_ligne(ligne)


def terminer_avec_succes(
    connexion: Connection, execution_id: uuid.UUID, *, instant: dt.datetime, items_processed: int
) -> LigneDExecution:
    """Marquer l'execution reussie, avec le nombre d'elements traites."""
    ligne = connexion.execute(
        _TERMINER_AVEC_SUCCES,
        {"id": execution_id, "instant": instant, "nombre": items_processed},
    ).first()
    assert ligne is not None  # noqa: S101 — `commencer_l_execution` vient de la rendre
    return _en_ligne(ligne)


def terminer_en_echec(
    connexion: Connection, execution_id: uuid.UUID, *, instant: dt.datetime, error_message: str
) -> LigneDExecution:
    """Marquer l'execution en echec. Le prochain cycle retentera la tache."""
    ligne = connexion.execute(
        _TERMINER_EN_ECHEC,
        {"id": execution_id, "instant": instant, "erreur": error_message},
    ).first()
    assert ligne is not None  # noqa: S101
    return _en_ligne(ligne)
