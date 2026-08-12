"""Journalisation des requetes HTTP.

LOT 1, sous-etape T4, story MVP-L01-US004.

FONDEMENT — cahier §28.1 : chaque ligne porte la route, la duree, le resultat
et le code d'erreur. C'est ce module qui les renseigne pour l'API ; le format
lui-meme vient de `packages/observabilite`.

CE QUI EST JOURNALISE, ET CE QUI NE L'EST PAS
    La route journalisee est le CHEMIN DE GABARIT quand FastAPI le connait —
    `/api/v1/personnes/{identifiant}` — et non le chemin concret. Deux raisons :
    l'agregation par route devient possible, et surtout un identifiant de
    ressource ne se retrouve pas dans les journaux, ce qui limite la donnee
    personnelle journalisee (cahier §28.2).

    La chaine de requete n'est jamais journalisee. Un magic link du LOT 3 y
    passera : `?token=...`. Le §28.2 interdit le magic link complet, et la
    parade la plus sure est de ne pas ecrire la chaine de requete du tout.
"""

from __future__ import annotations

import logging
import time

from fastapi import Request, Response

journal = logging.getLogger("app.requete")

# Les endpoints de sante sont interroges toutes les dix secondes par Docker.
# Les journaliser noierait tout le reste : 8 640 lignes par jour et par service,
# sans aucune valeur de diagnostic. Ils restent journalises en cas d'ECHEC.
ROUTES_SILENCIEUSES_SI_SUCCES = frozenset({"/health/live", "/health/ready", "/health/version"})


def route_de_gabarit(requete: Request) -> str:
    """Chemin de gabarit si FastAPI l'a resolu, sinon le chemin brut.

    Jamais la chaine de requete : voir l'avertissement en tete de module.
    """
    gabarit = requete.scope.get("route")
    chemin = getattr(gabarit, "path", None)
    return f"{requete.method} {chemin or requete.url.path}"


# Trois resultats, et non deux. Annoncer `succes` sur un 404 a cote d'un
# `code_erreur=http_404` est contradictoire a la lecture, et rend toute
# agregation ambigue : on ne sait plus si `succes` compte les refus.
#
#   succes  2xx et 3xx — l'API a fait ce qu'on lui demandait
#   refus   4xx        — l'API a correctement refuse : la faute est a l'appelant
#   echec   5xx        — l'API a echoue : la faute est a nous
#
# Seul `echec` justifie un niveau `error`. Un 404 journalise en erreur ferait
# sonner une alerte a chaque adresse mal tapee.
STATUT_MINIMAL_REFUS = 400
STATUT_MINIMAL_ECHEC = 500


def resultat_de(statut_http: int) -> str:
    """Traduire un code HTTP en resultat du cahier §28.1."""
    if statut_http >= STATUT_MINIMAL_ECHEC:
        return "echec"
    if statut_http >= STATUT_MINIMAL_REFUS:
        return "refus"
    return "succes"


def journaliser_requete(requete: Request, reponse: Response, debut_monotone: float) -> None:
    """Emettre la ligne de journal d'une requete servie."""
    duree_ms = int((time.monotonic() - debut_monotone) * 1000)
    statut = reponse.status_code
    resultat = resultat_de(statut)

    if resultat == "succes" and requete.url.path in ROUTES_SILENCIEUSES_SI_SUCCES:
        return

    journal.log(
        logging.ERROR if resultat == "echec" else logging.INFO,
        "requete servie",
        extra={
            "route": route_de_gabarit(requete),
            "duree_ms": duree_ms,
            "resultat": resultat,
            "code_erreur": None if statut < STATUT_MINIMAL_REFUS else f"http_{statut}",
            "statut_http": statut,
        },
    )
