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

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from app.auth.dependances import SessionEtablie, exiger_une_session, proteger_du_csrf
from app.permissions.services import entite_principale
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative
from app.support.signalement import creer_un_signalement

if TYPE_CHECKING:  # pragma: no cover
    from app.configuration.settings import Parametres

CODE_AUCUNE_ENTITE_PRINCIPALE: Final = "aucune_entite_principale"
MESSAGE_AUCUNE_ENTITE_PRINCIPALE: Final = (
    "Aucune appartenance active n'a ete trouvee pour rattacher ce signalement."
)

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

    return routeur
