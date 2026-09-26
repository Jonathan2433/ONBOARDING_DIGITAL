"""Les routes de l'onboarding — LOT 7, `T2` : la fiche d'arrivee en lecture.

Montee sous `/entities/{code}/people/{appartenance}/arrival-profile`, a cote
des routes de `app.people.routes` dont elle reutilise la resolution d'entite
et le gabarit de 404 unique — un chemin distinct pour « code d'entite inconnu »
apprendrait qu'une appartenance existe, l'exact defaut que ce projet refuse
depuis le LOT 4.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Final

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel

from app.auth.dependances import SessionEtablie, exiger_une_session
from app.configuration.settings import Parametres
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import resoudre_une_entite_active
from app.onboarding.fiche_arrivee import FicheArrivee, lire_la_fiche_arrivee
from app.onboarding.perimetre import peut_lire_la_fiche_arrivee
from app.permissions.services import resoudre_les_permissions
from app.shared.database import moteur
from app.shared.errors import ErreurApplicative

CODE_FICHE_HORS_PERIMETRE: Final = "fiche_arrivee_hors_perimetre"
MESSAGE_FICHE_HORS_PERIMETRE: Final = "Votre perimetre ne vous permet pas de consulter cette fiche."


class CercleDeLaFicheArrivee(BaseModel):
    """Le cercle principal, s'il existe — §10.2, reutilise depuis `T2`."""

    code: str
    nom: str
    jeton_de_couleur: str | None


class FicheDArrivee(BaseModel):
    """La fiche d'arrivee — modele §12.1, donnees organisationnelles du §10.2.

    `id` et `version` valent `None` tant qu'aucune ligne `arrival_profile`
    n'existe : c'est `T3` qui la cree. Un client qui les recoit nuls sait qu'il
    doit CREER, pas mettre a jour.
    """

    id: uuid.UUID | None
    version: int | None
    state: str
    entity_membership_id: uuid.UUID
    person_id: uuid.UUID
    first_name: str
    last_name: str
    preferred_name: str | None
    arrival_date: dt.date
    metier: str | None
    statut: str | None
    client: str | None
    dsm: str | None
    cercle_principal: CercleDeLaFicheArrivee | None
    short_intro: str | None
    fun_fact: str | None
    validated_at: dt.datetime | None
    published_at: dt.datetime | None
    recent_until: dt.date | None


def _en_reponse(fiche: FicheArrivee) -> FicheDArrivee:
    return FicheDArrivee(
        id=fiche.id,
        version=fiche.version,
        state=fiche.state,
        entity_membership_id=fiche.entity_membership_id,
        person_id=fiche.person_id,
        first_name=fiche.first_name,
        last_name=fiche.last_name,
        preferred_name=fiche.preferred_name,
        arrival_date=fiche.arrival_date,
        metier=fiche.metier,
        statut=fiche.statut,
        client=fiche.client,
        dsm=fiche.dsm,
        cercle_principal=(
            None
            if fiche.cercle_principal is None
            else CercleDeLaFicheArrivee(
                code=fiche.cercle_principal.code,
                nom=fiche.cercle_principal.nom,
                jeton_de_couleur=fiche.cercle_principal.jeton_de_couleur,
            )
        ),
        short_intro=fiche.short_intro,
        fun_fact=fiche.fun_fact,
        validated_at=fiche.validated_at,
        published_at=fiche.published_at,
        recent_until=fiche.recent_until,
    )


def routeur_onboarding(parametres: Parametres) -> APIRouter:
    """Routeur de l'onboarding, monte sous le prefixe versionne."""
    routeur = APIRouter(tags=["onboarding"])

    @routeur.get(
        "/entities/{code}/people/{appartenance}/arrival-profile",
        status_code=status.HTTP_200_OK,
        response_model=FicheDArrivee,
        responses={
            status.HTTP_401_UNAUTHORIZED: {"description": "Aucune session valide."},
            status.HTTP_403_FORBIDDEN: {
                "description": (
                    "Le perimetre de lecture du §7 ne couvre pas cette fiche : ni "
                    "SOI, ni ESM/ADM-E/SUPER dans l'entite, ni Booster du cercle "
                    "de la cible. `DSM` est a TIRET sur CETTE ligne du §7, malgre "
                    "« Consultants » ailleurs dans la matrice."
                )
            },
            status.HTTP_404_NOT_FOUND: {
                "description": (
                    "UNE SEULE forme pour trois causes : code d'entite inconnu, "
                    "appartenance inconnue ou d'une AUTRE entite, ou appartenance "
                    "ni FUTURE ni ACTIVE."
                )
            },
        },
        summary="Consulter la fiche d'arrivee d'un collaborateur",
        description=(
            "Donnees organisationnelles preremplies — arrivee, metier, statut, DSM, "
            "client, cercle principal, cahier §9.4 — et champs propres a la fiche "
            "— etat, presentation, fun fact, modele §12.1. Aucune ligne "
            "`arrival_profile` n'est creee par cette lecture : `id`/`version` "
            "valent `null` tant qu'elle n'existe pas."
        ),
    )
    def lire_la_fiche(
        code: Annotated[
            str,
            Path(
                min_length=1,
                max_length=LONGUEUR_MAXIMALE_CODE,
                description="Le `code` de l'entite, unique et jamais reattribue",
            ),
        ],
        appartenance: Annotated[uuid.UUID, Path(description="L'identifiant de l'appartenance")],
        appelant: SessionEtablie = Depends(exiger_une_session(parametres)),  # noqa: B008
    ) -> FicheDArrivee:
        """Consulter la fiche d'arrivee — cahier §9.4, modele §12.1."""
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
            autorise = peut_lire_la_fiche_arrivee(
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
                    code=CODE_FICHE_HORS_PERIMETRE,
                    message=MESSAGE_FICHE_HORS_PERIMETRE,
                    statut=status.HTTP_403_FORBIDDEN,
                )
        return _en_reponse(fiche)

    return routeur
