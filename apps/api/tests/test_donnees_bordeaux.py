"""Le classeur Bordeaux devient une source de provisionnement stricte."""

from __future__ import annotations

import datetime as dt

import pytest

from app.bordeaux.donnees import (
    DonneesBordeauxInvalides,
    _consolider,
    construire_le_courriel,
)
from app.bordeaux.parcours import TACHES_DU_PARCOURS_BORDEAUX


def ligne(**modifications: object) -> dict[str, object]:
    base: dict[str, object] = {
        "Arrivée": 45_000,
        "Nom": "D'HALLUIN",
        "Prénom": "Mathéa",
        "Type": "Direction salarié",
        "Statut": "Mission",
        "Cercle": None,
        "Entité": "EXALT Bordeaux",
    }
    return {**base, **modifications}


def test_le_courriel_normalise_accents_apostrophes_espaces_et_tirets() -> None:
    assert construire_le_courriel("Mathéa", "D'HALLUIN") == ("mathea.dhalluin@exalt-company.com")
    assert construire_le_courriel("Mohammed-Sadeq", "BEN  THAIER") == (
        "mohammed-sadeq.ben-thaier@exalt-company.com"
    )


def test_change_rejoint_projet() -> None:
    population = _consolider(
        [
            ligne(
                Nom="EXEMPLE",
                Prénom="Alice",
                Type="Consultant",
                Cercle="Cercle CHANGE",
            )
        ],
        verifier_responsabilites=False,
    )
    assert population.employes[0].cercle == "PROJET"


def test_la_direction_reste_identifiable_comme_dg() -> None:
    population = _consolider([ligne()], verifier_responsabilites=False)

    assert population.employes[0].categorie_professionnelle == "dg"


def test_un_doublon_ne_fabrique_pas_une_date_d_arrivee() -> None:
    population = _consolider(
        [
            ligne(Nom="CADIX", Prénom="Mila", Arrivée=46_125, Type="Consultant"),
            ligne(Nom="CADIX", Prénom="Mila", Arrivée=46_132, Type="Consultant"),
        ],
        verifier_responsabilites=False,
    )
    assert population.employes[0].date_d_arrivee is None
    assert population.avertissements == (
        "mila.cadix@exalt-company.com : 2 lignes fusionnees, date laissee vide",
    )


def test_un_doublon_metier_contradictoire_est_refuse() -> None:
    with pytest.raises(DonneesBordeauxInvalides, match="doublon contradictoire"):
        _consolider(
            [
                ligne(Nom="CADIX", Prénom="Mila", Type="Consultant"),
                ligne(Nom="CADIX", Prénom="Mila", Type="Digital Sales Manager"),
            ],
            verifier_responsabilites=False,
        )


def test_la_date_excel_est_convertie_sans_perdre_le_jour() -> None:
    population = _consolider(
        [ligne(Nom="EXEMPLE", Prénom="Alice", Type="Consultant", Arrivée=45_000)],
        verifier_responsabilites=False,
    )
    assert population.employes[0].date_d_arrivee == dt.date(2023, 3, 15)


def test_le_parcours_bordeaux_reproduit_les_six_phases_et_les_28_taches() -> None:
    assert len(TACHES_DU_PARCOURS_BORDEAUX) == 28
    assert {tache.echeance_jours for tache in TACHES_DU_PARCOURS_BORDEAUX} == {
        -30,
        0,
        1,
        2,
        4,
        30,
    }
    assert len({tache.code for tache in TACHES_DU_PARCOURS_BORDEAUX}) == 28
    assert all(len(tache.code) <= 64 for tache in TACHES_DU_PARCOURS_BORDEAUX)


def test_le_parcours_bordeaux_utilise_le_vocabulaire_booster() -> None:
    rencontre = next(
        tache for tache in TACHES_DU_PARCOURS_BORDEAUX if tache.code == "RENCONTRE_BOOSTER_CERCLE"
    )
    assert "Booster" in rencontre.titre
    assert "Représentant" not in rencontre.titre
