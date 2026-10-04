"""`GET /entities/{code}/events` et `POST /entities/{code}/events` — LOT 8.

LA LECTURE (`T2`, `MVP-L08-US003`) — la matrice §5 et sa section §11 accordent
la consultation a chacun des huit roles authentifies, `EMP` et `NEW` compris.
La route exige donc une session mais ne resout aucun role. Une consultation
d'une autre entite reste en lecture seule, conformement a RIGHTS-003.

LA CREATION (`T3`, `MVP-L08-US004`, 1 sur 3) — la matrice §11 donne a chaque
role EXACTEMENT une portee de creation, sauf au DSM qui en a deux (`Entite ou
consultants`, `ECART-067`, `DEC-622`). La garde de route n'exige donc que
l'appartenance a l'UN des six roles qui portent AU MOINS un droit de creation
quelque part ; la portee precise — et le rattachement exact au cercle ou au
bureau nomme — est revalidee par `creer_un_evenement`, qui seule connait la
portee demandee dans le corps de la requete. Meme repartition que
`creer_une_page_de_contenu` dans `app/content/routes.py`.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, status
from pydantic import BaseModel, Field

from app.auth.dependances import SessionEtablie, exiger_une_session, proteger_du_csrf
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import resoudre_une_entite_active
from app.events.ecriture import creer_un_evenement
from app.events.lecture import ClassementEvenement, lister_les_evenements
from app.events.perimetre import ROLES_DE_CREATION_EVENEMENT, PorteeDeCreation
from app.permissions.dependances import exiger_un_role_dans_l_entite
from app.permissions.services import resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative
from app.shared.pagination import TAILLE_PAR_DEFAUT, TailleDePage

if TYPE_CHECKING:  # pragma: no cover
    from app.configuration.settings import Parametres


class EvenementRendu(BaseModel):
    """Un evenement visible ; `etat=cancelled` porte le badge « Annule »."""

    identifiant: uuid.UUID
    titre: str
    description: str | None
    commence_le: dt.datetime
    finit_le: dt.datetime
    lieu: str | None
    etat: str
    annule_le: dt.datetime | None
    motif_d_annulation: str | None


class ReponseDesEvenements(BaseModel):
    """Une page d'un des deux classements temporels du cahier §10.6."""

    classement: ClassementEvenement
    evenements: list[EvenementRendu]
    page: int
    taille: int
    total: int
    pages: int


class DemandeDeCreationDEvenement(BaseModel):
    """Creer un evenement — matrice §11 « Creer », modele §17.1.

    **AUCUN CHAMP `etat`**, et ce n'est pas un oubli : le §17.1 nait `draft`
    (`DEC-620`), et la publication est une ligne SEPAREE du §11 — « Publier »,
    portee **Perimetre** — reservee a `T4`. Une demande qui pourrait publier
    confondrait deux droits que la matrice distingue, exactement le motif de
    `DemandeDeCreationDePage` au LOT 6.

    `portee` DIT au serveur quelle ligne du §11 est invoquee ; `cercle` et
    `bureau` ne sont lus que si elle le reclame. **PAR CODE, COMME PARTOUT
    AILLEURS DEPUIS `T3` ET `T4` DU LOT 6** : deux modes d'adressage d'une meme
    ressource divergeraient, et l'un des deux serait celui qu'aucun ecran
    n'emploie.
    """

    titre: str = Field(min_length=1, description="Le titre de l'evenement (§17.1)")
    description: str | None = Field(default=None, description="Facultatif (§17.1)")
    commence_le: dt.datetime = Field(description="`starts_at` — doit preceder `finit_le`")
    finit_le: dt.datetime = Field(description="`ends_at` — doit suivre `commence_le`")
    lieu: str | None = Field(default=None, description="`location_text`, facultatif (§17.1)")
    portee: PorteeDeCreation = Field(
        description=(
            "`entite` (ESM/ADM-E/SUPER/DSM), `cercle` (Booster, LE sien), "
            "`bureau` (responsable de bureau, LE sien) ou `consultants` "
            "(DSM seul — `ECART-067`, `DEC-622`)."
        )
    )
    cercle: str | None = Field(
        default=None, description="Le `code` du cercle — requis si `portee=cercle`"
    )
    bureau: str | None = Field(
        default=None, description="Le `code` du bureau — requis si `portee=bureau`"
    )


class ReponseDeCreationDEvenement(BaseModel):
    """Un evenement nouvellement cree, en BROUILLON."""

    identifiant: uuid.UUID
    titre: str
    description: str | None
    commence_le: dt.datetime
    finit_le: dt.datetime
    lieu: str | None
    etat: str
    version: int
    portee: PorteeDeCreation


