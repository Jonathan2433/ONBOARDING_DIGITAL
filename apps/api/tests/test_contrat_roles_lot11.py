"""Le manifeste declare-t-il la MEME grille de roles que le code ? — LOT 11, `T3`.

CE QUE CE FICHIER EPROUVE, ET POURQUOI IL EXISTE

  `T3` pose `ROLES_D_ATTRIBUTION_FRAMEWORK` (`app/organization/perimetre.py`)
  pour la premiere fois, consommee par son ecran DANS LA MEME sous-etape —
  pas de delai comme pour `rolesCycleDeVieFramework` au LOT 9 `T14`. Le
  manifeste la declare sous `rolesAttributionFramework`, et ce test la
  confronte, DANS LES DEUX SENS, a la constante Python : le manifeste ne peut
  pas en declarer PLUS (un role qui ouvrirait un bouton que l'API refuse,
  l'avertissement faux du §7.21) ni MOINS (un role a qui on masquerait un
  bouton que l'API accorderait).

  MEME PATTERN QUE `test_contrat_roles_lot9.py`.
"""

from __future__ import annotations

import json
import pathlib

from app.organization.perimetre import ROLES_D_ATTRIBUTION_FRAMEWORK
from app.permissions.services import RoleDeLaMatrice

MANIFESTE_DU_CONTRAT = "packages/contracts/src/contrat-api.json"


def _manifeste() -> dict[str, object]:
    chemin = pathlib.Path(__file__).resolve().parents[3] / MANIFESTE_DU_CONTRAT
    return json.loads(chemin.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _declares(manifeste: dict[str, object], cle: str) -> set[RoleDeLaMatrice]:
    codes = manifeste[cle]
    assert codes, f"le manifeste ne declare aucun role pour « {cle} »"
    assert isinstance(codes, list)
    return {RoleDeLaMatrice(code) for code in codes}


def test_rolesAttributionFramework_EST_LA_MEME_GRILLE_QUE_ROLES_D_ATTRIBUTION_FRAMEWORK() -> None:
    """§20 — attribuer/retirer le Booster ou un responsable de bureau.

    `ADM-E` EXCLU, a la difference de `rolesCycleDeVieFramework` (creation,
    archivage, restauration) : `ARB-DROIT-002` le dit en toutes lettres,
    « l'administrateur d'entite ne peut pas attribuer les responsabilites
    Framework ».
    """
    manifeste = _manifeste()
    assert _declares(manifeste, "rolesAttributionFramework") == ROLES_D_ATTRIBUTION_FRAMEWORK


def test_rolesAttributionFramework_EXCLUT_ADM_E() -> None:
    """Le point precis que `T3` ajoute a la grille deja connue."""
    manifeste = _manifeste()
    assert RoleDeLaMatrice.ADMINISTRATEUR_D_ENTITE not in _declares(
        manifeste, "rolesAttributionFramework"
    )
