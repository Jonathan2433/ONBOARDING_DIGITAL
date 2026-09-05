"""La route du trombinoscope — story `MVP-L05-US001`.

LOT 5, sous-etape `T2`.

La derivation complete -- qui peut lire, quels etats sont exclus, pourquoi les
deux filtres sont necessaires, d'ou vient l'ordre -- est dans l'en-tete de
`app/people/trombinoscope.py`. Ce module ne porte que ce qui releve de HTTP.

LE 404 EST CELUI DES DEUX AUTRES ROUTES D'ENTITE, EN CORPS ET EN EN-TETES

  Un code inconnu et une entite non active rendent la **meme** reponse que
  `/entities/{code}` et `/entities/{code}/permissions`. Deux routes qui
  distingueraient differemment apprendraient, par comparaison, qu'un brouillon
  existe -- et le LOT 9 en creera avant publication.

  Le gabarit n'est pas recopie : il est **importe** de `app.entities.routes`.

LE REFUS D'UNE TAILLE HORS LISTE EST UN 422 QUE JE N'ECRIS PAS

  `taille` est typee `TailleDePage`, un `Literal` des trois valeurs du §18.2.
  FastAPI refuse donc toute autre valeur avant d'entrer dans le corps, et
  `gerer_erreur_validation` traduit le refus au format du §18.3 -- `code`,
  `message`, `champ`, `details` et identifiant de correlation. Ecrire ici un
  `ErreurApplicative` de plus donnerait **deux** formes de refus pour une meme
  cause, et la seconde serait celle qu'aucun test de format n'examine.

  **Le service verifie POURTANT la meme chose, et ce n'est pas une redondance :**
  il est appelable hors HTTP -- par un futur export, par un script -- et une
  fonction qui accepte silencieusement une taille de 10 000 rendrait la borne du
  cahier dependante de son appelant.

`page` EST 1-INDEXEE, ET C'EST LE NUMERO QUE L'ECRAN AFFICHE

  Une page 0 n'a pas de sens pour un lecteur. `ge=1` fait refuser `page=0` par le
  meme 422, et la conversion en decalage est faite une seule fois, dans le
  service.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from pydantic import BaseModel

from app.auth.dependances import exiger_une_session
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import resoudre_une_entite_active
from app.people.trombinoscope import (
    TAILLE_PAR_DEFAUT,
    TailleDePage,
    lister_le_trombinoscope,
)
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

if TYPE_CHECKING:  # pragma: no cover
    from app.configuration.settings import Parametres


class CollaborateurDuTrombinoscope(BaseModel):
    """Une ligne du trombinoscope.

    Sept champs, et **ni photo ni informations professionnelles jointes** : le
    motif de ces absences est dans l'en-tete de `trombinoscope.py`, section « ce
    que `T2` ne fait pas ».

    Les noms sont en `snake_case`, comme `est_entite_principale` de `T8` du
    LOT 4 : c'est le contrat de `packages/contracts` qui traduit vers le
    `camelCase` du frontend, et sa garde **leve** si un champ manque.
    """

    id: uuid.UUID
    person_id: uuid.UUID
    first_name: str
    last_name: str
    preferred_name: str | None
    professional_category: str
    arrival_date: dt.date


class ReponseDuTrombinoscope(BaseModel):
    """Une page du trombinoscope, et de quoi savoir ou l'on est.

    `total` porte la population entiere, `pages` le nombre de pages. Le §10.1
    exige une « vue paginee » : sans ces deux nombres, l'ecran ne peut ni dire
    « page 2 sur 6 » ni desactiver le bouton suivant. `pages` est calcule **une
    seule fois, ici** -- le laisser au client dupliquerait la regle dans chaque
    consommateur.
    """

    collaborateurs: list[CollaborateurDuTrombinoscope]
    page: int
    taille: int
    total: int
    pages: int


def routeur_trombinoscope(parametres: Parametres) -> APIRouter:
    """Routeur du trombinoscope, monte sous le prefixe versionne."""
    routeur = APIRouter(tags=["trombinoscope"])

    #  La dependance passe par `dependencies=`, jamais par `Annotated[...]` : le
    #  piege est mesure dans `app/entities/routes.py`, et il produit un livrable
    #  qui PARAIT protege tout en refusant tout le monde avec un 422.
    @routeur.get(
        "/entities/{code}/people",
        dependencies=[Depends(exiger_une_session(parametres))],
        status_code=status.HTTP_200_OK,
        response_model=ReponseDuTrombinoscope,
        responses={
            status.HTTP_401_UNAUTHORIZED: {
                "description": (
                    "Aucune session valide. UNE SEULE forme pour cinq causes : cookie "
                    "absent, jeton inconnu, session revoquee, duree absolue depassee, "
                    "inactivite depassee."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "UNE SEULE forme pour DEUX causes : le code est inconnu, ou "
                    "l'entite existe sans etre active. Identique en corps ET en "
                    "en-tetes a celle de `/entities/{code}`."
                )
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`taille` hors des trois valeurs du cahier §18.2, ou `page` "
                    "inferieure a 1. Format du §18.3, produit par le gestionnaire "
                    "de validation et non par cette route."
                )
            },
        },
        summary="Lister les collaborateurs publies et actifs d'une entite",
        description=(
            "Le trombinoscope d'une entite, pagine. Cahier §18.2 : 25 par defaut, "
            "options 25, 50 et 100. Toute autre taille est refusee — arbitrage du "
            "25/08/2026. Exige une session : la matrice §5 refuse cette ressource a "
            "`ANON` et l'accorde aux huit roles authentifies, sans distinction, si "
            "bien qu'aucun role n'est examine ici. "
            "Seuls les profils `published` d'une appartenance `active` sont rendus : "
            "les deux filtres sont necessaires, et le motif mesure est dans le module "
            "de service. L'ordre est nom puis prenom, total par la cle primaire."
        ),
    )
    def lister_les_collaborateurs(
        #  `Path` et `Query` en defaut sont les fabriques de FastAPI, que ruff
        #  connait : `B008` ne s'y declenche pas, et un `noqa` inutile ferait
        #  echouer `RUF100`.
        code: str = Path(
            min_length=1,
            max_length=LONGUEUR_MAXIMALE_CODE,
            description="Le `code` de l'entite, unique et jamais reattribue",
        ),
        page: int = Query(
            1,
            ge=1,
            description="Numero de page, 1-indexee comme celui que l'ecran affiche",
        ),
        taille: Annotated[
            TailleDePage,
            Query(description="Elements par page — les trois valeurs du cahier §18.2, seules"),
        ] = TAILLE_PAR_DEFAUT,
    ) -> ReponseDuTrombinoscope:
        """Lister le trombinoscope — cahier §10.1 et §18.2, backlog `MVP-L05-US001`."""
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                #  Le motif precis ne sort pas : deux causes, une seule reponse.
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            #  La resolution et la page sont dans la MEME transaction : une entite
            #  suspendue entre les deux rendrait un trombinoscope d'entite
            #  inaccessible.
            #  `int(taille)` : `TailleDePage` est un `IntEnum`, et le service est
            #  HTTP-agnostique -- il recoit un entier, pas un type de la couche
            #  web. C'est aussi ce que le pilote attend en parametre lie.
            resultat = lister_le_trombinoscope(
                connexion, entite=entite.id, page=page, taille=int(taille)
            )

        #  Division entiere par excedent, sans `math.ceil` : une division
        #  flottante sur un total de plusieurs millions perdrait en precision.
        pages = -(-resultat.total // int(taille))

        return ReponseDuTrombinoscope(
            collaborateurs=[
                CollaborateurDuTrombinoscope(
                    id=ligne.id,
                    person_id=ligne.person_id,
                    first_name=ligne.first_name,
                    last_name=ligne.last_name,
                    preferred_name=ligne.preferred_name,
                    professional_category=ligne.professional_category,
                    arrival_date=ligne.arrival_date,
                )
                for ligne in resultat.collaborateurs
            ],
            page=page,
            taille=int(taille),
            total=resultat.total,
            pages=pages,
        )

    return routeur
