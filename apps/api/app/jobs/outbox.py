"""L'outbox transactionnelle — modele §20.2 — `T1`, story `MVP-L11-US002`.

`publier_dans_l_outbox` N'OUVRE JAMAIS SA PROPRE TRANSACTION

  C'est le point du patron « outbox » : la ligne doit etre ecrite dans la
  MEME transaction que l'action metier qui la motive, pour que les deux
  reussissent ou echouent ENSEMBLE. La fonction prend donc la `Connection` de
  l'appelant telle quelle, n'appelle jamais `commit()`, et c'est a l'appelant
  de committer — exactement le role que joue deja `enregistrer_un_evenement`
  (LOT 10, `app.audit.services`) pour l'audit.

LE RELAIS, LUI, OUVRE SA PROPRE TRANSACTION PAR MESSAGE

  `relayer_le_lot` lit un LOT de messages sous `FOR UPDATE SKIP LOCKED` — pour
  qu'un second relais concurrent ne bloque pas sur les lignes deja prises, et
  n'en retraite aucune en double — puis traite chaque message dans son PROPRE
  savepoint (`connexion.begin_nested()`), meme patron que
  `app.imports.execution`/`app.people.transfert_masse` : l'echec d'un message
  n'annule jamais le travail deja fait sur les precedents du meme lot.

T1 NE CABLE QU'UN SEUL `topic` : `email`

  Le modele §20.2 en liste cinq (e-mail, media, progression, supervision,
  export) ; seul l'envoi d'e-mail a un consommateur a ce lot (`US003`). Un
  message d'un autre `topic` est laisse NON TRAITE — ni erreur, ni perte,
  simplement en attente qu'un futur lot cable son relais. Le dire plutot que
  de lever une exception qui ferait echouer tout le lot pour un message qui
  n'a encore aucun consommateur (§6.5 de la passation).
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
import logging
import uuid
from typing import TYPE_CHECKING, Any, Final, cast

from sqlalchemy import text

from app.jobs import email as fournisseur_email
from app.jobs.execution import commencer_un_essai, terminer_avec_succes, terminer_en_echec
from app.jobs.modeles import TypeDeJob

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

journal = logging.getLogger("app.jobs.outbox")

TOPIC_EMAIL: Final = "email"

TAILLE_DE_LOT_PAR_DEFAUT: Final = 20

#  Deux requetes distinctes, et non une seule parametree : un message SANS
#  cle de deduplication n'a besoin d'aucun `ON CONFLICT`, et PostgreSQL
#  n'accepte de toute facon pas qu'une colonne cible d'un index partiel soit
#  absente de l'instruction pour que `ON CONFLICT` la resolve.
_PUBLIER_SANS_DEDUPLICATION: Final = text(
    "INSERT INTO outbox_message "
    "(topic, payload_json, available_at, created_at, updated_at) "
    "VALUES (:topic, :charge, :disponible_a, :instant, :instant) "
    "RETURNING id"
)

_PUBLIER_AVEC_DEDUPLICATION: Final = text(
    "INSERT INTO outbox_message "
    "(topic, payload_json, available_at, deduplication_key, created_at, updated_at) "
    "VALUES (:topic, :charge, :disponible_a, :cle, :instant, :instant) "
    "ON CONFLICT (deduplication_key) "
    "WHERE processed_at IS NULL AND deduplication_key IS NOT NULL "
    "DO NOTHING "
    "RETURNING id"
)

_TROUVER_LE_MESSAGE_EXISTANT: Final = text(
    "SELECT id FROM outbox_message WHERE deduplication_key = :cle AND processed_at IS NULL"
)

_LIRE_UN_LOT_A_RELAYER: Final = text(
    "SELECT id, topic, payload_json, attempt_count FROM outbox_message "
    "WHERE processed_at IS NULL AND available_at <= :instant "
    "ORDER BY available_at "
    "LIMIT :taille_de_lot "
    "FOR UPDATE SKIP LOCKED"
)

_MARQUER_TRAITE: Final = text(
    "UPDATE outbox_message SET processed_at = :instant, updated_at = :instant WHERE id = :id"
)

_MARQUER_EN_ECHEC: Final = text(
    "UPDATE outbox_message SET "
    "attempt_count = attempt_count + 1, last_error_code = :code_erreur, "
    #  Recul simple et borne : pas de politique de nouvelle tentative plus
    #  fine que celle, deja construite, de `async_job` — ce message sera
    #  repris par le prochain passage du relais, au plus tot dans une minute.
    "available_at = :instant + INTERVAL '1 minute', "
    "updated_at = :instant "
    "WHERE id = :id"
)


@dataclasses.dataclass(frozen=True, slots=True)
class _MessageARelayer:
    id: uuid.UUID
    topic: str
    payload_json: dict[str, Any]
    attempt_count: int


def publier_dans_l_outbox(
    connexion: Connection,
    *,
    topic: str,
    payload: dict[str, Any],
    instant: dt.datetime,
    available_at: dt.datetime | None = None,
    deduplication_key: str | None = None,
) -> uuid.UUID:
    """Ecrire un message technique, dans la transaction DE L'APPELANT.

    Si `deduplication_key` designe deja un message encore EN ATTENTE, rend
    l'identifiant de ce message existant plutot que d'en creer un second —
    c'est ce qui rend un appel rejoue sans effet supplementaire (`US002`).

    `payload` est serialise par `json.dumps` avant d'etre lie : un `dict`
    Python n'est pas adaptable tel quel par le pilote, meme pour poser une
    colonne `jsonb` — meme discipline qu'`app.audit.services`.
    """
    charge = json.dumps(payload)
    disponible_a = available_at if available_at is not None else instant
    if deduplication_key is None:
        ligne = connexion.execute(
            _PUBLIER_SANS_DEDUPLICATION,
            {"topic": topic, "charge": charge, "disponible_a": disponible_a, "instant": instant},
        ).first()
        assert ligne is not None  # noqa: S101
        return cast("uuid.UUID", ligne.id)

    ligne = connexion.execute(
        _PUBLIER_AVEC_DEDUPLICATION,
        {
            "topic": topic,
            "charge": charge,
            "disponible_a": disponible_a,
            "cle": deduplication_key,
            "instant": instant,
        },
    ).first()
    if ligne is not None:
        return cast("uuid.UUID", ligne.id)
    existant = connexion.execute(_TROUVER_LE_MESSAGE_EXISTANT, {"cle": deduplication_key}).first()
    assert existant is not None  # noqa: S101 — le conflit prouve qu'une ligne en attente existe
    return cast("uuid.UUID", existant.id)


def relayer_le_lot(
    connexion: Connection, *, instant: dt.datetime, taille_de_lot: int = TAILLE_DE_LOT_PAR_DEFAUT
) -> int:
    """Traiter jusqu'a `taille_de_lot` messages dus, chacun dans son PROPRE savepoint.

    Rend le nombre de messages EFFECTIVEMENT marques traites (succes ou
    `topic` non cable n'en font pas partie — ce dernier n'est pas un echec,
    voir l'en-tete du module).
    """
    lignes = connexion.execute(
        _LIRE_UN_LOT_A_RELAYER, {"instant": instant, "taille_de_lot": taille_de_lot}
    ).all()
    messages = [
        _MessageARelayer(
            id=ligne.id,
            topic=ligne.topic,
            payload_json=ligne.payload_json,
            attempt_count=ligne.attempt_count,
        )
        for ligne in lignes
    ]
    nombre_traites = 0
    for message in messages:
        with connexion.begin_nested():
            if _traiter_un_message(connexion, message, instant=instant):
                nombre_traites += 1
    return nombre_traites


def _traiter_un_message(
    connexion: Connection, message: _MessageARelayer, *, instant: dt.datetime
) -> bool:
    if message.topic != TOPIC_EMAIL:
        journal.info(
            "message de l'outbox laisse en attente : topic sans consommateur",
            extra={"topic": message.topic},
        )
        return False

    #  La cle d'idempotence du JOB est l'identifiant du MESSAGE lui-meme : si
    #  ce message a deja ete traite jusqu'au bout par une invocation
    #  precedente du relais (par exemple apres un crash entre l'envoi reussi
    #  et le `UPDATE processed_at`), `commencer_un_essai` rend `None` et
    #  aucun second e-mail n'est envoye — seul `processed_at` est rattrape.
    job = commencer_un_essai(
        connexion,
        job_type=TypeDeJob.EMAIL.value,
        idempotency_key=str(message.id),
        instant=instant,
    )
    if job is not None:
        try:
            fournisseur_email.envoyer_depuis_la_charge(message.payload_json)
        except fournisseur_email.EchecDEnvoi as erreur:
            code_erreur = type(erreur).__name__
            terminer_en_echec(connexion, job.id, instant=instant, error_code=code_erreur)
            connexion.execute(
                _MARQUER_EN_ECHEC,
                {"id": message.id, "instant": instant, "code_erreur": code_erreur},
            )
            return False
        terminer_avec_succes(connexion, job.id, instant=instant)

    connexion.execute(_MARQUER_TRAITE, {"id": message.id, "instant": instant})
    return True
