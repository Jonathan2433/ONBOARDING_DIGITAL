"""`GET /entities/{code}/framework` — LOT 6, sous-etape `T2`, `MVP-L06-US001`.

QUI LIT, ET POURQUOI AUCUN ROLE N'EST EXAMINE ICI

  **La matrice §5 donne « Framework | ANON — | EMP Lecture | NEW Lecture | DSM
  Lecture | ESM | BOOST | OFFICE | ADM-E | SUPER » : huit roles authentifies,
  sans distinction.** La route exige donc une session et rien de plus, exactement
  comme le trombinoscope de `T2` du LOT 5, dont la ligne du §5 est identique.

  **L'ANNEXE A §10.1 N'A NI COLONNE `EMP` NI COLONNE `NEW`**, et la lire seule
  aurait exclu l'acteur que la story nomme -- « **Employe** : Decouvrir le
  Framework ». C'est la forme exacte du piege de la colonne `OFFICE` au LOT 5.

  Le §5.1 ne change rien ici : hors de son entite principale, une personne
  « possede uniquement les droits `EMP` », et `EMP` a deja la lecture.

LE 404 EST LE MEME QUE CELUI DE `GET /entities/{code}`, ET C'EST VOULU

  La route resout d'abord l'entite ACTIVE. Une entite `draft`, `suspended` ou
  `archived` rend le meme 404 qu'un code inconnu : distinguer apprendrait
  l'existence d'une entite qu'on n'a pas le droit de voir.

CE QUE CETTE ROUTE NE SERT PAS

  **Aucun contenu editorial.** `content_page` existe depuis `T1`, mais la
  synthese est structurelle. Les blocs sont le sujet de `T5`.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING, Annotated, Final

from fastapi import APIRouter, Depends, Path, Query, status
from pydantic import BaseModel

from app.auth.dependances import exiger_une_session
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import resoudre_une_entite_active
from app.organization.bureaux import BureauDetaille, lire_le_bureau
from app.organization.cercles import CercleDetaille, MembreDuCercle, lire_le_cercle
from app.organization.framework import (
    CarteDeBureau,
    CarteDeCercle,
    CarteDeResponsabilite,
    TitulaireFramework,
    lire_la_page_framework,
)
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative
from app.shared.pagination import TAILLE_PAR_DEFAUT, TailleDePage

if TYPE_CHECKING:  # pragma: no cover
    from app.configuration.settings import Parametres

DESCRIPTION_401: Final = (
    "Aucune session valide. UNE SEULE forme pour cinq causes : cookie absent, "
    "jeton inconnu, session revoquee, duree absolue depassee, inactivite depassee."
)


class TitulaireRendu(BaseModel):
    """Une personne portant une responsabilite ACTIVE a l'instant de l'appel."""

    identifiant: uuid.UUID
    prenom: str
    nom: str


class ResponsabiliteRendue(BaseModel):
    """Une des QUATRE responsabilites Framework du cahier §6.2.

    `chemin_detaille` vaut `null` pour `BOOSTER` et `OFFICE_MANAGER`, qui n'ont
    **pas** de page propre : l'annexe A §10.1 en donne une a `DSM` et a `ESM`
    seulement, les deux autres se rejoignant PAR les cercles et les bureaux.
    **`null` n'est pas une chaine vide** : vide dirait « la page existe, son
    adresse est inconnue ».
    """

    type_de_responsabilite: str
    titulaires: list[TitulaireRendu]
    chemin_detaille: str | None


class CercleRendu(BaseModel):
    """Un cercle de la synthese.

    `jeton_de_couleur` est **nullable au catalogue**, et le rendre en chaine
    donnerait « None » sur les cercles qui n'en portent pas -- defaut `T10-8`,
    servi sur 100 % des cercles pendant deux lots.

    **LA COULEUR N'EST JAMAIS LA SEULE INFORMATION** : `code` et `nom` sont
    obligatoires, donc une carte reste lisible sans elle. C'est le critere de
    sortie n°4 du lot, tenu **structurellement** -- il n'existe aucune reponse
    ou le jeton serait present et le nom absent.
    """

    identifiant: uuid.UUID
    code: str
    nom: str
    description: str | None
    jeton_de_couleur: str | None
    booster: TitulaireRendu | None
    membres_actifs: int
    chemin_detaille: str


class BureauRendu(BaseModel):
    """Un bureau de la synthese, avec ses responsables ACTIFS.

    Le §8.4 en veut « entre un et trois **lorsqu'il est publie** », et `DEC-576`
    dit a partir de quand cela mord : quand sa page de contenu de type `OFFICE`
    est publiee. **Cette route ne l'exige pas** -- elle rend ce qui est, y compris
    zero responsable.

    **`DEC-583`, 15/09/2026 : le declencheur qui tiendra la borne est a `T7`**, et
    non a `T4` comme cette ligne l'annonçait. La borne ne mord qu'a la
    publication, et aucune route n'ecrivait dans `content_page` : un declencheur
    pose en lecture n'aurait eu aucun ecrivain pour l'exercer (§7.39, §7.41).
    """

    identifiant: uuid.UUID
    code: str
    nom: str
    description: str | None
    localisation: str | None
    responsables: list[TitulaireRendu]
    chemin_detaille: str


class ReponseDuFramework(BaseModel):
    """Les TROIS familles du cahier §10.3 — responsabilites, cercles, bureaux.

    **LES TROIS CLES SONT TOUJOURS PRESENTES**, meme vides. Une famille absente
    et une famille vide donneraient la meme observation cote client alors
    qu'elles ne disent pas la meme chose -- §7.0, quatrieme proposition.
    """

    responsabilites: list[ResponsabiliteRendue]
    cercles: list[CercleRendu]
    bureaux: list[BureauRendu]


class MembreRendu(BaseModel):
    """Un membre du cercle, actif a l'instant de l'appel.

    `type_d_appartenance` vaut `principal` ou `secondary` — §8.2. La distinction
    n'est pas decorative : `ARB-DROIT-004` donne au Booster la gestion de
    l'appartenance **secondaire** et lui refuse le cercle principal, le DSM, le
    client et le statut d'un membre seulement secondaire.
    """

    appartenance: uuid.UUID
    prenom: str
    nom: str
    type_d_appartenance: str


class ReponseDuCercle(BaseModel):
    """Un cercle et une PAGE de ses membres — `MVP-L06-US002`.

    **LA COULEUR N'EST JAMAIS LA SEULE INFORMATION, ET C'EST STRUCTUREL.** Le
    §8.1 l'exige parmi les contraintes de `circle` — ce n'est donc pas qu'un
    critere de sortie de la roadmap. `code` et `nom` sont obligatoires,
    `jeton_de_couleur` est nullable : il n'existe aucune reponse de cette forme
    ou le jeton serait present et le nom absent (§7.35).

    **`pages` VAUT AU MOINS 1, MEME SANS MEMBRE.** Un client qui lirait `0` ne
    saurait pas s'il doit afficher « aucun membre » ou « chargement ».
    """

    identifiant: uuid.UUID
    code: str
    nom: str
    description: str | None
    jeton_de_couleur: str | None
    booster: TitulaireRendu | None
    membres: list[MembreRendu]
    total_des_membres: int
    page: int
    taille: int
    pages: int
    chemin_detaille: str


class ReponseDuBureau(BaseModel):
    """Un bureau, ses responsables ACTIFS, et son etat de publication — `MVP-L06-US003`.

    **`responsables` N'EST PAS BORNE ICI, ET C'EST LE POINT DELICAT DE CETTE
    ROUTE.** Le §8.4 veut « entre un et trois responsables actifs **lorsqu'il est
    publie** » ; aucune contrainte de base ne l'exprime -- c'est un comptage
    borne -- et le declencheur qui le tiendra est pose en `T7`, la ou la
    publication a un ecrivain (`DEC-583`). Cette route rend donc **ce qui est**,
    y compris zero responsable et y compris plus de trois.

    **ELLE NE PAGINE PAS, ET CE N'EST PAS UN OUBLI.** Le §18.2 regit les
    POPULATIONS -- c'est pourquoi les membres d'un cercle se paginent en `T3`.
    Les responsables d'un bureau sont un ensemble que le §8.4 declare **borne** :
    paginer trois elements au plus inventerait un parametre que le cahier ne
    demande pas (§6.5).

    **`publie` VIENT DE LA PAGE DE CONTENU, JAMAIS DE LA TABLE `office`**, qui ne
    porte aucun etat de publication -- `DEC-576`, apres `ECART-031`. Sans lui, la
    reponse ne saurait pas distinguer un zero **legitime**, celui d'un bureau en
    brouillon, d'un zero qui **enfreint** le §8.4.
    """

    identifiant: uuid.UUID
    code: str
    nom: str
    description: str | None
    localisation: str | None
    responsables: list[TitulaireRendu]
    #  Le compte REEL, jamais le compte attendu. Il peut valoir zero, et il peut
    #  depasser trois : voir le docstring ci-dessus.
    nombre_de_responsables: int
    publie: bool
    chemin_detaille: str


def _membre(membre: MembreDuCercle) -> MembreRendu:
    return MembreRendu(
        appartenance=membre.appartenance,
        prenom=membre.prenom,
        nom=membre.nom,
        type_d_appartenance=membre.type_d_appartenance,
    )


def _cercle_detaille(cercle: CercleDetaille) -> ReponseDuCercle:
    return ReponseDuCercle(
        identifiant=cercle.identifiant,
        code=cercle.code,
        nom=cercle.nom,
        description=cercle.description,
        jeton_de_couleur=cercle.jeton_de_couleur,
        booster=None if cercle.booster is None else _titulaire(cercle.booster),
        membres=[_membre(m) for m in cercle.membres],
        total_des_membres=cercle.total_des_membres,
        page=cercle.page,
        taille=cercle.taille,
        pages=cercle.pages,
        chemin_detaille=cercle.chemin_detaille,
    )


def _titulaire(titulaire: TitulaireFramework) -> TitulaireRendu:
    return TitulaireRendu(
        identifiant=titulaire.identifiant, prenom=titulaire.prenom, nom=titulaire.nom
    )


def _responsabilite(carte: CarteDeResponsabilite) -> ResponsabiliteRendue:
    return ResponsabiliteRendue(
        type_de_responsabilite=carte.type_de_responsabilite,
        titulaires=[_titulaire(t) for t in carte.titulaires],
        chemin_detaille=carte.chemin_detaille,
    )


def _cercle(carte: CarteDeCercle) -> CercleRendu:
    return CercleRendu(
        identifiant=carte.identifiant,
        code=carte.code,
        nom=carte.nom,
        description=carte.description,
        jeton_de_couleur=carte.jeton_de_couleur,
        booster=None if carte.booster is None else _titulaire(carte.booster),
        membres_actifs=carte.membres_actifs,
        chemin_detaille=carte.chemin_detaille,
    )


def _bureau(carte: CarteDeBureau) -> BureauRendu:
    return BureauRendu(
        identifiant=carte.identifiant,
        code=carte.code,
        nom=carte.nom,
        description=carte.description,
        localisation=carte.localisation,
        responsables=[_titulaire(r) for r in carte.responsables],
        chemin_detaille=carte.chemin_detaille,
    )


def _bureau_detaille(bureau: BureauDetaille) -> ReponseDuBureau:
    return ReponseDuBureau(
        identifiant=bureau.identifiant,
        code=bureau.code,
        nom=bureau.nom,
        description=bureau.description,
        localisation=bureau.localisation,
        responsables=[_titulaire(r) for r in bureau.responsables],
        #  Derive du tuple, jamais compte a part : deux sources divergeraient.
        nombre_de_responsables=bureau.nombre_de_responsables,
        publie=bureau.publie,
        chemin_detaille=bureau.chemin_detaille,
    )


def routeur_framework(parametres: Parametres) -> APIRouter:
    """Routeur de la page Framework, monte sous le prefixe versionne."""
    routeur = APIRouter(tags=["framework"])

    @routeur.get(
        "/entities/{code}/framework",
        #  **`dependencies=` ET NON `Annotated[...]`.** Sous `from __future__
        #  import annotations`, FastAPI resout l'annotation dans les globals du
        #  module, n'y trouve pas la fermeture `parametres`, et prend le
        #  parametre pour une chaine de requete : 422 pour tout le monde, sur un
        #  livrable qui PARAIT protege. Mesure du 23/08/2026.
        #
        #  La forme `dependencies=[...]` suffit ici : la matrice §5 accorde la
        #  lecture aux huit roles sans distinction, donc l'appelant n'est pas lu.
        dependencies=[Depends(exiger_une_session(parametres))],
        status_code=status.HTTP_200_OK,
        response_model=ReponseDuFramework,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "UNE SEULE forme pour DEUX causes : le code est inconnu, ou "
                    "l'entite existe sans etre active. Identique en corps ET en "
                    "en-tetes a celle de `/entities/{code}`."
                )
            },
        },
        summary="La vue synthetique du Framework d'une entite",
        description=(
            "Les TROIS familles de cartes du cahier §10.3 — responsabilites, "
            "cercles, bureaux — et le chemin de la page detaillee de chacune. "
            "Exige une session : la matrice §5 refuse cette ressource a `ANON` et "
            "l'accorde aux huit roles authentifies **sans distinction**, `EMP` et "
            "`NEW` compris, si bien qu'aucun role n'est examine. "
            "Seules les responsabilites ACTIVES a l'instant nomment quelqu'un : "
            "une periode close ou future ne designe personne. "
            "Les cercles et bureaux archives sont exclus."
        ),
    )
    def lire_le_framework(
        code: str = Path(
            min_length=1,
            max_length=LONGUEUR_MAXIMALE_CODE,
            description="Le `code` de l'entite consultee, tel qu'il vit dans l'adresse",
        ),
    ) -> ReponseDuFramework:
        """La synthese Framework d'une entite — cahier §10.3."""
        #  L'instant est releve UNE FOIS et passe au service : deux appels a
        #  `now()` pourraient tomber de part et d'autre de la borne d'une
        #  periode, et rendre une synthese incoherente avec elle-meme.
        instant = dt.datetime.now(tz=dt.UTC)

        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            page = lire_la_page_framework(
                connexion, entite=entite.id, code_entite=entite.code, instant=instant
            )

        return ReponseDuFramework(
            responsabilites=[_responsabilite(c) for c in page.responsabilites],
            cercles=[_cercle(c) for c in page.cercles],
            bureaux=[_bureau(b) for b in page.bureaux],
        )

    @routeur.get(
        "/entities/{code}/circles/{code_cercle}",
        #  `dependencies=` et non `Annotated[...]` pour la DEPENDANCE : voir la
        #  route du Framework ci-dessus. La matrice §5 accorde la lecture des
        #  cercles aux huit roles sans distinction, donc l'appelant n'est pas lu.
        dependencies=[Depends(exiger_une_session(parametres))],
        status_code=status.HTTP_200_OK,
        response_model=ReponseDuCercle,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "UNE SEULE forme pour CINQ causes, a dessein : code d'entite "
                    "inconnu, entite non active, code de cercle inconnu, cercle "
                    "d'une AUTRE entite, ou cercle archive. Distinguer "
                    "apprendrait l'existence d'un cercle qu'on n'a pas a voir."
                )
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`taille` hors des trois valeurs du cahier §18.2, ou `page` "
                    "inferieure a 1. Format du §18.3, produit par le "
                    "gestionnaire de validation et non par cette route."
                )
            },
        },
        summary="La page detaillee d'un cercle, ses membres pagines",
        description=(
            "Couleur, description, membres et Booster — `MVP-L06-US002`. "
            "Exige une session : la matrice §5 refuse cette ressource a `ANON` et "
            "l'accorde aux huit roles authentifies **sans distinction**, `EMP` et "
            "`NEW` compris. "
            "**Les membres sont pagines** : le cahier §18.2 s'intitule "
            "« Pagination », vit dans le chapitre API et ne nomme aucune "
            "ressource — 25 par defaut, options 25, 50 et 100. "
            "Seuls les profils `published` d'une appartenance `active` sont "
            "rendus, et seules les appartenances au cercle ACTIVES a l'instant : "
            "une periode close ou future ne designe personne. "
            "Un cercle archive rend 404 ; sa lecture aura sa propre route, comme "
            "`fiche-archivee` au LOT 5."
        ),
    )
    def lire_un_cercle(
        code: str = Path(
            min_length=1,
            max_length=LONGUEUR_MAXIMALE_CODE,
            description="Le `code` de l'entite consultee, tel qu'il vit dans l'adresse",
        ),
        code_cercle: str = Path(
            min_length=1,
            max_length=LONGUEUR_MAXIMALE_CODE,
            description="Le `code` du cercle, unique dans l'entite (§8.1)",
        ),
        page: int = Query(
            1,
            ge=1,
            description="Numero de page, 1-indexee comme celui que l'ecran affiche",
        ),
        taille: Annotated[
            TailleDePage,
            Query(description="Membres par page — les trois valeurs du cahier §18.2, seules"),
        ] = TAILLE_PAR_DEFAUT,
    ) -> ReponseDuCercle:
        """La page detaillee d'un cercle — cahier §10.3, backlog `MVP-L06-US002`."""
        instant = dt.datetime.now(tz=dt.UTC)

        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            #  La resolution et la lecture sont dans la MEME transaction : une
            #  entite suspendue entre les deux rendrait la page d'une entite
            #  devenue inaccessible.
            cercle = lire_le_cercle(
                connexion,
                entite=entite.id,
                code_entite=entite.code,
                code_cercle=code_cercle,
                page=page,
                #  `int(taille)` : `TailleDePage` est un `IntEnum`, et le service
                #  compare a un tuple d'entiers.
                taille=int(taille),
                instant=instant,
            )
            if cercle is None:
                #  Trois causes de plus, meme reponse : code inconnu, autre
                #  entite, ou archive.
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )

        return _cercle_detaille(cercle)

    @routeur.get(
        "/entities/{code}/offices/{code_bureau}",
        #  `dependencies=` et non `Annotated[...]` pour la DEPENDANCE : voir la
        #  route du Framework. La matrice §5 accorde la lecture des bureaux aux
        #  huit roles sans distinction, donc l'appelant n'est pas lu.
        dependencies=[Depends(exiger_une_session(parametres))],
        status_code=status.HTTP_200_OK,
        response_model=ReponseDuBureau,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": DESCRIPTION_401},
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "UNE SEULE forme pour CINQ causes, a dessein : code d'entite "
                    "inconnu, entite non active, code de bureau inconnu, bureau "
                    "d'une AUTRE entite, ou bureau archive. Distinguer "
                    "apprendrait l'existence d'un bureau qu'on n'a pas a voir."
                )
            },
        },
        summary="La page detaillee d'un bureau, ses responsables actifs",
        description=(
            "Les responsables actifs d'un bureau, sa description, sa "
            "localisation — `MVP-L06-US003`. "
            "Exige une session : la matrice §5 refuse cette ressource a `ANON` et "
            "l'accorde aux huit roles authentifies **sans distinction**, `EMP` et "
            "`NEW` compris. "
            "**Aucune pagination** : le §18.2 regit les populations, et le §8.4 "
            "declare les responsables d'un bureau BORNES — « entre un et trois "
            "actifs lorsqu'il est publie ». "
            "**La borne n'est pas tenue en base et cette route ne la suppose "
            "pas** : elle rend ce qui est, zero compris et plus de trois compris. "
            "Le declencheur qui la tiendra est pose en `T7`, la ou la publication "
            "a un ecrivain (`DEC-583`). "
            "`publie` vient de la page de contenu de type `OFFICE`, jamais de la "
            "table `office`, qui ne porte aucun etat de publication (`DEC-576`). "
            "Seules les affectations ACTIVES a l'instant nomment quelqu'un : une "
            "periode close ou future ne designe personne. "
            "Un bureau archive rend 404 ; sa lecture aura sa propre route."
        ),
    )
    def lire_un_bureau(
        code: str = Path(
            min_length=1,
            max_length=LONGUEUR_MAXIMALE_CODE,
            description="Le `code` de l'entite consultee, tel qu'il vit dans l'adresse",
        ),
        code_bureau: str = Path(
            min_length=1,
            max_length=LONGUEUR_MAXIMALE_CODE,
            description="Le `code` du bureau, unique dans l'entite (§8.3)",
        ),
    ) -> ReponseDuBureau:
        """La page detaillee d'un bureau — cahier §10.3, backlog `MVP-L06-US003`."""
        #  L'instant est releve UNE FOIS : deux appels a `now()` pourraient tomber
        #  de part et d'autre de la borne d'une periode.
        instant = dt.datetime.now(tz=dt.UTC)

        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            #  Resolution et lecture dans la MEME transaction : une entite
            #  suspendue entre les deux rendrait la page d'une entite devenue
            #  inaccessible.
            bureau = lire_le_bureau(
                connexion,
                entite=entite.id,
                code_entite=entite.code,
                code_bureau=code_bureau,
                instant=instant,
            )
            if bureau is None:
                #  Trois causes de plus, meme reponse : code inconnu, autre
                #  entite, ou archive.
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )

        return _bureau_detaille(bureau)

    return routeur
