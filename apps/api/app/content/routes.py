"""Les routes editoriales — LOT 6, `T5` et `T6`, story `MVP-L06-US004`.

    GET  /entities/{code}/pages/{type_de_page}/{slug}    `T5`, lire le PUBLIE
    POST /entities/{code}/pages                          `T6`, creer un BROUILLON
    PUT  /entities/{code}/pages/{page}/contenu           `T6`, ecrire le contenu

DEUX ADRESSAGES, ET LA DIFFERENCE EST VOULUE

  La **lecture** adresse par `(type, slug)` : c'est l'adresse publique d'une page
  publiee, et le §15.1 la rend unique dans l'entite et le type. L'**ecriture**
  adresse par **identifiant**, parce qu'elle porte d'abord sur des BROUILLONS --
  que la lecture ne sert pas -- et parce qu'un slug est une adresse de
  publication, pas l'identite d'une ressource en cours de redaction.

  L'identifiant est rendu par la creation, et par la lecture de `T5`.

POURQUOI L'ADRESSE DE LECTURE PORTE LE TYPE **ET** LE SLUG

  L'unicite posee par `T1` est `(entity_id, page_type, slug)` sur les pages non
  archivees -- le §15.1 dit « `slug` | Unique dans l'entite **et le type** ».
  Adresser par le slug seul supposerait une unicite que le modele n'ecrit pas,
  et deux pages de types differents pourraient legitimement le partager.

  Une seule route couvre ainsi les CINQ types du §15.1 -- `HOME`, `FRAMEWORK`,
  `CIRCLE`, `OFFICE`, `LEGAL` -- la ou une route par ressource en aurait demande
  autant, chacune avec sa grille de roles a tenir a jour.

QUI LIT : LA MATRICE §5, ET SUREMENT PAS L'ANNEXE A §13 SEULE

  Le §13 porte une ligne « Consulter » a **six** colonnes et **ni `EMP` ni
  `NEW`**. Ces tableaux n'ONT PAS ces colonnes : une absence n'est pas une
  exclusion, et la lire comme telle refuserait le contenu a l'Employe -- l'acteur
  pour qui ce portail existe. Le §5 accorde « Framework », « Cercles » et
  « Bureaux » aux HUIT roles authentifies ; le contenu d'une page de cercle se
  consulte comme le cercle.

LE 404 COUVRE LE BROUILLON, ET C'EST LE POINT LE PLUS IMPORTANT DE LA LECTURE

  Une page en brouillon rend le MEME 404 qu'un slug inconnu. Distinguer
  apprendrait l'existence d'un brouillon a qui n'a pas le droit de le voir, et
  vaudrait `US006` -- « **previsualiser** puis publier » -- qui est la story de
  `T7`, avec sa propre grille : le §13 donne « Publier » a une portee
  **Perimetre** la ou « Modifier » vaut **Entite**.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING, Annotated, Final, TypeVar

from fastapi import APIRouter, Depends, Path, Request, status
from pydantic import BaseModel, Field

from app.auth.dependances import SessionEtablie, exiger_une_session, proteger_du_csrf
from app.content.cycle_de_vie import (
    PageArchivee,
    PagePubliee,
    PageRestauree,
    archiver_une_page,
    publier_une_page,
    restaurer_une_page,
)
from app.content.ecriture import (
    BlocDemande,
    creer_une_page,
    remplacer_le_contenu,
)
from app.content.modeles import TYPES_DE_BLOC, TYPES_DE_PAGE
from app.content.pages import PayloadNonObjet, lire_la_page_de_contenu
from app.content.perimetre import (
    ROLES_D_ECRITURE_EDITORIALE,
    ROLES_DE_CREATION,
    ActionEditoriale,
    resoudre_le_perimetre_editorial,
)
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import EntiteListee, resoudre_une_entite_active
from app.permissions.dependances import exiger_un_role_dans_l_entite
from app.permissions.services import resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable

    from sqlalchemy.engine import Connection

    from app.configuration.settings import Parametres

DESCRIPTION_401: Final = "Aucune session valide — la matrice §5 refuse cette ressource a `ANON`."

#  Un payload qui n'est pas un objet est un defaut de DONNEE, pas une faute de
#  l'appelant : 500, et le code le nomme pour que le journal soit exploitable.
CODE_CONTENU_ILLISIBLE: Final = "contenu_illisible"
MESSAGE_CONTENU_ILLISIBLE: Final = "Un bloc de cette page porte un contenu illisible."

#  **LA LONGUEUR MAXIMALE VIENT DE LA COLONNE**, §15.1 : `slug` est
#  `varchar(160)`. L'ecrire ici en dur divergerait au premier changement (§7.27).
LONGUEUR_MAXIMALE_SLUG: Final = 160


class BlocDeContenuRendu(BaseModel):
    """Un bloc, servi comme DONNEE et jamais comme du balisage.

    **`contenu` EST UN OBJET, ET C'EST LE TYPE QUI TIENT « AUCUN HTML EXECUTE ».**
    Il n'existe aucune valeur de cette forme ou un champ designerait du balisage
    a interpreter : le perdre exigerait de changer ce type, pas de retirer un
    controle (§7.35). Ses clefs ne sont pas contraintes -- le corpus n'en nomme
    aucune, `QO-121`.
    """

    identifiant: uuid.UUID
    type_de_bloc: str
    ordre: int
    contenu: dict[str, object]


class ReponseDeLaPageDeContenu(BaseModel):
    """Une page PUBLIEE et ses blocs, dans l'ordre — `MVP-L06-US004`.

    **`nombre_de_blocs` EST DERIVE DU TUPLE.** Deux sources pour une meme
    grandeur divergent (§7.0, sixieme proposition), et un client afficherait
    « 3 blocs » au-dessus de deux.
    """

    identifiant: uuid.UUID
    type_de_page: str
    titre: str
    slug: str
    publiee_le: str | None
    blocs: list[BlocDeContenuRendu]
    nombre_de_blocs: int


CODE_CONTENU_HORS_PERIMETRE: Final = "contenu_hors_perimetre"
MESSAGE_CONTENU_HORS_PERIMETRE: Final = "Votre perimetre ne vous permet pas de modifier ce contenu."


class BlocSoumis(BaseModel):
    """Un bloc tel que l'auteur le soumet — LOT 6, `T6`.

    **DEUX CHAMPS, ET LES ABSENTS SONT LE POINT.**

    Il n'y a **ni `ordre`** -- il vaut l'index dans la liste, si bien que deux
    blocs de meme rang sont impossibles a exprimer (§7.35) -- **ni identifiant**
    -- la liste remplace la liste -- **ni aucun champ de nature HTML** : pas de
    `html`, pas de `format`, pas de `rendu`. C'est le type qui tient « aucun HTML
    arbitraire n'est **accepte** », et non un filtre : chercher `<script` serait
    une heuristique, donc un defaut (§7.25).

    `contenu` est un **objet**, et Pydantic refuse tout le reste au format du
    §18.3. C'est ce refus a l'ECRITURE qui garantit que le 500 de `T5` --
    `PayloadNonObjet` -- ne survienne jamais pour une donnee ecrite par l'API.
    """

    type_de_bloc: str = Field(
        min_length=1,
        max_length=32,
        description="L'un des types de `DEC-577` — " + ", ".join(f"`{t}`" for t in TYPES_DE_BLOC),
    )
    contenu: dict[str, object] = Field(
        default_factory=dict,
        description=(
            "Les donnees du bloc. **Ses clefs ne sont pas contraintes** : le corpus n'en "
            "nomme aucune, et `QO-121` porte la question a Lea. Ce qui est contraint est "
            "que ce soit un OBJET — un scalaire ou un tableau ne peut pas porter les "
            "« champs structures » du §15.2."
        ),
    )


class DemandeDeCreationDePage(BaseModel):
    """Creer une page — §13 « Creer un contenu general », modele §15.1.

    **AUCUN CHAMP `etat` NI `publiee_le`**, et ce n'est pas un oubli : la valeur
    n'est pas ignoree, elle n'existe pas. Le §13 separe « Modifier » — portee
    Entite — de « Publier » — portee **Perimetre** — et une creation qui pourrait
    publier confondrait deux droits que le document distingue.
    """

    type_de_page: str = Field(
        min_length=1,
        max_length=32,
        description="L'un des types du §15.1 — " + ", ".join(f"`{t}`" for t in TYPES_DE_PAGE),
    )
    titre: str = Field(min_length=1, description="Le titre de la page (§15.1)")
    slug: str = Field(
        min_length=1,
        max_length=LONGUEUR_MAXIMALE_SLUG,
        description="Unique dans l'entite ET le type (§15.1)",
    )
    #  **PAR CODE, COMME PARTOUT AILLEURS DEPUIS `T3` ET `T4`.** Deux modes
    #  d'adressage d'une meme ressource divergeraient, et l'un des deux serait
    #  celui qu'aucun ecran n'emploie.
    cercle: str | None = Field(
        default=None, description="Le `code` du cercle — requis pour une page `CIRCLE` (§15.1)"
    )
    bureau: str | None = Field(
        default=None, description="Le `code` du bureau — requis pour une page `OFFICE` (§15.1)"
    )


class DemandeDEcritureDuContenu(BaseModel):
    """Remplacer le titre et les blocs d'une page — §13 « Modifier un contenu de … »."""

    #  §18.4 : « les modifications sensibles utilisent une concurrence optimiste.
    #  Une version obsolete produit un 409 **sans ecrasement silencieux** ».
    #  **OBLIGATOIRE, ET C'EST LE DEFAUT `T11-6` DU LOT 5 QUI L'A APPRIS** : un
    #  bouchon rendait 200 sur un corps vide, l'API rend 422.
    version: int = Field(ge=1, description="La version lue — §18.4, concurrence optimiste")
    titre: str = Field(min_length=1, description="Le titre de la page (§15.1)")
    blocs: list[BlocSoumis] = Field(
        default_factory=list,
        description=(
            "La liste **remplace** la liste. Les blocs retires sont ARCHIVES, jamais "
            "supprimes (modele §2.4). Une liste vide est legitime : une page sans bloc "
            "existe, et `T5` la rend avec un tableau vide."
        ),
    )


