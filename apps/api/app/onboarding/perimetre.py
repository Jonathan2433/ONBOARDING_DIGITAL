"""Qui peut LIRE la fiche d'arrivee d'un collaborateur — matrice §7, LOT 7 `T2`.

CE QUE LA MATRICE DONNE, ET LA CELLULE QUI SURPREND

  §7, lignes « Consulter sa fiche non publiee » et « Consulter les informations
  preremplies » — les DEUX rendent la MEME grille :

      NEW      Soi
      DSM      —
      ESM      Entite
      BOOST    Cercle
      OFFICE   —
      ADM-E    Entite
      SUPER    Global

  **`DSM` EST A TIRET ICI, ALORS QU'IL PORTE « CONSULTANTS » AILLEURS DANS LA
  MEME ANNEXE** — §8.1 « Consulter le parcours d'un collaborateur », §7
  « Modifier les informations organisationnelles ». Ce n'est pas une
  incoherence a corriger : la cellule de CETTE ligne, sur CETTE ressource, dit
  ce qu'elle dit. La confondre avec la ligne voisine accorderait un droit que
  la matrice refuse en toutes lettres — exactement le piege que le §2.1 de
  `fiche-lot-7.md` nomme pour `§8.1`.

`NEW` N'EST PAS UN ROLE DE `RoleDeLaMatrice`

  « Soi » n'est pas une portee organisationnelle, c'est une egalite entre
  l'acteur et la personne de la cible. Elle se vérifie donc AVANT toute
  resolution de role, sans avoir besoin d'interroger `resoudre_les_permissions`.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Final

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.permissions.services import RoleDeLaMatrice

#  §8.4 : le type qui porte le cercle du Booster. Litteral, comme
#  `app/permissions/perimetre.py` le fait deja pour le meme type — une
#  dependance croisee vers un module prive d'un autre domaine serait pire
#  qu'une constante repetee (§7.27, l'un ou l'autre cout, jamais les deux).
_TYPE_BOOSTER: Final[str] = "BOOSTER"

#  §7 « Cercle » : un membre — principal OU secondaire — du cercle dont
#  l'acteur est Booster. Aucune ligne du §7 ne restreint au seul principal,
#  contrairement a la lecture ECRITE du §6.1 pour d'autres actions.
_MEMBRE_DU_CERCLE_DU_BOOSTER: Final[str] = """
SELECT 1
FROM framework_responsibility_assignment AS fra
JOIN circle_membership AS cm
  ON cm.circle_id = fra.circle_id AND cm.entity_id = fra.entity_id
WHERE fra.person_id = :acteur AND fra.entity_id = :entite
  AND fra.responsibility_type = :type_booster
  AND fra.archived_at IS NULL AND fra.period @> :instant
  AND cm.entity_membership_id = :cible
  AND cm.archived_at IS NULL AND cm.period @> :instant
"""

_ROLES_ENTITE: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)


def peut_lire_la_fiche_arrivee(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    cible_appartenance: uuid.UUID,
    cible_personne: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    instant: dt.datetime,
) -> bool:
    """L'acteur peut-il lire la fiche d'arrivee de `cible_appartenance` ?

    `roles` vient de `resoudre_les_permissions`, donc le §5.1 est deja
    applique : hors de son entite principale une personne n'a que `EMP`, qui
    n'ouvre rien ici (§7 le met a tiret, comme `DSM` et `OFFICE`).
    """
    if acteur == cible_personne:
        return True
    if roles & _ROLES_ENTITE:
        return True
    if RoleDeLaMatrice.BOOSTER in roles:
        ligne = connexion.execute(
            text(_MEMBRE_DU_CERCLE_DU_BOOSTER),
            {
                "acteur": acteur,
                "entite": entite,
                "cible": cible_appartenance,
                "type_booster": _TYPE_BOOSTER,
                "instant": instant,
            },
        ).first()
        if ligne is not None:
            return True
    return False
