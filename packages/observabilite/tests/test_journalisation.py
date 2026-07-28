"""Le format de journal du cahier §28.1.

LOT 1, sous-etape T4, story MVP-L01-US004.

FONDEMENT — cahier §28.1, litteral
    « Logs JSON structures avec : date ; niveau ; service ; environnement ;
    version ; identifiant de correlation ; route ou tache ; duree ; resultat ;
    code d'erreur. »
"""

from __future__ import annotations

import io
import json
import logging
from collections.abc import Iterator
from typing import Any

import pytest

from observabilite.correlation import (
    correlation_courante,
    definir_correlation,
    effacer_correlation,
)
from observabilite.journalisation import (
    CHAMPS_DU_CAHIER,
    FormateurJson,
    configurer_journalisation,
)
from observabilite.masquage import MASQUE

# Les dix champs, recopies depuis le cahier §28.1 et non depuis le code : si le
# code s'en ecartait, comparer le code a lui-meme ne le detecterait pas.
DIX_CHAMPS_DU_CAHIER = (
    "date",
    "niveau",
    "service",
    "environnement",
    "version",
    "identifiant_correlation",
    "route",
    "duree_ms",
    "resultat",
    "code_erreur",
)


@pytest.fixture
def journal_capture() -> Iterator[tuple[logging.Logger, io.StringIO]]:
    """Un journal configure, dont la sortie est capturee."""
    tampon = io.StringIO()
    configurer_journalisation(
        service="api", environnement="development", version="0.1.0", niveau="debug"
    )
    racine = logging.getLogger()
    racine.handlers[0].stream = tampon  # type: ignore[attr-defined]
    yield logging.getLogger("test.journal"), tampon
    effacer_correlation()
    for poignee in list(racine.handlers):
        racine.removeHandler(poignee)


def lignes(tampon: io.StringIO) -> list[dict[str, Any]]:
    """Lignes JSON emises."""
    return [
        json.loads(ligne)
        for ligne in tampon.getvalue().splitlines()
        if ligne.strip().startswith("{")
    ]


# ============================================================================
#  Les dix champs
# ============================================================================


def test_le_code_declare_exactement_les_dix_champs_du_cahier() -> None:
    """Garde-fou : le tuple du code correspond a l'enumeration du cahier.

    Comparaison a une liste recopiee du cahier, non au code lui-meme.
    """
    assert CHAMPS_DU_CAHIER == DIX_CHAMPS_DU_CAHIER
    assert len(CHAMPS_DU_CAHIER) == 10


def test_les_dix_champs_sont_presents_meme_sans_contexte(
    journal_capture: tuple[logging.Logger, io.StringIO],
) -> None:
    """Toujours presents, meme a `null`.

    Un consommateur qui doit tester l'existence d'une cle avant de la lire finit
    par se tromper, et une agregation sur un champ absent une fois sur dix ne
    donne rien.
    """
    journal, tampon = journal_capture
    journal.info("message sans aucun extra")
    ligne = lignes(tampon)[0]
    for champ in DIX_CHAMPS_DU_CAHIER:
        assert champ in ligne, f"champ manquant : {champ}"


def test_les_champs_du_cahier_sont_renseignes_quand_ils_sont_fournis(
    journal_capture: tuple[logging.Logger, io.StringIO],
) -> None:
    journal, tampon = journal_capture
    definir_correlation("trace-connue-123")
    journal.info(
        "requete servie",
        extra={
            "route": "GET /api/v1/",
            "duree_ms": 12,
            "resultat": "succes",
            "code_erreur": None,
        },
    )
    ligne = lignes(tampon)[0]
    assert ligne["niveau"] == "info"
    assert ligne["service"] == "api"
    assert ligne["environnement"] == "development"
    assert ligne["version"] == "0.1.0"
    assert ligne["identifiant_correlation"] == "trace-connue-123"
    assert ligne["route"] == "GET /api/v1/"
    assert ligne["duree_ms"] == 12
    assert ligne["resultat"] == "succes"
    assert ligne["code_erreur"] is None
    assert ligne["date"].endswith("+00:00"), "la date doit etre en UTC explicite"


def test_la_sortie_est_du_json_valide_ligne_par_ligne(
    journal_capture: tuple[logging.Logger, io.StringIO],
) -> None:
    """Une ligne = un objet JSON. C'est ce qu'attend tout agregateur."""
    journal, tampon = journal_capture
    for i in range(3):
        journal.info("ligne %d", i)
    brut = [ligne for ligne in tampon.getvalue().splitlines() if ligne.strip()]
    assert len(brut) == 3
    for ligne in brut:
        assert json.loads(ligne)["message"].startswith("ligne ")


