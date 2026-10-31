"""Les routes de la photo de profil — LOT 11, `T2`, `MVP-L11-US004`/`US005`.

Montee SOUS `/entities/{code}/people/{appartenance}/photo`, le MEME chemin que
`GET .../photo` (LOT 5, `T5`, `app.people.routes`) : un GET lit la miniature
autorisee, cette sous-etape y ajoute les verbes d'ECRITURE. Reutilise la
resolution d'entite et le gabarit de 404 deja etablis par `app.people.routes`
et `app.onboarding.fiche_arrivee` — deux chemins qui distingueraient
differemment un code inconnu d'une appartenance inexistante apprendraient,
par comparaison, qu'un brouillon existe.

LE DEPOT EST GARDE PAR LA MEME GRILLE QUE LA FICHE D'ARRIVEE, ET C'EST
DELIBERE

  `peut_deposer_une_photo` (voir `perimetre.py`) dispatche sur `peut_
  completer_la_fiche_arrivee`/`peut_corriger_la_fiche_arrivee_apres_
  publication` (LOT 7) selon que `arrival_profile.state` vaut `published` ou
  non — la MEME lecture, `lire_la_fiche_arrivee`, que la route de `app.
  onboarding.routes` qui complete `short_intro`/`fun_fact`. C'est le MEME §7,
  « photo, presentation et fun fact », simplement jamais ecrit avant ce lot.

LA MISE EN FILE REVEILLE LE RELAIS PAR `BackgroundTasks`, JAMAIS PAR DRAMATIQ
DEPUIS L'API

  `app.jobs.outbox.relayer_le_lot` est une fonction PURE, deja importable
  sans aucun courtier — c'est `apps/worker/worker/actors.py` qui l'habille en
  acteur Dramatiq, pour un DECLENCHEMENT PERIODIQUE futur (`T4`, tache
  planifiee). L'API ne possede AUCUN courtier (c'est le WORKER qui le
  possede, voir l'en-tete d'`actors.py`) : lui en donner un pour ce seul
  reveil serait une DEUXIEME voie de declenchement, plus de surface a
  maintenir pour le meme effet. Apres le commit de la transaction d'upload,
  une tache de fond appelle donc DIRECTEMENT `relayer_le_lot`, dans sa PROPRE
  transaction courte — exactement la discipline que `T1` annoncait deja
  (« meme discipline que `BackgroundTasks` apres la reponse en
  `app.auth.routes` ») sans jamais l'avoir exercee, faute de premier
  appelant. `T2` est ce premier appelant.

  Un relais qui echouerait silencieusement (l'API tombe entre le commit et
  l'execution de la tache de fond) n'est pas un cas perdu : l'outbox reste
  ECRITE, et une future tache planifiee (`T4`) ou un nouveau depot relaieront
  le lot entier au passage suivant. Perdre LE REVEIL immediat ne perd jamais
  LE MESSAGE.

DEUX ROUTES DE LECTURE SANS LIGNE DE MATRICE PROPRE, POUR L'ECRAN SEUL

  `GET .../photo/droits` et `GET .../media/{media}/etat` ne servent aucune
  ligne du §6.1 — elles disent a l'ecran ce qu'il peut proposer et ou en est
  un depot en cours, pour que l'ecran n'ait pas a deviner un etat qu'il ne
  peut pas observer autrement. Voir `app.media.perimetre.peut_consulter_l_
  etat_d_un_media` pour la seule regle qu'elles ajoutent.
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid
from typing import Annotated, Final

from fastapi import APIRouter, BackgroundTasks, Depends, File, Path, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import text

from app.auth.dependances import SessionEtablie, exiger_une_session, proteger_du_csrf
from app.configuration.settings import Parametres
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import resoudre_une_entite_active
from app.jobs.outbox import relayer_le_lot
from app.media.autorisation import (
    CODE_MEDIA_INTROUVABLE,
    CODE_MEDIA_PAS_PRET,
    accorder_l_autorisation_photo,
    retirer_l_autorisation_photo,
)
from app.media.depot import deposer_une_photo
from app.media.modeles import SourceAutorisationPhoto
from app.media.perimetre import (
    peut_consulter_l_etat_d_un_media,
    peut_deposer_une_photo,
    peut_gerer_l_autorisation_photo,
)
from app.onboarding.fiche_arrivee import lire_la_fiche_arrivee
from app.permissions.services import resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

journal = logging.getLogger("app.media")

CODE_PHOTO_HORS_PERIMETRE: Final = "photo_hors_perimetre"
MESSAGE_PHOTO_HORS_PERIMETRE_DEPOT: Final = (
    "Votre perimetre ne vous permet pas de deposer cette photo."
)
MESSAGE_PHOTO_HORS_PERIMETRE_AUTORISATION: Final = (
    "Votre perimetre ne vous permet pas de gerer cette autorisation."
)

GABARIT_PHOTO: Final = "/entities/{code}/people/{appartenance}/photo"
GABARIT_AUTORISATION: Final = f"{GABARIT_PHOTO}/autorisation"
GABARIT_RETRAIT: Final = f"{GABARIT_AUTORISATION}/retrait"
GABARIT_DROITS: Final = f"{GABARIT_PHOTO}/droits"
GABARIT_ETAT_MEDIA: Final = "/entities/{code}/media/{media}/etat"

_LIGNE_ETAT_MEDIA: Final = text(
    "SELECT state, rejection_code, uploaded_by_person_id FROM media_asset "
    "WHERE id = :id AND entity_id = :entite"
)


class ReponseDeDepotDePhoto(BaseModel):
    """Ce que `POST .../photo` rend — le depot en quarantaine, pas encore pret."""

    id: str
    state: str


class EtatDUnMedia(BaseModel):
    """Ce que `GET .../media/{media}/etat` rend — pour suivre un depot en cours."""

    id: str
    state: str
    rejection_code: str | None


class DroitsDePhoto(BaseModel):
    """Ce que `GET .../photo/droits` rend — pour que l'ecran sache quoi proposer."""

    peut_deposer: bool
    peut_gerer_autorisation: bool


