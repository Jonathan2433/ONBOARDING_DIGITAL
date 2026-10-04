"""Lecture paginee des evenements — LOT 8, `T2`, `MVP-L08-US003`.

La frontiere est unique : un evenement est passe si ``ends_at <= instant`` et
reste a venir tant que ``ends_at > instant``. L'instant est fourni par
l'appelant et reutilise pour le total et la page ; aucun ``now()`` cache dans
le SQL ne peut donc classer differemment les deux requetes.

La consultation de la matrice §11 est accordee a tous les roles authentifies,
sans restriction de cercle ou de bureau. Les portees servent aux gestes de
gestion des sous-etapes suivantes, pas a retirer a un employe la lecture
generale que le tableau lui accorde explicitement.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import enum
import uuid
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.shared.pagination import TAILLES_DE_PAGE


class ClassementEvenement(enum.StrEnum):
    """Les deux onglets du cahier §10.6, jamais des etats stockes."""

    A_VENIR = "a_venir"
    PASSES = "passes"


@dataclasses.dataclass(frozen=True, slots=True)
class EvenementLu:
    """Les donnees publiquement consultables d'un evenement simple du MVP."""

    id: uuid.UUID
    title: str
    description: str | None
    starts_at: dt.datetime
    ends_at: dt.datetime
    location_text: str | None
    state: str
    cancelled_at: dt.datetime | None
    cancellation_reason: str | None


@dataclasses.dataclass(frozen=True, slots=True)
class PageDEvenements:
    """Une page et le total de la population correspondant au classement."""

    evenements: list[EvenementLu]
    total: int


_FILTRE_TEMPOREL: Final[dict[ClassementEvenement, str]] = {
    ClassementEvenement.A_VENIR: "e.ends_at > :instant",
    ClassementEvenement.PASSES: "e.ends_at <= :instant",
}

_ORDRE: Final[dict[ClassementEvenement, str]] = {
    ClassementEvenement.A_VENIR: "e.starts_at ASC, e.id ASC",
    ClassementEvenement.PASSES: "e.ends_at DESC, e.id DESC",
}


def lister_les_evenements(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    classement: ClassementEvenement,
    page: int,
    taille: int,
    instant: dt.datetime,
) -> PageDEvenements:
    """Lire une page d'evenements visibles de part ou d'autre de ``ends_at``.

    ``draft`` n'est pas public et ``archived`` disparait de la consultation.
    ``cancelled`` reste volontairement dans la meme population que
    ``published`` : son etat permet au client d'afficher le badge exige.
    """
    if page < 1:
        message = f"page doit valoir au moins 1, recu {page}"
        raise ValueError(message)
    if taille not in TAILLES_DE_PAGE:
        message = f"taille doit etre l'une de {TAILLES_DE_PAGE}, recu {taille}"
        raise ValueError(message)

    filtre = _FILTRE_TEMPOREL[classement]
    source = (
        "FROM event e WHERE e.entity_id = :entite "
        "AND e.archived_at IS NULL "
        "AND e.state IN ('published', 'cancelled') "
        f"AND {filtre}"
    )
    parametres: dict[str, object] = {"entite": entite, "instant": instant}
    total = int(connexion.execute(text(f"SELECT count(*) {source}"), parametres).scalar_one())

    lignes = (
        connexion.execute(
            text(
                "SELECT e.id, e.title, e.description, e.starts_at, e.ends_at, "
                "e.location_text, e.state, e.cancelled_at, e.cancellation_reason "
                f"{source} ORDER BY {_ORDRE[classement]} "
                "LIMIT :taille OFFSET :decalage"
            ),
            {**parametres, "taille": taille, "decalage": (page - 1) * taille},
        )
        .mappings()
        .all()
    )
    return PageDEvenements(evenements=[_en_evenement(ligne) for ligne in lignes], total=total)


def _en_evenement(ligne: Any) -> EvenementLu:
    return EvenementLu(
        id=ligne["id"],
        title=ligne["title"],
        description=ligne["description"],
        starts_at=ligne["starts_at"],
        ends_at=ligne["ends_at"],
        location_text=ligne["location_text"],
        state=ligne["state"],
        cancelled_at=ligne["cancelled_at"],
        cancellation_reason=ligne["cancellation_reason"],
    )
