"""Format d'erreur unique de l'API.

LOT 1, sous-etape T3, story MVP-L01-US003.

FONDEMENT — cahier des charges §18.3
    Toute erreur porte un format coherent comprenant : code, message, champ,
    details, et identifiant de correlation.

Les cinq champs sont TOUJOURS presents dans la reponse, meme a `null` : un
consommateur qui doit tester l'existence d'une cle avant de la lire finit par
se tromper. `champ` et `details` valent `null` quand ils ne s'appliquent pas.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.shared.correlation import correlation_courante


class ErreurApplicative(Exception):
    """Erreur metier portant directement le format du cahier §18.3."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        statut: int = status.HTTP_400_BAD_REQUEST,
        champ: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.statut = statut
        self.champ = champ
        self.details = details
        super().__init__(message)


def construire_corps(
    *,
    code: str,
    message: str,
    champ: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assembler le corps d'erreur du cahier §18.3."""
    return {
        "erreur": {
            "code": code,
            "message": message,
            "champ": champ,
            "details": details,
            "identifiant_correlation": correlation_courante(),
        }
    }


def _reponse(
    statut: int,
    code: str,
    message: str,
    champ: str | None = None,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=statut,
        content=construire_corps(code=code, message=message, champ=champ, details=details),
    )


async def gerer_erreur_applicative(_requete: Request, exception: Exception) -> JSONResponse:
    """Traduire une `ErreurApplicative` en reponse au format du cahier."""
    if not isinstance(exception, ErreurApplicative):  # pragma: no cover - garde de type
        raise exception
    return _reponse(
        exception.statut,
        exception.code,
        exception.message,
        exception.champ,
        exception.details,
    )


async def gerer_erreur_http(_requete: Request, exception: Exception) -> JSONResponse:
    """Donner aux erreurs HTTP de Starlette le meme format qu'aux autres.

    Sans ce gestionnaire, un 404 renverrait `{"detail": "Not Found"}` : un
    second format d'erreur, sans identifiant de correlation, que les clients
    devraient apprendre a lire en plus du premier.
    """
    if not isinstance(exception, StarletteHTTPException):  # pragma: no cover
        raise exception
    return _reponse(
        exception.status_code,
        f"http_{exception.status_code}",
        str(exception.detail),
    )


async def gerer_erreur_validation(_requete: Request, exception: Exception) -> JSONResponse:
    """Traduire une erreur de validation en une reponse 422 au format du cahier.

    Le premier champ fautif est remonte dans `champ`, la liste complete dans
    `details` : c'est ce que le §18.3 attend de ces deux cles.
    """
    if not isinstance(exception, RequestValidationError):  # pragma: no cover
        raise exception
    erreurs = exception.errors()
    premier_champ: str | None = None
    if erreurs:
        emplacement = [str(p) for p in erreurs[0].get("loc", ()) if p != "body"]
        premier_champ = ".".join(emplacement) or None
    return _reponse(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "validation_invalide",
        "La requete comporte des valeurs invalides.",
        premier_champ,
        {
            "violations": [
                {"champ": ".".join(str(p) for p in e["loc"]), "motif": e["msg"]} for e in erreurs
            ]
        },
    )


async def gerer_erreur_inattendue(_requete: Request, _exception: Exception) -> JSONResponse:
    """Filet de securite : aucune trace interne ne sort de l'API.

    Le message est volontairement generique. Le detail appartient au journal,
    ou l'identifiant de correlation permet de le retrouver — pas a la reponse,
    qu'un navigateur peut afficher.
    """
    return _reponse(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "erreur_interne",
        "Une erreur interne est survenue. Communiquez l'identifiant de correlation.",
    )
