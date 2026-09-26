"""Qui peut LIRE, COMPLETER ou VALIDER la fiche d'arrivee — matrice §7, LOT 7.

CE QUE LA MATRICE DONNE, ET LA CELLULE QUI SURPREND

  §7, TROIS lignes rendent la MEME grille — « Consulter sa fiche non publiee »,
  « Consulter les informations preremplies » (`T2`) et « Completer photo,
  presentation et fun fact » (`T3`) :

      NEW      Soi
      DSM      —
      ESM      Support (Entite)
      BOOST    Support cercle (Cercle)
      OFFICE   —
      ADM-E    Support (Entite)
      SUPER    Support (Global)

  **`DSM` EST A TIRET ICI, ALORS QU'IL PORTE « CONSULTANTS » AILLEURS DANS LA
  MEME ANNEXE** — §8.1 « Consulter le parcours d'un collaborateur », §7
  « Modifier les informations organisationnelles ». Ce n'est pas une
  incoherence a corriger : la cellule de CETTE ligne, sur CETTE ressource, dit
  ce qu'elle dit. La confondre avec la ligne voisine accorderait un droit que
  la matrice refuse en toutes lettres — exactement le piege que le §2.1 de
  `fiche-lot-7.md` nomme pour `§8.1`.

  **`Support` N'EST NULLE PART DANS LA LEGENDE §4** — meme piege que `§7.45`/
  `§7.46` : un mot employe comme valeur, absent de la legende. Cherche partout
  dans le corpus (§7 lignes 186-187, `photo_authorization.source` du modele
  §12.2 : `self_service`/`admin_support`/`migration`), rien ne le definit
  formellement au-dela de la portee deja lisible — la MEME portee que `Entite`/
  `Cercle`/`Global` ailleurs sur la meme ligne, l'unique difference etant
  semantique : une assistance sur la fiche d'un AUTRE, jamais une portee plus
  large. Aucune regle supplementaire (motif, audit) n'est ecrite nulle part
  pour ce mot : en inventer une serait §6.5.

  **PARCE QUE LES TROIS LIGNES CONCORDENT, LE MEME CALCUL LES GOUVERNE TOUTES
  LES TROIS** — §7.27, une regle, pas trois copies qui divergeraient au premier
  ajout. `peut_completer_la_fiche_arrivee` appelle le meme helper prive que
  `peut_lire_la_fiche_arrivee`.

  **LA LIGNE « VALIDER ET PUBLIER » DIVERGE, ET C'EST LA SEULE.** `BOOST` y est
  a TIRET, alors qu'il porte « Support cercle » sur les deux lignes
  precedentes — un Booster peut aider a completer, jamais valider ni publier.
  `peut_valider_et_publier_la_fiche_arrivee` est donc une fonction SEPAREE, qui
  n'appelle PAS le helper des deux premieres lignes.

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


def _dans_le_perimetre_personnel_non_publie(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    cible_appartenance: uuid.UUID,
    cible_personne: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    instant: dt.datetime,
) -> bool:
    """La grille commune a « Consulter » (x2) et « Completer » — §7, `T2`/`T3`.

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
    """L'acteur peut-il lire la fiche d'arrivee de `cible_appartenance` ? `T2`."""
    return _dans_le_perimetre_personnel_non_publie(
        connexion,
        entite=entite,
        acteur=acteur,
        cible_appartenance=cible_appartenance,
        cible_personne=cible_personne,
        roles=roles,
        instant=instant,
    )


def peut_completer_la_fiche_arrivee(
    connexion: Connection,
    *,
    entite: uuid.UUID,
    acteur: uuid.UUID,
    cible_appartenance: uuid.UUID,
    cible_personne: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
    instant: dt.datetime,
) -> bool:
    """L'acteur peut-il completer photo/presentation/fun fact ? `T3`.

    MEME GRILLE QUE LA LECTURE — voir l'en-tete du module. `Support` et
    `Support cercle` couvrent EXACTEMENT `Entite` et `Cercle` : aucune regle
    supplementaire (motif, fenetre temporelle) n'est ecrite au corpus.
    """
    return _dans_le_perimetre_personnel_non_publie(
        connexion,
        entite=entite,
        acteur=acteur,
        cible_appartenance=cible_appartenance,
        cible_personne=cible_personne,
        roles=roles,
        instant=instant,
    )


def peut_valider_et_publier_la_fiche_arrivee(
    *,
    acteur: uuid.UUID,
    cible_personne: uuid.UUID,
    roles: frozenset[RoleDeLaMatrice],
) -> bool:
    """L'acteur peut-il valider (et donc publier) la fiche ? `T3`.

    **LA SEULE DES TROIS LIGNES DU §7 OU `BOOST` EST A TIRET.** Un Booster
    peut aider un membre de son cercle a completer sa fiche ; il ne peut ni la
    valider ni la publier a sa place — §7, ligne « Valider et publier ».
    Aucune requete SQL n'est necessaire ici : ni `Soi` ni `Support` (Entite/
    Global) ne dependent du cercle de la cible.
    """
    if acteur == cible_personne:
        return True
    return bool(roles & _ROLES_ENTITE)
