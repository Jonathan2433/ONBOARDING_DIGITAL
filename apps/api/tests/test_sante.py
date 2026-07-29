"""Les trois endpoints de sante, et le format d'erreur.

LOT 1, sous-etape T3, story MVP-L01-US003.

FONDEMENT
    Cahier §18.7 pour les trois endpoints, §18.3 pour le format d'erreur.
    Critere litteral du backlog : « Chaque endpoint retourne un statut
    explicite ; readiness verifie les dependances necessaires ; la version
    correspond au build. »

CE QUI EST EPROUVE ICI SANS AUCUN SERVICE REEL
    Que `ready` repond **503** quand les dependances sont injoignables. C'est
    le test le plus important du fichier : un `ready` qui repond 200 sans base
    de donnees est un controle qui ne peut pas echouer, donc un controle
    inutile. Il est obtenu en pointant la configuration vers des ports fermes,
    ce qui ne demande d'arreter aucun service.

    La reciproque — `ready` repond 200 quand tout va bien — exige des services
    reels : elle est dans `test_integration.py`, marquee `integration`.
"""

from __future__ import annotations

from typing import Any

import pytest
from conftest import VARIABLES_MINIMALES
from fastapi.testclient import TestClient

from app.configuration.settings import Parametres
from app.main import creer_application
from app.shared.correlation import EN_TETE_CORRELATION

# Port de la plage dynamique, sur lequel rien n'ecoute. Sert a rendre les
# dependances volontairement injoignables.
PORT_FERME = 59999


def _parametres(**surcharges: Any) -> Parametres:
    valeurs = dict(VARIABLES_MINIMALES)
    valeurs.update(surcharges)
    return Parametres(**valeurs)


def _client(**surcharges: Any) -> TestClient:
    return TestClient(creer_application(_parametres(**surcharges)), raise_server_exceptions=False)


@pytest.fixture
def client_sans_dependances(environnement_vierge: None) -> TestClient:
    """Client dont les trois dependances pointent vers des ports fermes."""
    _ = environnement_vierge
    return _client(
        POSTGRES_HOST="127.0.0.1",
        POSTGRES_PORT=PORT_FERME,
        REDIS_HOST="127.0.0.1",
        REDIS_PORT=PORT_FERME,
        MINIO_ENDPOINT=f"127.0.0.1:{PORT_FERME}",
    )


# ============================================================================
#  /health/live
# ============================================================================


def test_live_repond_200_sans_toucher_aux_dependances(
    client_sans_dependances: TestClient,
) -> None:
    """`live` reste vert meme sans base de donnees, et c'est voulu.

    Si `live` sondait PostgreSQL, une panne de base ferait redemarrer l'API en
    boucle par l'orchestrateur, sans jamais corriger la cause.
    """
    reponse = client_sans_dependances.get("/health/live")
    assert reponse.status_code == 200
    assert reponse.json() == {"statut": "TEMOIN_T6_ATTENTE_FAUSSEE"}


# ============================================================================
#  /health/ready — le test qui compte
# ============================================================================


def test_ready_repond_503_quand_les_dependances_sont_injoignables(
    client_sans_dependances: TestClient,
) -> None:
    """Temoin negatif de la disponibilite : sans dependances, `ready` echoue."""
    reponse = client_sans_dependances.get("/health/ready")
    assert reponse.status_code == 503
    corps = reponse.json()
    assert corps["statut"] == "indisponible"
    assert {d["nom"] for d in corps["dependances"]} == {"postgresql", "redis", "minio"}
    assert all(d["statut"] == "indisponible" for d in corps["dependances"])


def test_ready_detaille_chaque_dependance(
    client_sans_dependances: TestClient,
) -> None:
    """Le diagnostic ne doit pas exiger de lire les journaux."""
    corps = client_sans_dependances.get("/health/ready").json()
    for dependance in corps["dependances"]:
        assert set(dependance) == {"nom", "statut", "duree_ms", "motif"}
        assert dependance["motif"], "le motif d'indisponibilite doit etre renseigne"


