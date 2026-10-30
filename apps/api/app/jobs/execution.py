"""Le cycle de vie d'un `async_job` — modele §20.1 — `T1`, story `MVP-L11-US001`.

LE CRITERE DE SORTIE EST « UN JOB REJOUE NE DUPLIQUE PAS SON EFFET », PAS
« UN JOB NE S'ECRIT QU'UNE FOIS »

  Deux appelants peuvent vouloir le MEME effet — un message Dramatiq relance
  par son propre mecanisme de reprise, ou l'outbox qui relaie deux fois le
  meme message parce que le premier relais a crashe avant de marquer
  `processed_at`. Le garde-fou n'est donc pas une simple insertion unique :
  c'est `commencer_un_essai`, qui refuse de DEMARRER un travail deja fait.

`commencer_un_essai` REND `None` QUAND IL N'Y A RIEN A FAIRE, JAMAIS UNE
EXCEPTION

  Un job deja `succeeded`, deja `running` (une seconde invocation concurrente
  du meme message), deja `failed` (tentatives epuisees) ou `cancelled`, n'est
  pas une ERREUR pour l'appelant : c'est le signal qu'il doit sauter son
  propre effet. Une
  exception forcerait l'appelant a la rattraper pour un cas qui n'en est pas
  un — meme parti que `rejouer_une_ligne` (LOT 9), qui laisse un code deja
  resolu disparaitre plutot que de lever sur un etat qui n'est pas une erreur.

L'UPSERT EST EN DEUX TEMPS, PAS UN SEUL, ET C'EST DELIBERE

  `INSERT ... ON CONFLICT DO NOTHING` cree la ligne si elle n'existe pas ;
  `UPDATE ... WHERE state = 'queued' RETURNING ...` la fait demarrer
  SEULEMENT si elle est dans l'etat qui le permet. Les deux requetes sont
  necessaires : fusionner l'upsert et le demarrage dans un seul
  `INSERT ... ON CONFLICT DO UPDATE` ecraserait une ligne `succeeded` ou
  `running` par la MEME condition qui doit au contraire la proteger.

  `failed` N'EST PAS REDEMARRABLE PAR CETTE FONCTION : `terminer_en_echec`
  (plus bas) ne pose `failed` qu'une fois les tentatives EPUISEES — elle
  repose `queued` tant qu'il en reste. Un job `failed` est donc un etat
  TERMINAL au meme titre que `succeeded`/`cancelled` : le relancer exigerait
  un geste EXPLICITE qui reinitialise `attempt_count`, que ce lot ne construit
  pas faute de consommateur (§6.5 de la passation).

`max_attempts` EST LU SUR LA LIGNE, JAMAIS PASSE UNE SECONDE FOIS

  Une fois le job cree, `max_attempts` lui appartient. `terminer_en_echec` le
  relit depuis la ligne plutot que de demander a l'appelant de le repasser —
  deux sources pour la meme valeur divergeraient au premier appel qui
  oublierait de le faire (§7.27 de la passation).
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import TYPE_CHECKING, Final

from sqlalchemy import text

from app.jobs.modeles import MAX_TENTATIVES_PAR_DEFAUT, EtatDuJob

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

_COLONNES: Final = (
    "id, entity_id, job_type, state, progress_current, progress_total, "
    "requested_by_person_id, idempotency_key, attempt_count, max_attempts, "
    "started_at, finished_at, last_heartbeat_at, error_code, result_reference, version"
)

_ASSURER_LA_LIGNE: Final = text(
    "INSERT INTO async_job "
    "(entity_id, job_type, state, requested_by_person_id, idempotency_key, max_attempts, "
    " created_at, created_by_person_id, updated_at, updated_by_person_id) "
    "VALUES (:entite, :type_job, 'queued', :demandeur, :cle, :tentatives_maximales, "
    " :instant, :demandeur, :instant, :demandeur) "
    "ON CONFLICT (job_type, idempotency_key) DO NOTHING"
)

_DEMARRER_UNE_TENTATIVE: Final = text(
    "UPDATE async_job SET "  # noqa: S608
    "state = 'running', "
    "attempt_count = attempt_count + 1, "
    "started_at = COALESCE(started_at, :instant), "
    "last_heartbeat_at = :instant, "
    "updated_at = :instant "
    "WHERE job_type = :type_job AND idempotency_key = :cle "
    "AND state = 'queued' "
    f"RETURNING {_COLONNES}"
)

_TERMINER_AVEC_SUCCES: Final = text(
    "UPDATE async_job SET "  # noqa: S608
    "state = 'succeeded', finished_at = :instant, result_reference = :resultat, "
    "updated_at = :instant "
    "WHERE id = :id "
    f"RETURNING {_COLONNES}"
)

_LIRE_POUR_ECHEC: Final = text(
    "SELECT attempt_count, max_attempts FROM async_job WHERE id = :id FOR UPDATE"
)

#  `:nouvel_etat` n'est lie QU'UNE FOIS, contre `state` seul : le comparer une
#  seconde fois a `'failed'` dans un `CASE` ferait deduire deux types pour le
#  MEME parametre (`character varying` contre `text`), la classe de defaut
#  §7.25 de la passation. `instant_de_fin` est donc calcule cote PYTHON, et
#  vaut `None` tant que l'etat n'est pas terminal.
_TERMINER_EN_ECHEC: Final = text(
    "UPDATE async_job SET "  # noqa: S608
    "state = :nouvel_etat, error_code = :code_erreur, "
    "finished_at = COALESCE(:instant_de_fin, finished_at), "
    "updated_at = :instant "
    "WHERE id = :id "
    f"RETURNING {_COLONNES}"
)


@dataclasses.dataclass(frozen=True, slots=True)
class LigneDeJob:
    """Une ligne de `async_job` — modele §20.1."""

    id: uuid.UUID
    entity_id: uuid.UUID | None
    job_type: str
    state: str
    progress_current: int | None
    progress_total: int | None
    requested_by_person_id: uuid.UUID | None
    idempotency_key: str
    attempt_count: int
    max_attempts: int
    started_at: dt.datetime | None
    finished_at: dt.datetime | None
    last_heartbeat_at: dt.datetime | None
    error_code: str | None
    result_reference: uuid.UUID | None
    version: int


def _en_ligne(ligne: object) -> LigneDeJob:
    return LigneDeJob(**dict(ligne._mapping))  # type: ignore[attr-defined]


def commencer_un_essai(
    connexion: Connection,
    *,
    job_type: str,
    idempotency_key: str,
    instant: dt.datetime,
    entity_id: uuid.UUID | None = None,
    requested_by_person_id: uuid.UUID | None = None,
    max_attempts: int = MAX_TENTATIVES_PAR_DEFAUT,
) -> LigneDeJob | None:
    """Assurer la ligne, puis la demarrer — ou rendre `None` s'il n'y a rien a faire.

    `None` signifie : ce job (ce `job_type` + cette `idempotency_key`) est deja
    `succeeded`, deja `running` ailleurs, deja `failed` (tentatives epuisees),
    ou `cancelled`. Dans tous ces cas, l'appelant ne doit PAS executer son
    effet une seconde fois.
    """
    connexion.execute(
        _ASSURER_LA_LIGNE,
        {
            "entite": entity_id,
            "type_job": job_type,
            "demandeur": requested_by_person_id,
            "cle": idempotency_key,
            "tentatives_maximales": max_attempts,
            "instant": instant,
        },
    )
    demarree = connexion.execute(
        _DEMARRER_UNE_TENTATIVE, {"type_job": job_type, "cle": idempotency_key, "instant": instant}
    ).first()
    if demarree is None:
        return None
    return _en_ligne(demarree)


def terminer_avec_succes(
    connexion: Connection,
    job_id: uuid.UUID,
    *,
    instant: dt.datetime,
    result_reference: uuid.UUID | None = None,
) -> LigneDeJob:
    """Marquer le job reussi. Appele une fois le travail reellement effectue."""
    ligne = connexion.execute(
        _TERMINER_AVEC_SUCCES, {"id": job_id, "instant": instant, "resultat": result_reference}
    ).first()
    assert ligne is not None  # noqa: S101 — la ligne existe : `commencer_un_essai` vient de la rendre
    return _en_ligne(ligne)


def terminer_en_echec(
    connexion: Connection, job_id: uuid.UUID, *, instant: dt.datetime, error_code: str
) -> LigneDeJob:
    """Marquer l'essai en echec : `queued` s'il reste des tentatives, sinon `failed`.

    LU EN DEUX TEMPS, SOUS `FOR UPDATE` : `attempt_count` vient d'etre
    incremente par `commencer_un_essai`, et c'est cette valeur, pas une
    hypothese, qui decide si une nouvelle tentative reste possible.
    """
    ligne_actuelle = connexion.execute(_LIRE_POUR_ECHEC, {"id": job_id}).first()
    assert ligne_actuelle is not None  # noqa: S101
    tentatives_restantes = ligne_actuelle.attempt_count < ligne_actuelle.max_attempts
    nouvel_etat = EtatDuJob.QUEUED.value if tentatives_restantes else EtatDuJob.FAILED.value
    instant_de_fin = None if tentatives_restantes else instant
    ligne = connexion.execute(
        _TERMINER_EN_ECHEC,
        {
            "id": job_id,
            "instant": instant,
            "instant_de_fin": instant_de_fin,
            "code_erreur": error_code,
            "nouvel_etat": nouvel_etat,
        },
    ).first()
    assert ligne is not None  # noqa: S101
    return _en_ligne(ligne)
