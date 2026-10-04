"""`GET /entities/{code}/events` — LOT 8, `T2`, `MVP-L08-US003`.

La matrice §5 et sa section §11 accordent la consultation a chacun des huit
roles authentifies, `EMP` et `NEW` compris. La route exige donc une session
mais ne resout aucun role. Une consultation d'une autre entite reste en lecture
seule, conformement a RIGHTS-003.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from pydantic import BaseModel

from app.auth.dependances import exiger_une_session
from app.entities.routes import (
    CODE_ENTITE_INTROUVABLE,
    LONGUEUR_MAXIMALE_CODE,
    MESSAGE_ENTITE_INTROUVABLE,
)
from app.entities.services import resoudre_une_entite_active
from app.events.lecture import ClassementEvenement, lister_les_evenements
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


def routeur_evenements(parametres: Parametres) -> APIRouter:
    """Routeur de lecture des evenements, monte sous le prefixe versionne."""
    routeur = APIRouter(tags=["evenements"])

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

    return routeur
