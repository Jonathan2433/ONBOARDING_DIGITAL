"""Corrélation et journalisation des jobs Dramatiq.

LOT 1, sous-etape T4, story MVP-L01-US004.

Critere litteral : « chaque requete ET chaque job portent un correlation_id ».
La moitie « requete » est eprouvee cote API ; celle-ci eprouve « job ».

Aucun Redis n'est necessaire : le courtier de test de Dramatiq suffit. Un test
qui exigerait une infrastructure pour verifier une regle de correlation serait
un test qu'on finit par ne plus lancer.
"""

from __future__ import annotations

import io
import json
import logging
from collections.abc import Iterator
from typing import Any

import pytest
from dramatiq import Message

from observabilite.correlation import (
    CLE_CORRELATION_MESSAGE,
    correlation_courante,
    definir_correlation,
    effacer_correlation,
)
from observabilite.journalisation import configurer_journalisation
from observabilite.masquage import MASQUE
from worker.journal import CorrelationEtJournal


@pytest.fixture
def tampon() -> Iterator[io.StringIO]:
    """Journal configure comme dans le worker, sortie capturee."""
    flux = io.StringIO()
    configurer_journalisation(
        service="worker", environnement="development", version="0.1.0", niveau="debug"
    )
    racine = logging.getLogger()
    racine.handlers[0].stream = flux  # type: ignore[attr-defined]
    yield flux
    effacer_correlation()
    for poignee in list(racine.handlers):
        racine.removeHandler(poignee)


def message_de_test(**options: Any) -> Message[Any]:
    """Un message Dramatiq minimal."""
    return Message(
        queue_name="emails",
        actor_name="envoyer_invitation",
        args=(),
        kwargs={},
        options=dict(options),
    )


def lignes(flux: io.StringIO) -> list[dict[str, Any]]:
    return [
        json.loads(ligne) for ligne in flux.getvalue().splitlines() if ligne.strip().startswith("{")
    ]


# ============================================================================
#  La trace franchit la frontière API -> worker
# ============================================================================


def test_l_identifiant_courant_est_inscrit_dans_le_message_a_l_enfilement() -> None:
    """C'est ce qui permettra de relier un job a la requete qui l'a declenche."""
    middleware = CorrelationEtJournal()
    definir_correlation("trace-de-la-requete")
    message = message_de_test()
    middleware.before_enqueue(None, message, 0)
    assert message.options[CLE_CORRELATION_MESSAGE] == "trace-de-la-requete"


def test_un_identifiant_deja_present_dans_le_message_n_est_pas_ecrase() -> None:
    """Un job reenfile doit conserver la trace de son origine."""
    middleware = CorrelationEtJournal()
    definir_correlation("trace-courante")
    message = message_de_test(**{CLE_CORRELATION_MESSAGE: "trace-d-origine"})
    middleware.before_enqueue(None, message, 0)
    assert message.options[CLE_CORRELATION_MESSAGE] == "trace-d-origine"


def test_un_identifiant_est_engendre_si_aucun_contexte_n_existe() -> None:
    """Job planifie ou emis par un outil : il doit quand meme etre tracable."""
    middleware = CorrelationEtJournal()
    effacer_correlation()
    message = message_de_test()
    middleware.before_enqueue(None, message, 0)
    assert message.options[CLE_CORRELATION_MESSAGE]


def test_le_worker_replace_l_identifiant_du_message_dans_le_contexte() -> None:
    """La moitie « job » du critere de la sous-etape."""
    middleware = CorrelationEtJournal()
    effacer_correlation()
    middleware.before_process_message(
        None, message_de_test(**{CLE_CORRELATION_MESSAGE: "trace-venue-de-l-api"})
    )
    assert correlation_courante() == "trace-venue-de-l-api"


def test_un_job_sans_identifiant_en_recoit_un_quand_meme() -> None:
    """Temoin negatif : aucun job ne doit s'executer sans trace."""
    middleware = CorrelationEtJournal()
    effacer_correlation()
    middleware.before_process_message(None, message_de_test())
    assert correlation_courante()


