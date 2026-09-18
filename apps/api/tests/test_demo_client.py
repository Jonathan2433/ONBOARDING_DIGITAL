"""Garde-fous statiques du decor de demonstration client."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from types import ModuleType

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


def test_couleurs_appartiennent_aux_quatre_jetons_compris_par_le_frontend() -> None:
    module = charger_script()

    assert module.COULEURS == {
        "TECH": "bleu",
        "DATA": "rose",
        "CLOUD": "bleu-fonce",
        "PROD": "jaune",
    }


def test_compte_de_demo_emploie_le_domaine_reserve() -> None:
    module = charger_script()

    assert module.ADRESSE_ADMIN == "demo.client@exemple.test"
