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
from collections.abc import Iterator
from typing import Any

import pytest

from app.configuration.settings import Parametres, parametres_en_cache

HOTE_LOCAL = "127.0.0.1"
DELAI_CONNEXION = 1.0

# Jeu minimal permettant a la configuration d'etre valide en developpement.
# Aucune de ces valeurs n'est un secret : elles ne servent qu'aux tests.
VARIABLES_MINIMALES: dict[str, Any] = {
    #  LOT 3, T7 : `APP_SECRET_KEY` est devenue OBLIGATOIRE dans tous les
    #  environnements — elle derive le jeton anti-CSRF, et `jeton_pour` leve sur
    #  une cle vide. Sans elle ici, tous les tests unitaires echoueraient sur le
    #  garde-fou, ce qui est exactement son role.
    #
    #  Cette valeur n'est pas un secret : elle depasse les 32 caracteres que le
    #  garde-fou de production exige, et aucun test unitaire n'ouvre de session.
    "APP_SECRET_KEY": "cle-de-test-sans-portee-quarante-caracteres",
    "POSTGRES_DB": "onboarding_test",
    "POSTGRES_USER": "utilisateur_de_test",
    "POSTGRES_PASSWORD": "valeur-de-test-sans-portee",
    #  LOT 3, T1 : les quatre variables des deux roles sont OBLIGATOIRES depuis
    #  `QO-116`, donc un test unitaire qui construit `Parametres` sans elles
    #  echouerait sur le garde-fou -- ce qui est exactement ce que le garde-fou
    #  doit faire. Ces valeurs n'ont aucune portee : aucun test unitaire ne se
    #  connecte.
    "POSTGRES_MIGRATIONS_USER": "migrations_de_test",
    "POSTGRES_MIGRATIONS_PASSWORD": "valeur-de-test-sans-portee",
    "POSTGRES_RUNTIME_USER": "execution_de_test",
    "POSTGRES_RUNTIME_PASSWORD": "valeur-de-test-sans-portee",
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


#  Etat de la sonde Redis, decide UNE FOIS pour toute la session.
#
#  `None` = pas encore sonde. Voir la fixture ci-dessous : sonder a chaque test
#  serait deja du gaspillage, mais **tenter une CONNEXION a chaque test quand
#  Redis est absent a bloque l'integration continue**.
_redis_joignable: bool | None = None


def _purger_les_compteurs_de_debit() -> None:
    """Effacer les compteurs de limitation de debit. Silencieuse et BORNEE.

    **LE COUT D'UN REDIS ABSENT EST LA RAISON D'ETRE DE CETTE FONCTION.** Ma
    premiere version ouvrait un client redis-py directement, en s'appuyant sur
    `socket_connect_timeout=1` pour borner l'attente. **Ce delai ne bornait
    rien** : redis-py 8 reprend DIX fois par defaut, et une tentative sur un port
    ferme coute **4,06 s** -- mesure faite. A deux purges par test et 613 tests,
    la tache « qualite » de l'integration continue, qui n'a **pas** de stack, est
    restee bloquee **plus de quatre-vingts minutes** sur l'etape des tests
    unitaires.

    Deux parades, et la premiere suffit presque :

      1. **la sonde de port precede la connexion**, et son resultat est memorise
         pour la session. `port_ouvert` coute **0,001 s** sur un port ferme, contre
         4,06 s pour redis-py -- soit quatre mille fois moins ;
      2. **la reprise est bornee a zero**, ce qui ramene une tentative ratee a
         0,003 s. Elle couvre le cas ou le port est ouvert mais Redis ne repond
         pas -- un conteneur qui demarre, par exemple.

    Elle reste silencieuse sur echec : un test unitaire ne doit dependre d'aucune
    stack, et lever ici ferait echouer des tests qui n'ont rien demande.
    """
    global _redis_joignable  # decision de session, memorisee une seule fois

    env = lire_env_du_depot()
    port = int(env.get("REDIS_HOST_PORT", "6379"))
    if _redis_joignable is None:
        _redis_joignable = port_ouvert(HOTE_LOCAL, port)
    if not _redis_joignable:
        return

    try:
        import redis
        from redis.backoff import NoBackoff
        from redis.retry import Retry

        from app.auth.debit import PREFIXE_REDIS

        client = redis.Redis(
            host=HOTE_LOCAL,
            port=port,
            password=env.get("REDIS_PASSWORD") or None,
            socket_connect_timeout=1,
            socket_timeout=1,
            retry=Retry(NoBackoff(), 0),
        )
        cles = list(client.scan_iter(match=f"{PREFIXE_REDIS}*", count=500))
        if cles:
            client.delete(*cles)
        client.close()
    except Exception:  # noqa: S110 — Redis absent ou en cours de demarrage
        pass


@pytest.fixture(autouse=True)
def compteurs_de_debit_neufs() -> Iterator[None]:
    """Effacer les compteurs de limitation de debit AVANT chaque test.

    LOT 3, `T8`. **CETTE FIXTURE EST AUTOUSE, ET C'EST UN CHOIX MESURE.**

    `T8` a ajoute une CONDITION a deux operations qui existaient deja : dix
    demandes de lien par adresse et par heure, cinq echecs administrateur par
    adresse. Les compteurs vivent dans Redis, donc **ils survivent d'un test au
    suivant** -- contrairement a une transaction annulee ou a un nettoyage SQL.

    Consequence immediate, et deux tests l'ont montree : un fichier qui produit
    cinq refus administrateur sur la meme adresse voit le sixieme rendre **429 au
    lieu de 400**, et il echoue sur un livrable conforme. C'est le §7.21 -- un
    controle juste hier, rendu faux par ce que nous venons d'ajouter.

    **POURQUOI ICI ET NON DANS LES FIXTURES CONCERNEES.** Corriger les deux
    fichiers fautifs aurait produit une liste implicite des fichiers a corriger,
    qui vieillit au premier test ajoute -- c'est exactement le §7.27, trois
    occurrences dans ce lot. Une fixture `autouse` couvre les fichiers presents
    **et futurs**.

    Le cout quand Redis est absent est traite dans `_purger_les_compteurs_de_debit`,
    et il n'est pas anecdotique : c'est ce qui a bloque l'integration continue.
    """
    _purger_les_compteurs_de_debit()
    yield
    #  **ET APRES AUSSI** : sans cela, `make debit-check` verrait les compteurs
    #  laisses par la suite de tests et son propre comptage serait faux.
    _purger_les_compteurs_de_debit()


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
        #  LOT 3, T7 : la VRAIE cle du `.env`, parce que les tests d'integration
        #  derivent des jetons anti-CSRF que l'API doit reconnaitre. Une cle
        #  differente de celle de l'API ferait echouer chaque jeton, et le message
        #  ne dirait pas que la cause est une variable non transmise -- c'est ce
        #  qui est arrive aux quatre roles PostgreSQL en `T1`.
        "APP_SECRET_KEY",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        #  MOINDRE PRIVILEGE — LOT 3, T1, `QO-116`, `DEC-518`.
        #  Les tests d'integration se connectent par `url_postgresql()`, qui
        #  emploie desormais le role d'EXECUTION. Sans ces quatre lignes, la
        #  connexion echoue sur « fe_sendauth: no password supplied » -- et le
        #  message ne dit pas que la cause est une variable non transmise.
        #  Les employer ici est le bon choix : **les tests eprouvent ainsi le
        #  MEME role que l'application**, donc ils echoueraient si un droit
        #  manquait a l'execution.
        "POSTGRES_MIGRATIONS_USER",
        "POSTGRES_MIGRATIONS_PASSWORD",
        "POSTGRES_RUNTIME_USER",
        "POSTGRES_RUNTIME_PASSWORD",
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
