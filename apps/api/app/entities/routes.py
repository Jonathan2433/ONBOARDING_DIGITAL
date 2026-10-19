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

import datetime as dt
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING, Final

from fastapi import APIRouter, Depends, Path, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import String

from app.auth.dependances import SessionEtablie, exiger_une_session, proteger_du_csrf
from app.entities.creation import DemandeDeCreationDEntite, creer_une_entite
from app.entities.modeles import Entity
from app.entities.services import lister_les_entites_actives, resoudre_une_entite_active
from app.permissions.services import est_super_administrateur
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative


def _longueur_du_code() -> int:
    """La longueur de `entity.code`, DERIVEE de la colonne et non recopiee.

    Ecrire `64` ici en ferait une seconde source, qui vieillirait au premier
    `ALTER TABLE` -- §7.27.

    **ELLE ECHOUE PLUTOT QUE DE SE REPLIER SUR UNE VALEUR PAR DEFAUT.** Un
    `or 64` aurait satisfait `mypy` et donne un nombre **qu'on ne peut pas
    tenir** : si la colonne cessait un jour d'etre une chaine bornee, la borne
    silencieuse de 64 deviendrait une invention. Mieux vaut un demarrage refuse,
    qui nomme la cause, qu'une valeur plausible -- c'est le septieme point du
    §7.0, et c'est le meme esprit que les onze garde-fous du §20.3.
    """
    type_de_colonne = Entity.__table__.c.code.type
    if not isinstance(type_de_colonne, String) or type_de_colonne.length is None:
        message = (
            f"`entity.code` n'est plus une chaine bornee : {type_de_colonne!r}. "
            f"La borne du parametre de chemin ne peut plus en etre derivee."
        )
        raise RuntimeError(message)
    return type_de_colonne.length


LONGUEUR_MAXIMALE_CODE: Final[int] = _longueur_du_code()

#  **UN SEUL GABARIT DE REFUS POUR DEUX CAUSES** : code inconnu, ou entite qui
#  existe sans etre active. Voir l'en-tete de `app/entities/services.py`.
CODE_ENTITE_INTROUVABLE: Final = "entite_introuvable"
MESSAGE_ENTITE_INTROUVABLE: Final = "Cette entite n'existe pas ou n'est pas accessible."

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


