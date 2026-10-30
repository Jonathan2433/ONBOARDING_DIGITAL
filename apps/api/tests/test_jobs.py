"""Le socle asynchrone du LOT 11 — `T1`, stories `US001`, `US002`, `US003`.

LES TROIS CRITERES DE SORTIE EPROUVES ICI, DIRECTEMENT

  1. « Redis peut etre vide sans perte de la source de verite metier » —
     `async_job` et `outbox_message` persistent dans PostgreSQL, jamais dans
     Redis ; aucun de ces tests n'ouvre de connexion Redis.
  2. « Un job rejoue ne duplique pas son effet » —
     `test_un_essai_deja_reussi_rend_none_a_la_relance`,
     `test_une_seconde_invocation_concurrente_ne_redemarre_pas_lessai`, et le
     temoin bout-en-bout de l'outbox qui rejoue le MEME message.
  3. « Les fichiers rejetes [...] chaque envoi est auditable » (par analogie
     avec le fournisseur d'e-mail, `US003`) — la paire
     `test_un_envoi_reussi_marque_le_message_traite` /
     `test_un_echec_d_envoi_laisse_le_message_a_reessayer` (§7.39 de la
     passation : tout refus/echec a son temoin de succes apparie).

Tous ces tests tournent sur une transaction ANNULEE — meme discipline que
`test_depots_et_services.py` (LOT 2, `T11`).
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.configuration.settings import Parametres
from app.jobs import email as fournisseur_email
from app.jobs.execution import commencer_un_essai, terminer_avec_succes, terminer_en_echec
from app.jobs.modeles import TypeDeJob
from app.jobs.outbox import TOPIC_EMAIL, publier_dans_l_outbox, relayer_le_lot
from app.shared.database import moteur

pytestmark = pytest.mark.integration


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make test-integration`."
        )


@pytest.fixture
def cx(parametres_de_la_stack: Parametres) -> Iterator[Connection]:
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        try:
            yield connexion
        finally:
            transaction.rollback()


#  Ancre DERIVEE de `now()`, jamais une date figee — §7.47 de la passation :
#  une date absolue comparee a un `now()` ailleurs finit par rendre un test
#  faux, sans qu'aucune ligne n'ait change.
@pytest.fixture
def instant() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _jeton() -> str:
    return str(uuid.uuid4())


# -----------------------------------------------------------------------
#  `US001` — le cycle de vie d'un `async_job`.
# -----------------------------------------------------------------------


def test_commencer_un_essai_cree_la_ligne_et_la_demarre(
    cx: Connection, instant: dt.datetime
) -> None:
    cle = _jeton()
    job = commencer_un_essai(
        cx, job_type=TypeDeJob.MAINTENANCE.value, idempotency_key=cle, instant=instant
    )
    assert job is not None
    assert job.state == "running"
    assert job.attempt_count == 1
    assert job.started_at is not None


def test_un_essai_deja_reussi_rend_none_a_la_relance(cx: Connection, instant: dt.datetime) -> None:
    """Le critere central de `US001` : rejouer un job TERMINE ne fait rien."""
    cle = _jeton()
    premier = commencer_un_essai(
        cx, job_type=TypeDeJob.EMAIL.value, idempotency_key=cle, instant=instant
    )
    assert premier is not None
    terminer_avec_succes(cx, premier.id, instant=instant)

    rejoue = commencer_un_essai(
        cx, job_type=TypeDeJob.EMAIL.value, idempotency_key=cle, instant=instant
    )
    assert rejoue is None


def test_une_seconde_invocation_concurrente_ne_redemarre_pas_lessai(
    cx: Connection, instant: dt.datetime
) -> None:
    """Le job reste `running` : une seconde invocation ne duplique pas l'effet
    pendant que la premiere travaille encore."""
    cle = _jeton()
    premier = commencer_un_essai(
        cx, job_type=TypeDeJob.MEDIA.value, idempotency_key=cle, instant=instant
    )
    assert premier is not None

    concurrent = commencer_un_essai(
        cx, job_type=TypeDeJob.MEDIA.value, idempotency_key=cle, instant=instant
    )
    assert concurrent is None


def test_un_type_de_job_different_avec_la_meme_cle_est_un_job_distinct(
    cx: Connection, instant: dt.datetime
) -> None:
    """`idempotency_key` est unique PAR `job_type` — voir l'en-tete du module."""
    cle = _jeton()
    pour_email = commencer_un_essai(
        cx, job_type=TypeDeJob.EMAIL.value, idempotency_key=cle, instant=instant
    )
    pour_export = commencer_un_essai(
        cx, job_type=TypeDeJob.EXPORT.value, idempotency_key=cle, instant=instant
    )
    assert pour_email is not None
    assert pour_export is not None
    assert pour_email.id != pour_export.id


