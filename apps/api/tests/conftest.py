"""Fixtures partagees des tests de l'API.

LOT 1, sous-etape T3, story MVP-L01-US003.

DEUX FAMILLES DE TESTS, ET POURQUOI ELLES SONT SEPAREES

  unitaires    Aucune dependance externe. Ils tournent partout, y compris en
               integration continue sans conteneur.
  integration  Ils exigent PostgreSQL, Redis et MinIO REELS. Le modele §28
               l'impose pour les migrations : « exécution sur PostgreSQL reel,
               jamais SQLite ».

Les tests d'integration se connectent aux ports publies sur la boucle locale
par la stack de developpement. Ils portent le marqueur `integration`.

ATTENTION : un test ignore n'est PAS un test qui passe. La cible
`make test-integration` ECHOUE si la stack est absente, au lieu de les ignorer
en silence — c'est elle qui donne la preuve, pas `make test`.
"""

from __future__ import annotations

import pathlib
import socket
from typing import Any

import pytest

from app.configuration.settings import Parametres, parametres_en_cache

HOTE_LOCAL = "127.0.0.1"
DELAI_CONNEXION = 1.0

# Jeu minimal permettant a la configuration d'etre valide en developpement.
# Aucune de ces valeurs n'est un secret : elles ne servent qu'aux tests.
VARIABLES_MINIMALES: dict[str, Any] = {
    "POSTGRES_DB": "onboarding_test",
    "POSTGRES_USER": "utilisateur_de_test",
    "POSTGRES_PASSWORD": "valeur-de-test-sans-portee",
    "REDIS_PASSWORD": "valeur-de-test-sans-portee",
    "MINIO_ROOT_USER": "utilisateur-de-test",
    "MINIO_ROOT_PASSWORD": "valeur-de-test-sans-portee",
    "MINIO_BUCKET": "bucket-de-test",
}


def port_ouvert(hote: str, port: int) -> bool:
    """Le port accepte-t-il une connexion TCP ?

    Ne sert QU'A decider si l'on tente les tests d'integration. Ne remplace pas
    les sondes de `/health/ready`, qui font un aller-retour applicatif reel :
    un port ouvert ne prouve pas qu'un service repond.
    """
    try:
        with socket.create_connection((hote, port), timeout=DELAI_CONNEXION):
            return True
    except OSError:
        return False


def lire_env_du_depot() -> dict[str, str]:
    """Lire le `.env` du depot pour obtenir les identifiants reels de la stack.

    Le fichier n'est pas versionne et ses valeurs sont engendrees localement par
    `make env` : aucun secret ne transite par le depot.
    """
    racine = pathlib.Path(__file__).resolve().parents[3]
    fichier = racine / ".env"
    if not fichier.exists():
        return {}
    valeurs: dict[str, str] = {}
    for brut in fichier.read_text(encoding="utf-8").splitlines():
        ligne = brut.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, _, valeur = ligne.partition("=")
        valeurs[cle.strip()] = valeur.strip()
    return valeurs


@pytest.fixture
def environnement_vierge(monkeypatch: pytest.MonkeyPatch) -> None:
    """Effacer toutes les variables connues du modele de configuration.

    Sans cela, un `.env` charge dans le terminal de l'operateur rendrait le
    resultat des tests dependant de sa machine : le test passerait chez lui et
    echouerait en integration continue, ou l'inverse.
    """
    for nom in Parametres.model_fields:
        monkeypatch.delenv(nom, raising=False)
    parametres_en_cache.cache_clear()


@pytest.fixture
def parametres_de_la_stack(environnement_vierge: None) -> Parametres:
    """Configuration pointant vers la stack de developpement, via la boucle locale.

    Les hotes internes `db`, `redis` et `minio` ne sont resolvables que dans le
    reseau Compose : depuis la machine, on passe par les ports publies sur
    127.0.0.1.
    """
    _ = environnement_vierge
    env = lire_env_du_depot()
    valeurs = dict(VARIABLES_MINIMALES)
    for nom in (
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "REDIS_PASSWORD",
        "MINIO_ROOT_USER",
        "MINIO_ROOT_PASSWORD",
        "MINIO_BUCKET",
    ):
        if nom in env:
            valeurs[nom] = env[nom]
    return Parametres(
        **valeurs,
        POSTGRES_HOST=HOTE_LOCAL,
        POSTGRES_PORT=int(env.get("POSTGRES_HOST_PORT", "5432")),
        REDIS_HOST=HOTE_LOCAL,
        REDIS_PORT=int(env.get("REDIS_HOST_PORT", "6379")),
        MINIO_ENDPOINT=f"{HOTE_LOCAL}:{env.get('MINIO_HOST_PORT', '9000')}",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Declarer le marqueur d'integration."""
    config.addinivalue_line("markers", "integration: exige PostgreSQL, Redis et MinIO reels")
