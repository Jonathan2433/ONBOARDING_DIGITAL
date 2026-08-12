"""Les trois endpoints de sante.

LOT 1, sous-etape T3, story MVP-L01-US003.

FONDEMENT — cahier des charges §18.7 : `/health/live`, `/health/ready`,
`/health/version`.

CE QUE CHACUN REPOND, ET POURQUOI C'EST DIFFERENT
    live     Le processus est-il vivant ? Ne touche AUCUNE dependance. Si
             `live` interrogeait PostgreSQL, une panne de base ferait
             redemarrer l'API en boucle par l'orchestrateur, sans jamais
             corriger la cause.
    ready    L'API peut-elle servir une requete utile ? Elle sonde reellement
             PostgreSQL, Redis et MinIO, et repond **503** si l'une manque.
             Un `ready` qui renvoie 200 quand la base est absente est un
             controle qui ne peut pas echouer.
    version  Quelle version est deployee ? Doit correspondre au build.

Ces endpoints ne sont PAS derriere le prefixe /api/v1 : ils appartiennent a
l'exploitation, pas au contrat metier versionne. Un changement de version
d'API ne doit pas deplacer l'adresse que sonde l'orchestrateur.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response, status

from app.configuration.settings import Parametres
from app.health.dependances import sonder_toutes

routeur = APIRouter(prefix="/health", tags=["sante"])


@routeur.get("/live", summary="Le processus est-il vivant ?")
def live() -> dict[str, str]:
    """Vivacite du processus. Ne sonde aucune dependance, volontairement."""
    return {"statut": "vivant"}


def _parametres(requete: Request) -> Parametres:
    """Configuration portee par l'application.

    Passer par `app.state` et non par un cache global rend l'API testable : un
    test peut construire une application dont les dependances pointent vers des
    ports fermes, et verifier que `ready` repond bien 503. Avec un cache global,
    ce test aurait exige d'arreter des services reels.
    """
    parametres: Parametres = requete.app.state.parametres
    return parametres


@routeur.get(
    "/ready",
    summary="L'API peut-elle servir une requete utile ?",
    # T10 — LE 503 EST DESORMAIS DOCUMENTE DANS LE SCHEMA, et il ne l'etait pas.
    #
    # La route renvoie 503 depuis `T3`, et le frontend le traite comme un etat
    # DEGRADE exploitable — meme forme de charge utile qu'un 200. Mais le schema
    # OpenAPI ne documentait que 200 : FastAPI ne devine pas les codes qu'une
    # route pose elle-meme sur l'objet `Response`.
    #
    # Constate par `apps/api/tests/test_contrat.py`, qui confronte le manifeste
    # partage au schema reellement monte. Un consommateur qui aurait engendre son
    # client depuis ce schema aurait donc traite le 503 comme une erreur
    # imprevue, alors que c'est precisement la reponse qui porte le diagnostic.
    responses={
        200: {"description": "Toutes les dependances sondees sont disponibles."},
        503: {
            "description": (
                "Au moins une dependance est indisponible. La charge utile a "
                "EXACTEMENT la meme forme qu'un 200 : c'est le champ `statut` qui "
                "distingue, et le detail par dependance qui porte le motif."
            )
        },
    },
)
def ready(requete: Request, reponse: Response) -> dict[str, Any]:
    """Disponibilite reelle : PostgreSQL, Redis et MinIO sont sondes.

    Renvoie **503** si une seule dependance manque. Le statut de chaque
    dependance est detaille, pour que le diagnostic ne demande pas de lire les
    journaux.
    """
    parametres = _parametres(requete)
    resultats = sonder_toutes(parametres)
    tout_va_bien = all(r.disponible for r in resultats)

    if not tout_va_bien:
        reponse.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "statut": "pret" if tout_va_bien else "indisponible",
        "dependances": [
            {
                "nom": r.nom,
                "statut": "disponible" if r.disponible else "indisponible",
                "duree_ms": r.duree_ms,
                "motif": r.motif,
            }
            for r in resultats
        ],
    }


@routeur.get("/version", summary="Quelle version est deployee ?")
def version(requete: Request) -> dict[str, str]:
    """Version applicative et empreinte de commit.

    `revision` est injectee a la construction de l'image en T7, depuis
    l'empreinte de commit, et alimente aussi le label OCI `revision` exige par
    `DEC-445`. Elle vaut `inconnue` tant qu'aucune valeur n'est fournie :
    afficher `0.0.0` serait affirmer une version qu'on ne connait pas.
    """
    parametres = _parametres(requete)
    return {
        "version": parametres.APP_VERSION,
        "revision": parametres.APP_REVISION,
        "environnement": parametres.APP_ENV,
    }