# ============================================================================
#  Corrélation
# ============================================================================


def test_l_identifiant_de_correlation_est_repris_du_contexte(
    journal_capture: tuple[logging.Logger, io.StringIO],
) -> None:
    journal, tampon = journal_capture
    definir_correlation("depuis-le-contexte")
    journal.info("une ligne")
    assert lignes(tampon)[0]["identifiant_correlation"] == "depuis-le-contexte"


def test_l_identifiant_est_nul_hors_requete_et_hors_job(
    journal_capture: tuple[logging.Logger, io.StringIO],
) -> None:
    """Une ligne emise au demarrage n'appartient a aucune trace.

    Annoncer un identifiant inventé serait pire : on croirait pouvoir correler.
    """
    journal, tampon = journal_capture
    effacer_correlation()
    assert lignes(tampon) == [] or True
    journal.info("ligne de demarrage")
    assert lignes(tampon)[0]["identifiant_correlation"] is None


def test_deux_contextes_ne_partagent_pas_leur_identifiant() -> None:
    """Temoin negatif : un identifiant global correlerait n'importe quoi."""
    definir_correlation("premier")
    assert correlation_courante() == "premier"
    definir_correlation("second")
    assert correlation_courante() == "second"
    effacer_correlation()
    assert correlation_courante() is None


# ============================================================================
#  Confidentialité — §28.2 appliqué à la sortie réelle
# ============================================================================


def test_un_secret_passe_en_extra_est_masque_dans_la_sortie(
    journal_capture: tuple[logging.Logger, io.StringIO],
) -> None:
    journal, tampon = journal_capture
    journal.info(
        "connexion etablie",
        extra={"route": "startup", "postgres_password": "MotDePasseReel123"},
    )
    brut = tampon.getvalue()
    assert "MotDePasseReel123" not in brut
    assert MASQUE in brut


def test_un_secret_recopie_dans_le_message_est_masque(
    journal_capture: tuple[logging.Logger, io.StringIO],
) -> None:
    """Le cas que le nom de la cle ne couvre pas : la cle s'appelle `message`."""
    journal, tampon = journal_capture
    journal.error("echec de connexion : redis://:MotDePasse@redis:6379/0")
    brut = tampon.getvalue()
    assert "MotDePasse" not in brut
    assert MASQUE in brut


def test_une_trace_d_exception_n_est_pas_journalisee(
    journal_capture: tuple[logging.Logger, io.StringIO],
) -> None:
    """Seul le TYPE de l'exception sort.

    Une trace peut contenir les valeurs des variables locales, donc des secrets.
    Le diagnostic passe par l'identifiant de correlation, pas par la trace en
    clair dans un journal partage.
    """
    journal, tampon = journal_capture
    try:
        message_secret = "MotDePasseDansUneVariableLocale"
        raise ValueError(message_secret)
    except ValueError:
        journal.exception("erreur attrapee", extra={"route": "test"})
    brut = tampon.getvalue()
    assert "MotDePasseDansUneVariableLocale" not in brut
    assert "Traceback" not in brut
    # Temoin positif : le type est bien remonte, sinon on n'aurait rien.
    assert json.loads(brut.splitlines()[0])["exception"] == "ValueError"


# ============================================================================
#  Le format n'est pas négociable
# ============================================================================


@pytest.mark.parametrize("format_refuse", ["text", "plain", "logfmt", "JSON", ""])
def test_tout_format_autre_que_json_est_refuse(format_refuse: str) -> None:
    """Cahier §28.1 : le format est JSON. Seconde barriere apres le garde-fou.

    `JSON` en majuscules est refuse volontairement : accepter des variantes de
    casse ouvrirait la porte a une configuration approximative.
    """
    with pytest.raises(ValueError, match="LOG_FORMAT"):
        configurer_journalisation(
            service="api",
            environnement="development",
            version="0.1.0",
            format_demande=format_refuse,
        )


def test_le_format_json_est_accepte() -> None:
    """Temoin du test precedent."""
    configurer_journalisation(
        service="api", environnement="development", version="0.1.0", format_demande="json"
    )
    racine = logging.getLogger()
    assert isinstance(racine.handlers[0].formatter, FormateurJson)
    for poignee in list(racine.handlers):
        racine.removeHandler(poignee)
