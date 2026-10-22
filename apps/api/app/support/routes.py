"""`POST /bug-reports` — LOT 10, `T11`, `MVP-L10-US005`.

AUCUNE GARDE DE RÔLE AU-DELÀ D'UNE SESSION ÉTABLIE, ET CE N'EST PAS UNE OMISSION

  La matrice §17 donne « Reporter un bug » à `DSM`, `ESM`, `BOOST`, `OFFICE`,
  `ADM-E` et `SUPER` SANS exception — la seule ligne de ce tableau qui ne
  porte aucun tiret. Son propre tableau n'énumère pas `EMP` en colonne, mais
  trois faits concordants, aucun deviné, règlent la question sans arbitrage :

    1. le backlog nomme l'acteur de la story `Utilisateur`
       (`MVP-L10-US005`, `docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md`),
       jamais un rôle précis — contrairement à `US004`
       (`ADM-E`/`SUPER` seuls, cité littéralement) ;
    2. le cahier §10.12 place le bouton au pied de page, sur les pages
       d'erreur et dans le menu mobile — des emplacements que `EMP` et `NEW`
       voient autant que les six rôles élargis, et un bouton qu'une partie des
       rôles qui le voient ne pourrait jamais actionner serait l'avertissement
       faux du §7.21 de la passation ;
    3. même motif exact que `GET /entities/{code}/accueil` (LOT 8, `T8`) :
       « Aucune garde de rôle au-delà d'une session établie ». Là, la matrice
       donnait « Lecture » aux huit rôles sans distinction ; ici, « Reporter
       un bug » n'a tout simplement pas de colonne où `EMP` pourrait être
       refusé — l'absence de tiret nulle part est l'inverse de `ROLES_DU_
       TABLEAU_DE_BORD` (LOT 9 `T5`), où `OFFICE` porte explicitement un
       tiret.

  La garde est donc `exiger_une_session`, pas `exiger_un_role_dans_l_entite`.

AUCUN CODE D'ENTITÉ DANS LE CHEMIN, ET C'EST DÉLIBÉRÉ

  Les routes `GET`/`POST` du lot sont toutes `/entities/{code}/...` parce
  qu'elles LISENT ou ÉCRIVENT une ressource D'UNE entité déjà désignée par
  l'appelant. Le signalement n'a pas cette désignation à chaque emplacement où
  le cahier le place : le pied de page et le menu mobile vivent À L'INTÉRIEUR
  d'une entité consultée (le code est dans l'adresse), mais les pages d'erreur
  du cahier §9.6 — démonstration citée : « création d'un signalement depuis
  une page d'erreur » — n'en portent structurellement AUCUNE : un visiteur qui
  atteint le fourre-tout 404 n'a pas nécessairement navigué depuis une entité.

  Plutôt que deux mécanismes (un avec code, un sans) pour une même écriture, ou
  qu'inventer une règle que rien ne décide sur laquelle entité attacher un
  signalement fait depuis une page sans contexte, ce service résout toujours
  la MÊME chose : l'entité PRINCIPALE du rapporteur
  (`app.permissions.services.entite_principale`, déjà posée et prouvée par le
  LOT 4). C'est la seule notion d'« entité de cette personne » qui existe déjà
  dans ce dépôt, valable qu'un code soit affiché ou non, et cohérente avec « Entité
  consultée » du modèle §21.4 dans le cas le plus fréquent — signaler un
  problème vu dans sa propre entité.

  **Limite documentée, pas résolue davantage faute de décision du corpus** : un
  DSM qui consulte une entité étrangère et y rencontre un bug verra son
  signalement attaché à SA entité principale, jamais à l'entité étrangère
  consultée. Aucun document ne nomme ce cas ; l'inventer serait trancher une
  question que personne n'a posée (§6.5 de la passation).
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING, Annotated, Final

from fastapi import APIRouter, Depends, Path, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.audit.modeles import EtatSignalement
from app.audit.motif import exiger_un_motif_si_necessaire
from app.auth.dependances import SessionEtablie, exiger_une_session, proteger_du_csrf
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import resoudre_une_entite_active
from app.permissions.dependances import (
    CODE_ROLE_REFUSE,
    MESSAGE_ROLE_REFUSE,
    exiger_un_role_dans_l_entite,
)
from app.permissions.services import RoleDeLaMatrice, entite_principale, resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative
from app.shared.pagination import TAILLE_PAR_DEFAUT, TailleDePage
from app.support.perimetre import (
    ROLES_DE_TRAITEMENT_DES_SIGNALEMENTS,
    a_la_lecture_complete,
    resoudre_le_perimetre_des_signalements,
)
from app.support.signalement import creer_un_signalement
from app.support.traitement import (
    CODE_SIGNALEMENT_INTROUVABLE,
    MESSAGE_SIGNALEMENT_INTROUVABLE,
    lire_l_historique_d_un_signalement,
    lister_les_signalements,
    modifier_l_etat_d_un_signalement,
    signalement_visible,
)

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

    from app.configuration.settings import Parametres

CODE_AUCUNE_ENTITE_PRINCIPALE: Final = "aucune_entite_principale"
MESSAGE_AUCUNE_ENTITE_PRINCIPALE: Final = (
    "Aucune appartenance active n'a ete trouvee pour rattacher ce signalement."
)

#  §17 : meme borne que les saisies libres de `DemandeDeSignalement`.
LONGUEUR_MAXIMALE_DU_COMMENTAIRE: Final = 2000

#  Bornes larges et arbitraires : aucun document ne nomme de longueur maximale
#  pour une saisie libre de signalement, et refuser silencieusement un texte
#  trop long serait pire que de le borner tres haut. Memes ordres de grandeur
#  que les autres saisies libres du depot (ex. `app/content/routes.py`).
LONGUEUR_MAXIMALE_DE_LA_SAISIE: Final = 10_000
LONGUEUR_MAXIMALE_DU_CHEMIN: Final = 2048


class DemandeDeSignalement(BaseModel):
    """Le corps envoyé par le bouton « Reporter un bug » — cahier §9.6/§10.12.

    **AUCUN CHAMP `environment`/`application_version`/`browser_summary`** :
    les trois sont ajoutés automatiquement par le serveur (voir l'en-tête
    d'`app/support/signalement.py`), jamais soumis par le client.
    """

    description: Annotated[
        str,
        Field(
            min_length=1,
            max_length=LONGUEUR_MAXIMALE_DE_LA_SAISIE,
            description="La description du probleme et de l'action tentee (cahier §9.6).",
        ),
    ]
    etapes_de_reproduction: Annotated[
        str | None,
        Field(
            default=None,
            max_length=LONGUEUR_MAXIMALE_DE_LA_SAISIE,
            description="Facultatif — modele §21.4.",
        ),
    ] = None
    chemin_de_page: Annotated[
        str,
        Field(
            min_length=1,
            max_length=LONGUEUR_MAXIMALE_DU_CHEMIN,
            description="La route du frontend affichee au moment du clic — ajout automatique.",
        ),
    ]


class ReponseDuSignalement(BaseModel):
    """Ce que la route rend apres creation — de quoi confirmer l'envoi."""

    identifiant: uuid.UUID
    etat: str
    cree_le: dt.datetime


class LigneDeSignalementRendue(BaseModel):
    """Une ligne de la liste — `T12`, matrice §17.

    Les quatre champs techniques sont `null` pour qui n'a que la « Lecture
    fonctionnelle » (l'`ESM`, lisant les signalements d'autrui) — jamais une
    absence de colonne, voir `app/support/perimetre.py`.
    """

    identifiant: uuid.UUID
    etat: str
    description: str
    etapes_de_reproduction: str | None
    chemin_de_page: str
    entite_id: uuid.UUID
    rapporteur_id: uuid.UUID
    cree_le: dt.datetime
    version: int
    version_application: str | None
    environnement: str | None
    resume_navigateur: str | None
    jeton_de_correlation: str | None


class ReponseDesSignalements(BaseModel):
    """Une page de signalements — meme forme que `ReponseDuJournalDAudit` (`T8`)."""

    signalements: list[LigneDeSignalementRendue]
    page: int
    taille: int
    total: int
    pages: int


class EvenementDHistoriqueRendu(BaseModel):
    """Une ligne de l'historique — `audit_event` de ce signalement."""

    survenu_le: dt.datetime
    ancien_etat: str | None
    nouvel_etat: str | None
    commentaire: str | None
    acteur_id: uuid.UUID | None


class ReponseDeLHistorique(BaseModel):
    """L'historique complet d'un signalement, le plus recent d'abord."""

    evenements: list[EvenementDHistoriqueRendu]


class DemandeDeChangementDEtat(BaseModel):
    """Corps de `POST .../bug-reports/{signalement}/etat` — matrice §17.

    `commentaire` sert DEUX fins : le commentaire du backlog `US006`, ET le
    motif obligatoire du §18.1 quand `SUPER` autorise l'appel (voir l'en-tete
    d'`app/support/traitement.py`) — jamais deux champs redondants.
    """

    model_config = ConfigDict(extra="forbid")

    nouvel_etat: EtatSignalement
    version: int = Field(
        ge=1,
        description=(
            "La version lue sur la liste des signalements. Cahier §18.4 : une "
            "version obsolete rend 409 sans ecrasement silencieux."
        ),
    )
    commentaire: Annotated[
        str | None,
        Field(default=None, max_length=LONGUEUR_MAXIMALE_DU_COMMENTAIRE),
    ] = None


class ReponseDeChangementDEtat(BaseModel):
    """Ce que le changement d'etat a produit."""

    etat: str
    version: int


def routeur_support(parametres: Parametres) -> APIRouter:
    """Routeur du signalement de bug, monte sous le prefixe versionne."""
    routeur = APIRouter(tags=["support"])

    def _proteger(requete: Request) -> None:
        """Les deux barrieres CSRF — `DEC-531`, meme motif que `content/routes.py`.

        **PAS RECOPIEE** : `proteger_du_csrf` vit dans `app/auth/dependances.py`
        depuis `T7` du LOT 5, et deux copies d'une meme regle divergent au
        premier changement (`DEC-466`).
        """
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")

    @routeur.post(
        "/bug-reports",
        status_code=status.HTTP_201_CREATED,
        response_model=ReponseDuSignalement,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": "Origine refusee ou jeton anti-CSRF absent/invalide (`DEC-531`)."
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "Description vide ou trop longue, ou aucune appartenance "
                    "principale active pour rattacher le signalement."
                )
            },
        },
        summary="Signaler un bug depuis l'application",
        description=(
            "Cahier §9.6/§10.12, matrice §17 « Reporter un bug » — ouvert a "
            "toute session authentifiee, sans distinction de role "
            "(`MVP-L10-US005`). Le contexte technique non sensible "
            "(`application_version`, `environment`, `browser_summary`) et "
            "l'identifiant de correlation sont ajoutes automatiquement ; "
            "aucune saisie metier n'est jointe au-dela de la description et "
            "des etapes de reproduction."
        ),
    )
    def signaler_un_bug(
        corps: DemandeDeSignalement,
        requete: Request,
        appelant: SessionEtablie = Depends(exiger_une_session(parametres)),  # noqa: B008
    ) -> ReponseDuSignalement:
        """Enregistrer un signalement de bug — cahier §9.6, points 1 a 4."""
        _proteger(requete)
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = entite_principale(connexion, appelant.personne)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_AUCUNE_ENTITE_PRINCIPALE,
                    message=MESSAGE_AUCUNE_ENTITE_PRINCIPALE,
                    statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
                )
            signalement = creer_un_signalement(
                connexion,
                entity_id=entite,
                reported_by_person_id=appelant.personne,
                description=corps.description,
                reproduction_steps=corps.etapes_de_reproduction,
                page_path=corps.chemin_de_page,
                application_version=parametres.APP_VERSION,
                environment=parametres.APP_ENV,
                user_agent=requete.headers.get("user-agent"),
                instant=instant,
            )
        return ReponseDuSignalement(
            identifiant=signalement.id,
            etat=signalement.state,
            cree_le=signalement.created_at,
        )

    # ========================================================================
    #
    #  LE TRAITEMENT DES SIGNALEMENTS — LOT 10, `T12`, `MVP-L10-US006`. Voir
    #  l'en-tete d'`app/support/perimetre.py` et d'`app/support/traitement.py`
    #  pour la derivation complete : qui voit quoi, pourquoi l'historique
    #  n'est pas servi par `GET /entities/{code}/audit`, et comment `QO-092`
    #  est resolue par la matrice plutot qu'arbitree.
    #
    # ========================================================================

    def _resoudre_l_entite_et_les_roles(
        connexion: Connection, *, code: str, appelant: SessionEtablie, instant: dt.datetime
    ) -> tuple[uuid.UUID, frozenset[RoleDeLaMatrice]]:
        """L'entite active, ET les roles resolus dans CETTE transaction.

        **AUCUNE GARDE COARSE ICI** : contrairement au journal d'audit (six
        roles, aucun tiret total), la liste des signalements n'a pas de
        plancher de role — `Soi` est servi a QUI QUE CE SOIT d'authentifie
        (voir `app.support.perimetre`). Le refus 403 n'existe donc QUE sur la
        route de changement d'etat, verifiee separement.
        """
        entite = resoudre_une_entite_active(connexion, code)
        if entite is None:
            raise ErreurApplicative(
                code=CODE_ENTITE_INTROUVABLE,
                message=MESSAGE_ENTITE_INTROUVABLE,
                statut=status.HTTP_404_NOT_FOUND,
            )
        permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
        return entite.id, frozenset(permissions.roles)

    @routeur.get(
        "/entities/{code}/bug-reports",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDesSignalements,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_404_NOT_FOUND: {"description": "Entite inconnue ou non active."},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": "`taille` hors des trois valeurs du cahier §18.2, ou `page` < 1."
            },
        },
        summary="Consulter les signalements, selon le perimetre resolu",
        description=(
            "Matrice §17 « Consulter ses signalements »/« Consulter les signalements "
            "de l'entite », `T12`, `MVP-L10-US006`. `Soi` pour qui n'a aucun role "
            "etendu, lecture fonctionnelle (sans contexte technique) pour l'`ESM`, "
            "complete pour `ADM-E`/`SUPER`. Le `total` sert de compteur back-office, "
            "filtrable par `etat`."
        ),
    )
    def consulter_les_signalements(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        page: Annotated[int, Query(ge=1, description="Numero de page, 1-indexee")] = 1,
        taille: Annotated[
            TailleDePage,
            Query(description="Elements par page — les trois valeurs du cahier §18.2, seules"),
        ] = TAILLE_PAR_DEFAUT,
        etat: Annotated[
            EtatSignalement | None,
            Query(description="Filtrer sur un etat exact — sert le compteur back-office."),
        ] = None,
        appelant: SessionEtablie = Depends(exiger_une_session(parametres)),  # noqa: B008
    ) -> ReponseDesSignalements:
        """Consulter les signalements — matrice §17, `T12`."""
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite_id, roles = _resoudre_l_entite_et_les_roles(
                connexion, code=code, appelant=appelant, instant=instant
            )
            perimetre = resoudre_le_perimetre_des_signalements(roles=roles)
            resultat = lister_les_signalements(
                connexion,
                entite=entite_id,
                acteur=appelant.personne,
                perimetre=perimetre,
                avec_lecture_complete=a_la_lecture_complete(perimetre=perimetre),
                filtre_etat=etat.value if etat is not None else None,
                page=page,
                taille=int(taille),
            )

        pages = -(-resultat.total // int(taille))
        return ReponseDesSignalements(
            signalements=[
                LigneDeSignalementRendue(
                    identifiant=ligne.id,
                    etat=ligne.state,
                    description=ligne.description,
                    etapes_de_reproduction=ligne.reproduction_steps,
                    chemin_de_page=ligne.page_path,
                    entite_id=ligne.entity_id,
                    rapporteur_id=ligne.reported_by_person_id,
                    cree_le=ligne.created_at,
                    version=ligne.version,
                    version_application=ligne.application_version,
                    environnement=ligne.environment,
                    resume_navigateur=ligne.browser_summary,
                    jeton_de_correlation=ligne.correlation_token,
                )
                for ligne in resultat.signalements
            ],
            page=page,
            taille=int(taille),
            total=resultat.total,
            pages=pages,
        )

    @routeur.get(
        "/entities/{code}/bug-reports/{signalement}/historique",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeLHistorique,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_404_NOT_FOUND: {
                "description": "Entite inconnue, ou signalement inconnu/hors du perimetre resolu."
            },
        },
        summary="Consulter l'historique d'un signalement",
        description=(
            "La suite des `audit_event` de ce signalement — jamais la route "
            "generique d'audit, dont le perimetre (matrice §16) differe de celui "
            "du support (matrice §17). Visible a qui peut deja voir le signalement "
            "lui-meme, jamais plus loin."
        ),
    )
    def consulter_l_historique(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite consultee",
            ),
        ],
        signalement: Annotated[uuid.UUID, Path(description="L'identifiant du signalement")],
        appelant: SessionEtablie = Depends(exiger_une_session(parametres)),  # noqa: B008
    ) -> ReponseDeLHistorique:
        """Consulter l'historique d'un signalement — matrice §17, `T12`."""
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite_id, roles = _resoudre_l_entite_et_les_roles(
                connexion, code=code, appelant=appelant, instant=instant
            )
            perimetre = resoudre_le_perimetre_des_signalements(roles=roles)
            if not signalement_visible(
                connexion,
                signalement=signalement,
                entite=entite_id,
                acteur=appelant.personne,
                perimetre=perimetre,
            ):
                raise ErreurApplicative(
                    code=CODE_SIGNALEMENT_INTROUVABLE,
                    message=MESSAGE_SIGNALEMENT_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            evenements = lire_l_historique_d_un_signalement(connexion, signalement=signalement)
        return ReponseDeLHistorique(
            evenements=[
                EvenementDHistoriqueRendu(
                    survenu_le=evenement.occurred_at,
                    ancien_etat=(evenement.old_values or {}).get("state"),
                    nouvel_etat=(evenement.new_values or {}).get("state"),
                    commentaire=evenement.reason,
                    acteur_id=evenement.actor_person_id,
                )
                for evenement in evenements
            ]
        )

    garde_du_traitement = exiger_un_role_dans_l_entite(
        parametres, ROLES_DE_TRAITEMENT_DES_SIGNALEMENTS
    )

    @routeur.post(
        "/entities/{code}/bug-reports/{signalement}/etat",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeChangementDEtat,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : ni `ADM-E` ni `SUPER` dans cette entite, ou le "
                    "jeton anti-CSRF manque ou ne correspond pas."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Entite inconnue, ou signalement inconnu dans cette entite."
            },
            status.HTTP_409_CONFLICT: {"description": "`version_obsolete` — cahier §18.4."},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "`motif_obligatoire` : `SUPER` autorise cet appel et `commentaire` "
                    "est absent ou vide (cahier §18.1, `ECART-064`)."
                )
            },
        },
        summary="Modifier l'etat d'un signalement",
        description=(
            "Matrice §17 « Modifier l'etat d'un signalement | Entite | Global », "
            "`T12`, `MVP-L10-US006`. Aucune transition n'est restreinte — le corpus "
            "ne porte aucun diagramme d'etat pour `bug_report`. `commentaire` est "
            "trace dans `audit_event.reason` : c'est l'historique du backlog, et le "
            "motif du §18.1 quand `SUPER` autorise l'appel."
        ),
    )
    def modifier_l_etat(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite",
            ),
        ],
        signalement: Annotated[uuid.UUID, Path(description="L'identifiant du signalement")],
        demande: DemandeDeChangementDEtat,
        requete: Request,
        appelant: SessionEtablie = Depends(garde_du_traitement),  # noqa: B008
    ) -> ReponseDeChangementDEtat:
        """Modifier l'etat d'un signalement — matrice §17, `T12`.

        **LA GARDE COARSE A RESOLU LES SIENS DANS SA PROPRE CONNEXION** :
        reverifies ici, dans la transaction qui ecrit — meme motif que
        `_resoudre_l_entite_et_verifier_le_role` (`app.organization.routes`).
        """
        _proteger(requete)
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite_id, roles = _resoudre_l_entite_et_les_roles(
                connexion, code=code, appelant=appelant, instant=instant
            )
            if not ROLES_DE_TRAITEMENT_DES_SIGNALEMENTS & roles:
                raise ErreurApplicative(
                    code=CODE_ROLE_REFUSE,
                    message=MESSAGE_ROLE_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            exiger_un_motif_si_necessaire(roles, demande.commentaire)
            resultat = modifier_l_etat_d_un_signalement(
                connexion,
                entite=entite_id,
                signalement=signalement,
                nouvel_etat=demande.nouvel_etat.value,
                version_attendue=demande.version,
                commentaire=demande.commentaire,
                acteur=appelant.personne,
                instant=instant,
            )
        return ReponseDeChangementDEtat(etat=resultat.state, version=resultat.version)

    return routeur
