"""`POST`/`GET /data-subject-requests` — LOT 10, `T14`, `MVP-L10-US008`.

ROUTES PLATES, MÊME RÉGIME QUE `/alerts` ET `POST /bug-reports`

  `data_subject_request` est une ressource GLOBALE (modèle §22.3, aucun
  `entity_id` — voir l'en-tête d'`app/audit/modeles.py`) : ses routes ne
  peuvent pas suivre le gabarit `/entities/{code}/...`. Voir l'en-tête
  d'`app/privacy/perimetre.py` et d'`app/privacy/traitement.py` pour la
  dérivation complète : pourquoi `ADM-E` est résolu « n'importe où », pourquoi
  aucun motif n'est jamais exigé, et pourquoi ce module ne pose que DEUX
  états.

UNE SEULE GARDE POUR TOUTES LES ROUTES, LECTURE COMPRISE

  À la différence des alertes (`T13`), où l'`ESM` reçoit une lecture
  « Limitée fonctionnelle » en plus d'`ADM-E`/`SUPER`, AUCUNE ligne de
  matrice ne donne de visibilité partielle sur une demande RGPD à qui que
  ce soit d'autre (voir `app/privacy/perimetre.py`) : une seule grille,
  `ROLES_DE_TRAITEMENT_DES_DEMANDES_RGPD`, garde TOUTES les routes — lecture
  et écriture confondues, jamais `exiger_une_session` seule.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING, Annotated, Any, Final

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.audit.modeles import TypeDeDemandeRGPD
from app.auth.dependances import SessionEtablie, exiger_une_session, proteger_du_csrf
from app.permissions.dependances import CODE_ROLE_REFUSE, MESSAGE_ROLE_REFUSE
from app.privacy.perimetre import (
    ROLES_DE_TRAITEMENT_DES_DEMANDES_RGPD,
    resoudre_les_roles_pour_les_demandes_rgpd,
)
from app.privacy.traitement import (
    ETAT_CLOS,
    cloturer_une_demande,
    lire_l_historique_d_une_demande,
    lire_une_demande,
    lister_les_demandes,
    receptionner_une_demande,
    verifier_l_identite,
)
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative
from app.shared.pagination import TAILLE_PAR_DEFAUT, TailleDePage

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable

    from app.configuration.settings import Parametres

#  Bornes larges et arbitraires, memes ordres de grandeur que les autres
#  saisies libres du depot (ex. `app/support/routes.py`) : aucun document ne
#  nomme de longueur maximale pour un canal ou une reponse de cloture.
LONGUEUR_MAXIMALE_DU_CANAL: Final = 200
LONGUEUR_MAXIMALE_DE_LA_REPONSE: Final = 10_000


class DemandeDeReceptionRGPD(BaseModel):
    """Le corps de `POST /data-subject-requests` — cahier §21.5."""

    model_config = ConfigDict(extra="forbid")

    personne_concernee_id: uuid.UUID = Field(description="La personne qui exerce son droit.")
    type_demande: TypeDeDemandeRGPD
    canal: Annotated[
        str,
        Field(
            min_length=1,
            max_length=LONGUEUR_MAXIMALE_DU_CANAL,
            description="Le canal officiel RGPD (e-mail, courrier...) — cahier §21.5.",
        ),
    ]


class LigneDeDemandeRGPDRendue(BaseModel):
    """Une ligne de `data_subject_request` — `T14`, matrice §18.

    `en_retard` est CALCULÉ à la lecture (`due_at < instant`, demande non
    close), jamais une colonne stockée.
    """

    identifiant: uuid.UUID
    personne_concernee_id: uuid.UUID
    type_demande: str
    canal: str
    recue_le: dt.datetime
    identite_verifiee: bool
    responsable_id: uuid.UUID
    echeance: dt.datetime
    en_retard: bool
    etat: str
    reponse: str | None
    cloturee_le: dt.datetime | None
    version: int


class ReponseDesDemandesRGPD(BaseModel):
    """Une page de demandes RGPD — meme forme que `ReponseDesAlertes`."""

    demandes: list[LigneDeDemandeRGPDRendue]
    page: int
    taille: int
    total: int
    pages: int


class EvenementDHistoriqueRGPDRendu(BaseModel):
    """Une ligne de l'historique — `audit_event` de cette demande."""

    survenu_le: dt.datetime
    anciennes_valeurs: dict[str, Any] | None
    nouvelles_valeurs: dict[str, Any] | None
    acteur_id: uuid.UUID | None


