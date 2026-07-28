"""Application FastAPI.

LOT 1, sous-etape T3, story MVP-L01-US003.

FONDEMENT — cahier des charges §18.1 : REST JSON interne, prefixe `/api/v1`,
OpenAPI genere, **documentation interactive uniquement en developpement et en
recette**, aucun acces public externe dans le MVP.

CE QUE CE MODULE NE FAIT PAS, ET NE DOIT PAS FAIRE AU LOT 1
    Aucune route metier, aucun modele SQLAlchemy metier, **aucune
    authentification, meme partielle, meme de test**, et aucun mecanisme de
    contournement. Les modules metier du cahier §16.1 appartiennent au LOT 2 et
    aux suivants, l'authentification au LOT 3.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.configuration.settings import Parametres, parametres_en_cache
from app.health import routeur as routeur_sante
from app.shared.correlation import EN_TETE_CORRELATION, definir_correlation
from app.shared.errors import (
    ErreurApplicative,
    gerer_erreur_applicative,
    gerer_erreur_http,
    gerer_erreur_inattendue,
    gerer_erreur_validation,
)
from app.shared.journal import journaliser_requete
from observabilite import configurer_journalisation


def creer_application(parametres: Parametres | None = None) -> FastAPI:
    """Assembler l'application.

    La configuration est passee en argument plutot que lue ici, pour que les
    tests puissent construire une application avec une configuration choisie
    sans toucher a l'environnement du processus.
    """
    config = parametres or parametres_en_cache()

    # La journalisation est installee AVANT tout le reste : une erreur survenant
    # pendant l'assemblage doit deja sortir au format JSON du cahier §28.1.
    # `LOG_FORMAT` est deja valide par le garde-fou de configuration ; l'appel
    # ci-dessous echouerait de toute facon sur une autre valeur.
    configurer_journalisation(
        service="api",
        environnement=config.APP_ENV,
        version=config.APP_VERSION,
        niveau=config.LOG_LEVEL,
        format_demande=config.LOG_FORMAT,
    )

    # La documentation interactive est INTERDITE en production (cahier §18.1).
    # Le garde-fou de configuration refuse deja de demarrer si
    # API_DOCS_ENABLED vaut true en production ; ceci est la seconde barriere,
    # au cas ou la premiere serait un jour contournee.
    documentation_active = config.API_DOCS_ENABLED and config.APP_ENV != "production"

    application = FastAPI(
        title="eXalt Onboarding Digital — API",
        version=config.APP_VERSION,
        docs_url="/docs" if documentation_active else None,
        redoc_url="/redoc" if documentation_active else None,
        openapi_url="/openapi.json" if documentation_active else None,
    )

    # La configuration est portee par l'application, non par un cache global :
    # c'est ce qui rend les endpoints de sante testables sans service reel.
    application.state.parametres = config

    @application.middleware("http")
    async def correlation_et_journal(
        requete: Request, appel_suivant: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Attacher un identifiant de correlation, puis journaliser la requete.

        L'identifiant est fixe AVANT l'appel suivant, pour que toute ligne de
        journal emise pendant le traitement le porte deja — y compris celles des
        gestionnaires d'erreur.

        Une valeur fournie par l'appelant est reprise, ce qui permet de suivre
        une trace a travers plusieurs services ; sinon elle est engendree. Elle
        est renvoyee dans l'en-tete de reponse pour que le client puisse la citer
        dans un signalement.
        """
        identifiant = definir_correlation(requete.headers.get(EN_TETE_CORRELATION))
        debut = time.monotonic()
        reponse = await appel_suivant(requete)
        reponse.headers[EN_TETE_CORRELATION] = identifiant
        journaliser_requete(requete, reponse, debut)
        return reponse

    # Un format d'erreur unique, quelle que soit l'origine de l'echec
    # (cahier §18.3).
    application.add_exception_handler(ErreurApplicative, gerer_erreur_applicative)
    application.add_exception_handler(StarletteHTTPException, gerer_erreur_http)
    application.add_exception_handler(RequestValidationError, gerer_erreur_validation)
    application.add_exception_handler(Exception, gerer_erreur_inattendue)

    # Les endpoints de sante sont hors du prefixe versionne, volontairement :
    # ils relevent de l'exploitation et leur adresse ne doit pas bouger avec
    # les versions de l'API.
    application.include_router(routeur_sante)

    # Le routeur metier versionne existe mais est vide : le contrat /api/v1 est
    # pose, son contenu appartient au LOT 2 et aux suivants.
    routeur_v1 = _routeur_versionne(config)
    application.include_router(routeur_v1)

    return application


def _routeur_versionne(config: Parametres) -> APIRouter:
    """Routeur du contrat versionne, vide au LOT 1."""
    routeur = APIRouter(prefix=config.API_PREFIX, tags=["v1"])

    @routeur.get("/", summary="Racine du contrat versionne")
    def racine() -> dict[str, str]:
        """Confirmer que le prefixe versionne est monte.

        Aucune donnee metier : le LOT 1 ne livre aucun ecran ni aucune
        ressource. Cette route existe pour que `/api/v1` ne renvoie pas 404,
        ce qui serait indistinguable d'une API mal deployee.
        """
        return {"api": "onboarding-digital", "version_contrat": "v1", "version": __version__}

    return routeur


# PAS d'instance construite a l'import.
#
# uvicorn est lance avec `--factory` et appelle `creer_application()` lui-meme.
# La premiere version de ce module se terminait par
# `application = creer_application()` : importer `app.main` suffisait alors a
# lire l'environnement, et la simple COLLECTE des tests echouait faute de
# variables. Un module qui lit son environnement a l'import n'est pas testable.
#
# Le refus de demarrer du cahier §20.3 est preserve : uvicorn appelle la
# fabrique au demarrage, `ConfigurationInvalide` y remonte, et le conteneur
# s'arrete avec un message nommant la variable fautive.
