"""Exiger un role DANS l'entite consultee — LOT 4, `T9`, story `MVP-L04-US005`.

CE QUE CE MODULE EST, ET CE QU'IL N'EST PAS

  La roadmap du LOT 4 est explicite en deux lignes voisines : « **route guards
  uniquement ergonomiques** » et « **controles d'autorisation systematiques dans
  l'API** ». La matrice §2.6 dit la meme chose autrement -- « le frontend peut
  masquer ou afficher les actions pour ameliorer l'experience, mais **l'API reste
  l'autorite finale** » -- et le §24.20 en fait un controle d'acceptation : « les
  actions interdites sont refusees cote API, **meme si la requete est construite
  manuellement** ».

  Ce module est cette autorite. Le masquage des menus vit dans le frontend, ne
  protege rien, et le dit a l'utilisateur.

LES HUIT VERIFICATIONS DU §2.6, ET CELLES QUI NE S'APPLIQUENT PAS ENCORE

  Le §2.6 exige de chaque requete sensible huit verifications. **Six sont faites
  ici, deux ne s'appliquent pas a ce lot**, et le dire vaut mieux que le laisser
  croire (§7.20) :

    1. l'identite de la personne        FAITE -- `exiger_une_session`
    2. l'etat actif du compte           FAITE -- indirectement, et c'est mesure :
                                        `T9` du LOT 3 revoque les sessions au
                                        depart, et un compte non actif n'a donc
                                        pas de session valide. Un test l'exige,
                                        plutot que de le supposer
    3. l'entite principale              FAITE -- `entite_principale`
    4. l'entite actuellement consultee   FAITE -- lue du chemin, resolue ACTIVE
    5. les responsabilites actives       FAITE -- `period @> instant`, jamais
                                        `ends_at IS NULL`
    6. le perimetre exact de la ressource   NE S'APPLIQUE PAS : ce lot n'expose
                                        aucune ressource au-dela de l'entite
                                        elle-meme. Le §5.1 dit ou cela se jouera
                                        -- « les controles cote API utilisent
                                        l'entite de la RESSOURCE »
    7. l'etat de la ressource           FAITE -- l'entite doit etre `active`,
                                        sinon 404 comme partout ailleurs
    8. contraintes metier supplementaires   NE S'APPLIQUE PAS : le lot est en
                                        lecture seule, aucune n'existe

POURQUOI UN 403 ET NON UN 404

  `exiger_une_scope` du LOT 3 rend **403** avec un gabarit unique. Ici la
  distinction compte : un **404** dirait « cette entite n'existe pas », ce qui est
  faux et deroutant -- l'appelant la consulte legitimement, il y a meme les droits
  `EMP`. Le 403 dit ce qui est vrai : la ressource existe, l'appelant n'y a pas
  droit.

  **Et cela ne fuite rien**, parce que la matrice §5 donne la lecture de l'entite
  aux huit roles authentifies : l'existence de l'entite n'est pas un secret. Le
  404 des entites non actives, lui, reste un 404 -- pour l'appelant, un brouillon
  n'existe pas, et c'est le choix de `T2`.

LE MOTIF DU REFUS NE SORT PAS

  Un seul gabarit, comme les cinq causes du refus de session et les quatre du
  refus de scope. Distinguer « vous n'etes pas ESM » de « vous n'etes pas dans
  votre entite principale » serait un oracle : on apprendrait, en changeant
  d'entite, ou se trouvent les administrateurs.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Final

from fastapi import Request, Response, status

from app.auth.dependances import SessionEtablie, exiger_une_session
from app.entities.routes import CODE_ENTITE_INTROUVABLE, MESSAGE_ENTITE_INTROUVABLE
from app.entities.services import resoudre_une_entite_active
from app.permissions.services import RoleDeLaMatrice, resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Iterable

    from app.configuration.settings import Parametres

#  **LE MEME GABARIT QUE LE REFUS DE SCOPE DU LOT 3**, et ce n'est pas une
#  paresse : deux libelles differents pour le meme genre de refus apprendraient a
#  un appelant lequel des deux mecanismes l'a arrete.
CODE_ROLE_REFUSE: Final = "acces_refuse"
MESSAGE_ROLE_REFUSE: Final = (
    "Cet acces a ete refuse. Verifiez l'entite consultee et les responsabilites qui y sont actives."
)

#  Le nom du parametre de chemin qui porte le code de l'entite. **Une constante,
#  parce que la dependance le lit dans `request.path_params` et qu'une faute de
#  frappe y serait SILENCIEUSE** : le code vaudrait `None`, l'entite serait
#  introuvable, et la route rendrait 404 pour tout le monde en paraissant sure.
#  Un test l'eprouve sur la route reelle.
PARAMETRE_DE_CHEMIN: Final = "code"


def exiger_un_role_dans_l_entite(
    parametres: Parametres, roles: Iterable[RoleDeLaMatrice]
) -> Callable[[Request, Response], SessionEtablie]:
    """Fabriquer une dependance qui exige l'un des `roles` DANS l'entite du chemin.

    Employee ainsi :

        @routeur.get(
            "/entities/{code}/administration",
            dependencies=[Depends(exiger_un_role_dans_l_entite(p, ROLES_ADMINISTRATION))],
        )

    **`roles` EST UNE DISJONCTION, PAS UNE CONJONCTION.** Le §23.1 pose l'union
    des droits : porter l'un des roles suffit. Exiger tous les roles n'aurait
    aucun sens -- personne n'est a la fois `ESM` et `ADM-E`, le §20 les distingue
    precisement.

    **LA FABRIQUE PREND `parametres`, ET NON LA DEPENDANCE.** Meme motif que
    `exiger_un_scope` : une dependance qui lirait la configuration serait
    intestable, et c'est la lecon `T7` du LOT 1.

    **`roles` EST FIGE A LA CONSTRUCTION.** Un `Iterable` consomme une seule fois
    -- un generateur, par exemple -- rendrait la dependance vraie au premier appel
    et fausse aux suivants, en silence. Le `frozenset` est pris ici, une fois.
    """
    exiges = frozenset(roles)
    if not exiges:
        #  Une liste vide rendrait la dependance TOUJOURS refusante, et une route
        #  ainsi gardee serait morte sans que rien ne le dise. C'est un garde-fou
        #  de programmation, pas une reponse HTTP : il doit exploser au demarrage.
        message = "exiger_un_role_dans_l_entite appelee sans aucun role : la route serait morte"
        raise ValueError(message)

    #  **LA VALIDATION DE SESSION EST REUTILISEE, PAS REECRITE.** `DEC-466` pour le
    #  masquage, `ECART-022` pour les modeles : deux chemins d'une meme regle
    #  divergent. Et celui-la porte le rafraichissement d'activite de `DEC-531`.
    controler_la_session = exiger_une_session(parametres)

    def controler(requete: Request, reponse: Response) -> SessionEtablie:
        appelant = controler_la_session(requete, reponse)

        code = requete.path_params.get(PARAMETRE_DE_CHEMIN)
        if not isinstance(code, str) or not code:
            #  Le chemin ne porte pas le parametre attendu : c'est une erreur de
            #  montage, pas un refus d'acces. Elle doit etre BRUYANTE, sinon la
            #  route rendrait 404 pour tout le monde en paraissant protegee.
            message = (
                f"la route ne porte pas de parametre de chemin `{PARAMETRE_DE_CHEMIN}` : "
                f"la dependance ne peut pas savoir quelle entite est consultee"
            )
            raise RuntimeError(message)

        #  L'instant est releve UNE FOIS : deux appels a `now()` dans une meme
        #  resolution pourraient tomber de part et d'autre de la borne d'une
        #  periode, et rendre un verdict incoherent avec lui-meme.
        instant = dt.datetime.now(tz=dt.UTC)

        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                #  Verification 7 du §2.6, « l'etat de la ressource ». Le meme 404
                #  qu'ailleurs : pour l'appelant, une entite non active n'existe pas.
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)

        if not exiges & set(permissions.roles):
            raise ErreurApplicative(
                code=CODE_ROLE_REFUSE,
                message=MESSAGE_ROLE_REFUSE,
                statut=status.HTTP_403_FORBIDDEN,
            )
        return appelant

    return controler