def routeur_evenements(parametres: Parametres) -> APIRouter:
    """Routeur de lecture et d'ecriture des evenements, monte sous le prefixe versionne."""
    routeur = APIRouter(tags=["evenements"])

    garde_de_creation = exiger_un_role_dans_l_entite(parametres, ROLES_DE_CREATION_EVENEMENT)

    @routeur.get(
        "/entities/{code}/events",
        dependencies=[Depends(exiger_une_session(parametres))],
        status_code=status.HTTP_200_OK,
        response_model=ReponseDesEvenements,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`classement` absent ou invalide, `taille` hors de 25/50/100, "
                    "ou `page` inferieure a 1."
                )
            },
        },
        summary="Consulter les evenements a venir ou passes",
        description=(
            "Les deux onglets du cahier §10.6. `passes` signifie `ends_at <= instant` ; "
            "`a_venir`, `ends_at > instant`, et inclut donc un evenement en cours. "
            "Seuls `published` et `cancelled` sont publics : un evenement annule reste "
            "visible avec son etat, un brouillon ou une archive est absent."
        ),
    )
    def consulter_les_evenements(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le code de l'entite consultee",
            ),
        ],
        classement: Annotated[
            ClassementEvenement,
            Query(description="`a_venir` ou `passes`, les deux onglets du cahier §10.6"),
        ],
        page: Annotated[int, Query(ge=1, description="Numero de page, 1-indexe")] = 1,
        taille: Annotated[
            TailleDePage,
            Query(description="Elements par page — 25, 50 ou 100, cahier §18.2"),
        ] = TAILLE_PAR_DEFAUT,
    ) -> ReponseDesEvenements:
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            resultat = lister_les_evenements(
                connexion,
                entite=entite.id,
                classement=classement,
                page=page,
                taille=int(taille),
                instant=instant,
            )

        pages = -(-resultat.total // int(taille))
        return ReponseDesEvenements(
            classement=classement,
            evenements=[
                EvenementRendu(
                    identifiant=evenement.id,
                    titre=evenement.title,
                    description=evenement.description,
                    commence_le=evenement.starts_at,
                    finit_le=evenement.ends_at,
                    lieu=evenement.location_text,
                    etat=evenement.state,
                    annule_le=evenement.cancelled_at,
                    motif_d_annulation=evenement.cancellation_reason,
                )
                for evenement in resultat.evenements
            ],
            page=page,
            taille=int(taille),
            total=resultat.total,
            pages=pages,
        )

    @routeur.post(
        "/entities/{code}/events",
        status_code=status.HTTP_201_CREATED,
        response_model=ReponseDeCreationDEvenement,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : soit aucun role de creation dans cette entite, soit "
                    "un role existe mais pas pour CETTE portee — un `ESM` qui demande "
                    "`cercle`, un `DSM` qui demande `cercle` ou `bureau`, un Booster sur "
                    "le cercle d'un AUTRE Booster. La matrice §11 n'accorde qu'une portee "
                    "par role, deux pour le DSM (`Entite`, `consultants`)."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`rattachement_requis` : `portee=cercle` exige un cercle, "
                    "`portee=bureau` exige un bureau. `ressource_introuvable` : le "
                    "cercle ou le bureau nomme n'est pas dans cette entite, ou il est "
                    "archive. `chronologie_invalide` : `finit_le` n'est pas posterieur "
                    "a `commence_le`."
                )
            },
        },
        summary="Creer un evenement, en BROUILLON",
        description=(
            "Matrice §11, cahier §10.6. L'evenement nait `draft` ; publier est `T4`. "
            "`ECART-067` (`DEC-622`) : la portee `consultants` du DSM ne reclame "
            "aucun rattachement — elle designe le DSM auteur lui-meme."
        ),
    )
    def creer_un_evenement_route(
        demande: DemandeDeCreationDEvenement,
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
        #  dans les globals du module, ou la fermeture `parametres` n'existe
        #  pas. Le piege est mesure depuis `T1` du LOT 4.
        appelant: SessionEtablie = Depends(garde_de_creation),  # noqa: B008
    ) -> ReponseDeCreationDEvenement:
        """Creer un evenement — matrice §11, modele §17.1."""
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            #  **LES PERMISSIONS SONT RESOLUES A NOUVEAU, DANS CETTE
            #  TRANSACTION.** La garde a resolu les SIENNES, dans sa propre
            #  connexion et a son propre instant : s'y fier ferait creer ce qui
            #  a ete autorise ailleurs. Meme motif que
            #  `ecrire_le_contenu_d_une_page` dans `app/content/routes.py`.
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            cree = creer_un_evenement(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                roles=frozenset(permissions.roles),
                title=demande.titre,
                description=demande.description,
                starts_at=demande.commence_le,
                ends_at=demande.finit_le,
                location_text=demande.lieu,
                portee=demande.portee,
                code_de_cercle=demande.cercle,
                code_de_bureau=demande.bureau,
                instant=instant,
            )

        return ReponseDeCreationDEvenement(
            identifiant=cree.identifiant,
            titre=cree.title,
            description=cree.description,
            commence_le=cree.starts_at,
            finit_le=cree.ends_at,
            lieu=cree.location_text,
            etat=cree.etat,
            version=cree.version,
            portee=cree.portee,
        )

    return routeur
