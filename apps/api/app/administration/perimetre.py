"""Qui voit quoi sur le tableau de bord administratif — cahier §10.8, §15.1.

LOT 9, sous-étape `T5`, story `MVP-L09-US001`.

AUCUNE LIGNE DE MATRICE NE S'APPELLE « TABLEAU DE BORD », ET C'EST MESURÉ

  Zéro occurrence de « tableau de bord » ou « dashboard » dans
  `MATRICE_ROLES_PERMISSIONS_EXALT.md`. Ce que le cahier §10.8 nomme
  (« profils actifs », « arrivées futures », « onboardings actifs », « tâches
  en retard », « profils incomplets », « derniers problèmes d'import CSV »)
  est gouverné, pièce par pièce, par des grilles déjà écrites ailleurs :

    - §15.1 « Reporting et exports » donne, pour « Consulter les compteurs »,
      « Consulter les profils incomplets » et « Consulter les arrivées à
      30 jours » : `DSM` Consultants, `ESM` Entité, `BOOST` Cercle, `OFFICE`
      —, `ADM-E` Entité, `SUPER` Global — EXACTEMENT la même grille pour les
      trois lignes ;
    - §8.1 « Consulter les tâches en retard » porte sa PROPRE grille, déjà
      codée par `T12` du LOT 7 (`app.onboarding.perimetre.
      resoudre_le_perimetre_du_suivi`) — un `Soi` en plus pour `NEW`, que ce
      module ne reproduit PAS : voir plus bas.

  « Profils actifs », « arrivées futures » et « onboardings actifs » ne sont
  nommés dans AUCUNE grille à eux seuls. Ils rejoignent le groupe du §15.1 :
  ce sont des COMPTEURS de la même nature que « Consulter les compteurs », et
  leur traiter une grille différente sans qu'aucune ligne ne le demande
  serait inventer une distinction que le corpus ne fait pas.

POURQUOI CE MODULE N'A PAS DE `SOI`, CONTRAIREMENT À CELUI DU SUIVI

  `resoudre_le_perimetre_du_suivi` dégrade vers `Soi` pour que N'IMPORTE QUI
  d'authentifié voie SES PROPRES tâches en retard — c'est la ligne `NEW` du
  §8.1. Aucune ligne du §15.1 ne porte de colonne `EMP` ni `NEW` : le
  tableau de bord est une vue D'ADMINISTRATION, pas une vue personnelle, et
  « nombre de profils incomplets dans l'entité » n'a pas de sens rapporté à
  « soi ». L'absence de `Soi` ici n'est donc pas un oubli, c'est la lecture
  du §15.1 à la lettre.

`OFFICE` EST À TIRET, ET C'EST LA MÊME CELLULE SUR LES TROIS LIGNES

  Le §15.1 met `OFFICE` à tiret sur « compteurs », « détail onboarding » et
  « profils incomplets » — troisième occurrence du piège déjà mesuré au
  LOT 5 et au LOT 7 (`fiche-lot-7.md` §2.1) : un rôle qui porte un droit réel
  ailleurs (la galerie et le contenu de son bureau) peut rester à tiret ici
  sans contradiction, les deux lignes ne régissant pas la même ressource.
"""

from __future__ import annotations

import enum
from typing import Final

from app.permissions.services import RoleDeLaMatrice

#  §15.1, les TROIS lignes concordantes : DSM, ESM, BOOST, ADM-E, SUPER —
#  jamais OFFICE, jamais EMP/NEW (aucune colonne pour eux sur ces lignes).
ROLES_DU_TABLEAU_DE_BORD: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.DSM,
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.BOOSTER,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)

#  Seuls ces trois rôles lancent, valident ou consultent un import — fiche
#  LOT 9 §2 « Permissions CSV ». `DSM`/`BOOST` y « valident dans leur
#  périmètre », ce qui désigne l'écran de l'import EN COURS (`T7`/`T8`),
#  jamais une synthèse des imports passés : aucune ligne du corpus ne leur
#  accorde cette lecture-ci, qui reste donc refusée par défaut (§2.5).
ROLES_DE_LECTURE_DES_IMPORTS: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)


class PerimetreDuTableauDeBord(enum.Enum):
    """§15.1 : TROIS portées, jamais une combinaison — la plus large détenue."""

    ENTITE = "entite"
    CONSULTANTS = "consultants"
    CERCLE = "cercle"


def resoudre_le_perimetre_du_tableau_de_bord(
    *, roles: frozenset[RoleDeLaMatrice]
) -> PerimetreDuTableauDeBord | None:
    """§15.1, littéralement : `ESM`/`ADM-E`/`SUPER` → Entité, `DSM` →
    Consultants, `BOOST` → Cercle, tout le reste (dont `OFFICE`) → refusé.

    `None` est le refus — jamais un `Soi` qui n'existe pas sur cette grille.
    La route est déjà gardée par `ROLES_DU_TABLEAU_DE_BORD` : ce `None` est
    un filet, pas un chemin atteignable en pratique.
    """
    if roles & frozenset(
        {
            RoleDeLaMatrice.ESM,
            RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
            RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
        }
    ):
        return PerimetreDuTableauDeBord.ENTITE
    if RoleDeLaMatrice.DSM in roles:
        return PerimetreDuTableauDeBord.CONSULTANTS
    if RoleDeLaMatrice.BOOSTER in roles:
        return PerimetreDuTableauDeBord.CERCLE
    return None