class ReponseDeCreationDePage(BaseModel):
    """La page neuve, toujours en BROUILLON."""

    identifiant: uuid.UUID
    type_de_page: str
    titre: str
    slug: str
    #  Rendu plutot que tu, et c'est une mesure et non une promesse : l'appelant
    #  LIT que sa page est en brouillon, au lieu de le deduire de la doc.
    etat: str
    version: int


class ReponseDEcritureDuContenu(BaseModel):
    """Ce que l'ecriture a produit — `MVP-L06-US004`.

    **`blocs_archives` EST RAPPORTE PLUTOT QUE TU** (§7.20) : un auteur qui envoie
    deux blocs la ou la page en portait cinq doit voir que trois ont quitte
    l'affichage. Le taire rendrait une suppression accidentelle invisible.
    """

    version: int
    blocs: list[BlocDeContenuRendu]
    nombre_de_blocs: int
    blocs_archives: int


class DemandeDeTransition(BaseModel):
    """Publier, archiver ou restaurer — **la version, et rien d'autre**.

    **AUCUN CHAMP D'ETAT CIBLE, ET C'EST LE MEME PARTI QUE LA CREATION DE `T6`.**
    Un champ `etat` laisserait croire a une machine a etats pilotee par
    l'appelant, et il faudrait alors refuser toutes les transitions que le §13
    n'ecrit pas. L'etat cible est porte par la ROUTE : trois chemins, trois
    lignes du §13, et les transitions absentes du document sont **inexprimables**
    plutot que refusees (§7.35).

    **AUCUN MOTIF NON PLUS.** Le §18.1 enumere les cinq cas ou un motif est
    obligatoire, et archiver un contenu n'y est pas. En demander un ici seulement
    donnerait une regle appliquee a une route sur quarante -- `ECART-064`.
    """

    #  §18.4, « concurrence optimiste [...] sans ecrasement silencieux ».
    #  Obligatoire comme pour l'ecriture : publier ce qu'un autre vient de
    #  reecrire est exactement ce que ce verrou existe pour empecher.
    version: int = Field(ge=1, description="La version lue — §18.4, concurrence optimiste")


