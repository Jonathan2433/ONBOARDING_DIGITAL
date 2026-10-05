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

LA MODIFICATION ET LA PUBLICATION (`T4`, `MVP-L08-US004`, 2 sur 3) — **LA MEME
GARDE COARSE SERT AUX TROIS VERBES**, parce que les six roles qui creent sont
exactement ceux qui portent au moins une ligne « Modifier » ou « Publier » du
§11. Le couple (role, evenement) precis est resolu par
`resoudre_le_perimetre_de_l_evenement`, qui rend un refus UNIQUE
(`acces_refuse`, 403) que l'evenement n'existe pas dans cette entite, que le
role n'y porte rien, ou qu'il y porte un droit mais pas celui demande — meme
discipline de refus par defaut que `T3`.

L'ANNULATION, L'ARCHIVAGE ET LA RESTAURATION (`T5`, `MVP-L08-US004`, 3 sur
3) — **LA MEME GARDE COARSE ENCORE**, et la MEME fonction de perimetre : un
evenement ARCHIVE n'offre plus que `RESTAURER`, et seulement aux roles de
portee Entite (`ARB-DROIT-003`).

LE RATTACHEMENT DES MEDIAS (`T6`) — **ENCORE LA MEME GARDE COARSE**, un
verbe de plus (`GERER_LES_MEDIAS`) qui partage, pour le DSM, la grille
« Perimetre » de `Publier`/`Annuler`/`Archiver`, jamais celle de `Modifier`.
Aucun televersement : le media doit deja exister, `ready`, dans cette
entite.
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
from app.events.ecriture import (
    CODE_ACCES_REFUSE,
    MESSAGE_ACCES_REFUSE,
    annuler_un_evenement,
    archiver_un_evenement,
    creer_un_evenement,
    gerer_les_medias_d_un_evenement,
    modifier_un_evenement,
    publier_un_evenement,
    restaurer_un_evenement,
)
from app.events.lecture import ClassementEvenement, lister_les_evenements
from app.events.perimetre import (
    ROLES_DE_CREATION_EVENEMENT,
    ActionEvenement,
    PorteeDeCreation,
    resoudre_le_perimetre_de_l_evenement,
)
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


class DemandeDeModificationDEvenement(BaseModel):
    """Modifier un evenement — matrice §11 « Modifier », modele §17.1.

    **`cercles`/`bureaux` A TROIS ETATS, ET C'EST STRUCTUREL** : absent (`None`)
    signifie « ne touche pas a cette dimension », une liste VIDE la VIDE — la
    liste remplace la liste, meme parti que `BlocSoumis` au LOT 6. Aucun champ
    `etat` : publier est la ligne SEPAREE du §11 servie par
    `DemandeDePublicationDEvenement`.
    """

    titre: str = Field(min_length=1, description="Le titre de l'evenement (§17.1)")
    description: str | None = Field(default=None, description="Facultatif (§17.1)")
    commence_le: dt.datetime = Field(description="`starts_at` — doit preceder `finit_le`")
    finit_le: dt.datetime = Field(description="`ends_at` — doit suivre `commence_le`")
    lieu: str | None = Field(default=None, description="`location_text`, facultatif (§17.1)")
    version: int = Field(ge=1, description="Concurrence optimiste — cahier §18.4")
    cercles: list[str] | None = Field(
        default=None,
        description=(
            "Remplace la liste des cercles rattaches par leur `code`. `None` : "
            "ne touche pas cette dimension. `[]` : la vide."
        ),
    )
    bureaux: list[str] | None = Field(
        default=None,
        description=(
            "Remplace la liste des bureaux rattaches par leur `code`. `None` : "
            "ne touche pas cette dimension. `[]` : la vide."
        ),
    )


class DemandeDePublicationDEvenement(BaseModel):
    """Publier un evenement — matrice §11 « Publier ». Immediate, sans second geste."""

    version: int = Field(ge=1, description="Concurrence optimiste — cahier §18.4")