def test_ready_ne_divulgue_aucun_secret(client_sans_dependances: TestClient) -> None:
    """`/health/ready` est interrogeable sans authentification.

    Le motif remonte est le TYPE de l'exception, jamais son message : un message
    de pilote peut contenir un identifiant, un nom d'utilisateur ou une URL avec
    mot de passe.
    """
    brut = client_sans_dependances.get("/health/ready").text
    for valeur in VARIABLES_MINIMALES.values():
        assert str(valeur) not in brut


# ============================================================================
#  /health/version
# ============================================================================


@pytest.mark.usefixtures("environnement_vierge")
def test_version_expose_la_version_et_la_revision() -> None:
    """« La version correspond au build » : elle vient de la configuration."""
    client = _client(APP_VERSION="0.1.0", APP_REVISION="abc1234", APP_ENV="recette")
    corps = client.get("/health/version").json()
    assert corps == {
        "version": "0.1.0",
        "revision": "abc1234",
        "environnement": "recette",
    }


@pytest.mark.usefixtures("environnement_vierge")
def test_version_annonce_inconnue_plutot_qu_une_revision_inventee() -> None:
    """Afficher `0.0.0` serait affirmer une version qu'on ne connait pas."""
    assert _client().get("/health/version").json()["revision"] == "inconnue"


# ============================================================================
#  Contrat versionne et documentation interactive
# ============================================================================


@pytest.mark.usefixtures("environnement_vierge")
def test_le_prefixe_versionne_est_monte() -> None:
    """`/api/v1` ne doit pas renvoyer 404 : ce serait indistinguable d'un
    deploiement rate."""
    corps = _client().get("/api/v1/").json()
    assert corps["version_contrat"] == "v1"


@pytest.mark.usefixtures("environnement_vierge")
def test_la_documentation_interactive_est_servie_hors_production() -> None:
    """Temoin positif : en developpement, la documentation est disponible."""
    assert _client(APP_ENV="development", API_DOCS_ENABLED=True).get("/docs").status_code == 200


@pytest.mark.usefixtures("environnement_vierge")
def test_la_documentation_interactive_est_absente_en_production() -> None:
    """Cahier §18.1 : documentation interactive interdite en production.

    Seconde barriere apres le garde-fou de configuration. Le test force
    `API_DOCS_ENABLED=true` en production pour prouver que meme une
    configuration fautive ne suffit pas a l'exposer.
    """
    client = _client(APP_ENV="production", API_DOCS_ENABLED=True)
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


# ============================================================================
#  Format d'erreur du cahier §18.3
# ============================================================================


@pytest.mark.usefixtures("environnement_vierge")
def test_une_erreur_porte_les_cinq_champs_du_cahier() -> None:
    """Code, message, champ, details, identifiant de correlation."""
    reponse = _client().get("/route-qui-nexiste-pas")
    assert reponse.status_code == 404
    erreur = reponse.json()["erreur"]
    assert set(erreur) == {
        "code",
        "message",
        "champ",
        "details",
        "identifiant_correlation",
    }
    assert erreur["code"] == "http_404"
    assert erreur["identifiant_correlation"]


@pytest.mark.usefixtures("environnement_vierge")
def test_l_identifiant_de_correlation_fourni_par_l_appelant_est_repris() -> None:
    """Une trace de bout en bout doit pouvoir traverser plusieurs services."""
    fourni = "trace-de-bout-en-bout-123"
    reponse = _client().get("/route-qui-nexiste-pas", headers={EN_TETE_CORRELATION: fourni})
    assert reponse.json()["erreur"]["identifiant_correlation"] == fourni
    assert reponse.headers[EN_TETE_CORRELATION] == fourni


@pytest.mark.usefixtures("environnement_vierge")
def test_un_identifiant_est_engendre_quand_l_appelant_n_en_fournit_pas() -> None:
    """Aucune reponse ne doit sortir sans identifiant de correlation."""
    reponse = _client().get("/health/live")
    assert reponse.headers[EN_TETE_CORRELATION]


@pytest.mark.usefixtures("environnement_vierge")
def test_deux_requetes_recoivent_deux_identifiants_distincts() -> None:
    """Temoin negatif : un identifiant constant ne correlerait rien."""
    client = _client()
    premier = client.get("/health/live").headers[EN_TETE_CORRELATION]
    second = client.get("/health/live").headers[EN_TETE_CORRELATION]
    assert premier != second