class ReponseDePublication(BaseModel):
    """`US006`, « la version publiee est identifiable » — la voici, datee."""

    version: int
    etat: str
    publiee_le: dt.datetime


class ReponseDArchivageDUnContenu(BaseModel):
    """Ce que l'archivage a produit.

    `publiee_le` reste rendu : une page archivee **apres** publication garde la
    date a laquelle elle a ete publiee, et `null` distingue celle qui ne l'a
    jamais ete. Deux histoires differentes, deux valeurs differentes.
    """

    version: int
    etat: str
    archivee_le: dt.datetime
    publiee_le: dt.datetime | None


class ReponseDeRestaurationDUnContenu(BaseModel):
    """La page revient en BROUILLON, et `etat` le DIT plutot que la doc.

    Republier est un second geste, explicite, a la grille du §13 « Publier ».
    """

    version: int
    etat: str
    publiee_le: dt.datetime | None


#  Le resultat d'une transition : `PagePubliee`, `PageArchivee` ou `PageRestauree`.
#  Un `TypeVar` plutot qu'une union, pour que chaque route recoive EXACTEMENT le
#  type de son service -- une union obligerait chaque appelant a le retrecir, et
#  mypy cesserait de verifier qu'on lit les bons champs.
_Resultat = TypeVar("_Resultat")


def _proteger(parametres: Parametres, requete: Request) -> None:
    """Appliquer les deux barrieres CSRF a une ecriture — `DEC-531`.

    **LE JETON EST LU DANS LE COOKIE, PAS RECU DE LA DEPENDANCE.**
    `SessionEtablie` ne le porte pas a dessein : le faire circuler multiplierait
    les endroits d'ou il peut fuir vers un journal. La garde a valide la session
    depuis ce meme cookie, donc il est la ; s'il manquait, passer `None`
    DESARMERAIT la barriere de jeton en silence, et on refuse plutot.

    **ELLE N'EST PAS RECOPIEE ICI** : `proteger_du_csrf` vit dans
    `app/auth/dependances.py` depuis `T7` du LOT 5, et deux copies d'une meme
    regle divergent au premier changement (`DEC-466`).
    """
    jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
    proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")