class ReponseDeLHistoriqueRGPD(BaseModel):
    """L'historique complet d'une demande, le plus recent d'abord."""

    evenements: list[EvenementDHistoriqueRGPDRendu]


class DemandeDeVerificationIdentite(BaseModel):
    """Corps de `POST .../verification-identite` — aucun autre champ necessaire."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(
        ge=1,
        description=(
            "La version lue sur la demande. Cahier §18.4 : une version "
            "obsolete rend 409 sans ecrasement silencieux."
        ),
    )


class DemandeDeClotureRGPD(BaseModel):
    """Corps de `POST .../cloture` — cahier §21.5 « cloture tracable »."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    reponse: Annotated[
        str,
        Field(
            min_length=1,
            max_length=LONGUEUR_MAXIMALE_DE_LA_REPONSE,
            description=(
                "Ce qui a ete transmis ou fait (« export structure » du "
                "backlog `US008`) — jamais un fichier genere, voir l'en-tete "
                "d'`app/privacy/traitement.py`."
            ),
        ),
    ]


class ReponseDeTransitionRGPD(BaseModel):
    """Ce qu'une transition (verification, cloture) a produit."""

    etat: str
    identite_verifiee: bool
    version: int


def _rendre_une_ligne(ligne: Any, *, instant: dt.datetime) -> LigneDeDemandeRGPDRendue:
    return LigneDeDemandeRGPDRendue(
        identifiant=ligne.id,
        personne_concernee_id=ligne.data_subject_person_id,
        type_demande=ligne.request_type,
        canal=ligne.channel,
        recue_le=ligne.received_at,
        identite_verifiee=ligne.identity_verified,
        responsable_id=ligne.responsible_person_id,
        echeance=ligne.due_at,
        en_retard=ligne.due_at < instant and ligne.state != ETAT_CLOS,
        etat=ligne.state,
        reponse=ligne.response,
        cloturee_le=ligne.closed_at,
        version=ligne.version,
    )