class ReponseDEvenementEcrit(BaseModel):
    """Un evenement apres modification ou publication."""

    identifiant: uuid.UUID
    titre: str
    description: str | None
    commence_le: dt.datetime
    finit_le: dt.datetime
    lieu: str | None
    etat: str
    version: int


class DemandeDAnnulationDEvenement(BaseModel):
    """Annuler un evenement — matrice §11 « Annuler ». Reste visible, badge « Annule »."""

    version: int = Field(ge=1, description="Concurrence optimiste — cahier §18.4")
    motif: str | None = Field(
        default=None, description="`cancellation_reason`, facultatif (modele §17.1)"
    )


class ReponseDAnnulationDEvenement(BaseModel):
    """Un evenement apres annulation."""

    version: int
    etat: str
    annule_le: dt.datetime
    motif_d_annulation: str | None


class DemandeDeTransitionDEvenement(BaseModel):
    """Archiver ou restaurer un evenement — aucun motif, meme parti que les pages (LOT 6)."""

    version: int = Field(ge=1, description="Concurrence optimiste — cahier §18.4")


class ReponseDArchivageDEvenement(BaseModel):
    """Un evenement apres archivage."""

    version: int
    etat: str
    archive_le: dt.datetime


class ReponseDeRestaurationDEvenement(BaseModel):
    """Un evenement apres restauration — revient en BROUILLON."""

    version: int
    etat: str


class MediaSoumis(BaseModel):
    """Un media a rattacher — l'ordre dans la liste EST l'ordre d'affichage."""

    media: uuid.UUID = Field(description="`media_asset_id`, deja televerse dans cette entite")
    role: str = Field(
        min_length=1, max_length=32, description="`display_role` — chaine libre non vide (§17.3)"
    )


class DemandeDeGestionDesMediasDEvenement(BaseModel):
    """Remplacer la liste COMPLETE des medias d'un evenement — matrice §11.

    **UNE SEULE FORME, CONTRAIREMENT A `cercles`/`bureaux` DE `T4`** : cette
    route n'a qu'une dimension, donc pas de distinction `None`/`[]` — une
    liste vide VIDE la galerie, et c'est la seule facon de le faire.
    """

    version: int = Field(ge=1, description="Concurrence optimiste — cahier §18.4")
    medias: list[MediaSoumis] = Field(
        description="Remplace la liste complete, dans l'ordre fourni."
    )


class MediaDEvenementRendu(BaseModel):
    """Un media rattache, tel que rendu apres l'ecriture."""

    media: uuid.UUID
    role: str
    ordre: int