class DemandeDAutorisation(BaseModel):
    """Le corps de `POST .../photo/autorisation` — quel media autoriser."""

    media_asset_id: str


class ReponseDAutorisation(BaseModel):
    """Ce que `POST .../photo/autorisation` rend."""

    id: str
    granted_at: str


class ReponseDeRetrait(BaseModel):
    """Ce que `POST .../photo/autorisation/retrait` rend."""

    autorisations_retirees: int


def _eveiller_le_relais(parametres: Parametres) -> None:
    """Relayer un lot de l'outbox — voir l'en-tete du module.

    Appelee APRES la reponse (`BackgroundTasks`) : une panne ici ne doit
    jamais faire echouer la requete qui l'a declenchee, et elle ne perd rien
    — voir l'en-tete.
    """
    try:
        with moteur(parametres).begin() as connexion:
            relayer_le_lot(connexion, instant=dt.datetime.now(tz=dt.UTC))
    except Exception:
        journal.exception("le reveil du relais de l'outbox a echoue")


def routeur_media(parametres: Parametres) -> APIRouter:
    """Les routes de depot et d'autorisation d'une photo de profil."""
    routeur = APIRouter(tags=["media"])

    @routeur.post(
        GABARIT_PHOTO,
        status_code=status.HTTP_201_CREATED,
        response_model=ReponseDeDepotDePhoto,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "Matrice §6.1 « Ajouter ou remplacer une photo », MEME GRILLE que "
                    "« Completer »/« Corriger apres publication » de la fiche d'arrivee "
                    "(LOT 7) : voir `app.media.perimetre`."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Code d'entite inconnu, ou appartenance hors de sa population."
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "description": (
                    "Fichier vide, nom vide une fois nettoye, taille superieure a 10 Mo, "
                    "ou type declare hors JPEG/PNG/WebP."
                )
            },
        },
        summary="Deposer une photo de profil en quarantaine",
        description=(
            "`MVP-L11-US004` : la photo est posee `pending`, jamais servie avant que "
            "son contenu reel ne soit verifie et sa miniature generee — "
            "`GET .../media/{media}/etat` pour suivre ce traitement."
        ),
    )
    def deposer_la_photo(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite",
            ),
        ],
        appartenance: Annotated[uuid.UUID, Path(description="L'identifiant de l'appartenance")],
        requete: Request,
        taches: BackgroundTasks,
        fichier: Annotated[UploadFile, File(description="La photo, deposee telle quelle.")],
        appelant: SessionEtablie = Depends(exiger_une_session(parametres)),  # noqa: B008
    ) -> ReponseDeDepotDePhoto:
        """Deposer (ou remplacer) une photo — matrice §6.1/§7."""
        jeton = requete.cookies.get(parametres.SESSION_COOKIE_NAME)
        proteger_du_csrf(parametres, requete, jeton_de_session=jeton or "")

        #  Lu AVANT la transaction : un corps illisible ne doit pas laisser une
        #  connexion ouverte en attente — meme discipline qu'`app.imports.routes`.
        contenu = fichier.file.read()

        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            fiche = lire_la_fiche_arrivee(
                connexion, entite=entite.id, appartenance=appartenance, instant=instant
            )
            if fiche is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            autorise = peut_deposer_une_photo(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                cible_appartenance=appartenance,
                cible_personne=fiche.person_id,
                roles=frozenset(permissions.roles),
                instant=instant,
                fiche_publiee=fiche.state == "published",
            )
            if not autorise:
                raise ErreurApplicative(
                    code=CODE_PHOTO_HORS_PERIMETRE,
                    message=MESSAGE_PHOTO_HORS_PERIMETRE_DEPOT,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            depose = deposer_une_photo(
                connexion,
                parametres,
                entite=entite.id,
                acteur=appelant.personne,
                nom_de_fichier=fichier.filename or "photo",
                content_type=fichier.content_type,
                contenu=contenu,
                instant=instant,
            )
        taches.add_task(_eveiller_le_relais, parametres)
        return ReponseDeDepotDePhoto(id=str(depose.id), state=depose.state)

    @routeur.get(
        GABARIT_DROITS,
        dependencies=[Depends(exiger_une_session(parametres))],
        status_code=status.HTTP_200_OK,
        response_model=DroitsDePhoto,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_404_NOT_FOUND: {"description": "Meme forme que le depot."},
        },
        summary="Les droits de l'appelant sur la photo d'une appartenance",
        description=(
            "Commodite d'ecran, aucune ligne de matrice propre — dit si l'appelant "
            "peut deposer une photo et/ou gerer l'autorisation de CETTE appartenance."
        ),
    )
    def lire_les_droits(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite",
            ),
        ],
        appartenance: Annotated[uuid.UUID, Path(description="L'identifiant de l'appartenance")],
        appelant: SessionEtablie = Depends(exiger_une_session(parametres)),  # noqa: B008
    ) -> DroitsDePhoto:
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            fiche = lire_la_fiche_arrivee(
                connexion, entite=entite.id, appartenance=appartenance, instant=instant
            )
            if fiche is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            roles = frozenset(permissions.roles)
            peut_deposer = peut_deposer_une_photo(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                cible_appartenance=appartenance,
                cible_personne=fiche.person_id,
                roles=roles,
                instant=instant,
                fiche_publiee=fiche.state == "published",
            )
            peut_gerer = peut_gerer_l_autorisation_photo(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                cible_appartenance=appartenance,
                cible_personne=fiche.person_id,
                roles=roles,
                instant=instant,
            )
        return DroitsDePhoto(peut_deposer=peut_deposer, peut_gerer_autorisation=peut_gerer)

    @routeur.get(
        GABARIT_ETAT_MEDIA,
        dependencies=[Depends(exiger_une_session(parametres))],
        status_code=status.HTTP_200_OK,
        response_model=EtatDUnMedia,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": "Ni l'auteur du depot, ni un role de portee entite."
            },
            status.HTTP_404_NOT_FOUND: {"description": "Media inconnu, ou d'une autre entite."},
        },
        summary="Suivre l'avancement du traitement d'un media depose",
        description=(
            "Commodite d'ecran apres un depot : `pending`/`processing` (en cours), "
            "`ready` (miniature prete, l'autorisation peut etre accordee), "
            "`rejected` (voir `rejection_code`)."
        ),
    )
    def lire_l_etat(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite",
            ),
        ],
        media: Annotated[uuid.UUID, Path(description="L'identifiant du media depose")],
        appelant: SessionEtablie = Depends(exiger_une_session(parametres)),  # noqa: B008
    ) -> EtatDUnMedia:
        instant = dt.datetime.now(tz=dt.UTC)
        with moteur(parametres).begin() as connexion:
            entite = resoudre_une_entite_active(connexion, code)
            if entite is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            ligne = (
                connexion.execute(_LIGNE_ETAT_MEDIA, {"id": media, "entite": entite.id})
                .mappings()
                .one_or_none()
            )
            if ligne is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            autorise = peut_consulter_l_etat_d_un_media(
                acteur=appelant.personne,
                uploaded_by_person_id=uuid.UUID(str(ligne["uploaded_by_person_id"])),
                roles=frozenset(permissions.roles),
            )
            if not autorise:
                raise ErreurApplicative(
                    code=CODE_PHOTO_HORS_PERIMETRE,
                    message=MESSAGE_PHOTO_HORS_PERIMETRE_DEPOT,
                    statut=status.HTTP_403_FORBIDDEN,
                )
        return EtatDUnMedia(
            id=str(media),
            state=str(ligne["state"]),
            rejection_code=(
                None if ligne["rejection_code"] is None else str(ligne["rejection_code"])
            ),
        )

    @routeur.post(
        GABARIT_AUTORISATION,
        status_code=status.HTTP_201_CREATED,
        response_model=ReponseDAutorisation,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": "Matrice §6.1 « Enregistrer l'autorisation photo »."
            },
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "Meme forme que le depot pour l'appartenance ; "
                    f"`{CODE_MEDIA_INTROUVABLE}` si le media n'existe pas dans cette entite."
                )
            },
            status.HTTP_409_CONFLICT: {
                "description": f"`{CODE_MEDIA_PAS_PRET}` : le media n'est pas encore `ready`."
            },
        },
        summary="Accorder l'autorisation d'affichage d'une photo",
        description=(
            "`MVP-L11-US005`. N'importe quelle autorisation ANTERIEURE reste active : "
            "voir `app.media.autorisation` pour le residu du LOT 5 tranche ici."
        ),
    )
    def accorder_l_autorisation(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite",
            ),
        ],
        appartenance: Annotated[uuid.UUID, Path(description="L'identifiant de l'appartenance")],
        demande: DemandeDAutorisation,
        requete: Request,
        appelant: SessionEtablie = Depends(exiger_une_session(parametres)),  # noqa: B008
    ) -> ReponseDAutorisation:
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
            fiche = lire_la_fiche_arrivee(
                connexion, entite=entite.id, appartenance=appartenance, instant=instant
            )
            if fiche is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            autorise = peut_gerer_l_autorisation_photo(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                cible_appartenance=appartenance,
                cible_personne=fiche.person_id,
                roles=frozenset(permissions.roles),
                instant=instant,
            )
            if not autorise:
                raise ErreurApplicative(
                    code=CODE_PHOTO_HORS_PERIMETRE,
                    message=MESSAGE_PHOTO_HORS_PERIMETRE_AUTORISATION,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            source = (
                SourceAutorisationPhoto.SELF_SERVICE.value
                if appelant.personne == fiche.person_id
                else SourceAutorisationPhoto.ADMIN_SUPPORT.value
            )
            ecrite = accorder_l_autorisation_photo(
                connexion,
                entite=entite.id,
                person_id=fiche.person_id,
                media_asset_id=uuid.UUID(demande.media_asset_id),
                source=source,
                acteur=appelant.personne,
                instant=instant,
            )
        return ReponseDAutorisation(id=str(ecrite.id), granted_at=ecrite.granted_at.isoformat())

    @routeur.post(
        GABARIT_RETRAIT,
        status_code=status.HTTP_200_OK,
        response_model=ReponseDeRetrait,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": "Matrice §6.1 « Retirer l'autorisation photo »."
            },
            status.HTTP_404_NOT_FOUND: {"description": "Meme forme que le depot."},
        },
        summary="Retirer toute autorisation active d'affichage d'une photo",
        description=(
            "`MVP-L11-US005`. Retire TOUTES les lignes actives de la personne, pas "
            "seulement la plus recente — voir `app.media.autorisation`. Idempotent : "
            "`autorisations_retirees` peut valoir `0`, ce n'est pas un refus."
        ),
    )
    def retirer_l_autorisation(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite",
            ),
        ],
        appartenance: Annotated[uuid.UUID, Path(description="L'identifiant de l'appartenance")],
        requete: Request,
        appelant: SessionEtablie = Depends(exiger_une_session(parametres)),  # noqa: B008
    ) -> ReponseDeRetrait:
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
            fiche = lire_la_fiche_arrivee(
                connexion, entite=entite.id, appartenance=appartenance, instant=instant
            )
            if fiche is None:
                raise ErreurApplicative(
                    code=CODE_ENTITE_INTROUVABLE,
                    message=MESSAGE_ENTITE_INTROUVABLE,
                    statut=status.HTTP_404_NOT_FOUND,
                )
            permissions = resoudre_les_permissions(connexion, appelant.personne, entite.id, instant)
            autorise = peut_gerer_l_autorisation_photo(
                connexion,
                entite=entite.id,
                acteur=appelant.personne,
                cible_appartenance=appartenance,
                cible_personne=fiche.person_id,
                roles=frozenset(permissions.roles),
                instant=instant,
            )
            if not autorise:
                raise ErreurApplicative(
                    code=CODE_PHOTO_HORS_PERIMETRE,
                    message=MESSAGE_PHOTO_HORS_PERIMETRE_AUTORISATION,
                    statut=status.HTTP_403_FORBIDDEN,
                )
            nombre = retirer_l_autorisation_photo(
                connexion, person_id=fiche.person_id, acteur=appelant.personne, instant=instant
            )
        return ReponseDeRetrait(autorisations_retirees=nombre)

    return routeur
