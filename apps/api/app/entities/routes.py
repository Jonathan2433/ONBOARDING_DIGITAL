"""La route du portail national — story `MVP-L04-US001`.

LOT 4, sous-etape `T1`.

**LA PREMIERE ROUTE METIER DU PROJET.** Les LOTS 1 a 3 n'exposaient que de la
sante, la racine du contrat versionne et l'authentification.

CE QU'ELLE EXIGE DE L'APPELANT, ET D'OU CELA VIENT

  La matrice §5 donne « Page nationale et carte des entites » a **`ANON` = tiret**
  et aux **huit** roles authentifies -- `EMP`, `NEW`, `DSM`, `ESM`, `BOOST`,
  `OFFICE`, `ADM-E`, `SUPER` -- tous a la coche. Le cahier §7.1 dit de son cote
  « une page nationale APRES authentification ».

  Il n'y a donc **rien a arbitrer et aucun role a distinguer** : une session
  valide suffit, et son absence refuse. Ajouter ici un controle de role exigerait
  plus que la matrice, ce qui est le defaut du §7.20 -- un controle qui echoue sur
  un livrable conforme.

  **`SERVICE` N'EST PAS DANS CE TABLEAU**, et le residuel est nomme plutot que
  comble : voir l'en-tete de `app/auth/dependances.py`.

ELLE EST LE PREMIER CONSOMMATEUR DE TROIS CHOSES LIVREES AU LOT 3

  La checklist `G3` en nommait trois qui attendaient leur premier consommateur.
  Celle-ci en active **une** -- la validation de session sur une route metier --
  et **pas** les deux autres :

    la protection CSRF     elle porte sur les ECRITURES. Cette route est un
                           `GET` : rien a proteger. `T8` de ce lot, qui changera
                           d'entite, sera le premier vrai consommateur si le
                           changement est une ecriture -- c'est un point de `T2`.
    la dependance de scope elle est pour les comptes de service, que la matrice
                           n'autorise pas ici. Toujours sans consommateur.

  Le dire vaut mieux que de laisser croire que le LOT 4 a tout referme des sa
  premiere sous-etape.

L'APPELANT N'EST PAS DANS LA SIGNATURE, ET C'EST EXACT

  La matrice ne distingue **aucun** role sur cette ressource : la dependance est
  la pour REFUSER, jamais pour filtrer, et le corps n'a donc rien a faire de
  l'identite de l'appelant. La declarer en parametre laisserait croire le
  contraire.

  **`T2` en aura besoin** -- l'entite consultee est propre a une session. Elle
  devra alors employer la forme a DEFAUT D'ARGUMENT, `appelant: SessionEtablie =
  Depends(...)` avec un `noqa: B008`, et surtout **pas** `Annotated[...]` : le
  piege est mesure juste au-dessus de la route.

POURQUOI UN OBJET ET NON UN TABLEAU JSON A LA RACINE

  `{"entites": [...]}` plutot que `[...]`. Un tableau a la racine ne peut pas
  recevoir de champ voisin sans casser ses consommateurs, et il en faudra un :
  `T2` doit dire **quelle entite est consultee**, et c'est precisement le point
  que le §8 de la fiche laisse ouvert. L'objet laisse la porte ouverte a cout
  nul ; le tableau la fermerait.

  Aucune pagination, et c'est mesure : le §30.25 du cahier borne la recette a
  **25 entites**. Paginer 25 lignes serait de la complexite sans besoin.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.auth.dependances import exiger_une_session
from app.entities.services import lister_les_entites_actives
from app.shared.database import moteur

if TYPE_CHECKING:  # pragma: no cover
    from app.configuration.settings import Parametres


class EntiteDuPortail(BaseModel):
    """Une entite de la page nationale.

    Quatre champs, et les trois absences sont motivees dans
    `app/entities/services.py`. **`status` n'y est pas** : toute entite rendue est
    active, donc le champ serait constant.
    """

    id: uuid.UUID
    code: str
    nom: str
    ville: str


class ReponseDesEntites(BaseModel):
    """La liste des entites actives, dans un ordre total et reproductible."""

    entites: list[EntiteDuPortail]


def routeur_entites(parametres: Parametres) -> APIRouter:
    """Routeur du portail national, monte sous le prefixe versionne."""
    routeur = APIRouter(tags=["entites"])

    #  **LA DEPENDANCE PASSE PAR `dependencies=`, ET NON EN DEFAUT D'ARGUMENT.**
    #  C'est la forme que `T10` du LOT 3 annoncait pour « les futures routes
    #  metier », et `B008` a raison de refuser un appel de fonction en defaut.
    #
    #  **ET LA TROISIEME FORME, `Annotated[...]`, EST UN PIEGE MESURE.** Sous
    #  `from __future__ import annotations`, l'annotation est une CHAINE que
    #  FastAPI resout dans les globals du module -- or `parametres` est une
    #  variable de fermeture, absente de ces globals. Mesure du 23/08/2026 sur un
    #  double jetable : la route rend **422** avec `loc: ["query", "a"]`. FastAPI
    #  n'a pas vu la dependance et a pris le parametre pour une chaine de requete.
    #  **Le defaut n'est donc pas un plantage mais un livrable qui paraît
    #  protege** : il ne refuse pas les appels sans session, il refuse TOUT LE
    #  MONDE en reclamant un parametre d'URL. Ne pas y revenir.
    @routeur.get(
        "/entities",
        dependencies=[Depends(exiger_une_session(parametres))],
        status_code=status.HTTP_200_OK,
        response_model=ReponseDesEntites,
        responses={
            status.HTTP_401_UNAUTHORIZED: {
                "description": (
                    "Aucune session valide. UNE SEULE forme pour cinq causes : cookie "
                    "absent, jeton inconnu, session revoquee, duree absolue depassee, "
                    "inactivite depassee."
                )
            }
        },
        summary="Lister les entites actives du portail national",
        description=(
            "Les entites `active` SEULEMENT — cahier §8.3, « un acces a chaque entite "
            "active ». Une entite `draft`, `suspended` ou `archived` n'est pas rendue. "
            "Exige une session : la matrice §5 refuse cette ressource a `ANON` et "
            "l'accorde aux huit roles authentifies, sans distinction."
        ),
    )
    def lister_les_entites() -> ReponseDesEntites:
        """Lister les entites actives — cahier §8.3, backlog `MVP-L04-US001`."""
        with moteur(parametres).begin() as connexion:
            entites = lister_les_entites_actives(connexion)

        return ReponseDesEntites(
            entites=[
                EntiteDuPortail(
                    id=entite.id,
                    code=entite.code,
                    nom=entite.display_name,
                    ville=entite.city,
                )
                for entite in entites
            ]
        )

    return routeur
