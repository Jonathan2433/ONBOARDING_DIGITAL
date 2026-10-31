"""Deposer une photo en quarantaine — modele §16.1, `T2`, `MVP-L11-US004`.

LA BORNE DE 10 Mo EST ICI, PAS EN BASE

  `media_asset.modeles` le dit en toutes lettres : une photo EST une image,
  et la base ne peut exprimer que la borne par `media_type` (20 Mo). La borne
  de 10 Mo propre a l'USAGE « photo de profil » est donc appliquee ici, AVANT
  toute ecriture — refuser une photo de 15 Mo APRES l'avoir deposee dans
  MinIO gaspillerait un depot que la contrainte DB aurait accepte.

LA VERIFICATION DU CONTENU REEL N'EST PAS ICI, ET C'EST ECRIT EN TOUTES LETTRES
AU MODELE

  « Verification du contenu reel obligatoire » (§16.1) est « le worker qui
  compare `mime_declared` a `mime_detected` » (modeles.py). Cette fonction ne
  fait donc qu'un filtre DECLARATIF et bon marche — le type MIME envoye par le
  navigateur doit ressembler a une image — avant de mettre en quarantaine.
  Un fichier malveillant qui mentirait sur son type MIME n'est PAS arrete ici :
  il l'est par `app.media.traitement`, qui decode reellement les octets.

L'ECRITURE SUIT L'ORDRE DEJA ETABLI PAR `app.imports.depot` (LOT 9, `T6`)

  Nettoyer le nom, refuser une taille ou un type manifestement invalides,
  calculer l'empreinte, PUIS inserer la ligne metier, PUIS deposer dans MinIO,
  PUIS publier dans l'outbox — toujours dans la MEME transaction. Un echec de
  depot MinIO annule tout, y compris la ligne `media_asset` : aucun octet
  orphelin, aucune ligne sans objet.

  **LA CLE D'OBJET EST DERIVEE DE L'IDENTIFIANT DE LA LIGNE, JAMAIS DU NOM
  SOUMIS** — §16.1, « aucun `object_key` fourni par le client ». Meme
  discipline que `imports/{entite}/{lot}.csv` : `media/{entite}/{media}/original`.

LA MISE EN FILE EST PUBLIEE DANS L'OUTBOX, PAS ENVOYEE DIRECTEMENT

  `publier_dans_l_outbox` (LOT 11, `T1`) ecrit le message `topic="media"` DANS
  LA MEME TRANSACTION que `media_asset` : si la transaction echoue, aucune
  tache n'est jamais declenchee pour un media qui n'existe pas. C'est la ROUTE
  qui, APRES commit, reveille le relais — meme discipline que `BackgroundTasks`
  pour un magic link (LOT 3) ou pour `relayer_l_outbox` lui-meme (`T1`).
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import uuid
from typing import TYPE_CHECKING, Final

from fastapi import status
from sqlalchemy import text

from app.jobs.outbox import TOPIC_MEDIA, publier_dans_l_outbox
from app.media.modeles import EtatMedia, TypeMedia
from app.media.objets import deposer_l_objet
from app.shared.errors import ErreurApplicative

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

    from app.configuration.settings import Parametres

#  Cahier §16.1 : « photo 10 Mo maximum » — plus stricte que la borne par
#  `media_type` (20 Mo) posee en base, voir l'en-tete.
TAILLE_MAXIMALE_PHOTO_OCTETS: Final[int] = 10 * 1024 * 1024

#  Filtre DECLARATIF seulement — voir l'en-tete. `image/jpg` n'est pas un type
#  MIME standard mais certains navigateurs l'envoient encore ; l'accepter ici
#  ne change rien a la verification reelle du worker.
TYPES_DECLARES_AUTORISES: Final[frozenset[str]] = frozenset(
    {"image/jpeg", "image/jpg", "image/png", "image/webp"}
)

CODE_FICHIER_VIDE: Final = "fichier_vide"
MESSAGE_FICHIER_VIDE: Final = "Le fichier envoye est vide."

CODE_NOM_DE_FICHIER_INVALIDE: Final = "nom_de_fichier_invalide"
MESSAGE_NOM_DE_FICHIER_INVALIDE: Final = "Le nom du fichier est vide une fois nettoye."

CODE_FICHIER_TROP_LOURD: Final = "fichier_trop_lourd"
MESSAGE_FICHIER_TROP_LOURD: Final = "Une photo de profil ne peut pas depasser 10 Mo."

CODE_TYPE_DECLARE_REFUSE: Final = "type_declare_refuse"
MESSAGE_TYPE_DECLARE_REFUSE: Final = (
    "Seules les images JPEG, PNG ou WebP sont acceptees pour une photo de profil."
)


@dataclasses.dataclass(frozen=True, slots=True)
class MediaDepose:
    """Ce que `deposer_une_photo` rend — l'identifiant a suivre en quarantaine."""

    id: uuid.UUID
    state: str