def _resoudre_ou_404(connexion: Connection, code: str) -> EntiteListee:
    """L'entite ACTIVE de ce code, ou le 404 que rend tout le reste de l'API."""
    entite = resoudre_une_entite_active(connexion, code)
    if entite is None:
        raise ErreurApplicative(
            code=CODE_ENTITE_INTROUVABLE,
            message=MESSAGE_ENTITE_INTROUVABLE,
            statut=status.HTTP_404_NOT_FOUND,
        )
    return entite


def routeur_contenus(parametres: Parametres) -> APIRouter:
    """Routeur du rendu et de l'ecriture editoriale, monte sous le prefixe versionne."""
    routeur = APIRouter(tags=["contenus"])

    @routeur.get(
        "/entities/{code}/pages/{type_de_page}/{slug}",
        #  `dependencies=` et non `Annotated[...]` : sous `from __future__ import
        #  annotations`, FastAPI resout l'annotation dans les globals du module,
        #  n'y trouve pas la fermeture `parametres`, et rend 422 pour tout le
        #  monde sur un livrable qui PARAIT protege. Mesure du 23/08/2026.
        dependencies=[Depends(exiger_une_session(parametres))],
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeLaPageDeContenu,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "UNE SEULE forme pour SIX causes, a dessein : code d'entite "
                    "inconnu, entite non active, type de page inconnu, slug "
                    "inconnu, page d'une AUTRE entite, ou page en BROUILLON / "
                    "archivee. Distinguer le brouillon apprendrait son existence, "
                    "et viderait `US006` de son sens."
                )
            },
        },
        summary="Une page de contenu publiee et ses blocs",
        description=(
            "Les blocs d'une page PUBLIEE, dans leur ordre d'affichage — "
            "`MVP-L06-US004`. "
            "Exige une session : la matrice §5 refuse cette ressource a `ANON` et "
            "l'accorde aux huit roles authentifies **sans distinction**. "
            "**Les blocs sont servis comme DONNEES**, jamais comme du balisage : "
            "le contenu de chaque bloc est un objet JSON, et la reponse ne porte "
            "aucun champ de nature HTML — « aucun HTML arbitraire n'est stocke ou "
            "execute », cahier §10.7 et modele §15.2. "
            "**Les clefs de ce contenu ne sont pas contraintes** : le corpus n'en "
            "nomme aucune, et `QO-121` porte la question. "
            "Une page en BROUILLON rend 404 : la previsualisation est `US006`, "
            "avec sa propre grille de roles."
        ),
    )
    def lire_une_page_de_contenu(
        code: str = Path(
            min_length=1,
            max_length=LONGUEUR_MAXIMALE_CODE,
            description="Le `code` de l'entite consultee, tel qu'il vit dans l'adresse",
        ),
        type_de_page: str = Path(
            min_length=1,
            max_length=32,
            description=(
                "Le type de page du §15.1 — "
                + ", ".join(f"`{t}`" for t in TYPES_DE_PAGE)
                + ". Un type inconnu rend 404, comme un slug inconnu."
            ),
        ),
        slug: str = Path(
            min_length=1,
            max_length=LONGUEUR_MAXIMALE_SLUG,
            description="Le `slug` de la page, unique dans l'entite ET le type (§15.1)",
        ),
    ) -> ReponseDeLaPageDeContenu:
        """Une page de contenu publiee et ses blocs — cahier §10.7, modele §15.2."""
        with moteur(parametres).begin() as connexion:
            #  **LA MEME RESOLUTION QUE LES DEUX ECRITURES**, et non une copie :
            #  deux chemins d'une meme regle divergent au premier changement
            #  (`DEC-466`). La forme etait ici en clair depuis `T5` ; `T6` l'a
            #  extraite en y ajoutant ses appelants, sans changer le comportement.
            entite = _resoudre_ou_404(connexion, code)
            #  **UN TYPE INCONNU N'EST PAS UNE FAUTE DE SYNTAXE, C'EST UN 404.**
            #  Le refuser en 422 distinguerait « ce type n'existe pas » de « cette
            #  page n'existe pas », ce qui ne sert personne et decrit le schema.
            if type_de_page not in TYPES_DE_PAGE:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            try:
                page = lire_la_page_de_contenu(
                    connexion, entite=entite.id, type_de_page=type_de_page, slug=slug
                )
            except PayloadNonObjet as erreur:
                #  Refuse VISIBLEMENT plutot que corrige en silence (§7.20) : le
                #  message du journal nomme le bloc, celui du client ne le nomme
                #  pas — il n'y peut rien, et l'identifiant ne le regarde pas.
                raise ErreurApplicative(
                    code=CODE_CONTENU_ILLISIBLE,
                    message=MESSAGE_CONTENU_ILLISIBLE,
                    statut=status.HTTP_500_INTERNAL_SERVER_ERROR,
                ) from erreur
            if page is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )

        return ReponseDeLaPageDeContenu(
            identifiant=page.identifiant,
            type_de_page=page.type_de_page,
            titre=page.titre,
            slug=page.slug,
            publiee_le=page.publiee_le,
            blocs=[
                BlocDeContenuRendu(
                    identifiant=b.identifiant,
                    type_de_bloc=b.type_de_bloc,
                    ordre=b.ordre,
                    contenu=b.contenu,
                )
                for b in page.blocs
            ],
            nombre_de_blocs=page.nombre_de_blocs,
        )

    # ========================================================================
    #
    #  L'ECRITURE — LOT 6, `T6`, `MVP-L06-US004` (2 sur 3)
    #
    #    **DEUX GARDES, PARCE QUE LE §13 PORTE DEUX LIGNES DIFFERENTES.** « Creer
    #    un contenu general » ne donne rien a `BOOST` ni a `OFFICE` ; « Modifier
    #    un contenu de cercle » donne au Booster la portee **Cercle**, et
    #    « Modifier un contenu de bureau » au responsable la portee **Bureau**.
    #    Une garde unique accorderait la creation a deux roles que le document en
    #    exclut -- exactement ce que `T8` du LOT 5 a evite en refusant de
    #    reutiliser `ROLES_D_ECRITURE` pour l'archivage.
    #
    #    **ET LA GRILLE DU LOT 5 NE SE REEMPLOIE PAS DANS L'AUTRE SENS NON PLUS :**
    #    `ROLES_D_ECRITURE` contient `DSM`, que le §13 met a tiret sur ses trois
    #    lignes de modification, et ne contient PAS `OFFICE`, qui porte ici un
    #    droit reel. Les deux grilles different dans les deux sens.
    #
    # ========================================================================
    garde_de_creation = exiger_un_role_dans_l_entite(parametres, ROLES_DE_CREATION)
    garde_d_ecriture = exiger_un_role_dans_l_entite(parametres, ROLES_D_ECRITURE_EDITORIALE)

    @routeur.post(
        "/entities/{code}/pages",
        status_code=status.HTTP_201_CREATED,
        response_model=ReponseDeCreationDePage,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : aucun role de CREATION dans cette entite. Le §13 "
                    "n'a qu'une ligne de creation — « Creer un contenu general » — et "
                    "elle ne porte ni `BOOST` ni `OFFICE` ni `DSM`. Le Booster **modifie** "
                    "le contenu de son cercle, il ne cree pas sa page, de la meme facon "
                    "que le §10.2 lui refuse « Creer un cercle »."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`slug_deja_pris` : le §15.1 veut le slug unique dans l'entite ET le "
                    "type. L'unicite est partielle sur les pages non archivees."
                )
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`type_de_page_refuse` : hors des types controles du §15.1. "
                    "`rattachement_requis` : une page `CIRCLE` exige un cercle, une page "
                    "`OFFICE` un bureau. `ressource_introuvable` : le cercle ou le bureau "
                    "nomme n'est pas dans cette entite, ou il est archive. "
                    "`slug_non_adressable` : une barre oblique rendrait la page "
                    "inatteignable par la route de lecture."
                )
            },
        },
        summary="Creer une page de contenu, en BROUILLON",
        description=(
            "Backlog `MVP-L06-US004`. **La page nait `draft`, et la demande ne porte "
            "aucun champ d'etat** : le §13 separe « Modifier » — portee Entite — de "
            "« Publier » — portee **Perimetre** — et les confondre viderait le critere "
            "« les contenus sont relus avant publication ». La publication est `US006`."
        ),
    )
    def creer_une_page_de_contenu(
        demande: DemandeDeCreationDePage,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        #  `Depends` en defaut et non dans `Annotated` : ce module porte
        #  `from __future__ import annotations`, et FastAPI resout l'annotation
        #  dans les globals du module, ou la fermeture `parametres` n'existe pas.
        #  Le piege est mesure depuis `T1` du LOT 4.
        appelant: SessionEtablie = Depends(garde_de_creation),  # noqa: B008
    ) -> ReponseDeCreationDePage:
        """Creer une page de contenu — matrice §13, modele §15.1."""
        _proteger(parametres, requete)

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = _resoudre_ou_404(connexion, code)
            creee = creer_une_page(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                type_de_page=demande.type_de_page,
                titre=demande.titre,
                slug=demande.slug,
                code_de_cercle=demande.cercle,
                code_de_bureau=demande.bureau,
                instant=instant,
            )

        return ReponseDeCreationDePage(
            identifiant=creee.identifiant,
            type_de_page=creee.type_de_page,
            titre=creee.titre,
            slug=creee.slug,
            etat=creee.etat,
            version=creee.version,
        )

    @routeur.put(
        "/entities/{code}/pages/{page}/contenu",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDEcritureDuContenu,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "Deux causes, deux codes. `acces_refuse` : aucun role d'ecriture "
                    "editoriale dans cette entite — `EMP`, `NEW` et **`DSM`** sont dans ce "
                    "cas, la colonne `DSM` du §13 etant a tiret sur les trois lignes de "
                    "modification. `contenu_hors_perimetre` : le role existe mais pas sur "
                    "CETTE page — un Booster sur la page d'un autre cercle, un responsable "
                    "de bureau sur une page de cercle, ou une responsabilite close ou "
                    "encore a venir."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`version_obsolete` : la page a change depuis votre lecture — cahier "
                    "§18.4, « sans ecrasement silencieux ». Couvre aussi la page archivee "
                    "entre la resolution du perimetre et l'ecriture."
                )
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`type_de_bloc_refuse` : hors des onze types de `DEC-577`, et la "
                    "reponse les enumere — un auteur qui a prouve son role doit savoir "
                    "ce qu'il peut poser. Un `contenu` qui n'est pas un objet JSON est "
                    "refuse par le type lui-meme, au format du §18.3."
                )
            },
        },
        summary="Remplacer le titre et les blocs d'une page",
        description=(
            "Backlog `MVP-L06-US004`, matrice §13. **La liste remplace la liste**, et "
            "les blocs retires sont **archives**, jamais supprimes (modele §2.4). "
            "`display_order` n'est pas un champ : il vaut l'index dans la liste, si bien "
            "que deux blocs de meme rang sont impossibles a exprimer.<br><br>"
            "**Aucun HTML n'est accepte, et c'est tenu par la STRUCTURE** : le contenu "
            "d'un bloc est un objet JSON, son type est controle, et il n'existe aucun "
            "champ qui designerait une chaine comme du balisage. Un filtre textuel serait "
            "une heuristique — `<` est legitime dans « a &lt; b ».<br><br>"
            "**`state` et `published_at` ne sont jamais touches** : publier est `US006`."
        ),
    )
    def ecrire_le_contenu_d_une_page(
        demande: DemandeDEcritureDuContenu,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        page: Annotated[
            uuid.UUID,
            Path(description="L'identifiant de la page, rendu par la creation et par la lecture"),
        ],
        appelant: SessionEtablie = Depends(garde_d_ecriture),  # noqa: B008
    ) -> ReponseDEcritureDuContenu:
        """Remplacer le contenu d'une page — matrice §13, modele §15.2."""
        _proteger(parametres, requete)

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = _resoudre_ou_404(connexion, code)
            #  **LES PERMISSIONS SONT RESOLUES A NOUVEAU, DANS CETTE TRANSACTION.**
            #  La garde a resolu les SIENNES, dans sa propre connexion et a son
            #  propre instant : s'y fier ferait ecrire ce qui a ete autorise
            #  ailleurs. Ce n'est pas une seconde copie de la regle, c'est le meme
            #  appel au bon instant et dans le bon perimetre transactionnel.
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            perimetre = resoudre_le_perimetre_editorial(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                page=page,
                roles=frozenset(permissions.roles),
                instant=instant,
            )
            if ActionEditoriale.MODIFIER not in perimetre.actions:
                #  **UN SEUL GABARIT POUR QUATRE CAUSES** : la page n'existe pas,
                #  elle est d'une autre entite, elle est archivee, ou le role ne
                #  porte pas sur elle. Les distinguer apprendrait l'existence
                #  d'une page a qui n'a pas le droit de l'editer, et le §2.5 pose
                #  le refus par defaut.
                raise ErreurApplicative(
                    code=CODE_CONTENU_HORS_PERIMETRE,
                    message=MESSAGE_CONTENU_HORS_PERIMETRE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            ecrit = remplacer_le_contenu(
                connexion,
                entite=entite.id,
                page=page,
                acteur=appelant.personne,
                version_attendue=demande.version,
                titre=demande.titre,
                blocs=tuple(
                    BlocDemande(type_de_bloc=b.type_de_bloc, contenu=b.contenu)
                    for b in demande.blocs
                ),
                instant=instant,
            )

        return ReponseDEcritureDuContenu(
            version=ecrit.version,
            blocs=[
                BlocDeContenuRendu(
                    identifiant=b.identifiant,
                    type_de_bloc=b.type_de_bloc,
                    ordre=b.ordre,
                    contenu=b.contenu,
                )
                for b in ecrit.blocs
            ],
            nombre_de_blocs=len(ecrit.blocs),
            blocs_archives=ecrit.blocs_archives,
        )

    #  **LES TROIS ROUTES DU CYCLE PARTAGENT UNE SEULE GARDE, ET C'EST EXACT.**
    #  `ROLES_DE_RESTAURATION` est INCLUS dans `ROLES_D_ECRITURE_EDITORIALE` --
    #  un test le mesure -- donc cette garde laisse passer tout ayant-droit des
    #  trois actions. Ce qui separe la restauration des deux autres n'est pas le
    #  role NU mais le couple (role, page) : un Booster franchit la garde puis se
    #  voit refuser par le perimetre, exactement comme il l'est deja sur la page
    #  d'un autre cercle. Une seconde garde donnerait DEUX endroits ou lire la
    #  meme grille, et c'est ce que `DEC-466` interdit.
    garde_du_cycle = garde_d_ecriture

    def _agir(
        requete: Request,
        *,
        code: str,
        page: uuid.UUID,
        action: ActionEditoriale,
        appelant: SessionEtablie,
        executer: Callable[[Connection, uuid.UUID, dt.datetime], _Resultat],
    ) -> _Resultat:
        """Le chemin commun des trois transitions — CSRF, entite, roles, perimetre.

        **ECRIT UNE FOIS PLUTOT QUE TROIS**, et le motif n'est pas l'economie de
        lignes : trois copies d'une meme sequence de garde divergent au premier
        changement, et la copie oubliee est celle qu'aucun test de format
        n'examine. C'est `ECART-022` et `DEC-466`, appliques a une route.

        **LES PERMISSIONS SONT RESOLUES A NOUVEAU DANS CETTE TRANSACTION.** La
        garde a resolu les SIENNES, dans sa propre connexion et a son propre
        instant : s'y fier ferait agir sur ce qui a ete autorise ailleurs.
        """
        _proteger(parametres, requete)

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = _resoudre_ou_404(connexion, code)
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            perimetre = resoudre_le_perimetre_editorial(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                page=page,
                roles=frozenset(permissions.roles),
                instant=instant,
            )
            if action not in perimetre.actions:
                #  **UN SEUL GABARIT POUR CINQ CAUSES** : la page n'existe pas,
                #  elle est d'une autre entite, le role ne porte pas sur elle, la
                #  transition n'est pas offerte par son etat, ou l'action n'est
                #  pas de sa portee -- le Booster qui veut restaurer. Les
                #  distinguer apprendrait l'existence et l'etat d'une page a qui
                #  n'a pas le droit d'y toucher, et le §2.5 pose le refus par
                #  defaut. C'est l'idiome de `T8` du LOT 5, ou « la cible est
                #  deja archivee » rend le meme 403 que « aucun role ».
                raise ErreurApplicative(
                    code=CODE_CONTENU_HORS_PERIMETRE,
                    message=MESSAGE_CONTENU_HORS_PERIMETRE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            return executer(connexion, entite.id, instant)

    @routeur.post(
        "/entities/{code}/pages/{page}/publication",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDePublication,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "Deux causes, deux codes. `acces_refuse` : aucun role editorial dans "
                    "cette entite. `contenu_hors_perimetre` : le role existe mais pas sur "
                    "CETTE page, **ou la page n'est pas un brouillon** — republier "
                    "ecraserait la date meme que `US006` demande d'identifier, et "
                    "l'archive se restaure avant de se publier."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`version_obsolete` : la page a change depuis votre lecture (§18.4). "
                    "`borne_des_responsables` : publier la page d'un bureau exige entre "
                    "un et trois responsables **actifs** — modele §8.4, `DEC-583`. C'est "
                    "le seul geste du projet qui fasse mordre cette borne."
                )
            },
        },
        summary="Publier une page — le brouillon devient public",
        description=(
            "Backlog `MVP-L06-US006`, matrice §13 « Publier immediatement ». La page "
            "passe de `draft` a `published` et **recoit sa date de publication**, ce qui "
            "la rend servie par la lecture de `T5`.<br><br>"
            "**Il n'existe aucune depublication** : le §13 porte « Publier », « Archiver » "
            "et « Restaurer », et aucune ligne ne ramene une page publiee au brouillon. "
            "Retirer une page du public se fait en l'archivant."
        ),
    )
    def publier_une_page_de_contenu(
        demande: DemandeDeTransition,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        page: Annotated[uuid.UUID, Path(description="L'identifiant de la page")],
        appelant: SessionEtablie = Depends(garde_du_cycle),  # noqa: B008
    ) -> ReponseDePublication:
        """Publier une page — matrice §13, story `MVP-L06-US006`."""

        def executer(connexion: Connection, entite: uuid.UUID, instant: dt.datetime) -> PagePubliee:
            return publier_une_page(
                connexion,
                entite=entite,
                page=page,
                acteur=appelant.personne,
                version_attendue=demande.version,
                instant=instant,
            )

        publiee = _agir(
            requete,
            code=code,
            page=page,
            action=ActionEditoriale.PUBLIER,
            appelant=appelant,
            executer=executer,
        )
        return ReponseDePublication(
            version=publiee.version, etat=publiee.etat, publiee_le=publiee.publiee_le
        )

    @routeur.post(
        "/entities/{code}/pages/{page}/archivage",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDArchivageDUnContenu,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : aucun role editorial. `contenu_hors_perimetre` : le "
                    "role ne porte pas sur cette page, ou elle est **deja archivee**."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_409_CONFLICT: {
                "description": "`version_obsolete` : la page a change depuis votre lecture."
            },
        },
        summary="Archiver une page — brouillon comme publiee",
        description=(
            "Backlog `MVP-L06-US006`, matrice §13 « Archiver » et §18 « Archiver un "
            "contenu dans son perimetre ». La page quitte la lecture publique.<br><br>"
            "**`archived_at` ET `state` sont ecrits dans le MEME `UPDATE`**, si bien "
            "qu'ils ne peuvent pas diverger par cette API.<br><br>"
            "**L'archivage LIBERE le slug** — l'index unique du §15.1 est partiel sur "
            "`archived_at IS NULL`. Une page neuve peut donc le reprendre, et c'est "
            "alors la RESTAURATION qui sera refusee, jamais l'archivage.<br><br>"
            "**Aucun motif n'est demande** : le §18.1 en enumere cinq cas, et archiver "
            "un contenu n'en est pas un."
        ),
    )
    def archiver_une_page_de_contenu(
        demande: DemandeDeTransition,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        page: Annotated[uuid.UUID, Path(description="L'identifiant de la page")],
        appelant: SessionEtablie = Depends(garde_du_cycle),  # noqa: B008
    ) -> ReponseDArchivageDUnContenu:
        """Archiver une page — matrice §13 et §18."""

        def executer(
            connexion: Connection, entite: uuid.UUID, instant: dt.datetime
        ) -> PageArchivee:
            return archiver_une_page(
                connexion,
                entite=entite,
                page=page,
                acteur=appelant.personne,
                version_attendue=demande.version,
                instant=instant,
            )

        archivee = _agir(
            requete,
            code=code,
            page=page,
            action=ActionEditoriale.ARCHIVER,
            appelant=appelant,
            executer=executer,
        )
        return ReponseDArchivageDUnContenu(
            version=archivee.version,
            etat=archivee.etat,
            archivee_le=archivee.archivee_le,
            publiee_le=archivee.publiee_le,
        )

    @routeur.post(
        "/entities/{code}/pages/{page}/restauration",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeRestaurationDUnContenu,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : aucun role editorial. `contenu_hors_perimetre` : "
                    "la page n'est pas archivee, **ou l'appelant n'a qu'une portee "
                    "locale** — le §13, le §18 et le cahier §10.1 mettent tous trois "
                    "`BOOST` et `OFFICE` a tiret sur la restauration, alors qu'ils "
                    "portent l'archivage de leur propre page. La grille est asymetrique, "
                    "et c'est ecrit trois fois."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`version_obsolete` : la page a change depuis votre lecture. "
                    "`slug_deja_pris` : une page vivante a repris le slug pendant "
                    "l'archivage — la restaurer le mettrait en double."
                )
            },
        },
        summary="Restaurer une page archivee — elle revient en BROUILLON",
        description=(
            "Backlog `MVP-L06-US006`, matrice §18 « Restaurer un contenu | Entite, "
            "restauration fonctionnelle », et `ARB-DROIT-003` qui nomme la condition du "
            "mot « Conditionnel » du §13.<br><br>"
            "**La page revient en `draft`, jamais en `published`** : restaurer n'est pas "
            "publier, le §13 en fait deux lignes a deux grilles, et `RIGHTS-001` refuse "
            "par defaut ce qui n'est pas explicitement accorde. Republier est un second "
            "geste, et il laisse sa trace. `QO-122` porte la question a Lea.<br><br>"
            "**`published_at` est CONSERVE** : la page a ete publiee ce jour-la, et "
            "l'effacer detruirait un fait."
        ),
    )
    def restaurer_une_page_de_contenu(
        demande: DemandeDeTransition,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        page: Annotated[uuid.UUID, Path(description="L'identifiant de la page")],
        appelant: SessionEtablie = Depends(garde_du_cycle),  # noqa: B008
    ) -> ReponseDeRestaurationDUnContenu:
        """Restaurer une page archivee — matrice §18, `ARB-DROIT-003`."""

        def executer(
            connexion: Connection, entite: uuid.UUID, instant: dt.datetime
        ) -> PageRestauree:
            return restaurer_une_page(
                connexion,
                entite=entite,
                page=page,
                acteur=appelant.personne,
                version_attendue=demande.version,
                instant=instant,
            )

        restauree = _agir(
            requete,
            code=code,
            page=page,
            action=ActionEditoriale.RESTAURER,
            appelant=appelant,
            executer=executer,
        )
        return ReponseDeRestaurationDUnContenu(
            version=restauree.version, etat=restauree.etat, publiee_le=restauree.publiee_le
        )

    return routeur
