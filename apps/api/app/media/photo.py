"""La photo de profil : autorisation, miniature, et jamais l'original.

LOT 5, sous-etape `T5`, story `MVP-L05-US005`.

CE QUE CETTE SOUS-ETAPE FAIT, ET CE QU'ELLE NE FAIT PAS

  `MVP-L05-US005` dit : « **Sans autorisation, avatar neutre ; retrait possible ;
  la photo originale n'est pas servie dans la liste.** » Trois obligations, et
  aucune ne parle de FABRIQUER une miniature.

  **La generation appartient au LOT 11**, et le cahier le dit en propre :
  `MVP-L11-US005`, « Generer miniatures et variantes sans doublon », dans « Medias,
  worker et taches planifiees ». Mesure du 06/09/2026 : **aucune bibliotheque de
  traitement d'image n'est installee**, zero occurrence de `pillow` ou `vips`.

  Ecrire ici un generateur enfreindrait la regle 1 -- un lot a la fois. `T5`
  **selectionne** donc la variante et la **sert**, et la borne de taille est posee
  en base, ou elle attend le producteur du LOT 11 (migration `0016`).

  **ET LE FORMAT DES VARIANTES RESTE NON TRANCHE, VOLONTAIREMENT.** `T1` avait
  laisse `FORMATS_VARIANTE` vide en notant que `T5` devait « decider et mesurer ».
  La reponse est qu'il ne lui appartient pas : c'est celui qui PRODUIT les
  variantes qui choisit leur format, donc le LOT 11. Une liste blanche inventee
  ici bloquerait ce lot -- §6.5.

`T5` ET `T6` SONT FUSIONNEES, ET C'EST UN ARBITRAGE

  La fiche decoupait `US005` en deux : `T5` les miniatures, `T6` l'autorisation.
  Les deux moities ne tiennent pas debout separement -- on ne peut pas prouver
  « sans autorisation, avatar neutre » sans servir quelque chose, et servir une
  photo sans verifier l'autorisation enfreindrait le §12.2. Un critere « l'original
  n'est jamais servi » serait d'ailleurs satisfait par une route qui ne sert RIEN,
  ce qui est le defaut du §7.0.

  Arbitrage de Jonathan du 06/09/2026 : **une seule sous-etape**, et le lot passe
  a onze. `DEC-564`.

LES QUATRE CONDITIONS, ET D'OU CHACUNE VIENT

  Une photo n'est servie que si les quatre sont reunies. Chacune a son test de
  refus **et** son temoin -- sans quoi une requete qui ne rend jamais rien les
  satisferait toutes.

    autorisation ACTIVE       §12.2 : « une photo ne peut etre utilisee
                              publiquement sans autorisation active ». Active =
                              `granted_at` atteint ET `withdrawn_at` nul.
                              **`withdrawn_at IS NULL` NE SUFFIT PAS SEUL** : une
                              autorisation datee du futur a elle aussi un retrait
                              nul, et la lecon est celle du §7.38 sur les periodes
    media `ready`             §16.1 : « seuls les medias `ready` peuvent etre
                              affiches ». Les cinq autres etats -- dont `rejected`
                              et `quarantined` -- ne sont pas affichables
    meme ENTITE               §25.3 : l'actif porte un `entity_id`, et une photo
                              d'une autre entite ne doit pas apparaitre ici
    variante `thumbnail`      §16.2 et §25.3 : c'est la « miniature
                              trombinoscope », et c'est la SEULE que la liste
                              sert. L'original a son propre `object_key`, qui
                              **n'est jamais rendu**

L'ORIGINAL N'EST JAMAIS SERVI, ET C'EST STRUCTUREL

  Cette fonction ne lit **pas** `media_asset.object_key`. Elle ne le selectionne
  pas, donc elle ne peut pas le rendre par erreur : le perdre exigerait de
  reecrire la requete, pas d'oublier un filtre. C'est le §7.35 -- rendre la
  propriete structurelle plutot que de renforcer un controle.

  Un test le confirme par l'autre bout : **aucune reponse d'aucune route** ne
  contient la valeur de `media_asset.object_key`.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import uuid
from typing import TYPE_CHECKING, Final

from sqlalchemy import text

from app.media.modeles import EtatMedia, TypeVarianteMedia
from app.people.modeles import ETAT_LISTE, VISIBILITE_LISTEE

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.engine import Connection

#  Cahier §25.3, en octets, et **une seule source** : la migration `0016` pose la
#  meme valeur en contrainte, et un test exige que les deux concordent (§7.27).
BORNE_MINIATURE_OCTETS: Final[int] = 100_000

#  Les valeurs derivees des enumerations, jamais ecrites en litteral.
ETAT_AFFICHABLE: Final[str] = EtatMedia.READY.value
VARIANTE_DE_LISTE: Final[str] = TypeVarianteMedia.MINIATURE_TROMBINOSCOPE.value


@dataclasses.dataclass(frozen=True, slots=True)
class MiniatureServie:
    """La miniature a servir, et rien de l'original.

    **AUCUN CHAMP NE PORTE `media_asset.object_key`**, et c'est le point : ce
    n'est pas un oubli qu'on pourrait combler, c'est la garantie que l'original ne
    peut pas fuir par cette structure.
    """

    object_key: str
    size_bytes: int
    mime: str


#  **LES QUATRE CONDITIONS, EN UNE SEULE SOURCE, PARTAGEE PAR DEUX APPELANTS.**
#
#  La LISTE doit savoir s'il y a une photo -- sans quoi elle emettrait un chemin
#  qui rend 404. La ROUTE doit lire la variante. Si les deux portaient leurs
#  propres conditions, elles divergeraient au premier ajout : la liste
#  montrerait une photo que la route refuse, ou l'inverse -- et **la liste ne
#  peut pas resoudre la photo ligne par ligne**, ce serait le N+1 que le critere
#  de `T3` interdit.
#
#  La liste l'emploie donc en `EXISTS` (aucune multiplication de lignes), la
#  route en `SELECT`. Le fragment porte `em` : il s'attend a etre place dans une
#  requete qui expose `entity_membership AS em`.
CONDITIONS_DE_LA_MINIATURE: Final[str] = """
FROM photo_authorization AS pa
JOIN media_asset AS a
     ON a.id = pa.media_asset_id AND a.archived_at IS NULL
    AND a.state = :etat_media AND a.entity_id = em.entity_id