_INSERER: Final = text(
    "INSERT INTO media_asset "
    "(entity_id, uploaded_by_person_id, state, media_type, original_filename, "
    " object_key, mime_declared, size_bytes, checksum_sha256, "
    " created_by_person_id, created_at, updated_at) "
    "VALUES "
    "(:entite, :acteur, :etat, :type_media, :nom, '', :mime, :taille, :empreinte, "
    " :acteur, :instant, :instant) "
    "RETURNING id, state"
)

_POSER_LA_CLE: Final = text(
    "UPDATE media_asset SET object_key = :cle, updated_at = :instant WHERE id = :id"
)


def _nettoyer_le_nom_de_fichier(nom: str) -> str:
    """Le nom nettoye — recopie de `app.imports.depot`, motif prive, §7.27."""
    return nom.replace("\\", "/").rsplit("/", maxsplit=1)[-1].strip()


def deposer_une_photo(
    connexion: Connection,
    parametres: Parametres,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    nom_de_fichier: str,
    content_type: str | None,
    contenu: bytes,
    instant: dt.datetime,
) -> MediaDepose:
    """Deposer une photo en quarantaine (`state='pending'`) et programmer son analyse.

    Leve `ErreurApplicative` (`422`) : fichier vide, nom vide une fois nettoye,
    taille superieure a 10 Mo, type declare hors JPEG/PNG/WebP.
    """
    nom_nettoye = _nettoyer_le_nom_de_fichier(nom_de_fichier)
    if not nom_nettoye:
        raise ErreurApplicative(
            code=CODE_NOM_DE_FICHIER_INVALIDE,
            message=MESSAGE_NOM_DE_FICHIER_INVALIDE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    if len(contenu) == 0:
        raise ErreurApplicative(
            code=CODE_FICHIER_VIDE,
            message=MESSAGE_FICHIER_VIDE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    if len(contenu) > TAILLE_MAXIMALE_PHOTO_OCTETS:
        raise ErreurApplicative(
            code=CODE_FICHIER_TROP_LOURD,
            message=MESSAGE_FICHIER_TROP_LOURD,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    type_declare = (content_type or "").strip().lower()
    if type_declare not in TYPES_DECLARES_AUTORISES:
        raise ErreurApplicative(
            code=CODE_TYPE_DECLARE_REFUSE,
            message=MESSAGE_TYPE_DECLARE_REFUSE,
            statut=status.HTTP_422_UNPROCESSABLE_CONTENT,
            champ="fichier",
        )

    empreinte = hashlib.sha256(contenu).hexdigest()

    creee = connexion.execute(
        _INSERER,
        {
            "entite": entite,
            "acteur": acteur,
            "etat": EtatMedia.PENDING.value,
            "type_media": TypeMedia.IMAGE.value,
            "nom": nom_nettoye,
            "mime": type_declare,
            "taille": len(contenu),
            "empreinte": empreinte,
            "instant": instant,
        },
    ).one()
    media_id = uuid.UUID(str(creee.id))

    #  La cle n'est connue qu'une fois l'identifiant genere — §16.1, jamais
    #  fournie par le client.
    cle = f"media/{entite}/{media_id}/original"
    deposer_l_objet(parametres, cle, contenu)
    connexion.execute(_POSER_LA_CLE, {"cle": cle, "instant": instant, "id": media_id})

    publier_dans_l_outbox(
        connexion,
        topic=TOPIC_MEDIA,
        payload={"media_asset_id": str(media_id)},
        instant=instant,
        deduplication_key=f"media:{media_id}",
    )

    return MediaDepose(id=media_id, state=str(creee.state))