def routeur_rgpd(parametres: Parametres) -> APIRouter:
    """Routeur du suivi d'une demande de droit RGPD, monte sous le prefixe versionne."""
    routeur = APIRouter(tags=["rgpd"])

    def _proteger(requete: Request) -> None:
        """Les deux barrieres CSRF — `DEC-531`. **PAS RECOPIEE**, voir
        `app/support/routes.py` pour le meme motif."""
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")

    def _exiger_le_traitement_des_demandes_rgpd(
        parametres: Parametres,
    ) -> Callable[[Request, Response], SessionEtablie]:
        """Coarse : exige `ADM-E` (n'importe ou) ou `SUPER` — garde UNIQUE de ce
        routeur, lecture et ecriture confondues (voir l'en-tete du module).
        Pas `exiger_un_role_dans_l_entite` : cette dependance EXIGE un
        parametre de chemin `code`, absent de toute route plate."""
        controler_la_session = exiger_une_session(parametres)

        def controler(requete: Request, reponse: Response) -> SessionEtablie:
            appelant = controler_la_session(requete, reponse)
            instant = dt.datetime.now(tz=dt.UTC)
            with moteur(parametres).connect() as connexion:
                roles = resoudre_les_roles_pour_les_demandes_rgpd(
                    connexion, personne=appelant.personne, instant=instant
                )
            if not ROLES_DE_TRAITEMENT_DES_DEMANDES_RGPD & roles:
                raise ErreurApplicative(
                    code=CODE_ROLE_REFUSE,
                    message=MESSAGE_ROLE_REFUSE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            return appelant

        return controler

    garde_du_traitement_rgpd = _exiger_le_traitement_des_demandes_rgpd(parametres)

    @routeur.post(
        "/data-subject-requests",
        status_code=status.HTTP_201_CREATED,
        response_model=LigneDeDemandeRGPDRendue,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : ni `ADM-E` ni `SUPER`, ou le jeton anti-CSRF "
                    "manque ou ne correspond pas."
                )
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": "`personne_concernee_introuvable`, ou canal vide/trop long."
            },
        },
        summary="Receptionner une demande de droit RGPD",
        description=(
            "Cahier §21.5, modele §22.3, `T14`, `MVP-L10-US008`. Reservee a "
            "`ADM-E`/`SUPER` par analogie avec la matrice §18 « Lancer "
            "l'anonymisation RGPD » — voir l'en-tete d'`app/privacy/"
            "perimetre.py`. Le `responsable` est TOUJOURS l'appelant : "
            "aucune route de reassignation n'est posee, faute de document "
            "qui la nomme."
        ),
    )
    def receptionner(
        corps: DemandeDeReceptionRGPD,
        requete: Request,
        appelant: SessionEtablie = Depends(garde_du_traitement_rgpd),  # noqa: B008
    ) -> LigneDeDemandeRGPDRendue:
        """Receptionner une demande de droit — cahier §21.5."""
        _proteger(requete)
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            ligne = receptionner_une_demande(
                connexion,
                data_subject_person_id=corps.personne_concernee_id,
                request_type=corps.type_demande.value,
                channel=corps.canal,
                responsible_person_id=appelant.personne,
                acteur=appelant.personne,
                instant=instant,
            )
        return _rendre_une_ligne(ligne, instant=instant)

    @routeur.get(
        "/data-subject-requests",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDesDemandesRGPD,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {"description": "`acces_refuse` : ni `ADM-E` ni `SUPER`."},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": "`taille` hors des trois valeurs du cahier §18.2, ou `page` < 1."
            },
        },
        summary="Consulter les demandes de droit RGPD",
    )
    def consulter_les_demandes(
        page: Annotated[int, Query(ge=1, description="Numero de page, 1-indexee")] = 1,
        taille: Annotated[
            TailleDePage,
            Query(description="Elements par page — les trois valeurs du cahier §18.2, seules"),
        ] = TAILLE_PAR_DEFAUT,
        etat: Annotated[str | None, Query(description="Filtrer sur un etat exact.")] = None,
        type_demande: Annotated[
            TypeDeDemandeRGPD | None, Query(description="Filtrer sur un type de demande.")
        ] = None,
        appelant: SessionEtablie = Depends(garde_du_traitement_rgpd),  # noqa: B008
    ) -> ReponseDesDemandesRGPD:
        """Consulter les demandes de droit RGPD — `T14`."""
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            resultat = lister_les_demandes(
                connexion,
                filtre_etat=etat,
                filtre_type=type_demande.value if type_demande is not None else None,
                page=page,
                taille=int(taille),
            )

        pages = -(-resultat.total // int(taille))
        return ReponseDesDemandesRGPD(
            demandes=[_rendre_une_ligne(ligne, instant=instant) for ligne in resultat.demandes],
            page=page,
            taille=int(taille),
            total=resultat.total,
            pages=pages,
        )

    @routeur.get(
        "/data-subject-requests/{demande}",
        status_code=status.HTTP_200_OK,
        response_model=LigneDeDemandeRGPDRendue,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {"description": "`acces_refuse`."},
            status.HTTP_404_NOT_FOUND: {"description": "Aucune demande avec cet identifiant."},
        },
        summary="Consulter une demande de droit RGPD",
    )
    def consulter_une_demande(
        demande: Annotated[uuid.UUID, Path(description="L'identifiant de la demande")],
        appelant: SessionEtablie = Depends(garde_du_traitement_rgpd),  # noqa: B008
    ) -> LigneDeDemandeRGPDRendue:
        """Consulter une demande de droit RGPD — `T14`."""
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            ligne = lire_une_demande(connexion, demande=demande)
        return _rendre_une_ligne(ligne, instant=instant)

    @routeur.get(
        "/data-subject-requests/{demande}/historique",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeLHistoriqueRGPD,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {"description": "`acces_refuse`."},
            status.HTTP_404_NOT_FOUND: {"description": "Aucune demande avec cet identifiant."},
        },
        summary="Consulter l'historique d'une demande de droit RGPD",
        description=(
            "La suite des `audit_event` de cette demande — reception, "
            "verification d'identite, cloture."
        ),
    )
    def consulter_l_historique(
        demande: Annotated[uuid.UUID, Path(description="L'identifiant de la demande")],
        appelant: SessionEtablie = Depends(garde_du_traitement_rgpd),  # noqa: B008
    ) -> ReponseDeLHistoriqueRGPD:
        """Consulter l'historique d'une demande de droit RGPD — `T14`."""
        with moteur(parametres).begin() as connexion:
            lire_une_demande(connexion, demande=demande)
            evenements = lire_l_historique_d_une_demande(connexion, demande=demande)
        return ReponseDeLHistoriqueRGPD(
            evenements=[
                EvenementDHistoriqueRGPDRendu(
                    survenu_le=evenement.occurred_at,
                    anciennes_valeurs=evenement.old_values,
                    nouvelles_valeurs=evenement.new_values,
                    acteur_id=evenement.actor_person_id,
                )
                for evenement in evenements
            ]
        )

    @routeur.post(
        "/data-subject-requests/{demande}/verification-identite",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeTransitionRGPD,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : ni `ADM-E` ni `SUPER`, ou le jeton anti-CSRF "
                    "manque ou ne correspond pas."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Aucune demande avec cet identifiant."},
            status.HTTP_409_CONFLICT: {"description": "`version_obsolete` — cahier §18.4."},
        },
        summary="Marquer l'identite du demandeur comme verifiee",
        description=(
            "Cahier §21.5 « verification d'identite adaptee » — aucune precondition d'etat."
        ),
    )
    def verifier_identite(
        demande: Annotated[uuid.UUID, Path(description="L'identifiant de la demande")],
        corps: DemandeDeVerificationIdentite,
        requete: Request,
        appelant: SessionEtablie = Depends(garde_du_traitement_rgpd),  # noqa: B008
    ) -> ReponseDeTransitionRGPD:
        """Verifier l'identite du demandeur — cahier §21.5."""
        _proteger(requete)
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            resultat = verifier_l_identite(
                connexion,
                demande=demande,
                version_attendue=corps.version,
                acteur=appelant.personne,
                instant=instant,
            )
        return ReponseDeTransitionRGPD(
            etat=resultat.state,
            identite_verifiee=resultat.identity_verified,
            version=resultat.version,
        )

    @routeur.post(
        "/data-subject-requests/{demande}/cloture",
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeTransitionRGPD,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "`acces_refuse` : ni `ADM-E` ni `SUPER`, ou le jeton anti-CSRF "
                    "manque ou ne correspond pas."
                )
            },
            status.HTTP_404_NOT_FOUND: {"description": "Aucune demande avec cet identifiant."},
            status.HTTP_409_CONFLICT: {
                "description": (
                    "`version_obsolete` (cahier §18.4), ou `transition_invalide` si la "
                    "demande est deja cloturee."
                )
            },
        },
        summary="Cloturer une demande de droit RGPD",
        description="Cahier §21.5 « cloture tracable », `T14`, `MVP-L10-US008`.",
    )
    def cloturer(
        demande: Annotated[uuid.UUID, Path(description="L'identifiant de la demande")],
        corps: DemandeDeClotureRGPD,
        requete: Request,
        appelant: SessionEtablie = Depends(garde_du_traitement_rgpd),  # noqa: B008
    ) -> ReponseDeTransitionRGPD:
        """Cloturer une demande de droit RGPD — cahier §21.5."""
        _proteger(requete)
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            resultat = cloturer_une_demande(
                connexion,
                demande=demande,
                version_attendue=corps.version,
                reponse=corps.reponse,
                acteur=appelant.personne,
                instant=instant,
            )
        return ReponseDeTransitionRGPD(
            etat=resultat.state,
            identite_verifiee=resultat.identity_verified,
            version=resultat.version,
        )

    return routeur
