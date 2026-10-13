"""Le catalogue des metiers d'une entite — LOT 9, `T14`.

CE QUE CETTE SUITE PROUVE

  Route posee en construisant l'ecran back-office (voir l'en-tete d'`app/
  people/catalogues.py`) : AUCUN role n'est distingue (une session etablie
  suffit, meme regime que le Framework), seuls les metiers ACTIFS et NON
  ARCHIVES sont rendus, et l'isolement entre entites est reel — un metier
  d'une AUTRE entite n'apparait jamais, meme code ou pas.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from conftest import HOTE_LOCAL, port_ouvert
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth.sessions import ouvrir_une_session
from app.configuration.settings import Parametres
from app.main import creer_application
from app.shared.database import moteur

ORIGINE_DE_TEST = "https://testserver"
CHEMIN_CATALOGUE = "/api/v1/entities/{code}/job-catalog"


def _exiger_postgresql(parametres: Parametres) -> None:
    if not port_ouvert(HOTE_LOCAL, parametres.POSTGRES_PORT):
        pytest.skip(
            "PostgreSQL absent — lancer `make up`. Un test ignore ne prouve rien : "
            "utiliser `make test-integration`."
        )


def _session(parametres: Parametres, personne: uuid.UUID) -> str:
    with moteur(parametres).begin() as cx:
        jeton, _ = ouvrir_une_session(
            cx,
            personne=personne,
            instant=dt.datetime.now(tz=dt.UTC),
            jours_absolus=parametres.SESSION_ABSOLUTE_DAYS,
        )
    return jeton


def _appeler(parametres: Parametres, chemin: str, jeton: str | None) -> Any:
    with TestClient(creer_application(parametres), base_url=ORIGINE_DE_TEST) as client:
        if jeton is not None:
            client.cookies.set(parametres.SESSION_COOKIE_NAME, jeton)
        return client.get(chemin)


@pytest.fixture
def decor(parametres_de_la_stack: Parametres) -> Iterator[dict[str, Any]]:
    """Une entite avec trois metiers (actif, inactif, archive), une AUTRE entite."""
    parametres = parametres_de_la_stack
    _exiger_postgresql(parametres)
    marqueur = f"t14l9{uuid.uuid4().hex[:10]}"
    r: dict[str, Any] = {"parametres": parametres}

    with moteur(parametres).begin() as cx:
        entite = cx.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
                "VALUES (:code, :nom, 'Bordeaux', 'FR', 'active', 'Europe/Paris') RETURNING id"
            ),
            {"code": f"{marqueur}-e", "nom": marqueur},
        ).scalar_one()
        r["entite"] = entite
        r["code"] = f"{marqueur}-e"

        autre_entite = cx.execute(
            text(
                "INSERT INTO entity (code, display_name, city, country_code, status, timezone) "
                "VALUES (:code, :nom, 'Nantes', 'FR', 'active', 'Europe/Paris') RETURNING id"
            ),
            {"code": f"{marqueur}-autre", "nom": f"{marqueur}-autre"},
        ).scalar_one()

        #  Le metier ACTIF de cette entite — le seul attendu dans la reponse.
        r["metier_actif"] = cx.execute(
            text(
                "INSERT INTO job_catalog (entity_id, code, label, display_order) "
                "VALUES (:e, :c, :l, 1) RETURNING id"
            ),
            {"e": entite, "c": f"{marqueur}-actif", "l": "Consultant actif"},
        ).scalar_one()

        #  Un metier INACTIF (active = false) — jamais propose.
        cx.execute(
            text(
                "INSERT INTO job_catalog (entity_id, code, label, display_order, active) "
                "VALUES (:e, :c, :l, 2, false)"
            ),
            {"e": entite, "c": f"{marqueur}-inactif", "l": "Consultant inactif"},
        )

        #  Un metier ARCHIVE — jamais propose non plus.
        cx.execute(
            text(
                "INSERT INTO job_catalog (entity_id, code, label, display_order, archived_at) "
                "VALUES (:e, :c, :l, 3, now())"
            ),
            {"e": entite, "c": f"{marqueur}-archive", "l": "Consultant archive"},
        )

        #  Un metier ACTIF d'une AUTRE entite — l'isolement doit l'exclure.
        cx.execute(
            text(
                "INSERT INTO job_catalog (entity_id, code, label, display_order) "
                "VALUES (:e, :c, :l, 1)"
            ),
            {"e": autre_entite, "c": f"{marqueur}-ailleurs", "l": "Metier d'une autre entite"},
        )

        personne = cx.execute(
            text(
                "INSERT INTO person (email, email_normalized, first_name, last_name, "
                "account_state) VALUES (:a, :a, 'Test', 'T14', 'active') RETURNING id"
            ),
            {"a": f"{marqueur}@exemple.test"},
        ).scalar_one()
        r["personne"] = personne
        cx.execute(
            text(
                "INSERT INTO entity_membership (person_id, entity_id, arrival_date, "
                "membership_state, professional_category, profile_visibility) "
                "VALUES (:p, :e, '2026-01-01', 'active', 'consultant', 'draft')"
            ),
            {"p": personne, "e": entite},
        )

    yield r


@pytest.mark.integration
def test_AUCUNE_SESSION_REND_401(decor: dict[str, Any]) -> None:
    reponse = _appeler(decor["parametres"], CHEMIN_CATALOGUE.format(code=decor["code"]), None)
    assert reponse.status_code == 401


@pytest.mark.integration
def test_UN_CODE_INCONNU_REND_404(decor: dict[str, Any]) -> None:
    jeton = _session(decor["parametres"], decor["personne"])
    reponse = _appeler(
        decor["parametres"], CHEMIN_CATALOGUE.format(code="code-totalement-inconnu"), jeton
    )
    assert reponse.status_code == 404


@pytest.mark.integration
def test_SEULS_LES_METIERS_ACTIFS_ET_NON_ARCHIVES_DE_CETTE_ENTITE_SONT_RENDUS(
    decor: dict[str, Any],
) -> None:
    """AUCUN role distingue — une session etablie suffit (meme regime que le Framework).

    **ISOLEMENT, DANS LE SENS DU REFUS** : le metier d'une autre entite,
    pourtant actif et non archive, n'apparait jamais ici.
    """
    jeton = _session(decor["parametres"], decor["personne"])
    reponse = _appeler(decor["parametres"], CHEMIN_CATALOGUE.format(code=decor["code"]), jeton)
    assert reponse.status_code == 200
    corps = reponse.json()
    identifiants = {m["identifiant"] for m in corps["metiers"]}
    assert identifiants == {str(decor["metier_actif"])}
    labels = {m["label"] for m in corps["metiers"]}
    assert labels == {"Consultant actif"}
