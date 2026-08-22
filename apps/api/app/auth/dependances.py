"""Exiger un scope de compte de service sur une route — story `MVP-L03-US007`.

LOT 3, sous-etape `T10`.

AUCUNE ROUTE NE CONSOMME ENCORE CE SCOPE, ET C'EST DIT

  Le §22 parle de « scripts internes » appelant l'API interne ; **aucun document
  n'enumere les routes qu'un compte de service peut appeler**, et aucune route
  metier n'existe -- le portail est le LOT 4, les collaborateurs le LOT 5.

  En inventer une pour « avoir quelque chose a montrer » serait §6.5, et pire :
  une route de diagnostic protegee par un scope deviendrait une surface a maintenir
  pour rien. **Le mecanisme est donc livre et prouve, et son premier consommateur
  viendra avec la premiere route metier.**

  C'est exactement le parti de `T7` pour le CSRF : les barrieres existent, aucune
  route metier ne les exerce encore, et le residuel est **nomme** plutot que
  masque par une route factice.

LE TRANSPORT EST UNE DERIVATION DECLAREE, PAS UNE REGLE INVENTEE

  Le corpus ne dit **pas** comment un jeton de service est presente. `Authorization:
  Bearer` est ce que le standard HTTP reserve a ce cas, comme `429` l'etait pour la
  limitation en `T8` et `403` plutot que `401` en `T7`. Employer un en-tete maison
  serait un choix arbitraire ; employer le standard est une derivation.

  **ET LE JETON NE VOYAGE JAMAIS DANS L'URL.** Une chaine de requete finit dans
  l'historique du navigateur, dans un en-tete `Referer` et dans tout journal
  d'acces de mandataire -- c'est le motif deja ecrit pour la consommation de magic
  link en `T4`.

LE REFUS EST UN SEUL GABARIT, ET IL EST 403

  Quatre causes -- forme invalide, jeton inconnu ou perime ou revoque, compte
  desactive, scope manquant -- rendent **la meme** reponse. Les distinguer dirait a
  un appelant s'il s'est approche.

  **`403` ET NON `401`**, meme motif qu'en `T7` : `401` signifie « authentifie-toi »,
  et un jeton parfaitement valide auquel il manque un scope est authentifie. `403`
  dit « je sais qui tu es, et je refuse cet appel-la ».
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from typing import TYPE_CHECKING, Final

from fastapi import Request, status

from app.auth.comptes_de_service import Authentification, authentifier_un_jeton
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

if TYPE_CHECKING:  # pragma: no cover
    from app.configuration.settings import Parametres

EN_TETE_AUTORISATION: Final = "Authorization"
PREFIXE_PORTEUR: Final = "Bearer "

CODE_SCOPE_REFUSE: Final = "acces_refuse"
MESSAGE_SCOPE_REFUSE: Final = (
    "Cet appel a ete refuse. Verifiez le jeton employe et les scopes qui lui sont accordes."
)


def exiger_un_scope(parametres: Parametres, scope: str) -> Callable[[Request], Authentification]:
    """Fabriquer une dependance FastAPI qui exige un scope.

    Employee ainsi par une future route metier :

        @routeur.get("/collaborateurs", dependencies=[Depends(exiger_un_scope(p, "people:read"))])

    **LA FABRIQUE PREND `parametres`, ET NON LA DEPENDANCE.** Le moteur de base de
    donnees se derive de la configuration, et une dependance qui la lirait
    elle-meme serait intestable -- c'est la lecon `T7` du LOT 1 : un livrable
    difficile a tester est un livrable qu'on ne teste pas.
    """

    def controler(requete: Request) -> Authentification:
        entete = requete.headers.get(EN_TETE_AUTORISATION, "")
        #  Un en-tete absent ou d'un autre schema donne une chaine vide, qui sera
        #  refusee pour forme invalide. **Aucune branche particuliere** : trois
        #  chemins de refus finiraient par ne pas rendre la meme reponse, et c'est
        #  la lecon de l'egalite anti-enumeration de `T3`.
        jeton = entete[len(PREFIXE_PORTEUR) :] if entete.startswith(PREFIXE_PORTEUR) else ""

        #  UNE SEULE TRANSACTION : la mise a jour de `last_used_at` et l'evenement
        #  d'audit sont indissociables. Un appel trace sans sa derniere utilisation,
        #  ou l'inverse, laisserait deux verites.
        with moteur(parametres).begin() as connexion:
            verdict = authentifier_un_jeton(
                connexion,
                jeton=jeton,
                instant=_maintenant(),
                scope_requis=scope,
                empreinte_origine=None,
            )

        if not verdict.reussie:
            #  Le motif est deja dans `auth_event`, ou l'operateur le lit. Il ne
            #  sort pas : distinguer les quatre causes serait un oracle.
            raise ErreurApplicative(
                code=CODE_SCOPE_REFUSE,
                message=MESSAGE_SCOPE_REFUSE,
                statut=status.HTTP_403_FORBIDDEN,
            )
        return verdict

    return controler


def _maintenant() -> dt.datetime:
    """L'instant courant, extrait pour rester injectable dans un test.

    Le §9.2 de la passation le dit : **le temps s'injecte, il ne s'attend pas.**
    Ici la dependance n'a pas de parametre d'instant -- une route HTTP n'en a
    pas -- donc l'injection passe par ce point unique.
    """
    return dt.datetime.now(tz=dt.UTC)
