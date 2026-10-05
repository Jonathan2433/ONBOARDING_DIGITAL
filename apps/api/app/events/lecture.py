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


# ============================================================================
#
#  LA LECTURE POUR LA GESTION — LOT 8, `T10`
#
#    **UN TROU DEPUIS `T2`, MEME MOTIF QUE `/pages/gestion` AU LOT 6 (`T10`).**
#    `lister_les_evenements`/`_en_evenement` ci-dessus ne servent que
#    `published`/`cancelled` : un evenement en BROUILLON, ou ARCHIVE, n'a
#    jamais ete lisible par aucune route avant celle-ci. Un ecran de gestion
#    doit pourtant retrouver les deux — le premier pour le publier, le second
#    pour le restaurer — et `version`, dont toute ecriture suivante a besoin
#    pour la concurrence optimiste du §18.4, qu'aucune des deux reponses
#    publiques ne porte.
#
# ============================================================================


@dataclasses.dataclass(frozen=True, slots=True)
class EvenementDeGestion:
    """Le sommaire d'un evenement, TOUS ETATS confondus — `T10`."""

    identifiant: uuid.UUID
    titre: str
    etat: str
    commence_le: dt.datetime
    finit_le: dt.datetime
    version: int


_EVENEMENTS_DE_L_ENTITE: Final = text(
    """
    SELECT id, title, state, starts_at, ends_at, version
      FROM event
     WHERE entity_id = :entite
     ORDER BY starts_at DESC, id
    """
)


def lister_les_evenements_pour_gestion(
    connexion: Connection, *, entite: uuid.UUID
) -> tuple[EvenementDeGestion, ...]:
    """Le sommaire de TOUS les evenements de l'entite, tous etats confondus.

    **AUCUNE PORTEE LOCALE N'EST APPLIQUEE ICI**, meme parti que
    `lister_les_pages_de_l_entite` (LOT 6, `T10`) : un Booster voit donc TOUS
    les evenements de son entite, mais ne pourra OUVRIR que le sien — refuse
    en 403 par `lire_un_evenement_pour_gestion`, qui resout le perimetre.
    """
    lignes = connexion.execute(_EVENEMENTS_DE_L_ENTITE, {"entite": entite})
    return tuple(
        EvenementDeGestion(
            identifiant=ligne[0],
            titre=str(ligne[1]),
            etat=str(ligne[2]),
            commence_le=ligne[3],
            finit_le=ligne[4],
            version=int(ligne[5]),
        )
        for ligne in lignes
    )


@dataclasses.dataclass(frozen=True, slots=True)
class MediaDeGestion:
    """Un media rattache, tel que lu pour l'ecran de gestion."""

    media: uuid.UUID
    role: str
    ordre: int


@dataclasses.dataclass(frozen=True, slots=True)
class EvenementPourGestion:
    """Un evenement, TOUS ETATS confondus, avec sa `version` et ses rattachements."""

    identifiant: uuid.UUID
    titre: str
    description: str | None
    commence_le: dt.datetime
    finit_le: dt.datetime
    lieu: str | None
    etat: str
    version: int
    annule_le: dt.datetime | None
    motif_d_annulation: str | None
    archive_le: dt.datetime | None
    cercles: tuple[str, ...]
    bureaux: tuple[str, ...]
    medias: tuple[MediaDeGestion, ...]


_EVENEMENT_POUR_GESTION: Final = text(
    """
    SELECT title, description, starts_at, ends_at, location_text, state, version,
           cancelled_at, cancellation_reason, archived_at
      FROM event
     WHERE id = :evenement AND entity_id = :entite
    """
)

#  Les codes des cercles/bureaux RATTACHES, tries pour un affichage stable.
#  Le rattachement est ce qui peut etre ARCHIVE (`T4`) ; le cercle/bureau CIBLE
#  n'est pas refiltre par son propre `archived_at` — une lecture dit ce qui
#  EST rattache, elle ne presume pas que la cible l'est encore.
_CERCLES_RATTACHES: Final = text(
    """
    SELECT c.code
      FROM event_circle_scope ecs
      JOIN circle c ON c.id = ecs.circle_id AND c.entity_id = ecs.entity_id
     WHERE ecs.event_id = :evenement AND ecs.entity_id = :entite
       AND ecs.archived_at IS NULL
     ORDER BY c.code
    """
)
_BUREAUX_RATTACHES: Final = text(
    """
    SELECT o.code
      FROM event_office_scope eos
      JOIN office o ON o.id = eos.office_id AND o.entity_id = eos.entity_id
     WHERE eos.event_id = :evenement AND eos.entity_id = :entite
       AND eos.archived_at IS NULL
     ORDER BY o.code
    """
)
_MEDIAS_RATTACHES: Final = text(
    """
    SELECT media_asset_id, display_role, display_order
      FROM event_media
     WHERE event_id = :evenement AND entity_id = :entite
       AND archived_at IS NULL
     ORDER BY display_order
    """
)


def lire_un_evenement_pour_gestion(
    connexion: Connection, *, entite: uuid.UUID, evenement: uuid.UUID
) -> EvenementPourGestion | None:
    """Un evenement et ses rattachements, TOUS ETATS confondus, avec sa `version`.

    `None` couvre deux causes, sans les distinguer : l'evenement n'existe pas,
    ou il appartient a une AUTRE entite — la cle composite `(id, entity_id)`
    du §25.3 rend la seconde aussi sure qu'un filtre explicite.
    """
    ligne = connexion.execute(
        _EVENEMENT_POUR_GESTION, {"evenement": evenement, "entite": entite}
    ).one_or_none()
    if ligne is None:
        return None

    parametres = {"evenement": evenement, "entite": entite}
    cercles = tuple(
        str(code) for code in connexion.execute(_CERCLES_RATTACHES, parametres).scalars()
    )
    bureaux = tuple(
        str(code) for code in connexion.execute(_BUREAUX_RATTACHES, parametres).scalars()
    )
    medias = tuple(
        MediaDeGestion(media=m[0], role=str(m[1]), ordre=int(m[2]))
        for m in connexion.execute(_MEDIAS_RATTACHES, parametres)
    )

    return EvenementPourGestion(
        identifiant=evenement,
        titre=str(ligne[0]),
        description=ligne[1],
        commence_le=ligne[2],
        finit_le=ligne[3],
        lieu=ligne[4],
        etat=str(ligne[5]),
        version=int(ligne[6]),
        annule_le=ligne[7],
        motif_d_annulation=ligne[8],
        archive_le=ligne[9],
        cercles=cercles,
        bureaux=bureaux,
        medias=medias,
    )