JOIN media_variant AS v
     ON v.media_asset_id = a.id AND v.archived_at IS NULL
    AND v.entity_id = a.entity_id AND v.variant_type = :variante
WHERE pa.person_id = em.person_id AND pa.archived_at IS NULL
  AND pa.granted_at <= :instant AND pa.withdrawn_at IS NULL
"""

#  Les parametres que le fragment exige. **DECLARES ET CONFRONTES** : un test
#  verifie que la liste les fournit tous, sinon la requete leverait a
#  l'execution et non a la lecture.
PARAMETRES_DE_LA_MINIATURE: Final[tuple[str, ...]] = ("etat_media", "variante", "instant")

#  **LA REQUETE NE SELECTIONNE PAS `a.object_key`.** Voir l'en-tete : c'est ce qui
#  rend impossible de servir l'original par distraction.
#
#  **`ORDER BY ... LIMIT 1` ET NON `one_or_none()`.** Le §12.2 n'impose AUCUNE
#  unicite sur `photo_authorization` -- `T1` l'a mesure et a fige l'absence par un
#  test -- et son couple `granted_at` / `withdrawn_at` decrit clairement une
#  histoire : accorder, retirer, accorder de nouveau. Plusieurs lignes actives
#  restent donc possibles, et toutes sont « actives » au sens du §12.2 : en servir
#  une est correct. La plus RECEMMENT accordee est la moins surprenante, et
#  l'ordre total -- `v.id` en second -- evite qu'elle change d'un appel a l'autre.
#
#  Un `one_or_none()` aurait leve un 500 sur un etat que le corpus autorise.
_MINIATURE: Final[str] = f"""
SELECT v.object_key, v.size_bytes, v.variant_format
FROM entity_membership AS em, LATERAL (
  SELECT v.object_key, v.size_bytes, v.variant_format, pa.granted_at, v.id
  {CONDITIONS_DE_LA_MINIATURE}
  ORDER BY pa.granted_at DESC, v.id
  LIMIT 1
) AS v
WHERE em.id = :appartenance AND em.entity_id = :entite
  AND em.membership_state = :etat AND em.profile_visibility = :visibilite
"""  # noqa: S608 — le seul fragment interpole est une constante de ce module


def resoudre_la_miniature(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    appartenance: uuid.UUID,
    instant: dt.datetime,
) -> MiniatureServie | None:
    """La miniature autorisee d'une appartenance, ou `None`.

    **`None` SIGNIFIE « AVATAR NEUTRE », ET COUVRE CINQ CAUSES** : pas
    d'autorisation, autorisation retiree, autorisation pas encore active, media
    non `ready`, ou aucune variante `thumbnail`. Les cinq donnent la meme
    observation cote appelant, et c'est voulu -- distinguer « il a une photo mais
    tu n'y as pas droit » de « il n'a pas de photo » apprendrait quelque chose que
    le §21.2 ne veut pas dire.

    La population est celle du trombinoscope : une photo servie pour un profil que
    la liste exclut rendrait le filtre de la liste decoratif.
    """
    ligne = connexion.execute(
        text(_MINIATURE),
        {
            "appartenance": appartenance,
            "entite": entite,
            "instant": instant,
            "etat": ETAT_LISTE,
            "visibilite": VISIBILITE_LISTEE,
            "etat_media": ETAT_AFFICHABLE,
            "variante": VARIANTE_DE_LISTE,
        },
    ).one_or_none()
    if ligne is None:
        return None
    return MiniatureServie(
        object_key=str(ligne.object_key),
        size_bytes=int(ligne.size_bytes),
        mime=_mime_de(str(ligne.variant_format)),
    )


#  Le format de la variante vers son type MIME. **DECLARE, ET NON DEVINE** : le
#  corpus ne nomme aucun format -- zero occurrence de `webp`, `avif`, `jpeg` ou
#  `png` dans les cinq documents -- et c'est le LOT 11, qui PRODUIT les variantes,
#  qui choisira. Cette table couvre les formats d'image courants pour que la route
#  puisse repondre ; un format inconnu tombe sur un type generique plutot que sur
#  une erreur, parce qu'un octet servi vaut mieux qu'une page cassee.
_MIMES: Final[dict[str, str]] = {
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "avif": "image/avif",
}
MIME_PAR_DEFAUT: Final[str] = "application/octet-stream"


def _mime_de(format_: str) -> str:
    """Le type MIME d'un format de variante, ou un type generique."""
    return _MIMES.get(format_.strip().lower(), MIME_PAR_DEFAUT)