def test_un_echec_remet_en_file_tant_que_des_tentatives_restent(
    cx: Connection, instant: dt.datetime
) -> None:
    cle = _jeton()
    job = commencer_un_essai(
        cx,
        job_type=TypeDeJob.EXPORT.value,
        idempotency_key=cle,
        instant=instant,
        max_attempts=3,
    )
    assert job is not None
    apres_echec = terminer_en_echec(cx, job.id, instant=instant, error_code="ErreurDeTest")
    assert apres_echec.state == "queued"
    assert apres_echec.attempt_count == 1

    repris = commencer_un_essai(
        cx, job_type=TypeDeJob.EXPORT.value, idempotency_key=cle, instant=instant, max_attempts=3
    )
    assert repris is not None
    assert repris.attempt_count == 2


def test_un_echec_apres_la_derniere_tentative_passe_a_failed_et_ny_reste(
    cx: Connection, instant: dt.datetime
) -> None:
    """`failed` est un etat TERMINAL : une relance ulterieure rend `None`,
    exactement comme `succeeded` — voir l'en-tete d'`execution.py`."""
    cle = _jeton()
    job = commencer_un_essai(
        cx,
        job_type=TypeDeJob.PURGE.value,
        idempotency_key=cle,
        instant=instant,
        max_attempts=1,
    )
    assert job is not None
    apres_echec = terminer_en_echec(cx, job.id, instant=instant, error_code="ErreurDeTest")
    assert apres_echec.state == "failed"
    assert apres_echec.finished_at is not None

    relance = commencer_un_essai(
        cx, job_type=TypeDeJob.PURGE.value, idempotency_key=cle, instant=instant, max_attempts=1
    )
    assert relance is None


# -----------------------------------------------------------------------
#  `US002` — l'outbox transactionnelle.
# -----------------------------------------------------------------------


def test_publier_dans_l_outbox_ecrit_dans_la_transaction_de_l_appelant(
    cx: Connection, instant: dt.datetime
) -> None:
    identifiant = publier_dans_l_outbox(
        cx, topic="demonstration", payload={"valeur": "test"}, instant=instant
    )
    ligne = cx.execute(
        text("SELECT topic, payload_json, processed_at FROM outbox_message WHERE id = :id"),
        {"id": identifiant},
    ).one()
    assert ligne.topic == "demonstration"
    assert ligne.payload_json == {"valeur": "test"}
    assert ligne.processed_at is None


def test_un_rollback_de_la_transaction_appelante_efface_aussi_le_message(
    parametres_de_la_stack: Parametres, instant: dt.datetime
) -> None:
    """L'ATOMICITE, prouvee par un VRAI rollback — pas seulement affirmee.

    `US002` : « l'action metier et l'outbox sont atomiques ». Le message
    publie DANS une transaction qui echoue ne doit survivre NULLE PART,
    exactement comme l'action metier qu'il accompagnait.
    """
    _exiger_postgresql(parametres_de_la_stack)
    with moteur(parametres_de_la_stack).connect() as connexion:
        transaction = connexion.begin()
        identifiant = publier_dans_l_outbox(
            connexion, topic="demonstration", payload={}, instant=instant
        )
        transaction.rollback()

        verification = connexion.begin()
        try:
            trouve = connexion.execute(
                text("SELECT 1 FROM outbox_message WHERE id = :id"), {"id": identifiant}
            ).first()
            assert trouve is None
        finally:
            verification.rollback()


def test_republier_avec_la_meme_cle_de_deduplication_rend_le_message_existant(
    cx: Connection, instant: dt.datetime
) -> None:
    cle = _jeton()
    premier = publier_dans_l_outbox(
        cx, topic="demonstration", payload={}, instant=instant, deduplication_key=cle
    )
    second = publier_dans_l_outbox(
        cx, topic="demonstration", payload={}, instant=instant, deduplication_key=cle
    )
    assert premier == second
    total = cx.execute(
        text("SELECT count(*) FROM outbox_message WHERE deduplication_key = :cle"), {"cle": cle}
    ).scalar_one()
    assert total == 1


def test_un_topic_sans_consommateur_est_laisse_en_attente(
    cx: Connection, instant: dt.datetime
) -> None:
    """`T1` ne cable que `email` — voir l'en-tete d'`outbox.py`."""
    publier_dans_l_outbox(cx, topic="generation_de_media", payload={}, instant=instant)
    nombre_traites = relayer_le_lot(cx, instant=instant)
    assert nombre_traites == 0