def test_l_identifiant_est_efface_apres_le_job(tampon: io.StringIO) -> None:
    """Un fil du pool est reutilise.

    Laisser l'identifiant du job precedent ferait attribuer les lignes du suivant
    a la trace du premier. Une correlation fausse est pire qu'une correlation
    absente, parce qu'on la croit.
    """
    _ = tampon
    middleware = CorrelationEtJournal()
    message = message_de_test(**{CLE_CORRELATION_MESSAGE: "trace-du-job"})
    middleware.before_process_message(None, message)
    assert correlation_courante() == "trace-du-job"
    middleware.after_process_message(None, message)
    assert correlation_courante() is None


# ============================================================================
#  Le journal du job — cahier §28.1
# ============================================================================


def test_un_job_reussi_est_journalise_avec_les_champs_du_cahier(
    tampon: io.StringIO,
) -> None:
    middleware = CorrelationEtJournal()
    message = message_de_test(**{CLE_CORRELATION_MESSAGE: "trace-1"})
    middleware.before_process_message(None, message)
    middleware.after_process_message(None, message)

    ligne = lignes(tampon)[0]
    assert ligne["service"] == "worker"
    assert ligne["route"] == "emails/envoyer_invitation"
    assert ligne["resultat"] == "succes"
    assert ligne["code_erreur"] is None
    assert ligne["duree_ms"] is not None
    assert ligne["identifiant_correlation"] == "trace-1"


def test_un_job_en_echec_porte_le_type_de_l_exception(tampon: io.StringIO) -> None:
    middleware = CorrelationEtJournal()
    message = message_de_test(**{CLE_CORRELATION_MESSAGE: "trace-2"})
    middleware.before_process_message(None, message)
    middleware.after_process_message(None, message, exception=ValueError("motif"))

    ligne = lignes(tampon)[0]
    assert ligne["niveau"] == "error"
    assert ligne["resultat"] == "echec"
    assert ligne["code_erreur"] == "ValueError"


def test_un_job_ignore_est_journalise(tampon: io.StringIO) -> None:
    """Un job qui disparait sans trace est une panne muette."""
    middleware = CorrelationEtJournal()
    message = message_de_test(**{CLE_CORRELATION_MESSAGE: "trace-3"})
    middleware.before_process_message(None, message)
    middleware.after_skip_message(None, message)

    ligne = lignes(tampon)[0]
    assert ligne["niveau"] == "warning"
    assert ligne["resultat"] == "ignore"
    assert ligne["code_erreur"] == "job_ignore"


def test_les_arguments_du_job_ne_sont_jamais_journalises(tampon: io.StringIO) -> None:
    """Cahier §28.2.

    Les arguments d'un job peuvent porter une adresse e-mail, un identifiant de
    personne, ou le jeton d'un magic link. Seul leur NOMBRE est utile.
    """
    middleware = CorrelationEtJournal()
    message: Message[Any] = Message(
        queue_name="emails",
        actor_name="envoyer_magic_link",
        args=("jean.dupont@exalt-company.com",),
        kwargs={"jeton": "AbCdEf123456SecretDuMagicLink"},
        options={CLE_CORRELATION_MESSAGE: "trace-4"},
    )
    middleware.before_process_message(None, message)
    middleware.after_process_message(None, message)

    brut = tampon.getvalue()
    assert "jean.dupont@exalt-company.com" not in brut
    assert "AbCdEf123456SecretDuMagicLink" not in brut
    # Temoin positif : la ligne existe et compte bien deux arguments, sinon
    # l'absence ci-dessus ne prouverait rien.
    ligne = lignes(tampon)[0]
    assert ligne["contexte"]["nombre_arguments"] == 2
    assert ligne["route"] == "emails/envoyer_magic_link"


def test_un_secret_dans_les_options_du_message_est_masque(tampon: io.StringIO) -> None:
    """Le masquage s'applique aussi aux journaux du worker."""
    middleware = CorrelationEtJournal()
    message = message_de_test(**{CLE_CORRELATION_MESSAGE: "trace-5"})
    middleware.before_process_message(None, message)
    logging.getLogger("worker.job").info(
        "detail",
        extra={"route": "emails/x", "smtp_password": "MotDePasseSmtp"},
    )
    brut = tampon.getvalue()
    assert "MotDePasseSmtp" not in brut
    assert MASQUE in brut