class DemandeDeCreationDEntiteRequete(BaseModel):
    """Creer une entite — LOT 9, `T12`. Voir `app/entities/creation.py`.

    `premier_administrateur` DESIGNE une personne EXISTANTE — cette route ne
    cree personne, elle nomme seulement qui administre la nouvelle entite.

    `motif` est OBLIGATOIRE, et non conditionnel comme ailleurs (§18.1,
    `ECART-064`, LOT 10 `T7`) : la garde de cette route N'ACCEPTE QUE `SUPER`
    (voir `_exiger_le_super_administrateur` ci-dessous) — l'intersection avec
    les roles autorisants vaut donc toujours `{SUPER}`, jamais conditionnelle.
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(
        min_length=1,
        max_length=LONGUEUR_MAXIMALE_CODE,
        description="Unique, et JAMAIS reattribue — verrouille des la creation",
    )
    nom: str = Field(min_length=1, description="`display_name`")
    ville: str = Field(min_length=1, description="`city`")
    pays: str = Field(min_length=2, max_length=2, description="ISO 3166-1 alpha-2, ex. `FR`")
    fuseau: str = Field(min_length=1, description="IANA, ex. `Europe/Paris`")
    premier_administrateur: uuid.UUID = Field(
        description="La personne qui devient administrateur de cette entite"
    )
    motif: str = Field(
        min_length=1,
        max_length=2000,
        description="Le motif du §18.1 — toujours obligatoire ici (`ECART-064`).",
    )


class ReponseDeCreationDEntite(BaseModel):
    """Ce que la creation a produit."""

    id: uuid.UUID
    code: str
    version: int


#  **UNE GARDE GLOBALE, DISTINCTE DE `exiger_un_role_dans_l_entite`** (LOT 9,
#  `T12`). Celle-ci lit `code` dans le CHEMIN et resout une entite deja
#  existante — exactement ce qu'une route qui CREE une entite ne peut pas
#  faire. Le cahier §21 est litteral : « Seul le role `SUPER` peut […] creer
#  une entite » — une portee GLOBALE, sans aucune entite consultee.
#
#  **DEFINIE ICI, PAS DANS `app.permissions.dependances`** : ce module-la
#  importe deja `CODE_ENTITE_INTROUVABLE`/`MESSAGE_ENTITE_INTROUVABLE` DEPUIS
#  `app.entities.routes` (pour `exiger_un_role_dans_l_entite`). L'y placer
#  aurait ferme un cycle d'imports — mesure directement, `ImportError:
#  cannot import name … (most likely due to a circular import)`.
CODE_ACCES_REFUSE: Final = "acces_refuse"
MESSAGE_ACCES_REFUSE: Final = (
    "Cet acces a ete refuse. Seul un super-administrateur peut creer une entite."
)


def _exiger_le_super_administrateur(parametres: Parametres) -> Callable[..., SessionEtablie]:
    """Fabriquer une dependance qui exige le role technique GLOBAL `SUPER_ADMIN`.

    Reutilise `est_super_administrateur`, LA MEME requete que la branche 1 de
    `resoudre_les_permissions` (§7.27) : aucune seconde regle qui pourrait
    diverger de la premiere au premier reglage change.
    """
    controler_la_session = exiger_une_session(parametres)

    def controler(requete: Request, reponse: Response) -> SessionEtablie:
        appelant = controler_la_session(requete, reponse)
        instant = dt.datetime.now(tz=dt.UTC)

        with moteur(parametres).connect() as connexion:
            autorise = est_super_administrateur(connexion, appelant.personne, instant)

        if not autorise:
            raise ErreurApplicative(
                code=CODE_ACCES_REFUSE,
                message=MESSAGE_ACCES_REFUSE,
                statut=status.HTTP_403_FORBIDDEN,
            )
        return appelant

    return controler


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

    @routeur.get(
        "/entities/{code}",
        dependencies=[Depends(exiger_une_session(parametres))],
        status_code=status.HTTP_200_OK,
        response_model=EntiteDuPortail,
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
                    "l'entite existe sans etre active. Le §8.3 donne acces aux entites "
                    "ACTIVES : pour l'appelant, une entite `draft` n'est pas interdite, "
                    "elle n'existe pas. Distinguer les deux cas apprendrait qu'un "
                    "brouillon existe, et le LOT 9 en creera avant publication."
                )
            },
        },
        summary="Resoudre l'entite consultee par son code",
        description=(
            "L'entite consultee vit dans l'ADRESSE, et le cahier le determine : le §8.1, "
            "le §9.1 et le §9.2 font tous atterrir sur la page nationale apres "
            "connexion, si bien qu'une memoire serveur du dernier choix n'aurait aucun "
            "consommateur. Cette route resout le code que porte l'URL. "
            "AUCUNE PERMISSION N'EST TRANSFEREE : la matrice §5 donne la lecture de "
            "toutes les entites aux huit roles authentifies, donc la reponse est la MEME "
            "que l'appelant appartienne a cette entite ou non."
        ),
    )
    def resoudre_l_entite(
        #   en defaut est la forme de FastAPI, et `B008` ne s'y
        #  declenche pas : ruff connait les fabriques de FastAPI. Un `noqa`
        #  inutile ici ferait echouer `RUF100`.
        code: str = Path(
            min_length=1,
            max_length=LONGUEUR_MAXIMALE_CODE,
            description="Le `code` de l'entite, unique et jamais reattribue",
        ),
    ) -> EntiteDuPortail:
        """Resoudre l'entite consultee — cahier §9.2 etape 4, backlog `MVP-L04-US001`."""
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)

        if entite is None:
            #  Le motif precis ne sort pas : deux causes, une seule reponse.
            raise ErreurApplicative(
                code=CODE_ENTITE_INTROUVABLE,
                message=MESSAGE_ENTITE_INTROUVABLE,
                statut=status.HTTP_404_NOT_FOUND,
            )
        return EntiteDuPortail(
            id=entite.id,
            code=entite.code,
            nom=entite.display_name,
            ville=entite.city,
        )

    @routeur.post(
        "/entities",
        status_code=status.HTTP_201_CREATED,
        response_model=ReponseDeCreationDEntite,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : seul le role technique GLOBAL `SUPER_ADMIN` peut "
                    "creer une entite — cahier §21, litteral."
                )
            },
            status.HTTP_409_CONFLICT: {
                "description": "`code_deja_utilise` : ce code est deja pris par une autre entite."
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`personne_introuvable` : la personne designee comme premier "
                    "administrateur n'existe pas."
                )
            },
        },
        summary="Creer une nouvelle entite depuis des modeles generiques",
        description=(
            "Cahier §4.1, §21 ; backlog `MVP-L09-US007`. **L'ENTITE NAIT VIERGE** — "
            "aucun contenu, aucune responsabilite Framework, aucun modele d'onboarding "
            "n'est seme : rien n'existe a copier depuis Bordeaux, et la resolution "
            "`DSM > CIRCLE > ENTITY > GLOBAL` (LOT 7) retombe deja sur le modele "
            "d'onboarding GLOBAL generique des qu'aucun modele propre a l'entite "
            "n'existe. Voir `app/entities/creation.py`.<br><br>"
            "**CREE DIRECTEMENT `active`** (`activated_at` pose), aucun etat `draft` "
            "intermediaire dans cette sous-etape.<br><br>"
            "**LE PREMIER ADMINISTRATEUR EST NOMME DANS LE MEME APPEL** — "
            "`technical_role_assignment` (`ENTITY_ADMIN`), sans quoi l'entite "
            "resterait injoignable localement jusqu'a un second geste manuel."
        ),
    )
    def creer_l_entite(
        demande: DemandeDeCreationDEntiteRequete,
        requete: Request,
        appelant: SessionEtablie = Depends(_exiger_le_super_administrateur(parametres)),  # noqa: B008
    ) -> ReponseDeCreationDEntite:
        """Creer une entite — cahier §4.1/§21, backlog `MVP-L09-US007`."""
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            cree = creer_une_entite(
                connexion,
                demande=DemandeDeCreationDEntite(
                    code=demande.code,
                    display_name=demande.nom,
                    city=demande.ville,
                    country_code=demande.pays,
                    timezone=demande.fuseau,
                    premier_administrateur=demande.premier_administrateur,
                ),
                acteur=appelant.personne,
                instant=instant,
                motif=demande.motif,
            )
        return ReponseDeCreationDEntite(id=cree.id, code=cree.code, version=cree.version)

    return routeur
