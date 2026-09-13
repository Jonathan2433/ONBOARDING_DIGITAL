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
from typing import TYPE_CHECKING, Final

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel

from app.auth.dependances import exiger_une_session
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import resoudre_une_entite_active
from app.organization.framework import (
    CarteDeBureau,
    CarteDeCercle,
    CarteDeResponsabilite,
    TitulaireFramework,
    lire_la_page_framework,
)
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

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
    zero responsable, et c'est `T4` qui posera le declencheur.
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

    return routeur
