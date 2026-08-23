"""Les dependances d'autorisation des routes — LOT 3 `T10`, LOT 4 `T1`.

Deux dependances, pour deux natures d'appelant :

  `exiger_une_session`  une PERSONNE, par son cookie de session. LOT 4, `T1`.
  `exiger_un_scope`     un COMPTE DE SERVICE, par un jeton porteur. LOT 3, `T10`.

**ELLES NE SE SUBSTITUENT PAS L'UNE A L'AUTRE**, et la matrice le dit : son
tableau du §5 porte neuf colonnes, de `ANON` a `SUPER`, et **`SERVICE` n'y figure
pas**. Un compte de service n'est donc pas autorise par ce tableau sur les
ressources qu'il decrit -- lui ouvrir la page nationale serait inventer une ligne
que la matrice n'a pas. Le residuel est **nomme** au compte rendu de `T1` plutot
que comble par une hypothese.

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

import dataclasses
import datetime as dt
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING, Final

from fastapi import Request, Response, status

from app.auth.comptes_de_service import Authentification, authentifier_un_jeton
from app.auth.sessions import lire_et_rafraichir
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

#  **UN SEUL GABARIT DE REFUS POUR CINQ CAUSES** : cookie absent, jeton inconnu,
#  session revoquee, duree absolue depassee, inactivite depassee. C'est le meme
#  texte que la route `GET /auth/session` de `T6`, et ce n'est pas une
#  coincidence : deux libelles differents pour le meme refus apprendraient a un
#  appelant lequel des cinq cas il a rencontre.
CODE_SESSION_EXIGEE: Final = "session_refusee"
MESSAGE_SESSION_EXIGEE: Final = "Aucune session valide. Connectez-vous pour continuer."


@dataclasses.dataclass(frozen=True, slots=True)
class SessionEtablie:
    """L'appelant, une fois sa session validee.

    **ELLE NE PORTE PAS LE JETON.** Une route metier n'en a aucun besoin -- il
    vit dans un cookie `HttpOnly` -- et le faire circuler dans le code applicatif
    multiplierait les endroits d'ou il peut fuir vers un journal.
    """

    personne: uuid.UUID
    identifiant: uuid.UUID


def exiger_une_session(parametres: Parametres) -> Callable[[Request, Response], SessionEtablie]:
    """Fabriquer une dependance FastAPI qui exige une session de personne valide.

    Employee ainsi :

        @routeur.get("/entities")
        def lister(appelant: SessionEtablie = Depends(exiger_une_session(parametres))): ...

    CE QU'ELLE AUTORISE EST DERIVE DE LA MATRICE, PAS CHOISI

      Son tableau du §5 donne la « Page nationale et carte des entites » a
      **`ANON` = tiret** et aux **huit** roles authentifies -- `EMP`, `NEW`,
      `DSM`, `ESM`, `BOOST`, `OFFICE`, `ADM-E`, `SUPER` -- tous a la coche. Il
      n'y a donc **aucune distinction de role a faire** : la seule question est
      « une session valide, oui ou non ». Ajouter un controle de role ici
      exigerait plus que la matrice, ce qui est le defaut du §7.20.

    ELLE RAFRAICHIT L'ACTIVITE, ET CELA REPOND AU RESIDUEL DE `DEC-531`

      Elle reutilise `lire_et_rafraichir`, **le seul chemin de validation de
      session du projet**. En ecrire un second, en lecture seule, donnerait deux
      chemins qui divergent -- c'est ce que `DEC-466` interdit pour le masquage
      et `ECART-022` pour les modeles de configuration.

      **CONSEQUENCE, ET ELLE DOIT ETRE DITE : chaque lecture metier ECRIT
      desormais `last_activity_at`.** `T6` du LOT 3 avait nomme comme une entorse
      assumee le fait qu'un `GET` ecrive, sur la seule route de session, et
      `DEC-531` renvoyait le reexamen au LOT 4. Le reexamen donne ceci :
      **l'entorse ne disparait pas, elle se generalise**, et elle reste
      acceptable pour la raison que `T6` avait deja mesuree -- l'effet porte sur
      la session de l'appelant lui-meme, si bien qu'un site tiers qui la
      declencherait ne ferait que prolonger la session de sa victime. Aucun gain
      pour lui. **C'est aussi la semantique que le mot « inactivite » exige** :
      un utilisateur qui navigue sans jamais appeler la route de session serait
      autrement deconnecte alors qu'il est actif.

    ELLE POSE `Cache-Control: no-store`, ET CE N'EST PAS UN ORNEMENT

      La reponse d'une route protegee est propre a un appelant. Sans cet en-tete,
      un mandataire partage -- et Caddy est devant -- pourrait servir a un second
      appelant la reponse construite pour le premier. La route de session de `T6`
      le pose deja ; la dependance le pose pour **toutes** les routes qu'elle
      protege, ce qui evite d'avoir a s'en souvenir une fois par route.
    """

    def controler(requete: Request, reponse: Response) -> SessionEtablie:
        reponse.headers["Cache-Control"] = "no-store"
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)

        with moteur(parametres).begin() as connexion:
            etat = lire_et_rafraichir(
                connexion,
                jeton=jeton,
                instant=_maintenant(),
                jours_d_inactivite=parametres.SESSION_IDLE_DAYS,
            )

        if etat.personne is None or etat.identifiant is None:
            #  Le motif precis est dans `etat.motif`, et il ne sort pas : cinq
            #  causes, une seule reponse.
            raise ErreurApplicative(
                code=CODE_SESSION_EXIGEE,
                message=MESSAGE_SESSION_EXIGEE,
                statut=status.HTTP_401_UNAUTHORIZED,
            )
        return SessionEtablie(personne=etat.personne, identifiant=etat.identifiant)

    return controler


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
