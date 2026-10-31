"""Verifier le contenu reel d'une photo et en generer la miniature — `T2`.

Modele §16.1 (« verification du contenu reel obligatoire »), §16.2 (« versions
generees »), `MVP-L11-US005` : « la relance est idempotente ; les variantes
respectent les budgets ; l'original reste protege ».

CE QUE CETTE FONCTION EST APPELEE PAR, ET POURQUOI ELLE N'OUVRE PAS SA PROPRE
TRANSACTION

  Elle est appelee par `app.jobs.outbox._traiter_un_message`, DANS le
  savepoint du relais — exactement comme `app.jobs.email.envoyer_depuis_la_
  charge` l'est pour un e-mail. Elle recoit donc la `Connection` de
  l'appelant et ne committe jamais elle-meme.

POURQUOI PILLOW EST LE VERIFICATEUR DE CONTENU, PAS UNE SECONDE BIBLIOTHEQUE

  « Verification du contenu reel » (§16.1) ne demande pas un antivirus : le mot
  « quarantaine » du titre de `T2` decrit la MACHINE D'ETATS elle-meme — un
  media `pending`/`processing` n'est JAMAIS servi (`resoudre_la_miniature`,
  LOT 5), donc l'isolement est deja structurel avant que cette fonction ne
  tourne. Ce qu'il reste a verifier est plus etroit : le contenu EST-IL
  reellement l'image qu'il pretend etre ? Decoder entierement les octets avec
  Pillow et constater qu'ils forment une image valide dans un format connu
  EST cette verification — un fichier qui n'est pas une image echoue au
  decodage, quel que soit le nom ou le type MIME qu'il a declares.

UN REJET EST UN SUCCES DU JOB, PAS UN ECHEC

  Un contenu illisible ou dans un format non autorise transitionne le media
  vers `rejected` et la fonction REND NORMALEMENT — le job a fait son travail,
  qui etait precisement de trancher. Seule une panne SYSTEME (MinIO
  injoignable, refus d'ecriture) leve `EchecDeTraitement`, pour que `app.jobs.
  execution.terminer_en_echec` reprogramme un nouvel essai : rejouer un rejet
  de contenu ne changerait rien, rejouer une panne transitoire peut reussir.

IDEMPOTENCE A DEUX NIVEAUX, PAS UN SEUL

  Le niveau EXTERIEUR est `commencer_un_essai`/`job_type=MEDIA` : un message
  d'outbox deja traite jusqu'au bout ne relance jamais cette fonction. Le
  niveau INTERIEUR, DANS la fonction, est l'`INSERT ... ON CONFLICT DO
  NOTHING` sur `uq_media_variant_asset_type_non_archive` — le MEME motif que
  `outbox_message.deduplication_key` (`T1`) : si un essai precedent avait deja
  pose la variante puis echoue APRES (par exemple au moment de marquer l'actif
  `ready`), le reessai ne la pose pas deux fois.

LE FORMAT DES VARIANTES EST CHOISI ICI, ET C'EST CE QUE `media/photo.py` (LOT 5)
ANNONCAIT

  « C'est celui qui PRODUIT les variantes qui choisira » (`media/photo.py`,
  `_MIMES`, qui connait deja `jpeg`). JPEG est retenu : compression avec perte
  reglable (necessaire pour tenir sous 100 Ko, `BORNE_MINIATURE_OCTETS`),
  support universel, et `_mime_de` le traduit deja en `image/jpeg`. Une photo
  PNG transparente est applatie sur un fond blanc avant encodage — JPEG ne
  porte pas de canal alpha.

UNE SEULE VARIANTE, LA MINIATURE DE TROMBINOSCOPE — ET LES QUATRE AUTRES NE
SONT PAS CONSTRUITES

  Le §16.2 en nomme cinq, mais `T2` sert « l'ecran de depot de photo de
  profil » (fiche-lot-11.md) : la fiche et le trombinoscope affichent tous
  deux la photo a la MEME taille CSS (`.profil-photo`/`.trombi-photo`,
  5rem x 5rem — chantiers front `S10`/`S11`), et `resoudre_la_miniature`
  (LOT 5) ne sert deja que `thumbnail`. `carte`, `pleine largeur`, `apercu
  video` et `format optimise` n'ont aucun consommateur avant que des medias
  d'un autre domaine (evenements, contenus) ne construisent le leur — les
  construire ici serait une table SANS CONSOMMATEUR, §6.5.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import uuid
from typing import TYPE_CHECKING, Any, Final

from PIL import Image, UnidentifiedImageError
from sqlalchemy import text

from app.configuration.settings import parametres_en_cache
from app.media.modeles import EtatMedia, TypeVarianteMedia
from app.media.objets import ObjetIntrouvable, ObjetNonDepose, deposer_l_objet, lire_l_objet

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

    from app.configuration.settings import Parametres

__all__ = ["EchecDeTraitement", "generer_les_variantes_depuis_la_charge"]

#  §16.2/`media/photo.py` : la variante que la liste et la fiche servent.
VARIANTE_SERVIE: Final[str] = TypeVarianteMedia.MINIATURE_TROMBINOSCOPE.value

#  Cote de la miniature carree, en pixels — trois fois la taille d'affichage
#  CSS (5rem = 80px a 16px/rem) pour rester nette sur un ecran « retina »,
#  sans faire exploser le budget de taille.
COTE_DE_LA_MINIATURE_PIXELS: Final[int] = 240

#  Meme valeur que `media/photo.py::BORNE_MINIATURE_OCTETS` et la migration
#  `0016` : UNE SEULE SOURCE, confrontee par un test (§7.27).
BORNE_MINIATURE_OCTETS: Final[int] = 100_000

#  Qualites JPEG essayees dans l'ordre, jusqu'a tenir sous la borne. La
#  derniere est conservee meme si elle la depasse encore : a 240x240, aucune
#  photo reelle ne l'exige, et un octet servi vaut mieux qu'un echec (§7.0).
QUALITES_JPEG_DECROISSANTES: Final[tuple[int, ...]] = (85, 75, 65, 55, 45, 35, 25)

#  Les SEULS formats que cette fonction accepte en sortie du decodage Pillow.
#  Une liste blanche, pas une liste des formats dangereux a exclure : le §7.46
#  de la passation l'a appris pour les URL, et la meme regle vaut pour les
#  octets — enumerer ce qu'on REFUSE vieillirait a la premiere extension Pillow.
FORMATS_DECODES_AUTORISES: Final[frozenset[str]] = frozenset({"jpeg", "png", "webp"})

CODE_CONTENU_ILLISIBLE: Final = "contenu_illisible"
CODE_FORMAT_NON_AUTORISE: Final = "format_non_autorise"


class EchecDeTraitement(RuntimeError):
    """Une panne SYSTEME — MinIO illisible ou non ecrivable — jamais un rejet de contenu."""


_LIGNE_DU_MEDIA: Final = text(
    "SELECT id, entity_id, state, object_key FROM media_asset WHERE id = :id FOR UPDATE"
)

_REJETER: Final = text(
    "UPDATE media_asset SET state = :etat, rejection_code = :code, updated_at = :instant "
    "WHERE id = :id"
)

_ACCEPTER: Final = text(
    "UPDATE media_asset SET state = :etat, mime_detected = :mime, width = :largeur, "
    "height = :hauteur, ready_at = :instant, updated_at = :instant WHERE id = :id"
)

_POSER_LA_VARIANTE: Final = text(
    "INSERT INTO media_variant "
    "(media_asset_id, entity_id, variant_type, width, height, variant_format, "
    " size_bytes, checksum_sha256, object_key, created_at, updated_at) "
    "VALUES "
    "(:media, :entite, :variante, :largeur, :hauteur, :format, :taille, :empreinte, "
    " :cle, :instant, :instant) "
    "ON CONFLICT (media_asset_id, variant_type) WHERE archived_at IS NULL DO NOTHING"
)


def _aplatir_sur_fond_blanc(image: Image.Image) -> Image.Image:
    """Une image avec canal alpha, posee sur un fond blanc — JPEG n'a pas d'alpha."""
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        image_rgba = image.convert("RGBA")
        fond = Image.new("RGB", image_rgba.size, (255, 255, 255))
        fond.paste(image_rgba, mask=image_rgba.split()[-1])
        return fond
    return image.convert("RGB")


def _recadrer_en_carre(image: Image.Image) -> Image.Image:
    """Un carre centre, cote le plus petit des deux — jamais de deformation."""
    largeur, hauteur = image.size
    cote = min(largeur, hauteur)
    gauche = (largeur - cote) // 2
    haut = (hauteur - cote) // 2
    return image.crop((gauche, haut, gauche + cote, haut + cote))


def _encoder_sous_la_borne(image: Image.Image) -> bytes:
    """Les octets JPEG les plus proches de la qualite maximale sous la borne."""
    derniers_octets = b""
    for qualite in QUALITES_JPEG_DECROISSANTES:
        tampon = io.BytesIO()
        image.save(tampon, format="JPEG", quality=qualite, optimize=True)
        derniers_octets = tampon.getvalue()
        if len(derniers_octets) <= BORNE_MINIATURE_OCTETS:
            return derniers_octets
    return derniers_octets


def generer_les_variantes_depuis_la_charge(
    connexion: Connection,
    payload: dict[str, Any],
    *,
    instant: dt.datetime,
    parametres: Parametres | None = None,
) -> None:
    """Traiter le media decrit par la charge d'un `outbox_message(topic='media')`.

    Lit l'actif SOUS VERROU (`FOR UPDATE`, deja dans le savepoint de
    l'appelant), decode ses octets, et transitionne vers `ready` (avec sa
    miniature) ou `rejected` (avec un `rejection_code`). Un actif qui n'est
    plus `pending` (deja traite par un essai anterieur rattrape par ce
    reessai) ne fait RIEN — l'idempotence exterieure l'a deja decide.

    `parametres` resolu par `parametres_en_cache()` si omis — meme patron que
    `app.jobs.email.obtenir_le_fournisseur` : l'appelant du relais (le worker)
    n'a pas a connaitre la configuration MinIO pour appeler cette fonction.
    """
    parametres_effectifs = parametres if parametres is not None else parametres_en_cache()
    media_id = uuid.UUID(str(payload["media_asset_id"]))
    ligne = connexion.execute(_LIGNE_DU_MEDIA, {"id": media_id}).mappings().one_or_none()
    if ligne is None or str(ligne["state"]) != EtatMedia.PENDING.value:
        return

    try:
        contenu = lire_l_objet(parametres_effectifs, str(ligne["object_key"]))
    except ObjetIntrouvable as erreur:
        raise EchecDeTraitement("original illisible") from erreur

    try:
        image = Image.open(io.BytesIO(contenu))
        image.load()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        connexion.execute(
            _REJETER,
            {
                "etat": EtatMedia.REJECTED.value,
                "code": CODE_CONTENU_ILLISIBLE,
                "instant": instant,
                "id": media_id,
            },
        )
        return

    format_detecte = (image.format or "").lower()
    if format_detecte not in FORMATS_DECODES_AUTORISES:
        connexion.execute(
            _REJETER,
            {
                "etat": EtatMedia.REJECTED.value,
                "code": CODE_FORMAT_NON_AUTORISE,
                "instant": instant,
                "id": media_id,
            },
        )
        return

    miniature = _recadrer_en_carre(_aplatir_sur_fond_blanc(image))
    miniature = miniature.resize(
        (COTE_DE_LA_MINIATURE_PIXELS, COTE_DE_LA_MINIATURE_PIXELS), Image.Resampling.LANCZOS
    )
    octets_variante = _encoder_sous_la_borne(miniature)
    empreinte_variante = hashlib.sha256(octets_variante).hexdigest()
    cle_variante = f"media/{ligne['entity_id']}/{media_id}/{VARIANTE_SERVIE}.jpg"

    try:
        deposer_l_objet(parametres_effectifs, cle_variante, octets_variante)
    except ObjetNonDepose as erreur:
        raise EchecDeTraitement("variante non deposee") from erreur

    connexion.execute(
        _POSER_LA_VARIANTE,
        {
            "media": media_id,
            "entite": ligne["entity_id"],
            "variante": VARIANTE_SERVIE,
            "largeur": COTE_DE_LA_MINIATURE_PIXELS,
            "hauteur": COTE_DE_LA_MINIATURE_PIXELS,
            "format": "jpeg",
            "taille": len(octets_variante),
            "empreinte": empreinte_variante,
            "cle": cle_variante,
            "instant": instant,
        },
    )
    connexion.execute(
        _ACCEPTER,
        {
            "etat": EtatMedia.READY.value,
            "mime": f"image/{format_detecte}",
            "largeur": image.width,
            "hauteur": image.height,
            "instant": instant,
            "id": media_id,
        },
    )
