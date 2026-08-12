"""Journalisation des requetes HTTP.

LOT 1, sous-etape T4, story MVP-L01-US004.

Critere litteral : « chaque requete ET chaque job portent un correlation_id ».
Ce fichier eprouve la moitie « requete » ; la moitie « job » est dans
`apps/worker/tests/test_journal_worker.py`.
"""

from __future__ import annotations

import io
import json
import logging
from collections.abc import Iterator
from typing import Any

import pytest
from conftest import VARIABLES_MINIMALES
from fastapi.testclient import TestClient

from app.configuration.settings import Parametres
from app.main import creer_application
from app.shared.journal import ROUTES_SILENCIEUSES_SI_SUCCES, resultat_de
from observabilite.correlation import EN_TETE_CORRELATION
from observabilite.masquage import MASQUE


@pytest.fixture
def client_et_journal(
    environnement_vierge: None,
) -> Iterator[tuple[TestClient, io.StringIO]]:
    """Une application dont la sortie de journal est capturee."""
    _ = environnement_vierge
    application = creer_application(Parametres(**VARIABLES_MINIMALES, APP_VERSION="0.1.0"))
    tampon = io.StringIO()
    racine = logging.getLogger()
    racine.handlers[0].stream = tampon  # type: ignore[attr-defined]
    yield TestClient(application, raise_server_exceptions=False), tampon
    for poignee in list(racine.handlers):
        racine.removeHandler(poignee)


def lignes(tampon: io.StringIO) -> list[dict[str, Any]]:
    return [
        json.loads(ligne)
        for ligne in tampon.getvalue().splitlines()
        if ligne.strip().startswith("{")
    ]


# ============================================================================
#  Chaque requête porte un identifiant de corrélation
# ============================================================================


def test_chaque_requete_est_journalisee_avec_son_identifiant(
    client_et_journal: tuple[TestClient, io.StringIO],
) -> None:
    client, tampon = client_et_journal
    client.get("/api/v1/", headers={EN_TETE_CORRELATION: "trace-connue"})
    ligne = lignes(tampon)[0]
    assert ligne["identifiant_correlation"] == "trace-connue"
    assert ligne["route"] == "GET /api/v1/"
    assert ligne["service"] == "api"
    assert ligne["duree_ms"] is not None


def test_deux_requetes_donnent_deux_traces_distinctes(
    client_et_journal: tuple[TestClient, io.StringIO],
) -> None:
    """Temoin negatif : un identifiant constant ne correlerait rien."""
    client, tampon = client_et_journal
    client.get("/api/v1/")
    client.get("/api/v1/")
    identifiants = {ligne["identifiant_correlation"] for ligne in lignes(tampon)}
    assert len(identifiants) == 2


# ============================================================================
#  Les trois résultats
# ============================================================================


@pytest.mark.parametrize(
    ("statut", "attendu"),
    [(200, "succes"), (302, "succes"), (400, "refus"), (404, "refus"), (500, "echec")],
)
def test_le_resultat_distingue_succes_refus_et_echec(statut: int, attendu: str) -> None:
    """Annoncer `succes` sur un 404 a cote d'un `code_erreur` serait contradictoire.

    Trois valeurs et non deux : `refus` dit que la faute est a l'appelant,
    `echec` qu'elle est a nous. Seul `echec` justifie un niveau `error`, sinon
    une adresse mal tapee ferait sonner une alerte.
    """
    assert resultat_de(statut) == attendu


def test_un_404_est_journalise_en_refus_et_non_en_erreur(
    client_et_journal: tuple[TestClient, io.StringIO],
) -> None:
    client, tampon = client_et_journal
    client.get("/route-absente")
    ligne = lignes(tampon)[0]
    assert ligne["resultat"] == "refus"
    assert ligne["code_erreur"] == "http_404"
    assert ligne["niveau"] == "info", "un 404 ne doit pas faire sonner une alerte"


# ============================================================================
#  Le bruit des sondes de santé
# ============================================================================


@pytest.mark.parametrize("chemin", sorted(ROUTES_SILENCIEUSES_SI_SUCCES))
def test_les_sondes_de_sante_ne_sont_pas_journalisees_quand_elles_reussissent(
    chemin: str, client_et_journal: tuple[TestClient, io.StringIO]
) -> None:
    """Docker les interroge toutes les dix secondes : 8 640 lignes par jour.

    `/health/ready` echoue ici, faute de services : seuls `live` et `version`
    sont reellement silencieux. Le test l'accepte pour les deux cas.
    """
    client, tampon = client_et_journal
    reponse = client.get(chemin)
    journalisee = any(ligne["route"].endswith(chemin) for ligne in lignes(tampon))
    if reponse.status_code < 400:
        assert not journalisee, f"{chemin} ne devait pas etre journalisee"
    else:
        assert journalisee, f"{chemin} en echec doit etre journalisee"


def test_une_sonde_de_sante_en_echec_est_journalisee(
    client_et_journal: tuple[TestClient, io.StringIO],
) -> None:
    """Le silence ne doit jamais masquer une panne.

    `/health/ready` repond 503 sans services : la ligne doit sortir.
    """
    client, tampon = client_et_journal
    reponse = client.get("/health/ready")
    assert reponse.status_code == 503
    routes = [ligne["route"] for ligne in lignes(tampon)]
    assert any("/health/ready" in route for route in routes)


# ============================================================================
#  Confidentialité — §28.2
# ============================================================================


def test_la_chaine_de_requete_n_est_jamais_journalisee(
    client_et_journal: tuple[TestClient, io.StringIO],
) -> None:
    """Un magic link du LOT 3 passera par la : `?token=...`.

    Le §28.2 interdit le magic link complet. La parade la plus sure est de ne
    pas ecrire la chaine de requete du tout.
    """
    client, tampon = client_et_journal
    client.get("/api/v1/?token=JetonQuiNeDoitPasEtreJournalise&page=2")
    brut = tampon.getvalue()
    assert "JetonQuiNeDoitPasEtreJournalise" not in brut
    assert "page=2" not in brut
    # Temoin positif : la requete a bien ete journalisee, sinon l'absence
    # ci-dessus ne prouverait rien.
    assert lignes(tampon)[0]["route"] == "GET /api/v1/"


def test_aucune_valeur_de_configuration_n_apparait_dans_les_journaux(
    client_et_journal: tuple[TestClient, io.StringIO],
) -> None:
    """Controle d'ensemble sur la sortie reelle."""
    client, tampon = client_et_journal
    client.get("/api/v1/")
    client.get("/health/ready")
    brut = tampon.getvalue()
    for valeur in VARIABLES_MINIMALES.values():
        assert str(valeur) not in brut, f"valeur de configuration divulguee : {valeur}"


def test_un_secret_journalise_explicitement_est_masque(
    client_et_journal: tuple[TestClient, io.StringIO],
) -> None:
    """Le filtre s'applique aussi a ce que le code applicatif journalise."""
    client, tampon = client_et_journal
    _ = client
    logging.getLogger("app.test").info(
        "tentative", extra={"route": "test", "smtp_password": "MotDePasseSmtp"}
    )
    brut = tampon.getvalue()
    assert "MotDePasseSmtp" not in brut
    assert MASQUE in brut