# -----------------------------------------------------------------------
#  `US003`, et le relais de bout en bout — les trois stories travaillent
#  ensemble, exactement comme la fiche du lot l'a regroupe.
# -----------------------------------------------------------------------


class _FournisseurFactice:
    """Un fournisseur jetable, pour isoler le relais de l'outbox du SMTP reel."""

    def __init__(self, *, echoue: bool = False) -> None:
        self.echoue = echoue
        self.envois: list[dict[str, str | None]] = []

    def envoyer(
        self, *, destinataire: str, sujet: str, corps_texte: str, corps_html: str | None = None
    ) -> None:
        if self.echoue:
            raise fournisseur_email.EchecDEnvoi("echec simule, aucune donnee du courriel")
        self.envois.append(
            {
                "destinataire": destinataire,
                "sujet": sujet,
                "corps_texte": corps_texte,
                "corps_html": corps_html,
            }
        )


def _charge_email(destinataire: str = "test@exalt-company.com") -> dict[str, str]:
    return {"destinataire": destinataire, "sujet": "Sujet de test", "corps_texte": "Corps de test"}


def test_un_envoi_reussi_marque_le_message_traite(
    cx: Connection, instant: dt.datetime, monkeypatch: pytest.MonkeyPatch
) -> None:
    fournisseur = _FournisseurFactice()
    monkeypatch.setattr(fournisseur_email, "obtenir_le_fournisseur", lambda *a, **k: fournisseur)

    identifiant = publier_dans_l_outbox(
        cx, topic=TOPIC_EMAIL, payload=_charge_email(), instant=instant
    )
    nombre_traites = relayer_le_lot(cx, instant=instant)

    assert nombre_traites == 1
    assert len(fournisseur.envois) == 1
    ligne = cx.execute(
        text("SELECT processed_at FROM outbox_message WHERE id = :id"), {"id": identifiant}
    ).one()
    assert ligne.processed_at is not None


def test_un_echec_d_envoi_laisse_le_message_a_reessayer(
    cx: Connection, instant: dt.datetime, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Temoin apparie au precedent (§7.39) : le meme chemin, l'issue opposee."""
    fournisseur = _FournisseurFactice(echoue=True)
    monkeypatch.setattr(fournisseur_email, "obtenir_le_fournisseur", lambda *a, **k: fournisseur)

    identifiant = publier_dans_l_outbox(
        cx, topic=TOPIC_EMAIL, payload=_charge_email(), instant=instant
    )
    nombre_traites = relayer_le_lot(cx, instant=instant)

    assert nombre_traites == 0
    ligne = cx.execute(
        text(
            "SELECT processed_at, attempt_count, last_error_code, available_at "
            "FROM outbox_message WHERE id = :id"
        ),
        {"id": identifiant},
    ).one()
    assert ligne.processed_at is None
    assert ligne.attempt_count == 1
    assert ligne.last_error_code == "EchecDEnvoi"
    assert ligne.available_at > instant


def test_rejouer_le_relais_sur_un_message_deja_traite_ne_renvoie_pas_le_courriel(
    cx: Connection, instant: dt.datetime, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LE TEMOIN DECISIF DE `US002` : le MEME message, relaye DEUX fois.

    Simule un relais relance apres un crash entre l'envoi reussi et le
    `UPDATE processed_at` : si le second passage renvoyait l'e-mail, ce test
    verrait DEUX envois. `commencer_un_essai` l'empeche.
    """
    fournisseur = _FournisseurFactice()
    monkeypatch.setattr(fournisseur_email, "obtenir_le_fournisseur", lambda *a, **k: fournisseur)

    identifiant = publier_dans_l_outbox(
        cx, topic=TOPIC_EMAIL, payload=_charge_email(), instant=instant
    )
    #  Simule le crash : le premier passage reussit l'envoi (job `succeeded`)
    #  mais JAMAIS le `UPDATE processed_at` qui le suit — exactement l'etat
    #  qu'un relais interrompu laisserait.
    cx.execute(
        text(
            "INSERT INTO async_job "
            "(job_type, state, idempotency_key, attempt_count, started_at, finished_at, "
            " created_at, updated_at) "
            "VALUES ('email', 'succeeded', :cle, 1, :instant, :instant, :instant, :instant)"
        ),
        {"cle": str(identifiant), "instant": instant},
    )

    nombre_traites = relayer_le_lot(cx, instant=instant)

    assert nombre_traites == 1  # processed_at est rattrape...
    assert len(fournisseur.envois) == 0  # ...mais AUCUN e-mail n'est reenvoye
