"""`GET /entities/{code}/permissions` — LOT 4, sous-etape `T8`, `MVP-L04-US002`.

POURQUOI UNE ROUTE, ET POURQUOI UN `GET`

  Le cahier §23.3 et la matrice §23.3 posent cinq regles au changement d'entite.
  Les DEUX PREMIERES sont des interdictions d'ecriture -- « ne modifie pas
  l'entite principale de la personne », « ne transfere pas ses responsabilites ».

  **Un `GET` les tient par construction, et c'est le vrai argument de
  conception.** Depuis `DEC-545`, l'entite consultee vit dans l'ADRESSE : changer
  d'entite est une NAVIGATION, pas une ecriture. Il n'y a donc aucun endroit ou
  l'entite principale pourrait etre modifiee, et le §7.32 s'applique -- ne pas
  ecrire une defense contre un etat que la conception rend impossible, mais
  EXIGER qu'il reste impossible. Le controle de `T8` compare l'etat de la base
  avant et apres un changement d'entite, table par table.

  La troisieme regle -- « recharge les permissions » -- est ce que cette route
  rend possible : sans elle, le frontend n'aurait rien a recharger.
  La quatrieme -- « annule les requetes et caches » -- est tenue depuis `T2`,
  par l'`AbortController` du cadre applicatif.
  La cinquieme -- « visible dans l'en-tete » -- est tenue depuis `T3`.

LA REPONSE EST BORNEE A CE QUE LA MATRICE DIT, ET PAS PLUS

  Elle porte les codes de role du §3 et le fait de consulter ou non son entite
  principale. Elle NE PORTE PAS de liste d'actions autorisees : la matrice en
  declare des dizaines, par ressource, et les inventer ici serait exactement le
  §6.5. Le §5.1 est d'ailleurs explicite sur le point ou cela se joue -- « les
  controles cote API utilisent l'entite de la RESSOURCE » -- donc chaque route
  metier des lots suivants tranchera sur sa propre ressource.

  `est_entite_principale` n'est pas une commodite : c'est la seule information du
  §5.1 qui ne se lit pas dans la liste des roles. Une personne sans aucune
  responsabilite rend `["EMP"]` dans son entite principale **et** ailleurs ; le
  frontend a besoin de savoir laquelle des deux, parce que le §5.1 lui interdit
  de PROPOSER des actions hors de son entite principale.

`T13` DU LOT 7 AJOUTE `appartenance`, ET CE N'EST PAS UNE ACTION DE PLUS

  Le §6.5 interdit d'inventer ce que le corpus ne decide pas ; ceci ne decide
  RIEN de nouveau, ca n'est qu'une IDENTITE. Aucune route de l'onboarding
  n'accepte de cible implicite (§7, §8.1) : sans cet identifiant, l'ecran
  « Mon onboarding » n'aurait aucun moyen de savoir quelle URL appeler pour
  la fiche et le parcours DE L'APPELANT LUI-MEME. Reutiliser cette route
  plutot qu'en ajouter une troisieme evite un aller-retour reseau de plus —
  elle est deja appelee une fois par page par le cadre applicatif.

LE 404 EST LE MEME QUE CELUI DE `GET /entities/{code}`, ET C'EST VOULU

  La route resout d'abord l'entite ACTIVE. Une entite `draft`, `suspended` ou
  `archived` rend 404, avec le meme gabarit : deux routes qui distingueraient
  differemment apprendraient a un appelant, par comparaison, qu'un brouillon
  existe. Le §8.3 donne acces aux entites actives ; pour l'appelant, les autres
  n'existent pas.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING, Final

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel

from app.auth.dependances import SessionEtablie, exiger_une_session
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import resoudre_une_entite_active
from app.permissions.services import resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

if TYPE_CHECKING:  # pragma: no cover
    from app.configuration.settings import Parametres

DESCRIPTION_401: Final = (
    "Aucune session valide. UNE SEULE forme pour cinq causes : cookie absent, "
    "jeton inconnu, session revoquee, duree absolue depassee, inactivite depassee."
)


class PermissionsDeLEntiteConsultee(BaseModel):
    """Les droits de l'appelant DANS l'entite consultee.

    `roles` porte les codes du §3 de la matrice, tries. L'ordre est total et
    reproductible : le controle de `T8` compare deux reponses octet a octet.

    `appartenance` — LOT 7, `T13`. `None` hors de l'entite principale, ou sans
    appartenance occupante. Voir `permissions.services._appartenance_occupante` :
    c'est le SEUL moyen dont dispose l'ecran du nouvel arrivant pour savoir
    quelle URL appeler pour SA propre fiche et SON propre parcours — aucune
    route de l'onboarding n'accepte de cible implicite.
    """

    entite: uuid.UUID
    code: str
    est_entite_principale: bool
    roles: list[str]
    appartenance: uuid.UUID | None


def routeur_permissions(parametres: Parametres) -> APIRouter:
    """Routeur des permissions de l'entite consultee, sous le prefixe versionne."""
    routeur = APIRouter(tags=["permissions"])

    @routeur.get(
        "/entities/{code}/permissions",
        status_code=status.HTTP_200_OK,
        response_model=PermissionsDeLEntiteConsultee,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "UNE SEULE forme pour DEUX causes : le code est inconnu, ou l'entite "
                    "existe sans etre active. Identique au 404 de `GET /entities/{code}`."
                )
            },
        },
        summary="Les droits de l'appelant dans l'entite consultee",
        description=(
            "Matrice §5.1 : hors de son entite principale, une personne « possede "
            "UNIQUEMENT les droits `EMP` » et ses responsabilites « ne s'appliquent "
            "pas ». Dans son entite principale, les droits de plusieurs "
            "responsabilites se cumulent (§23.1). Le super-administrateur est la "
            "seule exception globale. "
            "Un role CLOTURE n'accorde rien : le controle §24.12 est tenu par la "
            "plage `period`, et non par `ends_at IS NULL` qui laisserait passer une "
            "affectation future."
        ),
    )
    def lire_les_permissions(
        #  `Depends` en defaut d'argument : c'est la forme du docstring de
        #  `exiger_une_session`, et la seule qui rende l'appelant LISIBLE dans le
        #  corps. `dependencies=[...]` suffit quand on jette le resultat, ce qui
        #  est le cas des deux routes de `T1` -- pas ici.
        #
        #  **NE PAS PASSER PAR `Annotated[...]`** : sous `from __future__ import
        #  annotations`, FastAPI resout l'annotation dans les globals du module,
        #  n'y trouve pas la fermeture `parametres`, et prend le parametre pour
        #  une chaine de requete. Mesure du 23/08/2026 : **422**, `loc: ["query",
        #  "a"]`. Le livrable PARAIT protege et refuse tout le monde.
        appelant: SessionEtablie = Depends(exiger_une_session(parametres)),  # noqa: B008
        code: str = Path(
            min_length=1,
            max_length=LONGUEUR_MAXIMALE_CODE,
            description="Le `code` de l'entite consultee, tel qu'il vit dans l'adresse",
        ),
    ) -> PermissionsDeLEntiteConsultee:
        """Resoudre les permissions de l'entite consultee — matrice §5.1 et §23.1."""
        #  L'instant est releve UNE FOIS et passe au service. Deux appels a
        #  `now()` dans une meme resolution pourraient tomber de part et d'autre
        #  de la borne d'une periode, et rendre un ensemble de roles incoherent
        #  avec lui-meme.
        instant = dt.datetime.now(tz=dt.UTC)

        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)

        return PermissionsDeLEntiteConsultee(
            entite=permissions.entite,
            code=entite.code,
            est_entite_principale=permissions.est_entite_principale,
            roles=[role.value for role in permissions.roles],
            appartenance=permissions.appartenance,
        )

    return routeur
