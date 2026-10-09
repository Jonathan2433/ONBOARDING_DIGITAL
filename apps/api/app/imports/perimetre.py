"""Qui charge un CSV — matrice §14 « Imports CSV » — LOT 9, `T6`, `MVP-L09-US004` (1/2).

UNE SEULE GRILLE, ET ELLE EST DEJA CONNUE DU DEPOT

  Le §14 donne, a la lettre : « Charger un CSV | DSM — | ESM Entite | BOOST — |
  OFFICE — | ADM-E Entite | SUPER Global ». C'est MOT POUR MOT la grille deja
  posee par `app.organization.perimetre.ROLES_DE_CYCLE_DE_VIE_FRAMEWORK` (LOT 9
  `T4`) — `ESM`/`ADM-E` dans leur entite, `SUPER` partout, les trois autres a
  tiret. Le §2 de la fiche le confirme : « Seuls ESM, ADM-E (portee Entite) et
  SUPER (portee Globale) chargent, lancent et rejouent un import ».

  **UNE COPIE PRIVEE, PAS UN IMPORT CROISE** (§7.27) : importer la constante de
  `app.organization` coupleraient deux domaines sans rapport — cercles/bureaux
  d'un cote, imports CSV de l'autre — pour une coincidence de grille qui
  pourrait diverger demain sans qu'aucun des deux modules n'en soit informe.

CE QUE CE MODULE NE REGLE PAS

  **« Previsualiser et corriger », « Valider les rapprochements », « Lancer
  l'import », « Consulter le rapport », « Rejouer les lignes rejetees »** sont
  des lignes DISTINCTES du §14, chacune avec sa propre grille (certaines
  portent `Consultants`/`Cercle` pour `DSM`/`BOOST`, que « Charger un CSV»
  n'accorde pas). Elles arrivent avec `T7` a `T10` ; les inventer ici deborderait
  le perimetre d'une sous-etape (§2, regle n°1).
"""

from __future__ import annotations

from typing import Final

from app.permissions.services import RoleDeLaMatrice

#  §14 « Charger un CSV » : ESM et ADM-E dans leur entite, SUPER partout, les
#  trois autres (DSM, BOOST, OFFICE) a tiret.
ROLES_DE_DEPOT_DE_L_IMPORT: Final[frozenset[RoleDeLaMatrice]] = frozenset(
    {
        RoleDeLaMatrice.ESM,
        RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE,
        RoleDeLaMatrice.SUPER_ADMINISTRATEUR,
    }
)
