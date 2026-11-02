"""Garde-fous statiques du decor de demonstration client."""

from __future__ import annotations

import importlib.util
import pathlib
import re
import sys
from types import ModuleType
from typing import Any

RACINE = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = RACINE / "infra" / "scripts" / "preparer-demo-client.py"


def charger_script() -> ModuleType:
    specification = importlib.util.spec_from_file_location("preparer_demo_client", SCRIPT)
    assert specification is not None
    assert specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def test_personas_sont_fictifs_uniques_et_deterministes() -> None:
    module = charger_script()
    adresses = [persona.adresse for persona in module.PERSONAS]

    assert len(adresses) == 8
    assert len(set(adresses)) == len(adresses)
    assert all(adresse.startswith("demo.") for adresse in adresses)
    assert all(adresse.endswith("@exemple.test") for adresse in adresses)
    assert all(persona.presentation and persona.anecdote for persona in module.PERSONAS)


def test_les_jetons_de_la_demo_sont_des_cercles_que_le_frontend_sait_rendre() -> None:
    """Les jetons sont DERIVES du design system, jamais recopies ici.

    L'ancienne version de ce test comparait `COULEURS` a un dictionnaire ecrit en
    toutes lettres : il prouvait que le script n'avait pas change, pas que ses
    valeurs seraient comprises. Une liste recopiee vieillit au premier ajout
    (§7.27), et c'est exactement ce qui s'est produit -- les quatre etiquettes de
    couleur ont cesse d'etre des jetons valides au chantier `E4` (`DEC-682`).

    Les huit cercles de la charte sont donc RELEVES dans `jetons.css`, ou ils
    sont declares `--cercle-<cle>`. Cette feuille est une projection verifiee de
    `jetons.ts` (`jetons-css.test.ts`), donc la relever revient a relever la
    source. Un neuvieme cercle y entrerait sans que ce test ait a changer.
    """
    module = charger_script()
    feuille = (RACINE / "packages" / "ui" / "src" / "jetons.css").read_text(encoding="utf-8")
    cercles = {
        correspondance.group(1) for correspondance in re.finditer(r"--cercle-([a-z]+)\s*:", feuille)
    }

    #  SANS CE COMPTE, une expression cassee rendrait un ensemble vide et
    #  l'inclusion ci-dessous tiendrait sans rien prouver (§7.0, 3e proposition).
    assert len(cercles) == 8, f"huit cercles attendus dans jetons.css, {len(cercles)} releves"
    assert module.COULEURS, "la demonstration doit colorer au moins un cercle"
    inconnus = set(module.COULEURS.values()) - cercles
    assert not inconnus, f"jetons inconnus du design system : {sorted(inconnus)}"


def test_compte_de_demo_emploie_le_domaine_reserve() -> None:
    module = charger_script()

    assert module.ADRESSE_ADMIN == "demo.client@exemple.test"


def test_enrichissement_prepare_l_identite_attendue_par_admin_local() -> None:
    module = charger_script()

    class ConnexionEspionne:
        def __init__(self) -> None:
            self.requetes: list[str] = []
            self.parametres: list[dict[str, Any]] = []

        def execute(self, requete: Any, parametres: dict[str, Any]) -> None:
            self.requetes.append(str(requete))
            self.parametres.append(parametres)

    connexion = ConnexionEspionne()
    module.preparer_identite_administrateur(connexion)

    assert len(connexion.requetes) == 2
    assert "INSERT INTO person" in connexion.requetes[0]
    assert "ON CONFLICT (email_normalized) DO UPDATE" in connexion.requetes[0]
    assert "INSERT INTO technical_role_assignment" in connexion.requetes[1]
    assert "'SUPER_ADMIN'" in connexion.requetes[1]
    assert connexion.parametres == [
        {"adresse": "demo.client@exemple.test"},
        {"adresse": "demo.client@exemple.test"},
    ]
