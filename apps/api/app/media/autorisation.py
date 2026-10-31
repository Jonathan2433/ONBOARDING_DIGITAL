"""Accorder et retirer l'autorisation photo — modele §12.2, `T2`, `MVP-L11-US005`.

LE RESIDU DU LOT 5 EST TRANCHE ICI : DEUX AUTORISATIONS ACTIVES NE SE
REMPLACENT PAS, ELLES COEXISTENT

  `app/media/modeles.py` (LOT 5, `T1`) notait : « le service devra dire ce
  qu'il fait de deux autorisations actives, et si le corpus reste muet, ouvrir
  une question au registre ». Le corpus reste muet — ni le §12.2, ni le §25.1,
  ni le §25.4 n'ecrivent d'unicite — et `resoudre_la_miniature` (LOT 5, `T5`)
  a deja fige la lecture : `ORDER BY granted_at DESC, v.id LIMIT 1`, parce que
  « plusieurs lignes actives restent possibles, et toutes sont actives au sens
  du §12.2 ».

  **`accorder_l_autorisation_photo` NE RETIRE DONC JAMAIS UNE AUTORISATION
  ANTERIEURE.** Chaque action fait EXACTEMENT ce que son nom dit — « Enregistrer
  l'autorisation » et « Retirer l'autorisation » sont deux lignes SEPAREES de
  la matrice §6.1, avec des grilles de permission distinctes — et ajouter un
  effet de bord a l'une (retirer les autres pendant qu'on en accorde une
  nouvelle) serait une regle que ni le modele ni la matrice n'ecrivent. La
  photo la plus RECEMMENT autorisee est servie — c'est deja le comportement
  de `resoudre_la_miniature` — sans qu'aucune ligne anterieure n'ait besoin
  d'etre touchee.

  Consequence directe : accorder une autorisation sur UN NOUVEAU media
  deplace silencieusement la photo servie, sans qu'aucune ligne existante ne
  bouge. Retirer EXPLICITEMENT reste la seule facon de revenir a l'avatar
  neutre — exactement ce que la ligne « Retirer l'autorisation photo »
  decrit.

POURQUOI `retirer_l_autorisation_photo` RETIRE TOUTES LES LIGNES ACTIVES, ET
NON UNE SEULE

  Puisque plusieurs lignes peuvent etre actives a la fois (ci-dessus), et que
  la matrice ne nomme qu'UNE action « Retirer l'autorisation » — jamais
  « retirer LA PLUS RECENTE » —, retirer doit couvrir l'ETAT « autorisation
  active », pas une ligne precise. Sans cela, une ligne ancienne oubliee
  resterait active et pourrait redevenir la plus recente si celle qui la
  recouvrait etait un jour archivee.

UN MEDIA DOIT ETRE `ready` AVANT D'ETRE AUTORISE

  Rien dans le modele ne l'ecrit explicitement, mais `resoudre_la_miniature`
  exige deja `state = 'ready'` ET une variante `thumbnail` existante : accorder
  une autorisation sur un media encore `pending`/`processing` ne changerait
  rien a l'affichage avant que le traitement ne termine, et accorder sur un
  media `rejected` ne produirait jamais d'affichage. Le refuser ICI, en
  `409`, dit la vraie cause plutot que de laisser l'appelant deviner pourquoi
  la photo n'apparait jamais.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import TYPE_CHECKING, Final

from fastapi import status
from sqlalchemy import text

from app.media.modeles import EtatMedia
from app.shared.errors import ErreurApplicative

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

CODE_MEDIA_INTROUVABLE: Final = "media_introuvable"
MESSAGE_MEDIA_INTROUVABLE: Final = "Ce media n'existe pas, ou appartient a une autre entite."

CODE_MEDIA_PAS_PRET: Final = "media_pas_pret"
MESSAGE_MEDIA_PAS_PRET: Final = (
    "Ce media n'est pas encore pret — attendez la fin de son traitement avant de l'autoriser."
)


@dataclasses.dataclass(frozen=True, slots=True)
class AutorisationEcrite:
    """Ce que `accorder_l_autorisation_photo` rend."""

    id: uuid.UUID
    granted_at: dt.datetime


_MEDIA_PRET: Final = text(
    "SELECT 1 FROM media_asset WHERE id = :media AND entity_id = :entite AND state = :etat"
)

_ACCORDER: Final = text(
    "INSERT INTO photo_authorization "
    "(person_id, media_asset_id, granted_at, source, created_by_person_id, "
    " created_at, updated_at) "
    "VALUES (:personne, :media, :instant, :source, :acteur, :instant, :instant) "
    "RETURNING id, granted_at"
)

_RETIRER: Final = text(
    "UPDATE photo_authorization SET "
    "withdrawn_at = :instant, updated_at = :instant, updated_by_person_id = :acteur, "
    "version = version + 1 "
    "WHERE person_id = :personne AND withdrawn_at IS NULL"
)


def accorder_l_autorisation_photo(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    person_id: uuid.UUID,
    media_asset_id: uuid.UUID,
    source: str,
    acteur: uuid.UUID,
    instant: dt.datetime,
) -> AutorisationEcrite:
    """Enregistrer une autorisation — matrice §6.1 « Enregistrer l'autorisation photo ».

    Leve `ErreurApplicative` : `404` media introuvable ou d'une autre entite,
    `409` media pas encore `ready`.
    """
    pret = connexion.execute(
        _MEDIA_PRET, {"media": media_asset_id, "entite": entite, "etat": EtatMedia.READY.value}
    ).first()
    if pret is None:
        existe = connexion.execute(
            text("SELECT 1 FROM media_asset WHERE id = :media AND entity_id = :entite"),
            {"media": media_asset_id, "entite": entite},
        ).first()
        if existe is None:
            raise ErreurApplicative(
                code=CODE_MEDIA_INTROUVABLE,
                message=MESSAGE_MEDIA_INTROUVABLE,
                statut=status.HTTP_404_NOT_FOUND,
            )
        raise ErreurApplicative(
            code=CODE_MEDIA_PAS_PRET,
            message=MESSAGE_MEDIA_PAS_PRET,
            statut=status.HTTP_409_CONFLICT,
        )

    creee = connexion.execute(
        _ACCORDER,
        {
            "personne": person_id,
            "media": media_asset_id,
            "instant": instant,
            "source": source,
            "acteur": acteur,
        },
    ).one()
    return AutorisationEcrite(id=uuid.UUID(str(creee.id)), granted_at=creee.granted_at)


def retirer_l_autorisation_photo(
    connexion: Connection, *, person_id: uuid.UUID, acteur: uuid.UUID, instant: dt.datetime
) -> int:
    """Retirer TOUTES les autorisations actives de la personne — voir l'en-tete.

    Rend le nombre de lignes retirees. `0` n'est pas une erreur : retirer une
    autorisation deja retiree (ou jamais accordee) est sans effet, pas refuse
    — meme discipline idempotente que le reste du projet.
    """
    resultat = connexion.execute(
        _RETIRER, {"instant": instant, "acteur": acteur, "personne": person_id}
    )
    return resultat.rowcount
