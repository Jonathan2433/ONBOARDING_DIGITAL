"""`GET /entities/{code}/pages/{type_de_page}/{slug}` — LOT 6, `T5`, `MVP-L06-US004`.

POURQUOI L'ADRESSE PORTE LE TYPE **ET** LE SLUG

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

LE 404 COUVRE LE BROUILLON, ET C'EST LE POINT LE PLUS IMPORTANT DE CETTE ROUTE

  Une page en brouillon rend le MEME 404 qu'un slug inconnu. Distinguer
  apprendrait l'existence d'un brouillon a qui n'a pas le droit de le voir, et
  vaudrait `US006` -- « **previsualiser** puis publier » -- qui est la story de
  `T7`, avec sa propre grille : le §13 donne « Publier » a une portee
  **Perimetre** la ou « Modifier » vaut **Entite**.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Final

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel

from app.auth.dependances import exiger_une_session
from app.content.modeles import TYPES_DE_PAGE
from app.content.pages import PayloadNonObjet, lire_la_page_de_contenu
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import resoudre_une_entite_active
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

if TYPE_CHECKING:  # pragma: no cover
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


def routeur_contenus(parametres: Parametres) -> APIRouter:
    """Routeur du rendu editorial, monte sous le prefixe versionne."""
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
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
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

    return routeur