class ReponseDeGestionDesMediasDEvenement(BaseModel):
    """Un evenement apres remplacement de sa liste de medias."""

    version: int
    medias: list[MediaDEvenementRendu]


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

    @routeur.put(
        "/entities/{code}/events/{evenement}",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDEvenementEcrit,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : un seul gabarit pour trois causes — l'evenement "
                    "n'existe pas dans cette entite (ou est archive), le role n'y porte "
                    "rien, ou il y porte un droit mais pas `Modifier` (matrice §11). "
                    "Le meme code couvre un cercle/bureau NOMME dans `cercles`/`bureaux` "
                    "que l'acteur n'a pas le droit d'y attacher."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`version_obsolete` : l'evenement a change depuis votre lecture, ou "
                    "a ete archive entre-temps — cahier §18.4."
                )
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`chronologie_invalide` : `finit_le` n'est pas posterieur a "
                    "`commence_le`. `ressource_introuvable` : un cercle ou bureau nomme "
                    "n'est pas dans cette entite. `doublon_dans_la_liste` : un meme code "
                    "nomme deux fois dans `cercles` ou `bureaux`."
                )
            },
        },
        summary="Modifier un evenement",
        description=(
            "Matrice §11 « Modifier ». `cercles`/`bureaux` remplacent la liste "
            "complete des rattachements de leur dimension si fournis — `T4`, "
            "« rattachements multiples »."
        ),
    )
    def modifier_un_evenement_route(
        demande: DemandeDeModificationDEvenement,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        evenement: Annotated[
            uuid.UUID, Path(description="L'identifiant de l'evenement, rendu par la creation")
        ],
        appelant: SessionEtablie = Depends(garde_de_creation),  # noqa: B008
    ) -> ReponseDEvenementEcrit:
        """Modifier un evenement — matrice §11, modele §17.1."""
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
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            roles = frozenset(permissions.roles)
            perimetre = resoudre_le_perimetre_de_l_evenement(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                evenement=evenement,
                roles=roles,
                instant=instant,
            )
            if ActionEvenement.MODIFIER not in perimetre.actions:
                raise ErreurApplicative(
                    code=CODE_ACCES_REFUSE,
                    message=MESSAGE_ACCES_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            ecrit = modifier_un_evenement(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                roles=roles,
                evenement=evenement,
                title=demande.titre,
                description=demande.description,
                starts_at=demande.commence_le,
                ends_at=demande.finit_le,
                location_text=demande.lieu,
                version_attendue=demande.version,
                codes_de_cercle=demande.cercles,
                codes_de_bureau=demande.bureaux,
                instant=instant,
            )

        return ReponseDEvenementEcrit(
            identifiant=ecrit.identifiant,
            titre=ecrit.title,
            description=ecrit.description,
            commence_le=ecrit.starts_at,
            finit_le=ecrit.ends_at,
            lieu=ecrit.location_text,
            etat=ecrit.etat,
            version=ecrit.version,
        )

    @routeur.post(
        "/entities/{code}/events/{evenement}/publication",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDEvenementEcrit,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : l'evenement n'existe pas dans cette entite, le "
                    "role n'y porte rien, ou il y porte `Modifier` sans `Publier` — "
                    "pour le DSM, « Perimetre » seul (ses consultants nommes), jamais "
                    "« cree par lui » seul (§3 de la matrice, §7.45 de la passation)."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`version_obsolete` : l'evenement a change depuis votre lecture, "
                    "ou n'est plus `draft` — aucune republication (meme discipline que "
                    "`publier_une_page` au LOT 6)."
                )
            },
        },
        summary="Publier un evenement",
        description="Matrice §11 « Publier ». Immediate, en un clic, sans republication possible.",
    )
    def publier_un_evenement_route(
        demande: DemandeDePublicationDEvenement,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        evenement: Annotated[
            uuid.UUID, Path(description="L'identifiant de l'evenement, rendu par la creation")
        ],
        appelant: SessionEtablie = Depends(garde_de_creation),  # noqa: B008
    ) -> ReponseDEvenementEcrit:
        """Publier un evenement — matrice §11, modele §17.1."""
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
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            perimetre = resoudre_le_perimetre_de_l_evenement(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                evenement=evenement,
                roles=frozenset(permissions.roles),
                instant=instant,
            )
            if ActionEvenement.PUBLIER not in perimetre.actions:
                raise ErreurApplicative(
                    code=CODE_ACCES_REFUSE,
                    message=MESSAGE_ACCES_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            publie = publier_un_evenement(
                connexion,
                entite=entite.id,
                evenement=evenement,
                acteur=appelant.personne,
                version_attendue=demande.version,
                instant=instant,
            )

        return ReponseDEvenementEcrit(
            identifiant=publie.identifiant,
            titre=publie.title,
            description=publie.description,
            commence_le=publie.starts_at,
            finit_le=publie.ends_at,
            lieu=publie.location_text,
            etat=publie.etat,
            version=publie.version,
        )

    @routeur.post(
        "/entities/{code}/events/{evenement}/annulation",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDAnnulationDEvenement,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : l'evenement n'existe pas dans cette entite, le "
                    "role n'y porte rien, ou il y porte `Modifier` sans `Annuler` — "
                    "pour le DSM, « Perimetre » seul (ses consultants nommes), jamais "
                    "« cree par lui » seul (meme grille que `Publier`, §3 de la matrice)."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`version_obsolete` : l'evenement a change depuis votre lecture, "
                    "ou n'est plus `published` — seul un evenement publie s'annule."
                )
            },
        },
        summary="Annuler un evenement",
        description=(
            "Matrice §11 « Annuler ». L'evenement reste visible avec un badge « Annule » "
            "(cahier §10.6) — seule l'archivage le retire de la consultation."
        ),
    )
    def annuler_un_evenement_route(
        demande: DemandeDAnnulationDEvenement,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        evenement: Annotated[
            uuid.UUID, Path(description="L'identifiant de l'evenement, rendu par la creation")
        ],
        appelant: SessionEtablie = Depends(garde_de_creation),  # noqa: B008
    ) -> ReponseDAnnulationDEvenement:
        """Annuler un evenement — matrice §11, modele §17.1."""
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
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            perimetre = resoudre_le_perimetre_de_l_evenement(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                evenement=evenement,
                roles=frozenset(permissions.roles),
                instant=instant,
            )
            if ActionEvenement.ANNULER not in perimetre.actions:
                raise ErreurApplicative(
                    code=CODE_ACCES_REFUSE,
                    message=MESSAGE_ACCES_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            annule = annuler_un_evenement(
                connexion,
                entite=entite.id,
                evenement=evenement,
                acteur=appelant.personne,
                version_attendue=demande.version,
                motif=demande.motif,
                instant=instant,
            )

        return ReponseDAnnulationDEvenement(
            version=annule.version,
            etat=annule.etat,
            annule_le=annule.annule_le,
            motif_d_annulation=annule.motif_d_annulation,
        )

    @routeur.post(
        "/entities/{code}/events/{evenement}/archivage",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDArchivageDEvenement,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : l'evenement n'existe pas dans cette entite, le "
                    "role n'y porte rien, il y porte `Modifier` sans `Archiver`, ou il "
                    "est **deja archive**."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_409_CONFLICT: {
                "description": "`version_obsolete` : l'evenement a change depuis votre lecture."
            },
        },
        summary="Archiver un evenement — brouillon, publie ou annule",
        description=(
            "Matrice §11 « Archiver », §18 « Archiver un evenement ». L'evenement quitte "
            "la consultation publique (`T2`). Aucun motif n'est demande — §18.1 ne le "
            "nomme pas pour cette ressource."
        ),
    )
    def archiver_un_evenement_route(
        demande: DemandeDeTransitionDEvenement,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        evenement: Annotated[
            uuid.UUID, Path(description="L'identifiant de l'evenement, rendu par la creation")
        ],
        appelant: SessionEtablie = Depends(garde_de_creation),  # noqa: B008
    ) -> ReponseDArchivageDEvenement:
        """Archiver un evenement — matrice §11 et §18."""
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
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            perimetre = resoudre_le_perimetre_de_l_evenement(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                evenement=evenement,
                roles=frozenset(permissions.roles),
                instant=instant,
            )
            if ActionEvenement.ARCHIVER not in perimetre.actions:
                raise ErreurApplicative(
                    code=CODE_ACCES_REFUSE,
                    message=MESSAGE_ACCES_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            archive = archiver_un_evenement(
                connexion,
                entite=entite.id,
                evenement=evenement,
                acteur=appelant.personne,
                version_attendue=demande.version,
                instant=instant,
            )

        return ReponseDArchivageDEvenement(
            version=archive.version, etat=archive.etat, archive_le=archive.archive_le
        )

    @routeur.post(
        "/entities/{code}/events/{evenement}/restauration",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeRestaurationDEvenement,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : l'evenement n'est pas archive, ou l'appelant n'a "
                    "qu'une portee locale — le §11 met `DSM`, `BOOST` et `OFFICE` a "
                    "tiret sur la restauration, meme s'ils portent l'archivage de "
                    "l'evenement. Seuls `ESM`/`ADM-E`/`SUPER` restaurent (`ARB-DROIT-003`)."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_409_CONFLICT: {
                "description": "`version_obsolete` : l'evenement a change depuis votre lecture."
            },
        },
        summary="Restaurer un evenement archive — il revient en BROUILLON",
        description=(
            "Matrice §11 « Restaurer », `ARB-DROIT-003` qui nomme explicitement "
            "l'evenement parmi les cinq ressources que l'ESM restaure librement dans "
            "son entite.<br><br>"
            "**L'evenement revient en `draft`, jamais en `published` ni `cancelled`** : "
            "restaurer n'est pas publier, et `RIGHTS-001` refuse par defaut ce qui "
            "n'est pas explicitement redecide. Republier ou annuler est un second "
            "geste, qui laisse sa propre trace."
        ),
    )
    def restaurer_un_evenement_route(
        demande: DemandeDeTransitionDEvenement,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        evenement: Annotated[
            uuid.UUID, Path(description="L'identifiant de l'evenement, rendu par la creation")
        ],
        appelant: SessionEtablie = Depends(garde_de_creation),  # noqa: B008
    ) -> ReponseDeRestaurationDEvenement:
        """Restaurer un evenement archive — matrice §11, `ARB-DROIT-003`."""
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
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            perimetre = resoudre_le_perimetre_de_l_evenement(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                evenement=evenement,
                roles=frozenset(permissions.roles),
                instant=instant,
            )
            if ActionEvenement.RESTAURER not in perimetre.actions:
                raise ErreurApplicative(
                    code=CODE_ACCES_REFUSE,
                    message=MESSAGE_ACCES_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            restaure = restaurer_un_evenement(
                connexion,
                entite=entite.id,
                evenement=evenement,
                acteur=appelant.personne,
                version_attendue=demande.version,
                instant=instant,
            )

        return ReponseDeRestaurationDEvenement(version=restaure.version, etat=restaure.etat)

    @routeur.put(
        "/entities/{code}/events/{evenement}/medias",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeGestionDesMediasDEvenement,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : l'evenement n'existe pas dans cette entite (ou est "
                    "archive), le role n'y porte rien, ou il y porte `Modifier` sans "
                    "`Ajouter une image ou vidéo` — pour le DSM, « Perimetre » seul (ses "
                    "consultants nommes), jamais « cree par lui » seul (meme grille que "
                    "`Publier`/`Annuler`/`Archiver`)."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_409_CONFLICT: {
                "description": "`version_obsolete` : l'evenement a change depuis votre lecture."
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`ressource_introuvable` : un media nomme n'est pas dans cette entite, "
                    "ou il est archive. `media_non_pret` : seul un media `ready` est "
                    "rattachable. `doublon_dans_la_liste` : un meme media nomme deux fois."
                )
            },
        },
        summary="Remplacer la liste des medias d'un evenement",
        description=(
            "Matrice §11 « Ajouter une image ou vidéo ». La liste REMPLACE la liste "
            "complete, dans l'ordre fourni — `[]` la vide. Aucun televersement : le "
            "media doit deja exister, `ready`, dans cette entite (LOT 11)."
        ),
    )
    def gerer_les_medias_d_un_evenement_route(
        demande: DemandeDeGestionDesMediasDEvenement,
        requete: Request,
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        evenement: Annotated[
            uuid.UUID, Path(description="L'identifiant de l'evenement, rendu par la creation")
        ],
        appelant: SessionEtablie = Depends(garde_de_creation),  # noqa: B008
    ) -> ReponseDeGestionDesMediasDEvenement:
        """Remplacer la liste des medias d'un evenement — matrice §11, modele §17.3."""
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
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            perimetre = resoudre_le_perimetre_de_l_evenement(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                evenement=evenement,
                roles=frozenset(permissions.roles),
                instant=instant,
            )
            if ActionEvenement.GERER_LES_MEDIAS not in perimetre.actions:
                raise ErreurApplicative(
                    code=CODE_ACCES_REFUSE,
                    message=MESSAGE_ACCES_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            resultat = gerer_les_medias_d_un_evenement(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                evenement=evenement,
                version_attendue=demande.version,
                medias=[(item.media, item.role) for item in demande.medias],
                instant=instant,
            )

        return ReponseDeGestionDesMediasDEvenement(
            version=resultat.version,
            medias=[
                MediaDEvenementRendu(media=m.media_asset_id, role=m.role, ordre=m.ordre)
                for m in resultat.medias
            ],
        )

    return routeur
