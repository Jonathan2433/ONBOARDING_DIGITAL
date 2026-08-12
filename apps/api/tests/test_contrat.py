"""Le schema OpenAPI reellement servi respecte-t-il le contrat partage ?

LOT 1, sous-etape T10, story MVP-L01-US007.

CE QUE CE CONTROLE FERME

    `packages/contracts/src/contrat-api.json` declare le contrat de l'API :
    chemins, methodes, codes exploitables. Le frontend en tire ses types et ses
    constantes. Sans controle, cette declaration serait une AFFIRMATION : rien
    n'empecherait l'API de renommer `/health/ready` en laissant le frontend
    interroger un chemin qui rend 404.

    Ce test lit le manifeste et le confronte au schema que l'application MONTE
    reellement. Une route ajoutee, retiree ou renommee sans mise a jour du
    manifeste fait echouer `make check`.

POURQUOI CE SENS DE VERIFICATION, ET NON UNE GENERATION

    On aurait pu engendrer les types TypeScript depuis le schema OpenAPI. Mesure
    du 30/07/2026 : `components.schemas` du schema servi est **VIDE** — les routes
    de sante rendent des dictionnaires sans modele de reponse declare. Generer
    depuis ce schema aurait produit des types `unknown`, donc l'illusion d'un
    contrat type. Le manifeste declare, et ce test verifie : c'est plus honnete,
    et cela echoue dans le sens utile.

    Le jour ou l'API declarera des modeles de reponse — au LOT 2, quand les
    premieres formes metier arriveront — la generation redeviendra possible, et ce
    test restera le garde-fou de la coherence.

CE QU'IL NE VERIFIE PAS, ET IL FAUT LE DIRE

    Il verifie l'ENSEMBLE DES CHEMINS et les codes DECLARES par le schema, pas les
    formes de reponse : le schema ne les porte pas. Les formes sont verifiees
    ailleurs — par `validerEtatServices` et `validerVersion` du paquet de contrat,
    appeles sur les reponses reelles par les tests du frontend, et par les tests
    de `apps/api/tests/test_sante.py` cote serveur.

    Il n'a pas besoin de la stack : il monte l'application et lit son schema, sans
    interroger PostgreSQL, Redis ni MinIO. Il n'est donc PAS marque `integration`,
    et il tourne dans `make test` comme dans l'integration continue.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from conftest import VARIABLES_MINIMALES
from fastapi.testclient import TestClient

from app.configuration.settings import Parametres
from app.main import creer_application

RACINE = Path(__file__).resolve().parents[3]
MANIFESTE = RACINE / "packages" / "contracts" / "src" / "contrat-api.json"


def _client() -> TestClient:
    """Un client monte sur une configuration VALIDE.

    `creer_application()` sans argument lit l'environnement, que la fixture
    `environnement_vierge` a efface : les onze garde-fous du cahier 20.3
    refusent alors de demarrer, et c'est leur role. On passe donc des
    parametres explicites, comme `test_sante.py` le fait depuis `T3`.
    """
    return TestClient(creer_application(Parametres(**VARIABLES_MINIMALES)))


@pytest.fixture(scope="module")
def contrat() -> dict[str, Any]:
    """Le manifeste partage, lu depuis le disque et non recopie ici."""
    assert MANIFESTE.is_file(), f"manifeste introuvable : {MANIFESTE}"
    donnees: dict[str, Any] = json.loads(MANIFESTE.read_text(encoding="utf-8"))
    return donnees


@pytest.fixture
def schema(environnement_vierge: None) -> dict[str, Any]:
    """Le schema OpenAPI que l'application monte reellement.

    `environnement_vierge` est la fixture de `conftest.py` : elle efface les
    variables du modele pour qu'un `.env` charge dans le terminal ne rende pas le
    resultat dependant de la machine. Meme convention que `test_sante.py`.
    """
    with _client() as client:
        reponse = client.get("/openapi.json")
    assert reponse.status_code == 200
    donnees: dict[str, Any] = reponse.json()
    return donnees


def test_le_manifeste_declare_au_moins_les_trois_endpoints_de_sante(
    contrat: dict[str, Any],
) -> None:
    """Un manifeste vide ferait passer toutes les comparaisons d'ensembles.

    C'est la parade au detecteur muet : sans ce controle, retirer toutes les
    entrees du manifeste rendrait les deux ensembles vides, donc egaux.
    """
    cles = {e["cle"] for e in contrat["endpoints"]}
    assert {"live", "ready", "version"} <= cles, f"cles declarees : {sorted(cles)}"
    assert len(contrat["endpoints"]) >= 3


def test_les_chemins_du_schema_sont_exactement_ceux_du_manifeste(
    contrat: dict[str, Any], schema: dict[str, Any]
) -> None:
    """L'egalite est exigee dans LES DEUX SENS, et c'est le point.

    Une inclusion simple laisserait passer deux derives opposees : une route
    ajoutee a l'API sans etre declaree — donc invisible du frontend — et une
    route declaree que l'API ne sert pas — donc un 404 chez le consommateur.
    """
    declares = {(e["chemin"], e["methode"].lower()) for e in contrat["endpoints"]}
    servis = {
        (chemin, methode.lower())
        for chemin, operations in schema["paths"].items()
        for methode in operations
    }
    assert declares == servis, (
        f"declares seulement : {sorted(declares - servis)} ; "
        f"servis seulement : {sorted(servis - declares)}"
    )


def test_chaque_code_declare_est_documente_par_le_schema(
    contrat: dict[str, Any], schema: dict[str, Any]
) -> None:
    """Les codes exploitables du manifeste existent bien dans le schema.

    Le 503 de `/health/ready` est le cas qui compte : le frontend le traite comme
    un etat DEGRADE exploitable, pas comme une erreur. Si l'API cessait de le
    documenter, la page de statut afficherait une panne la ou il y a un
    diagnostic.
    """
    examines = 0
    for entree in contrat["endpoints"]:
        operation = schema["paths"][entree["chemin"]][entree["methode"].lower()]
        documentes = set(operation.get("responses", {}))
        for code in entree["codesExploitables"]:
            examines += 1
            # AUCUNE ECHAPPATOIRE. Ma premiere version acceptait « ou code == 200 »,
            # parce que FastAPI documente 200 par defaut et pas les codes qu'une
            # route pose elle-meme. Le controle a alors constate que le 503 de
            # `/health/ready` n'etait PAS documente — un consommateur qui aurait
            # engendre son client depuis ce schema aurait traite le diagnostic
            # comme une erreur imprevue. La route le documente maintenant
            # (`responses=`), et l'exigence peut donc etre sans exception.
            assert str(code) in documentes, (
                f"{entree['chemin']} : code {code} declare exploitable par le "
                f"contrat mais ABSENT du schema, qui documente {sorted(documentes)}"
            )
    assert examines >= 5, f"{examines} codes examines, au moins 5 attendus"


def test_le_prefixe_versionne_du_manifeste_est_celui_de_l_application(
    contrat: dict[str, Any], schema: dict[str, Any]
) -> None:
    """Et les endpoints de sante en sont bien EXCLUS — DEC-465.

    Les prefixer par megarde produirait un 404 que rien ne distinguerait d'une API
    mal deployee. C'est la raison pour laquelle `DEC-465` les place hors du
    prefixe, et ce controle le verifie sur le schema plutot que sur une intention.
    """
    prefixe = contrat["prefixeVersionne"]
    assert any(chemin.startswith(prefixe) for chemin in schema["paths"]), (
        f"aucun chemin sous {prefixe} : le prefixe declare n'est pas celui monte"
    )
    sante = [e["chemin"] for e in contrat["endpoints"] if e["chemin"].startswith("/health/")]
    assert len(sante) == 3, f"3 endpoints de sante attendus, {len(sante)} declares"
    for chemin in sante:
        assert not chemin.startswith(prefixe), f"{chemin} ne doit PAS etre prefixe (DEC-465)"


@pytest.mark.usefixtures("environnement_vierge")
def test_l_en_tete_de_correlation_declare_est_celui_que_l_api_renvoie(
    contrat: dict[str, Any],
) -> None:
    """Le nom de l'en-tete est partage par l'API, le worker et le frontend.

    Le verifier sur une REPONSE REELLE et non sur une constante : c'est le seul
    moyen de savoir que le middleware le pose effectivement sous ce nom.
    """
    with _client() as client:
        reponse = client.get("/health/live")
    assert reponse.status_code == 200
    attendu = contrat["enTeteCorrelation"]
    assert attendu in reponse.headers, (
        f"en-tete {attendu} absent de la reponse ; en-tetes recus : {sorted(reponse.headers)}"
    )
