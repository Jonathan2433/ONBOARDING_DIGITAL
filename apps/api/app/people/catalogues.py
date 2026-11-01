"""Le catalogue des métiers d'une entité, en LECTURE — LOT 9, `T14`.

POURQUOI CE MODULE EXISTE, ET POURQUOI SEULEMENT MAINTENANT

  `job_catalog` (modèle §6.3, LOT 2) existe depuis le début du projet, et
  `job_catalog_id` était un champ obligatoire de `POST …/people` (`T2`) et de
  `POST …/changement-d-entite` (`T3`) depuis l'ouverture du LOT 9 — mais
  AUCUNE route ne sert jamais la LISTE des métiers d'une entité, mesuré sur
  les 85 chemins du manifeste avant `T14`. `apps/web/src/api/trombinoscope.ts`
  le nommait déjà, en tête de fichier, depuis le LOT 5 : « les métiers,
  clients et DSM arriveront avec le back-office du LOT 9 ».

  **DEPUIS `DEC-675` (LOT 11 `T5`), LE MÉTIER EST REDEVENU FACULTATIF** sur
  ces deux routes et sur le transfert en masse — ce module reste utile tel
  quel : un formulaire qui laisse encore le choix d'en renseigner un a
  toujours besoin de connaître les options.

  `T14` est le premier écran qui a BESOIN de cette liste — un formulaire ne
  peut pas proposer un choix dont il ne connaît pas les options (même constat
  que `CriteresDeRecherche` du trombinoscope) — et pose donc cette lecture,
  exactement comme `T14` du LOT 7 avait posé `GET …/templates` en construisant
  son propre écran.

CE QUE CE MODULE NE FAIT JAMAIS

  Aucune écriture : `job_catalog` est alimenté ailleurs (hors périmètre de ce
  lot, aucune story ne le nomme). Seuls les métiers ACTIFS et NON ARCHIVÉS
  sont rendus — un métier retiré du catalogue ne doit pas être proposable à
  une création ou un changement d'entité, bien qu'il reste lisible par son
  identifiant pour les lignes qui le portent déjà.
"""

from __future__ import annotations

import dataclasses
import uuid
from typing import Final

from sqlalchemy import text
from sqlalchemy.engine import Connection


@dataclasses.dataclass(frozen=True, slots=True)
class MetierDuCatalogue:
    """Un métier configurable, actif et non archivé, d'une entité."""

    identifiant: uuid.UUID
    code: str
    label: str


_LISTER_LE_CATALOGUE_DES_METIERS: Final = text(
    """
    SELECT id, code, label
      FROM job_catalog
     WHERE entity_id = :entite AND active = true AND archived_at IS NULL
     ORDER BY display_order, label
    """
)


def lister_le_catalogue_des_metiers(
    connexion: Connection, *, entite: uuid.UUID
) -> list[MetierDuCatalogue]:
    """Les métiers ACTIFS d'une entité, triés comme le §6.3 l'ordonne (`display_order`)."""
    lignes = connexion.execute(_LISTER_LE_CATALOGUE_DES_METIERS, {"entite": entite}).all()
    return [
        MetierDuCatalogue(identifiant=ligne.id, code=ligne.code, label=ligne.label)
        for ligne in lignes
    ]
