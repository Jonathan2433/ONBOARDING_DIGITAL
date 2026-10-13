"""Le manifeste declare-t-il les MEMES grilles de roles que le code ? — LOT 9, `T14`.

CE QUE CE FICHIER EPROUVE, ET POURQUOI IL EXISTE

  `T14` est le PREMIER ecran a consommer cinq grilles de roles posees par `T2`
  a `T11` sans jamais avoir eu de consommateur avant lui (meme situation que
  `rolesAdministration` au LOT 4, `rolesCycleDeVie` au LOT 5 : la grille vit
  en Python depuis la sous-etape qui l'a ecrite, et n'entre dans le manifeste
  — la source unique de `DEC-492` — qu'au moment ou un ecran en a besoin).

  Chaque grille est ici CONFRONTEE, DANS LES DEUX SENS, a la constante Python
  qu'elle doit refleter : le manifeste ne peut pas en declarer PLUS (un role
  qui ouvrirait un bouton que l'API refuse, l'avertissement faux du §7.21) ni
  MOINS (un role a qui on masquerait un bouton que l'API accorderait).

  MEME PATTERN QUE `test_archivage.py::test_le_MANIFESTE_declare_la_MEME_
  grille_que_le_service` — lecture du manifeste, conversion de chaque code en
  `RoleDeLaMatrice` (leve si un code est inconnu, plutot que de rendre un
  ecran inerte en silence), egalite d'ensemble.
"""

from __future__ import annotations

import json
import pathlib

from app.administration.perimetre import ROLES_DU_TABLEAU_DE_BORD
from app.imports.decisions import ROLES_DE_VALIDATION_DES_RAPPROCHEMENTS
from app.imports.perimetre import ROLES_DE_DEPOT_DE_L_IMPORT
from app.organization.perimetre import ROLES_DE_CYCLE_DE_VIE_FRAMEWORK
from app.permissions.perimetre import ROLES_D_ECRITURE
from app.permissions.services import RoleDeLaMatrice

#  Le manifeste du contrat, source unique de `DEC-492` — lue par TypeScript ET
#  par Python. Le chemin est relatif a la racine du depot, comme dans
#  `test_archivage.py`.
MANIFESTE_DU_CONTRAT = "packages/contracts/src/contrat-api.json"


def _manifeste() -> dict[str, object]:
    chemin = pathlib.Path(__file__).resolve().parents[3] / MANIFESTE_DU_CONTRAT
    return json.loads(chemin.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _declares(manifeste: dict[str, object], cle: str) -> set[RoleDeLaMatrice]:
    codes = manifeste[cle]
    assert codes, f"le manifeste ne declare aucun role pour « {cle} »"
    assert isinstance(codes, list)
    #  La conversion ajoute une exigence utile : un code qui ne serait pas un
    #  role connu leve ICI, au lieu de rendre l'ecran inerte en silence.
    return {RoleDeLaMatrice(code) for code in codes}


def test_rolesEcriture_EST_LA_MEME_GRILLE_QUE_ROLES_D_ECRITURE() -> None:
    """`T2`/`T3`/`T11` — creer, transferer un collaborateur, en masse.

    Cinq roles : DSM et BOOST y figurent, mais `resoudre_l_autorisation_de_
    creation` resserre encore pour chacun d'eux — cette grille ne sert qu'a ne
    pas proposer le formulaire a qui n'a AUCUN droit d'ecriture nulle part.
    """
    assert _declares(_manifeste(), "rolesEcriture") == ROLES_D_ECRITURE


def test_rolesCycleDeVieFramework_EST_LA_MEME_GRILLE_QUE_ROLES_DE_CYCLE_DE_VIE_FRAMEWORK() -> None:
    """`T4` — archiver et restaurer un cercle ou un bureau.

    **DECLAREE SEPAREMENT DE `rolesCycleDeVie`** (le profil, LOT 5) : les deux
    portent aujourd'hui les memes trois roles, et c'est une coincidence, pas
    une derivation — les fusionner ferait suivre l'une quand la matrice
    change l'autre, en silence (§7.27).
    """
    manifeste = _manifeste()
    assert _declares(manifeste, "rolesCycleDeVieFramework") == ROLES_DE_CYCLE_DE_VIE_FRAMEWORK
    assert "rolesCycleDeVie" in manifeste
    assert "rolesCycleDeVieFramework" in manifeste


def test_rolesTableauDeBord_EST_LA_MEME_GRILLE_QUE_ROLES_DU_TABLEAU_DE_BORD() -> None:
    """`T5` — le tableau de bord administratif, `US001`.

    OFFICE a tiret : la grille reutilise le §15.1 « Reporting et exports »,
    aucune ligne de la matrice ne s'appelant « tableau de bord ».
    """
    assert _declares(_manifeste(), "rolesTableauDeBord") == ROLES_DU_TABLEAU_DE_BORD


def test_rolesDepotDeLImport_EST_LA_MEME_GRILLE_QUE_ROLES_DE_DEPOT_DE_L_IMPORT() -> None:
    """`T6`/`T9`/`T10` — charger, lancer, rejouer un import CSV.

    Trois roles seulement : DSM et BOOST valident un rapprochement dans leur
    perimetre (`rolesValidationDesRapprochements`) sans pouvoir deposer ni
    lancer — deux grilles distinctes, jamais fusionnees.
    """
    manifeste = _manifeste()
    assert _declares(manifeste, "rolesDepotDeLImport") == ROLES_DE_DEPOT_DE_L_IMPORT
    assert "rolesValidationDesRapprochements" in manifeste
    assert "rolesDepotDeLImport" in manifeste


def test_rolesValidationDesRapprochements_EST_LA_MEME_GRILLE_QUE_LE_SERVICE() -> None:
    """`T8` — rapprocher un client et enregistrer une decision d'import.

    Quatre roles : DSM s'y ajoute par rapport a `rolesDepotDeLImport`. Le
    SERVICE resserre encore pour deux types precis (`person_merge`,
    `profile_reactivation`, refuses a tout DSM) — cette liste ne le distingue
    pas, elle sert seulement a proposer le formulaire.
    """
    assert (
        _declares(_manifeste(), "rolesValidationDesRapprochements")
        == ROLES_DE_VALIDATION_DES_RAPPROCHEMENTS
    )
